# pi 官方 Subagent 扩展 — 通用安装手册（Agent 执行手册）

> **阅读对象：AI Agent（执行者）。**
> 本文是一份可执行的安装手册，同时兼容 **Ubuntu/Linux、macOS 与 Windows（Git Bash / WSL）**。
> 本手册**不写死任何用户个人路径**（不出现具体用户名、`C:\Users\xxx`、`/mnt/c/Users/xxx` 之类的内容）；所有路径在 §2 由 Agent 现场探测得出，并在关键节点经用户确认。
> 除 §1 外，各章节均要求你在 `bash` 中以命令落实，并在关键节点向用户确认。
>
> 安装对象：**官方第一方示例**（`@earendil-works/pi-coding-agent` 自带），不是社区包 `pi-subagents`。

---

## 0. 前置事实（平台无关，执行前背下来）

| 项 | 值 |
|---|---|
| pi 配置目录（全局默认） | `~/.pi/agent`；可用环境变量 `PI_CODING_AGENT_DIR` 覆盖 |
| 系统级扩展 | `~/.pi/agent/extensions/`（Windows 原生进程 = `%USERPROFILE%\.pi\agent\`） |
| 系统级 agents | `~/.pi/agent/agents/*.md` |
| 系统级 prompts | `~/.pi/agent/prompts/*.md` |
| 项目级 | `.pi/extensions/`、`.pi/agents/`、`.pi/prompts/`（随仓库共享） |
| 项目级生效条件 | **项目必须已受信任**（`/trust`）；否则 `.pi` 下 extensions/prompts 不加载 |
| 官方源示例位置 | npm 全局安装目录下：`@earendil-works/pi-coding-agent/examples/extensions/subagent/` |
| 示例依赖 | 零第三方依赖（仅 node 内置 + pi 内置），装完即可用 |
| 自定义批处理 agent | 安装时创建名为 `action` 的自定义 agent（§3.4）：调用时**手动指定执行文档路径**，照文档执行后**仅输出一个 JSON** |

判据一句话：**pi 的 `settings.json` / `sessions/` / `skills/` 在哪个目录，系统级就装到哪个目录。** 不要凭直觉猜，必须现场探测（§2.3）。

---

## 1. ⚠️ 决策门（第一步，必须先询问用户，禁止跳过）

**在执行任何安装动作之前，停下，向用户提问（两条都要问）：**

```
① 当前操作系统（供核对，Agent 随后会用 §2.2 实测）：
     A. Ubuntu / Linux（含 WSL 内的 Linux）
     B. Windows（Git Bash / MSYS2 / Cygwin）
     C. macOS
 ② subagent 扩展的安装级别：
     A. 项目级（装进当前项目 .pi/，随仓库版本化、团队共享）
     B. 系统级（装进 pi 配置目录，所有项目可用）
```

执行规则（对 Agent）：
- **没有得到明确的答复之前，禁止执行 §3 及之后的任何安装命令。**
- 若用户反问「你看着办 / 按文档默认」：默认推荐 **A（项目级）**，但必须在执行前再次向用户说明这一默认并取得同意。
- 用户选定后，记为 `INSTALL_LEVEL=project|system`；等下还用 §2.2 实测操作系统，**若实测结果与用户回答不一致，停下来再次向用户确认，不许自行决定**。
- 若选 A，还需在 §4 完成项目信任处理；选 B 则跳至 §5 验证。
- 记录你做出的每一次「询问→答复」，便于用户复核。

---

## 2. 环境探测与共同前置检查（两种级别都要；先在 bash 里做完）

> 本节把三个关键路径全部现场探测出来，之后三节不再出现任何硬编码路径：
> `OS`（操作系统）、`CFG`（pi 配置目录）、`SRC`（官方源示例目录）。

### 2.1 pi 已安装

```bash
command -v pi && pi --version || { echo "pi 未安装"; exit 1; }
```

### 2.2 操作系统识别（Ubuntu? Windows? macOS?）

```bash
# —— 判定 OS 家族（在 bash 里跑，Git Bash 里 uname 返回 MINGW/MSYS，不会误判成 Linux）——
case "$(uname -s)" in
  Linux*)  OS=linux ;;                       # Ubuntu / WSL 内 Linux / 其他 Linux
  Darwin*) OS=darwin ;;                      # macOS
  MINGW*|MSYS*|CYGWIN*) OS=gitbash ;;        # Windows 上的 Git Bash / MSYS2 / Cygwin
  *) OS=unknown ;;
esac

# —— 是否运行在 WSL 里？（uname -r 含 microsoft）——
IS_WSL=no
if [ "$OS" = "linux" ] && [ -r /proc/version ] && grep -qi microsoft /proc/version; then
  IS_WSL=yes
fi

echo "OS=$OS   IS_WSL=$IS_WSL"
echo "HOME=$HOME        USERPROFILE=${USERPROFILE:-<未设置>}"
```

判定含义（读给用户听，作为 §1 ① 的核对结果）：
- `OS=linux, IS_WSL=no` → **原生 Ubuntu/Linux**，配置目录就是 `~/.pi/agent`，最简单。
- `OS=gitbash` → **Windows 原生进程 + Git Bash**，配置目录在 Windows 用户目录（§2.3 解析）。
- `OS=linux, IS_WSL=yes` → **最容易装错**：shell 是 WSL 的 Linux，但 pi 既可能是 **Windows 原生进程**（配置在 Windows 侧目录），也可能是 **WSL 里装的 Linux 版 pi**（配置在 WSL `~`）。到底哪个，必须交 §2.3 探测并请用户确认，**禁止猜**。

### 2.3 定位 pi 实际配置目录（关键，禁止猜）

```bash
# ① 显示显式覆盖变量
echo "PI_CODING_AGENT_DIR=${PI_CODING_AGENT_DIR:-<未设置>}"

# ② 探测：优先级 = 环境变量 > （平台候选 + 现场命中 settings/sessions）＞ 询问用户
CFG=""
if [ -n "$PI_CODING_AGENT_DIR" ]; then
  CFG="$PI_CODING_AGENT_DIR"; echo "✓ 使用环境变量指定：$CFG"
else
  candidates=""
  case "$OS" in
    linux|darwin)
      candidates="$HOME/.pi/agent"
      # WSL：追加 Windows 侧候选（/mnt/c/Users/<*>/ .pi/agent）
      [ "$IS_WSL" = "yes" ] && candidates="$candidates $(ls -d /mnt/c/Users/*/.pi/agent 2>/dev/null)"
      ;;
    gitbash)
      candidates="${USERPROFILE:-$HOME}/.pi/agent"
      ;;
  esac
  for c in $candidates; do
    # 只有「存在 settings.json 或 sessions/」的目录才算 pi 真正的配置目录
    if [ -e "$c/settings.json" ] || [ -d "$c/sessions" ]; then
      echo "✓ 命中：$c  ← pi 实际配置目录"
      [ -z "$CFG" ] && CFG="$c"
    else
      echo "✗ 跳过：$c （无 settings/sessions，是残留目录）"
    fi
  done
  # Windows 侧解析为非 Windows 风格路径（Git Bash 内部使用）
  [ "$OS" = "gitbash" ] && [ -n "$CFG" ] && CFG="$(cygpath -u "$CFG")"
