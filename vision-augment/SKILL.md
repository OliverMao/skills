---
name: vision-augment
description: 为「非多模态（纯文本）模型」赋予视觉能力。当你需要理解一张图片的内容（截图、UI、图表、照片、文档扫描件等），但当前模型不支持图像输入时，调用本技能：它会把图片发送给一个外部多模态视觉模型，取回结构化的「描述先验」，从而让你「看见」图片并基于该描述回答视觉问题、执行任务。
---

# Vision Augment（视觉增强）

## 它解决什么问题

你（当前模型）无法直接接收图像。本技能通过一个**多模态视觉模型**把图片翻译成文字描述（描述先验），再交给你使用。本质上是一个"图像 -> 文本"的桥接层。

## 何时使用

- 用户贴了一张截图/照片/图表/界面，要求你分析、描述、抽取文字或操作；
- 需要 OCR 提取图片中的文字；
- 需要理解 UI 布局、网页结构、图表数据；
- 需要根据图片回答具体问题；
- 任务中引用了一个图像路径或 URL，且你无法直接看到。

## 智能配置（自动询问并持久化）

视觉模型通过 OpenAI 兼容的 `/v1/chat/completions` 接口访问，需要 `api_base` 与 `model`（可选 `api_key`）。

**配置来源优先级（从高到低）：**

1. 命令行 `--base / --model / --api-key`（临时覆盖，不写盘）
2. 环境变量 `VISION_API_BASE / VISION_MODEL / VISION_API_KEY`
3. 持久化配置文件（默认 `~/.config/vision-augment/settings.json`）
4. 都没有 → **首次调用时交互询问你，并自动写入配置文件持久化**，下次直接复用

### 实际使用时的自动行为

- **首次运行时**：如果你没设环境变量也没配置文件，脚本会提示你输入网关地址和视觉模型名，你确认后它保存到配置文件，之后不再询问。
- **之后运行时**：直接复用已保存的配置，全程零提示。
- 想临时用别的模型（不覆盖已保存配置），用 `--base/--model` 即可。

### 显式配置工具 `scripts/setup.py`

```bash
python3 scripts/setup.py              # 查看当前配置（脱敏显示来源）
python3 scripts/setup.py --set        # 交互重新设置并持久化
python3 scripts/setup.py --clear      # 删除持久化配置
python3 scripts/setup.py --test       # 测试 API 连通性
```

### 环境变量方式（可选）

```bash
export VISION_API_BASE="http://10.127.48.252:PORT/v1"   # 你的多模态模型网关
export VISION_MODEL="glm-5.2"                           # 视觉模型名
export VISION_API_KEY="dummy"                           # 视情况
```

> 如果通过 litellm 等代理把所有模型聚合在一个网关下，`VISION_API_BASE` 指该网关地址（通常即 `/v1`），`VISION_MODEL` 指其中**支持视觉**的模型名。请勿把纯文本模型当成视觉模型使用——本技能依赖多模态能力。

## ⚠️ 最重要约束：主模型绝不能自己读图片

当前主模型**不支持图像输入**。把任何图片内容塞进上下文都会导致会话报错。因此必须遵守：

- **禁止**用 `read` 工具或任何方式**直接读取/打开图片文件**，也**不要**把图片的 base64 或二进制内容打印出来。
- 图片只允许落在**磁盘缓存目录**里，由 `describe.py` 脚本去读取并交给视觉模型；主模型全程只接触**文字路径**和**文字描述先验**。

**图片统一暂存到项目缓存目录（约定为 `./.pi/tmp/image/`）：**

```bash
# 用户给了一张图片/截图/文件时：
# 1. 把它复制/保存到缓存目录（若尚未在那里）
mkdir -p ./.pi/tmp/image
cp <原始图片路径> ./.pi/tmp/image/            # 或用截图/导出工具写入该目录
# 2. 再把缓存目录里的图片路径传给 describe.py
python3 scripts/describe.py ./.pi/tmp/image/<文件名>
```

> 临时目录约定 `./.pi/tmp/image/` 可在 `VISION_STAGE_DIR` 覆盖；图片路径与脚本调用是否同目录无关，只要给出**完整/正确路径**即可。
> 脚本“描述缓存”自动锚定到 skill 目录下的 `.pi/tmp/vision_cache`（不依赖调用时的当前目录），无需手动管理。

> 若拿到的是 URL 而非本地文件，可直接把 URL 传给 describe.py（视觉模型网关拉取，不经过主模型上下文）。

## 使用方法

调用脚本把图片转成描述先验，然后把描述纳入你的推理：

```bash
python3 scripts/describe.py <图片路径或URL>
```

