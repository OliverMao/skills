#!/usr/bin/env python3
"""
vision-augment / describe.py
=============================
给「非多模态模型」赋予视觉能力：调用一个多模态（视觉）模型，
把一张图片转换成结构化的「描述先验」文本，供当前文本模型参考。

用法（OpenAI 兼容接口，默认）：
    python3 describe.py <图片路径或URL> [选项]

示例：
    python3 describe.py screenshot.png
    python3 describe.py /data/img/logo.png --mode detailed
    python3 describe.py https://example.com/x.png --mode ocr
    python3 describe.py frame.jpg --mode detailed --max-size 768
    python3 describe.py ui.png --mode detailed --qa "这个按钮是什么颜色？"

选项：
    --mode {detailed|quick|ocr|layout|caption}
        detailed   (默认) 详尽描述：主体、颜色、布局、文字、背景、风格
        quick      快速摘要，适合大致了解画面
        ocr        只输出图像中的文字
        layout     只输出区域/布局结构（适合 UI、图表、页面截图）
        caption    一句话标题/图注
    --qa "问题"    让视觉模型针对图片回答指定问题（附加语义，不评估图片质量）
    --max-size N   先把图片等比缩放到最长边不超过 N 像素（默认 1024），
                   省 token、兼容小视觉模型；0 表示不缩放
    --base64       强制用 base64 内联上传（兼容不支持 image_url 的网关）
    --json         输出原始 JSON 响应
    --detail       传给视觉模型的 detail 参数（auto/low/high）

配置（智能）：命令行 --base/--model/--api-key > 环境变量 > 配置文件 > 交互询问并持久化
    VISION_API_BASE / VISION_MODEL / VISION_API_KEY : 环境变量
    配置文件                                : ~/.config/vision-augment/settings.json
    首次未配置时，脚本会交互询问并把配置持久化，后续直接复用。
    用 --base/--model 显式传入可作为临时覆盖，不写盘。

退出码：
    0  成功（描述写入 stdout；同时写入 描述先验 到 ./.pi/tmp/vision_cache/<hash>.txt）
    2  参数错误
    3  图片读取/下载失败
    4  视觉 API 调用失败
"""

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# 默认缓存/暂存目录：相对脚本所在目录解析(skill 根)，而非依赖调用方 cwd。
_SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = _SCRIPT_DIR.parent / ".pi" / "tmp" / "vision_cache"
DEFAULT_STAGE_DIR = _SCRIPT_DIR.parent / ".pi" / "tmp" / "image"

try:
    from PIL import Image
    HAVE_PIL = True
except Exception:  # pragma: no cover
    HAVE_PIL = False

try:
    import requests
    HAVE_REQUESTS = True
except Exception:  # pragma: no cover
    HAVE_REQUESTS = False


# ---------------------------------------------------------------- helpers ---
import config as _cfg

class VisionError(Exception):
    pass


def fetch_image_bytes(src: str) -> tuple[bytes, str]:
    """返回 (图片二进制, 来源描述)。支持本地文件与 http(s) URL。

    对本地文件会校验其是否为受支持的图片格式；非图片会报错，避免把
    任意文件/二进制当作图片处理。
    """
    if src.startswith(("http://", "https://")):
        # URL 由视觉模型网关直接拉取，这里只须保证能下载
        if not HAVE_REQUESTS:
            with urllib.request.urlopen(src, timeout=60) as resp:
                data = resp.read()
        else:
            r = requests.get(src, timeout=120)
            r.raise_for_status()
            data = r.content
        if not data:
            raise VisionError(f"URL 未返回内容: {src}")
        return data, src
    p = Path(src)
    if not p.exists():
        raise VisionError(f"文件不存在: {src}")
    data = p.read_bytes()
    # 严格校验是图片(magic)，避免把非图片文件当图片处理
    if not _looks_like_image(data, allow_default=False):
        stage = os.environ.get("VISION_STAGE_DIR") or str(DEFAULT_STAGE_DIR)
        raise VisionError(
            f"文件不是受支持的图片格式: {src}\n"
            f"提示: 请先把图片保存到项目缓存目录({stage})再传入，"
            f"不要直接把日志/文本/其他文件当图片传入。"
        )
    return data, str(p)


def _looks_like_image(data: bytes, allow_default: bool = True) -> bool:
    """用文件头 magic 判断是否为已知图片格式。allow_default 用于 http URL(难判断)"。"""
    for magic in (
        b"\xff\xd8\xff",       # JPEG
        b"\x89PNG\r\n\x1a\n",  # PNG
        b"GIF8",                # GIF
        b"RIFF",                # WEBP (RIFF....WEBP)
        b"BM",                  # BMP
    ):
        if data.startswith(magic):
            return True
    if allow_default:
        # 对 URL 内容兜底：非空白即认为是图片(由视觉 API 最终裁决)
        return bool(data.strip())
    return False