fi

[ -n "$CFG" ] || { echo "⚠️ 无法自动确定 pi 配置目录 —— 停下，把上面候选清单贴给用户，请其指认。"; exit 1; }
echo ">>> 最终 CFG=$CFG"
```

- **允许多个候选「命中」吗？** 不允许多选。若上面打出了不止一个 `✓ 命中`（常见于 WSL + 同时存在 Windows 侧与 WSL 侧 pi）——**停下，把清单贴给用户，请用户确认用哪个**；若只有一个命中，直接把该目录当作 `CFG` 并**向用户复述确认**。
- `CFG` 统一用 Linux 风格路径：原生系统 `/home/...`；WSL 指向 Windows 侧时用 `/mnt/c/...`。用户看到的 Windows 路径（`C:\Users\...`）与它一一对应，不会弄混。

### 2.4 定位官方源示例目录（不写死个人路径）

```bash
# npm 全局安装根目录（Linux = /usr/lib/...；Windows Git Bash = C:\Users\<用户>\AppData\Roaming\npm\...）
NPM_GLOBAL_ROOT="$(npm root -g 2>/dev/null || true)"
case "$OS" in
  gitbash) NPM_GLOBAL_ROOT="$(cygpath -u "$NPM_GLOBAL_ROOT" 2>/dev/null || echo "$NPM_GLOBAL_ROOT")" ;;
