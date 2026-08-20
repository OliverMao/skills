#!/usr/bin/env python3
"""
vision-augment / config.py
==========================
智能配置管理：统一处理视觉模型配置的「查询 -> 询问 -> 持久化」。

配置来源优先级（从高到低）：
  1. 命令行参数（--base / --model / --api-key） —— 临时，不持久化
  2. 环境变量 VISION_API_BASE / VISION_API_KEY / VISION_MODEL / VISION_CONFIG / VISION_MAX_SIZE / VISION_CACHE_DIR
  3. 持久化配置文件（默认 ~/.config/vision-augment/settings.json）

规则：
  - 若配置缺失，describe.py 会**交互式询问用户**并写入配置文件（持久化），下次直接复用。
  - 显式用 --base / --model 传入的视为临时覆盖，不写盘。
"""

import json
import os
import sys
from pathlib import Path


def norm_base(base: str) -> str:
    """规范化 OpenAI 兼容接口地址：补全协议与 /v1 后缀。"""
    base = base.strip()
    if not base:
        return base
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        base = base[: base.rfind("/chat/completions")].rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    # 若只填了 host:port（无路径），补 /v1
    if base.count("/") == 2:
        base += "/v1"
    return base

# 配置文件名与键
CONFIG_FILE_NAME = "settings.json"
DEFAULT_DIR = Path.home() / ".config" / "vision-augment"

# 需要的字段
FIELDS = (
    ("VISION_API_BASE", "api_base", "OpenAI 兼容接口地址(如 http://host:port/v1)"),
    ("VISION_MODEL",   "model",     "视觉模型名(如 glm-5.2)"),
    ("VISION_API_KEY", "api_key",   "API Key(可留空用 dummy)"),
)


def config_path() -> Path:
    """返回配置文件路径。可用 VISION_CONFIG 覆盖。"""
    env = os.environ.get("VISION_CONFIG")
    if env:
        return Path(env).expanduser()
    return DEFAULT_DIR / CONFIG_FILE_NAME


def load_config() -> dict:
    """读取持久化配置；不存在/损坏则返回空 dict。"""
    p = config_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(cfg: dict) -> Path:
    """原子写入配置。返回写入路径。"""
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return p


def resolve_config(cli: dict) -> dict:
    """
    合并出最终配置 dict。优先级：cli > env > file。
    cli 里 value 为 None 表示未显式传入。
    """
    final = {}

    # 1. 配置文件（最低层）
    final.update(load_config())

    # 2. 环境变量
    for env, key, _ in FIELDS:
        if os.environ.get(env):
            final[key] = os.environ[env].strip()
    if os.environ.get("VISION_MAX_SIZE"):
        final["max_size"] = int(os.environ["VISION_MAX_SIZE"])
    if os.environ.get("VISION_CACHE_DIR"):
        final["cache_dir"] = os.environ["VISION_CACHE_DIR"]
    # 暂存目录(图片落地约定)，仅作为约定提示；默认值由 describe.py 按脚本位置解析
    if os.environ.get("VISION_STAGE_DIR"):
        final["stage_dir"] = os.environ["VISION_STAGE_DIR"]

    # 3. 命令行（最高层，临时覆盖）
    for env, key, _ in FIELDS:
        v = cli.get(key)
        if v:
            if key == "api_base":
                final["api_base"] = v  # 注意：环境变量名是 VISION_API_BASE，key 统一
            else:
                final[key] = v

    return final


def is_configured(final: dict) -> bool:
    """是否已具备发起视觉请求的必要配置。"""
    return bool(final.get("api_base") and final.get("model"))


def need_interactive(final: dict, cli_forced: dict) -> bool:
    """
    是否需要交互询问用户：
      - 未配置，且用户没有显式用命令行指定缺失项。
    """
    if is_configured(final):
        return False
    # 命令行显式要求非交互
    if cli_forced.get("non_interactive"):
        return False
    return True


def ask_and_persist(prefill: dict | None = None) -> dict:
    """交互式询问缺失的配置项，写回配置文件并返回最终配置。"""
    prefill = prefill or {}
    print("── 首次使用 vision-augment，请配置视觉模型 ──", file=sys.stderr)
    print("(将保存到 %s)" % config_path(), file=sys.stderr)
    print("", file=sys.stderr)

    new_cfg = {}
    for env, key, label in FIELDS:
        cur = (
            os.environ.get(env)
            or prefill.get(key)
        )
        prompt = f"  {label} [{cur if cur else ''}]: "
        ans = input(prompt).strip()
        if not ans and cur:
            ans = cur
        if ans:
            new_cfg[key] = ans
    if not new_cfg.get("api_key"):
        new_cfg["api_key"] = "dummy"

    save_config(new_cfg)
    print("", file=sys.stderr)
    print(f"✔ 配置已保存到 {config_path()}", file=sys.stderr)

    # 合并已有 + 新增，返回
    merged = dict(load_config())
    merged.update(new_cfg)
    return merged
