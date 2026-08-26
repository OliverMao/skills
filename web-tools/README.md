# web-tools — 无头浏览器驱动的网络搜索 Skill（Bing / Google / GitHub）

基于 [Obscura](https://github.com/h4ckf0r0day/obscura)（Rust 无头浏览器，原生渲染、无需 Chromium）
的 pi Skill：**搜索 = 无头浏览器渲染 SERP + 抽取**；附带任意 URL 渲染/截图基础能力。

## 能力一览

| 能力 | 命令 / 接口 |
|------|------------|
| 搜索（三引擎并行） | `python3 scripts/search.py "关键词"` |
| 仅 Bing / 中文 Bing | `-e bing` / `-e bing --cn` |
| 仅 Google | `-e google` |
| GitHub 仓储 / 代码 | `-e github -t repo` / `-e github -t code` |
| JSON 输出 | `-j` |
| 无头浏览器 CDP | `bash scripts/serve.sh` → `ws://127.0.0.1:9222/devtools/browser` |
| 渲染截图 | `bash scripts/shot.sh <url> [out.png]` |
| 渲染抽取 | `scripts/bin/obscura fetch <url> --dump text\|links\|markdown\|html` |
| 页面 JS 求值 | `scripts/bin/obscura fetch <url> --eval "<expr>"` |
| 停止服务 | `bash scripts/stop.sh` |
| 更新/下载二进制 | `bash scripts/download.sh [版本]` |

## Skill 注册（让 pi 发现）

1. 目录即标准 Agent Skill（`SKILL.md` 前置字段声明 name/description）。
2. 二选一：
   - `bash scripts/install.sh` — 软链到全局 `~/.pi/agent/skills/web-tools`；
   - 或手动在 `~/.pi/agent/settings.json` 的 `skills` 数组加本目录绝对路径。
3. 会话里触发：任务匹配自动加载，或 `/skill:web-tools`。

> 依赖渐进式披露：常驻上下文只有 description 一行，正文按需读取。

## 目录结构

```
web-tools/
├── SKILL.md
├── README.md
└── scripts/
    ├── bin/            # 自带二进制(obscura + obscura-worker)
    ├── download.sh     # 拉取/更新官方 release
    ├── search.py       # 搜索入口（无头浏览器渲染 + 抽取；GitHub API 兜底）
    ├── serve.sh        # 开启无头浏览器 CDP 服务
    ├── shot.sh         # 命令行截图
    ├── stop.sh         # 停 serve
    └── install.sh      # 注册为全局 skill (web-tools)
├── screenshots/        # 截图输出
└── logs/
```

## 搜索实现

- **Bing**：`obscura fetch bing.com/search?q=.. --dump markdown --stealth` → 解析 `## [Title](url)` + 摘要
- **Google**：同上渲染；检测到 CAPTCHA / unusual traffic（云 IP 常见）则跳过并提示。
  住宅网络下可正常出结果。
- **GitHub**：先渲染 `github.com/search?type=repositories` 页；被限流自动降级官方 REST API
  （`search/repositories`、`search/code`，含 star/语言/描述）。
- 反爬：无头浏览器本身 + `--stealth` 指纹，无需手写 UA/Cookie。

## 备注

- 每引擎一次完整渲染约 5–20s；`all` 串行约 3×。
- `GITHUB_TOKEN` 可提升 GitHub API 限流 60/h→5000/h；**代码搜索必需**。
- Obscura 默认拦截私有网段（SSRF 保护）；访问 localhost/内网加 `--allow-private-network`（脚本已默认）。
- 截图给非多模态主模型“看”时，配合 `vision-augment` skill 转成文字描述。
- 曾作为纯 HTTP 抓取的重构方向已回滚：搜索底层的“渲染”环节刻意留在无头浏览器内。
