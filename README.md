# skills-dev

面向 **Pi Agent**（`pi`）的 Agent Skills 集合仓库。每个 skill 都是一个符合
[Agent Skills 标准](https://agentskills.io/specification) 的目录（含 `SKILL.md`），
供 pi 在任务匹配时按需加载（渐进式披露：常驻上下文只有 description，正文随用随读）。

> 本 README 主要教你**如何安装 / 注册 / 更新 / 卸载**这些 skill。安装完成后，
> 在 pi 会话里**任务匹配即自动加载**，也可用 `/skill:<name>` 强制加载。

## 目录

| skill | 作用 | 依赖 | 首次需要做的初始化 |
|-------|------|------|-------------------|
| [`vision-augment`](vision-augment/) | 为「纯文本模型」赋予视觉能力：把图片交给外部多模态模型，取回文字描述先验（支持 OCR / 布局 / 问答） | Python3（Pillow、requests）| 配置一个多模态模型网关 |
| [`web-tools`](web-tools/) | 无头浏览器驱动的网络搜索（Bing / Google / GitHub）+ 任意 URL 渲染、截图 | Python3 + Obscura 无头浏览器二进制（约 200MB） | `install.sh` 会自动下载二进制 |

> `arena/` 是本仓库内部的 **skill 测试场**，与安装无关，可忽略。

## 前置要求

- 已安装 **Pi Agent**（`pi`）；skill 命令可用需在 `/settings` 或 `settings.json`
  打开 `"enableSkillCommands": true`（默认开）。
- `python3`（两个 skill 都用 Python 驱动）。
- 安装/使用前**先审查 skill 内容**：skill 可以指引模型执行任意操作（官方安全提醒）。

---

## 快速安装：如果你是 AI，你会怎么做

> 本仓库的安装既可由人手动执行（下节），也可**交给读到此文的 AI 代劳**。
> 如果你是 AI（例如用户正在 pi 会话里说「帮我把这套 skill 装上」），按下面步骤**自己动手**，
> 不要让用户逐条敲命令。路径一律用占位符：把 `<仓库>` 替换为用户告知的仓库绝对路径
> （例如 `/home/xx/skills-dev` 或 `D:/xx/skills-dev`）。

1. **读文档**：`read <仓库>/README.md`，了解两个 skill（`vision-augment`、`web-tools`）的结构、依赖与下面「前置要求」。
2. **定路径**：确认仓库绝对路径 `$SKILLS_DIR`（向用户确认或从当前工作目录推断），所有命令都用它。
3. **注册（优先方式 A）**：把两个 skill 的绝对路径写入 `~/.pi/agent/settings.json` 的 `skills` 数组：
   ```json
   { "skills": [ "<仓库>/vision-augment", "<仓库>/web-tools" ] }
   ```
4. **注册（无法改 settings.json 时用方式 B）**：软链到 `~/.pi/agent/skills/`。
   - Windows/WSL：⚠️ **必须用 Windows junction**（`mklink /J`），参考 `web-tools/scripts/install.sh` 的做法；
     别用 WSL 的 `ln -s`（Windows 版 pi 读不到 Linux 软链，会报 EACCES）。
5. **web-tools 二进制**：若 `<仓库>/web-tools/scripts/bin/obscura` 不存在，执行
   `cd <仓库>/web-tools && bash scripts/download.sh`（首次约 200MB）。
6. **vision-augment 配置**：提示用户提供视觉模型网关，或帮忙跑 `python3 <仓库>/vision-augment/scripts/setup.py --set`。
7. **汇报验证**：告知用户重开 pi 会话后用 `/skill:web-tools` 与 `/skill:vision-augment` 验证（见下节）。

> 原则：**路径必须用户确认，绝不臆造或写死某台机器的具体路径**；安装是自动化操作，你能执行就不甩给用户。

---

## 安装（注册给 pi）

pi 发现 skill 的方式有三种：**settings.json 的 `skills` 数组**、**全局 `~/.pi/agent/skills/`**、
**项目级 `.pi/skills/`**（或 CLI `--skill <path>`）。任选其一即可。

### 方式 A：settings.json `skills` 数组（推荐，无需软链）

编辑全局配置文件 `~/.pi/agent/settings.json`
（Windows 上即 `C:\Users\<你>\.pi\agent\settings.json`），加上 `skills` 数组，
填入各 skill 目录的**绝对路径**：

```json
{
  "skills": [
    "<仓库>/vision-augment",
    "<仓库>/web-tools"
  ]
}
```

> 也可以指向**仓库根目录**（`<仓库>`）：pi 会在该位置下
> **递归发现**所有含 `SKILL.md` 的目录。这样今后 `git pull` 新增的 skill 自动生效。
> 版本升级后 pi 仍按绝对路径读取同一位置，**无需重装**。

### 方式 B：全局软链到 `~/.pi/agent/skills/`

把 skill 目录链接进 pi 的全局技能目录：

- **Linux / macOS**：

  ```bash
  ln -s /绝对/路径/skills-dev/vision-augment ~/.pi/agent/skills/vision-augment
  ln -s /绝对/路径/skills-dev/web-tools    ~/.pi/agent/skills/web-tools
  ```

- **Windows / WSL**：⚠️ 不要用 WSL 的 `ln -s`（Linux 软链 Windows 版 pi 读不到，
  报 `EACCES`）。**web-tools 自带安装脚本**，用 Windows 原生 junction 注册：

  ```bash
  cd <仓库>/web-tools
  bash scripts/install.sh          # 自动: mklink /J ~/.../skills/web-tools + 缺二进制时自动下载
  ```

  `vision-augment` 同理可参考该脚本的做法手动执行
  `cmd.exe /c "mklink /J <Windows目标> <Windows源>"`。

### 方式 C：项目级 `.pi/skills/`（仅本仓库内测试用）

仓库内 `arena/` 用的就是这种方式：在项目根 `.pi/skills/` 下软链 skill，
**仅在该项目被 pi 信任后**才会加载。日常个人使用不必走这条，详见 `arena/README.md`。

### 方式 D：CLI 临时加载

```bash
pi --skill /绝对/路径/skills-dev/web-tools
```

---

## 首次初始化（每个 skill 各一次）

安装并**重开一个 pi 会话**后，按需初始化：

### vision-augment：配置视觉模型网关

它通过 OpenAI 兼容的 `/v1/chat/completions` 访问一个**多模态**模型。二选一：

```bash
# 交互式配置并持久化（推荐）
python3 vision-augment/scripts/setup.py --set

# 或临时用环境变量
export VISION_API_BASE="http://<host>:<port>/v1"
export VISION_MODEL="glm-5.2"
export VISION_API_KEY="dummy"
```

首次直接调用时若配置缺失，`describe.py` 也会在后台交互询问并自动持久化。

### web-tools：确认二进制就绪

```bash
ls web-tools/scripts/bin/obscura        # 已由 install.sh 自动下载
# 缺少时手动补：
cd web-tools && bash scripts/download.sh
# 可选：配 GITHUB_TOKEN 提升 GitHub API 限流（代码搜索必需）
```

---

## 验证是否装好

```bash
pi     # 或 cd 到某项目
```

在会话里：

- `/skill:web-tools` — 应能加载该 skill，随后可执行搜索脚本；
- 直接提出与 skill 匹配的任务（如「用 skill 搜索 xxx」/「请描述这张图」）— 任务匹配会自动加载；
- 或对 `vision-augment` 敲 `/skill:vision-augment` 强制加载。

> 若命令不存在，确认 `enableSkillCommands` 已开启并**重开会话**。

## 更新

仓库即单一事实源（新增/修改 skill 直接编辑仓库）。`git pull` 后：

- **软链 / settings 指向仓库** → 改动即时生效，**无需重装**；
- web-tools 二进制升级：`cd web-tools && bash scripts/download.sh <版本>`。

## 卸载

- settings.json 方式：从 `skills` 数组移除对应路径；
- 软链方式：删除 `~/.pi/agent/skills/<name>` 链接本身，**不要**删仓库目录。

---

## 上报 / 贡献

欢迎在仓库内新增 skill：建一个目录，含 `SKILL.md`
（frontmatter 必须有 `name` + `description`），脚本、文档、资源随意放；
命名规则：小写字母/数字/连字符，如 `my-skill`。