esac

SRC="$NPM_GLOBAL_ROOT/@earendil-works/pi-coding-agent/examples/extensions/subagent"
echo ">>> 官方源示例 SRC=$SRC"
ls -la "$SRC" || {
  echo "未在 npm 全局目录找到官方示例。备选兜底："
  echo '  find / -path "*pi-coding-agent/examples/extensions/subagent" -type d 2>/dev/null'
  echo "若仍找不到，请询问用户 pi 装在哪里（或在 pi 会话里跑 \`/environment\` 查看安装路径）。"
  exit 1
}
```

> 若用户不是用 npm 装的 pi（bun / 本地源码 / 其他包管理器），`npm root -g` 可能为空——按上面的兜底处理，不要硬猜。

### 2.5 目标目录现状（决定安装还是重装）

```bash
# 系统级目标现状 / 项目级目标现状
echo "CFG=$CFG"; ls -la "$CFG/extensions" 2>/dev/null || echo "（无 extensions 目录，将新建）"
PROJECT_ROOT="$(pwd)"; echo "PROJECT_ROOT=$PROJECT_ROOT"; ls -la "$PROJECT_ROOT/.pi" 2>/dev/null || echo "（项目无 .pi，将新建）"

# 若已存在 subagent 残留，先清理再装（避免新旧混用；按最终级别二选一）
rm -rf "$CFG/extensions/subagent"                 # 系统级旧残留
rm -rf "$PROJECT_ROOT/.pi/extensions/subagent"    # 项目级旧残留
```

---

## 3. 按级别执行安装

> 变量：`SRC`=官方源示例目录（§2.4），`CFG`=pi 配置目录（§2.3）。
> 若 symlink 在 Windows/WSL 间失效（pi 报找不到 `agents.ts`），把所处分支里的 `ln -sf` 换成 `cp -rf`（§3.3）。
> **无论安装到哪种级别，装完扩展都要执行 §3.4 创建自定义 `action` agent。**

### 3.1 系统级安装（`INSTALL_LEVEL=system`）

```bash
# 扩展本体（index.ts + agents.ts 都要，必须在带 index.ts 的子目录里）
mkdir -p "$CFG/extensions/subagent"
ln -sf "$SRC/index.ts" "$CFG/extensions/subagent/index.ts"
ln -sf "$SRC/agents.ts" "$CFG/extensions/subagent/agents.ts"

