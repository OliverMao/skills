---
name: web-tools
description: 网络搜索（Bing/Google/GitHub），Obscura 无头浏览器渲染。用本 skill 时：直接执行下节给出的唯一命令模板（绝对路径、一步到位），不得读取/翻开本 skill 目录内的任何其他文件。根据需求只调换 query 与参数（引擎/条数/精简），一次调用返回结果+一行降级摘要。
---

# Web Search（Bing / Google / GitHub）— 使用须知与命令模板

## 铁律（务必遵守，节省上下文）

- 使用本 skill 的唯一方式 = 执行下面的唯一命令模板。**不需要、也不允许**：
  - 读取本 skill 下的任何文件（`scripts/search.py`、`README.md`、`SKILL.md` 以外的正文、`scripts/bin/*` 等）
  - 列出/查看本 skill 目录（`ls`、`find`、`cat`、`grep`、查看二进制版本、`--help` 探测）
- 本文件已包含决策所需的全部信息；`search.py` 自包含、自带引擎自动降级/失败提示，
  缺失二进制时脚本自身会报一行提示——无需提前检查。
- 一次搜索的成功 = 一次 bash 调用（命令模板）+ 按 §3 解读结果。

## 唯一命令模板（直接替换 `"<query>"`，其余按需增减）

```bash
python3 /mnt/d/mProject/agent/skills-dev/web-tools/scripts/search.py "<query>" [-e bing|google|github|all] [-n N] [--brief] [--cn] [--min-stars N] [-t code]
```

参数速查（不知道用哪个就只填 query，用缺省）：
- `-e` 引擎：`bing`(默认场景推荐) / `google` / `github`(找开源项目) / `all`(多源交叉)
- `-n` 条数：默认 3；要全面 `5~8`，要快 `2`
- `--brief` 摘要截短省 token；`--cn` 中文检索(bing)；`--min-stars N` 过滤低星 GitHub 仓库
- `-t code` GitHub 代码搜索（需环境变量 GITHUB_TOKEN）

## 引擎与参数决策（30 秒想清楚）

| 意图 | 用 |
|------|-----|
| 找开源项目/记忆/RAG/agent 方案 | `-e github "类目词"`（如 `agent memory`）或具体项目名 |
| 通用网页/文档/教程/中文资料 | `-e bing` 或 `-e bing --cn` |
| 英文权威/多源验证 | `-e all` 或 `-e google`（云 IP 下 google 会被拦，见 §3） |
| 上下文紧张/高频搜索 | `-e bing -n 2 --brief` |

经验：多数检索 `-e bing -n 3` 一次即够；不要无脑 all、不要为“显得全面”重复搜同一 query。

## 结果解读（无需重试的正常情况）

- `> google:blocked` / `> github:html-limited(…)` ＝ 自动降级成功（Google 云IP被CAPTCHA、
  GitHub /search 二次限流→已改 topics 渲染），结果照常可用，**不要重试**。
- `> github:code-search需 GITHUB_TOKEN` 仅与 `-t code` 有关，普通搜索无视。
- `NONE` ＝ 该引擎无结果 → 换词/换引擎，勿原地重试。
- 结果跑题/垃圾 → 是 query 问题：精简关键词、改类目词、或加 `--min-stars`。

## 开销底线

输出已最小化（stdout 纯结果 / stderr 仅一行摘要）。本轮以下操作一律避免：
读取脚本文件、查看目录、pprint 输出、把搜索结果再次贴进长摘要——结果本身就是给模型用的。

## 附（仅当确实需要“看”页面时才额外调用）

无头浏览器基础能力：`scripts/bin/obscura fetch <url> --dump text|links|markdown`、
`bash scripts/shot.sh <url>`。默认搜索任务用不到。