def to_data_url(b64: str, mime: str) -> str:
    return f"data:{mime};base64,{b64}"


def guess_mime(data: bytes) -> str:
    for magic, mime in (
        (b"\xff\xd8\xff", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"GIF8", "image/gif"),
        (b"RIFF", "image/webp"),
        (b"BM", "image/bmp"),
    ):
        if data.startswith(magic):
            return mime
    return "image/png"


def shrink(data: bytes, mime: str, max_size: int, out_format: str = "PNG") -> tuple[bytes, str]:
    """等比缩放到最长边 <= max_size，返回 (编码后bytes, 输出mime)。"""
    if not HAVE_PIL:
        if max_size:
            print("[warn] 未安装 Pillow，跳过缩放（pip install pillow）", file=sys.stderr)
        return data, mime
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    if max_size:
        w, h = img.size
        longest = max(w, h)
        if longest > max_size:
            scale = max_size / longest
            img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    if out_format.upper() == "JPEG":
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue(), "image/jpeg"
    img.save(buf, format="PNG")
    return buf.getvalue(), "image/png"


# ------------------------------------------------------------- prompt text ---
MODE_PROMPTS = {
    "detailed": (
        "请详细描述这张图片，作为给一个「看不见图片的文本模型」的视觉先验。"
        "请按照以下维度组织输出：\n"
        "1) 画面主体：图中主要是什么对象/场景/人物，在做什么；\n"
        "2) 布局构图：元素的位置关系、层次、前景/背景；\n"
        "3) 颜色与风格：主色调、明暗、艺术风格/材质；\n"
        "4) 文字内容：把图中所有可见文字原样抄录，并说明位置；\n"
        "5) 细节线索：任何对下游任务有意义的小细节、图标、状态、异常。\n"
        "用简洁的条目化中文描述，客观、具体、不臆测。"
    ),
    "quick": (
        "用 2-3 句话概括这张图：主要是什么、包含哪些关键元素、大致内容。"
        "作为给看不见图的文本模型的快速视觉摘要。"
    ),
    "ocr": (
        "只做 OCR：把图片中出现的所有文字按出现顺序原样输出，"
        "每一段前面标注它在图中大致的位置（如顶部/底部/左上角等）。"
        "不要添加任何解释或评价。"
    ),
    "layout": (
        "这张图很可能是 UI 界面/网页/图表截图的截图。请只描述其布局结构：\n"
        "按从上到下、从左到右列出主要的区块/控件（导航、侧栏、卡片、按钮、表格、图表等），"
        "每个区块注明其类型与内容要点。用于帮助看不见图的模型重构界面逻辑。"
    ),
    "caption": (
        "为这张图写一句话标题/图注，准确概括其核心内容。只输出这一句话。"
    ),
}

DEFAULT_PROMPT_TEMPLATE = (
    "请详细描述这张图片，作为给一个「看不见图片的文本模型」的视觉先验。\n"
    "内容包括：画面主体、布局构图、颜色风格、图中的全部文字、以及任何细节线索。\n"
    "用条目化的中文客观描述。"
)


def build_prompt(mode: str, qa: str | None) -> str:
    if qa:
        base = MODE_PROMPTS.get(mode, DEFAULT_PROMPT_TEMPLATE)
        return (
            f"{base}\n\n额外问题（请优先结合图片内容回答）：\n{qa}"
        )
    return MODE_PROMPTS.get(mode, DEFAULT_PROMPT_TEMPLATE)


# ------------------------------------------------------------- API caller ---
def call_vision_openai(cfg: dict, args) -> dict:
    """通过 OpenAI 兼容的 /v1/chat/completions 调用视觉模型。cfg 为合并后的配置。"""
    base = _cfg.norm_base(cfg["api_base"])
    key = cfg.get("api_key", "dummy") or "dummy"
    url = base + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    data, src = fetch_image_bytes(args.input)
    mime = guess_mime(data)
    max_size = args.max_size if args.max_size is not None else int(cfg.get("max_size", 1024))
    if max_size:
        data, mime = shrink(data, mime, max_size,
                            "JPEG" if mime in ("image/jpeg", "image/webp") else "PNG")

    if args.base64 or src.startswith(("data:", "http://", "https://")):
        if args.base64:
            data_url = to_data_url(base64.b64encode(data).decode(), mime)
        else:
            # 直接传 URL（若来自 http 源，保存原始 URL；本地文件则内联）
            if src.startswith("http"):
                data_url = src
            else:
                data_url = to_data_url(base64.b64encode(data).decode(), mime)
    else:
        data_url = to_data_url(base64.b64encode(data).decode(), mime)

    image_content = {"type": "image_url", "image_url": {"url": data_url}}
    if args.detail:
        image_content["image_url"]["detail"] = args.detail

    payload = {
        "model": cfg["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    image_content,
                    {"type": "text", "text": build_prompt(args.mode, args.qa)},
                ],
            }
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }

    if HAVE_REQUESTS:
        r = requests.post(url, headers=headers, json=payload, timeout=args.timeout)
        if r.status_code >= 400:
            raise VisionError(f"API {r.status_code}: {r.text[:800]}")
        return r.json()
    # 退化为 urllib
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise VisionError(f"API {e.code}: {e.read().decode()[:800]}")