# 官方示例 agent（用户级，所有项目可见）
mkdir -p "$CFG/agents"
for f in "$SRC"/agents/*.md; do
  ln -sf "$f" "$CFG/agents/$(basename "$f")"
done

# 工作流模板
mkdir -p "$CFG/prompts"
for f in "$SRC"/prompts/*.md; do
  ln -sf "$f" "$CFG/prompts/$(basename "$f")"
done
```

### 3.2 项目级安装（`INSTALL_LEVEL=project`）

```bash
P="$(pwd)"   # 项目根 = 当前 cwd（必须是用户选定的那个项目）

mkdir -p "$P/.pi/extensions/subagent" "$P/.pi/agents" "$P/.pi/prompts"
cp "$SRC/index.ts" "$SRC/agents.ts" "$P/.pi/extensions/subagent/"
cp "$SRC"/agents/*.md "$P/.pi/agents/"
cp "$SRC"/prompts/*.md "$P/.pi/prompts/"

# —— 项目级必做补丁：默认 agentScope 由 "user" 改为 "both" ——
# 原因：官方默认 "user" 时模型看不到 .pi/agents/ 里的项目 agent；
#       改成 "both" 后项目级 agent 默认可见可用。
sed -i 's/params.agentScope ?? "user"/params.agentScope ?? "both"/' "$P/.pi/extensions/subagent/index.ts"
sed -i 's/args.agentScope ?? "user"/args.agentScope ?? "both"/'   "$P/.pi/extensions/subagent/index.ts"
# 核对（所有 agentScope 默认值都应为 both）
grep -n 'agentScope.*\?\?' "$P/.pi/extensions/subagent/index.ts"
```

### 3.3 symlink 失效兜底（两种级别通用）

若 `/reload` 后报找不到 `agents.ts` / 模块错误（NTFS 符号链接未被 Windows node 跟随，或 WSL 跨文件系统失效）：
把对应分支里的 `ln -sf` 全部换成 `cp -rf`，其余不变。代价：升级 pi 后文件不自动跟随更新。

### 3.4 创建自定义 `action` agent（两种级别都要做）

> 行为约定（按需，可改）：
> - 调用 `action` 时**每次手动指定执行文档路径**（不给路径 → 直接返回 failed，不乱找文件）；
> - 流程 = 读指定 md → 实际执行 → 对照验收标准自检 → **只输出一个 JSON**；
> - 输出契约：`{"status":"success|failed","reason":"..."}`。
> - 若想改成固定读某路径的 md / 再加别名 agent（如 `执行.md`），复制下面的模板改路径即可。

```bash
# 目标位置：
#   - 系统级：ACTION_DST="$CFG/agents/action.md"
#   - 项目级：ACTION_DST="$P/.pi/agents/action.md"
ACTION_DST="$CFG/agents/action.md"   # 按实际级别改这一行
mkdir -p "$(dirname "$ACTION_DST")"   # 目标目录可能尚不存在，先建好

cat > "$ACTION_DST" <<'ACTION'
---
name: action
description: 批处理执行器。读取指定的执行文档(.md)并严格遵守其中的步骤/目标/验收标准在目标仓库中执行，结束后仅输出一个 JSON 结果，不输出任何其他内容。
tools: read, write, edit, bash, grep, find, ls
---

你是 `action`，一个严格的批处理执行器。你只做一件事：**照着执行文档，把它落地。**

## 输入
任务中**必须**给出执行文档的路径（.md）。若调用方没给路径，不要自己找文件臆测——直接返回 failed，`reason` 写「缺少执行文档路径，请指定要执行的 .md」。

## 执行流程（严格遵守顺序）
1. **读文档**：用 `read` 读取指定执行文档全文，逐条解析其中的 背景 / 目标 / 步骤 / 验收标准 / 禁止事项。
2. **执行**：按文档对目标仓库/文件实际执行——需要读就读、需要改就改（write/edit）、需要跑命令就跑（bash）。
3. **自检**：执行完对照文档的「验收标准」逐条核验；没写验收标准的，自行按「目标是否达成」判断。
4. **只输出一个 JSON**（最后一步，除此之外全程不得输出任何解释性文字），形如：
   {"status":"success|failed","reason":"..."}
   - `reason` 必须写清：成功时简述达成了什么；失败时说明卡在第几步、失败原因、影响。

## 铁律
- 文档里「禁止」做的事，一律不做。
- 遇到文档不明确之处：优先按文档上下文判明；仍歧义 → 把歧义点作为 `failed` 原因返回，不得臆测执行。
- 除最终 JSON 外，不输出与任务无关的说明、寒暄、总结。
ACTION

echo "已写入 $ACTION_DST"; ls -la "$ACTION_DST"
```

> ⚠️ 项目级安装时，`action` 属于项目级 agent，必须同时满足 §3.2 的 agentScope=both 补丁（已做）与 §4 的项目信任，之后模型才能看到/调用它。

---

## 4. 项目信任（仅 `INSTALL_LEVEL=project` 必做）

项目级扩展、项目级 prompts **只在项目受信任后加载**。执行：

```bash
# 4.1 检查当前项目是否已在信任列表
grep -F "$PROJECT_ROOT" "$CFG/trust.json" 2>/dev/null   # 看有没有当前项目路径
```

- 若不在信任列表 → **要求用户到 pi 里执行 `/trust`**（或首次启动时 pi 会弹信任提示，让用户确认「信任」）。
- 信任后再 `/reload` 加载项目级扩展。
- 交互模式下，未信任项目首次调用项目级 agent 还会再弹一次确认（`confirmProjectAgents` 默认开）；信任后跳过。

> 安全告知用户：项目级 = 仓库可控代码/prompt，只对可信来源的仓库使用。

---

## 5. 验证（两种级别共用）

加载后（`/reload`），按顺序给用户跑通三种形态并展示结果：

```text
用 scout 摸底这个仓库                                # 单个
Run 2 scouts in parallel: one to find models, ...    # 并行（≤8 任务 / 4 并发）
Use a chain: scout → planner                          # 链式（{previous}）
/implement <某改动>                                   # 工作流模板
用 action 执行 <某执行文档.md>                       # 自定义批处理 agent（§3.4）
```

判定标准：
- 看到子进程流式跑、结尾有 `turns / tokens / cost / context` → 成功；
- 项目级：确认 scout 来自 `.pi/agents/`（可用 `subagent` 工具的 agent 列表/`[both]` 标注核对）；
- `action`：应在输出中只有一段 JSON，且 `status` 为 `success`；不给它路径时应返回 `failed`（说明缺少路径）而非乱猜文件；
- 失败：按 §3.3 兜底（换 `cp`）后重试。

---

## 6. 收尾询问（可选但推荐）

安装成功并验证后（`action` 已在 §3.4 装好），询问用户是否还需要：
1. **调整 `action` 行为**：默认 = 每次手动指定执行文档路径 + 仅输出一个 JSON。若用户想要「固定读某路径的 md」「多建一个 `执行.md` 别名 agent」等，按 §3.4 的模板复制改写即可。
2. 是否要让主模型「调用 subagent 时默认带 agentScope: both」——系统级默认不需要；
   项目级已通过 §3.2 补丁覆盖。

---

## 7. 清理 / 卸载（按实际安装级别执行）

```bash
# 系统级
rm -rf "$CFG/extensions/subagent"
rm -f  "$CFG/agents"/action.md "$CFG/agents"/scout.md "$CFG/agents"/planner.md \
       "$CFG/agents"/reviewer.md "$CFG/agents"/worker.md
rm -f  "$CFG/prompts"/implement.md "$CFG/prompts"/scout-and-plan.md \
       "$CFG/prompts"/implement-and-review.md

# 项目级
P="$(pwd)"
rm -rf "$P/.pi/extensions/subagent"
rm -f  "$P/.pi/agents"/action.md "$P/.pi/agents"/scout.md "$P/.pi/agents"/planner.md \
       "$P/.pi/agents"/reviewer.md "$P/.pi/agents"/worker.md
rm -f  "$P/.pi/prompts"/implement.md "$P/.pi/prompts"/scout-and-plan.md \
       "$P/.pi/prompts"/implement-and-review.md
```

> ⚠️ 删除 `agents/*.md` 前先确认里面没有用户自建 agent（`action` 或用户另加的）。

---

## 8. 常见问题（Agent 自查清单）

| 症状 | 处理 |
|---|---|
| 装到 WSL 的 `~/.pi/agent` 不生效 | pi 很可能是 **Windows 原生进程** → 应装 §2.3 探测出的 Windows 侧配置目录（`/mnt/c/Users/<用户>/.pi/agent`） |
| 不确定装到哪 | 跑 §2.3，看哪个目录有 `settings.json`/`sessions/`；命中多个就贴给用户确认 |
| 项目级 reload 后无工具 | 项目未信任：先 `/trust` 再 `/reload`（§4） |
| 报找不到 `agents.ts` | symlink 跨文件系统失效 / NTFS 不跟随 → 换 `cp`（§3.3） |
| 模型说没有可用的项目 agent | 默认 scope 仍为 user：核对 §3.2 的两处 `sed` 补丁是否都生效 |
| 找不到官方源示例 | `npm root -g` 为空（bun/其他安装方式）→ §2.4 兜底：`find / -path "*pi-coding-agent/examples/extensions/subagent"` 或问用户 |
| 与社区 `pi-subagents` 混淆 | 本手册只装官方第一方示例；社区包另文档 |