脚本会输出结构化的中文描述文本。你应当**把它当作你"看到"的结果**，基于它回答用户的问题，并在回复中自然引用图片细节。**你的上下文里全程只会有这段文字，不会有任何图片字节。**

### 常用模式

```bash
# 1) 通用详尽描述（默认，适合大多数情况）
python3 scripts/describe.py screenshot.png

# 2) 只想看图大致是什么
python3 scripts/describe.py photo.jpg --mode quick

# 3) 抽取图中文字（OCR）
python3 scripts/describe.py scan.png --mode ocr

# 4) 理解 UI / 页面 / 图表布局
python3 scripts/describe.py ui.png --mode layout

# 5) 一句话图注
python3 scripts/describe.py pic.png --mode caption

# 6) 针对图片回答具体问题（推荐：先 detailed 再追问细节）
python3 scripts/describe.py ui.png --mode detailed --qa "这个页面的主要功能是什么？"
```

### 关键选项

| 选项 | 作用 |
|------|------|
| `--mode` | `detailed` / `quick` / `ocr` / `layout` / `caption` 五种描述粒度 |
| `--qa "问题"` | 让视觉模型针对图片回答指定问题 |
| `--max-size N` | 先把图片缩放到最长边 ≤ N 像素（默认 1024），省 token、兼容小模型；`0` 不缩放 |
| `--base64` | 强制 base64 内联上传（网关不支持 http URL 时用） |
| `--detail high` | 让兼容模型用更高清晰度采样 |
| `--json` | 输出原始 API JSON（未过滤，含思考内容，仅供调试） |

### 覆盖默认配置（命令行临时覆盖，不写盘）

```bash
python3 scripts/describe.py x.png --base "http://host:port/v1" --model "glm-5.2" --api-key "xxx"

# 配置缺失时跳过询问、直接报错（适合非交互/自动化场景）
python3 scripts/describe.py x.png -y
```

## 思考内容过滤（自动）

许多视觉模型是**思考模式**（reasoning/CoT），响应里会混入思考过程。本技能在把描述先验交给 agent 之前，会自动剔除：

- 独立字段：`reasoning_content` / `thinking` / `reasoning` 等（只取 `content`）；
- `content` 内被标签包裹的思考区：`<thinking>…</thinking>`、`[reasoning]…[/reasoning]`、`<reasoning>`、`<thought>`、`<analysis>`、`<cot>` 等（兼容 `< >` 与 `[ ]` 两种括号、大小写不敏感、多段思考）。

因此 agent 拿到的描述先行总是**干净的最终答案**，不含任何思维链。
> 调试排错需要看原始响应时，用 `--json` 输出未过滤的完整 JSON。

## 工作流程建议

1. **默认先跑 `--mode detailed`** 拿到完整描述先验；
2. 若问题集中在界面上，改用 `--mode layout`；集中在文字上，用 `--mode ocr`；
3. 需要精确答案时，用 `--qa` 让视觉模型直接回答，能减少你的推断误差；
4. 把描述先验和用户问题结合，组织成你的最终回答。

## 后端细节与排查

### 图片如何上传
- **本地文件**：自动 base64 内联上传（无需外部 URL）。
- **http(s) URL**：直接传 URL（需网关能公网访问），或用 `--base64` 强制转内联。

### 兼容性
- 依赖 Pillow（缩放）与 requests，二者通常已就绪。缺失时 `pip install pillow requests`。
- 脚本会尽力兼容：无 Pillow 时不做缩放；无 requests 时退回 urllib。

### 退出码
- `0` 成功；`2` 参数/配置错误；`3` 图片读取失败；`4` 视觉 API 调用失败。

### 常见报错
- **`视觉模型未配置完整`** → 运行 `python3 scripts/setup.py --set` 交互配置，或设置 `VISION_API_BASE` / `VISION_MODEL`。
- **`API 4xx`** → 检查 key、模型名、网关 `/v1` 路径。
- **模型无法理解图片** → 该模型可能不是多模态的，换用真正的视觉模型。
- **图片太大/超时** → 加 `--max-size 768` 减小体积。

## 缓存

每次成功的描述会写入**描述缓存**，自动锚定在 skill 目录下的 `.pi/tmp/vision_cache/`（不依赖调用时的当前目录），可用 `VISION_CACHE_DIR` 覆盖：

```bash
# 两个临时目录分工：
#   <项目>/.pi/tmp/image/           <- 待识别图片的暂存区（主模型放置）
#   <skill>/.pi/tmp/vision_cache/   <- 已生成的描述先验缓存（describe.py 自动写）
```

对同一图片重复提问时，直接读取缓存文件（纯文本描述）复用，不必再次调用 API：

```bash
cat <skill>/.pi/tmp/vision_cache/<hash>.txt
```