def extract_text(resp: dict) -> str:
    """从响应中提取最终答案文本，并剔除模型思考过程（reasoning）内容。"""
    try:
        msg = resp["choices"][0]["message"]
    except Exception:
        return json.dumps(resp, ensure_ascii=False, indent=2)

    content = msg.get("content") or ""
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return clean_reasoning(text)


def clean_reasoning(text: str) -> str:
    """
    从模型返回文本中剔除「思考过程」内容，只保留最终答案。

    覆盖两类来源：
      1. content 内用标签包裹的思考区，如 <thinking>…</thinking>、[reasoning]…[/reasoning] 等；
      2. 思考区恰好位于开头、后续是正式答案的情况（无闭合标签）会尽量剥离。

    标签兼容 < > 与 [ ] 两种括号形式，且允许开/闭括号形式不同（如 [thinking]>...</thinking>）。
    """
    if not text:
        return text

    # 常见思考标签名
    tag_names = [
        "thinking", "reasoning", "thought", "analysis",
        "cot", "internal", "chain_of_thought", "scratchpad",
    ]

    def _find_closer(l_text: str, start: int, name: str) -> int | None:
        """从 start 起找最近的闭合标签（/name> 或 /name]，两种括号形式），返回索引或 None。"""
        best = None
        for cc in (f"/{name}>", f"/{name}]"):
            j = l_text.find(cc, start)
            if j != -1 and (best is None or j < best):
                best = j
        return best

    lowered = text.lower()
    changed = True
    while changed:
        changed = False
        for name in tag_names:
            # 该标签的两种开括号形式
            for open_tag in (f"<{name}>", f"[{name}]"):
                while True:
                    i = lowered.find(open_tag)
                    if i == -1:
                        break
                    j = _find_closer(lowered, i + len(open_tag), name)
                    if j is None:
                        # 无闭合：剥离从开标签到文本末尾的整段思考
                        text = text[:i]
                    else:
                        text = text[:i] + text[j + len(f"/{name}>"):]
                    lowered = text.lower()
                    changed = True
    return text.strip()



def main() -> int:
    p = argparse.ArgumentParser(description="call a vision model to describe an image")
    p.add_argument("input", help="image path or URL")
    p.add_argument("-m", "--mode", default="detailed",
                   choices=["detailed", "quick", "ocr", "layout", "caption"])
    p.add_argument("--qa", default=None, help="an extra question to answer about the image")
    p.add_argument("--max-size", type=int, default=None,
                   help="最长边像素上限；0=不缩放；默认 1024")
    p.add_argument("-b", "--base", default=None, help="OpenAI 兼容接口地址(临时覆盖，不写盘)")
    p.add_argument("--api-key", default=None, help="API Key(临时覆盖)")
    p.add_argument("--model", default=None, help="视觉模型名(临时覆盖)")
    p.add_argument("--detail", default=None, choices=["auto", "low", "high"])
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--max-tokens", type=int, default=1500)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--base64", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("-y", "--yes", dest="non_interactive", action="store_true",
                   help="非交互：配置缺失时直接报错而不询问")
    args = p.parse_args()

    # ── 智能配置：解析(命令行 > 环境变量 > 配置文件)，缺失则询问并持久化 ──
    cli = {
        "api_base": args.base,
        "model": args.model,
        "api_key": args.api_key,
        "non_interactive": args.non_interactive,
    }
    cfg = _cfg.resolve_config(cli)
    if _cfg.need_interactive(cfg, cli):
        cfg = _cfg.ask_and_persist(cfg)
        # 询问后仍可能缺，交由下方校验
    if not _cfg.is_configured(cfg):
        print(
            "[error] 视觉模型未配置完整。请运行 `python3 scripts/setup.py --set` "
            "进行交互配置，或设置 VISION_API_BASE / VISION_MODEL 环境变量。",
            file=sys.stderr,
        )
        return 2

    try:
        resp = call_vision_openai(cfg, args)
        if args.as_json:
            print(json.dumps(resp, ensure_ascii=False, indent=2))
            return 0
        text = extract_text(resp)

        # 同时把描述缓存到 cache_dir/<hash>.txt，便于再次引用
        try:
            raw, _ = fetch_image_bytes(args.input)
            h = hashlib.sha256(raw).hexdigest()[:16]
            cache_dir = Path(cfg.get("cache_dir") or DEFAULT_CACHE_DIR).expanduser()
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / f"{h}.txt").write_text(text, encoding="utf-8")
        except Exception:
            pass

        print(text)
        return 0
    except VisionError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 4
    except Exception as e:  # noqa: BLE001
        print(f"[error] 未预期异常: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
