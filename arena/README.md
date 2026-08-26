# Arena（Skill 测试场）

`arena` 是本项目（`skills-dev`）中专门用来**测试 skill 效果**的沙盒目录。

在这里，你可以用 pi agent 实际加载、触发、并验证某个 skill 是否按预期工作，
而不用改动 skill 本体（`../<skill-name>/`）。

## 目录结构

```
arena/
├── README.md            # 本说明
├── .pi/                 # 在 arena 里跑 pi 的运行时目录
│   ├── skills/          # ← skill 发现目录（pi 项目级 skills 加载点）
│   │   └── vision-augment -> ../../../vision-augment   # 软链到真实 skill
│   └── tmp/             # 运行时缓存（图片暂存、描述缓存等）
│       └── image/       # 主模型放置待识别图片的暂存区
├── assets/              # 测试素材（样例图片、样例输入等）
└── tests/               # 测试用例 / 测试记录
```

## 用法：用 pi 测试 skill

### 1. 让 pi 能发现要测的 skill

pi 会从项目级目录 `.pi/skills/`（以及祖先目录的 `.pi/skills/`）加载 skill。
`arena` 下已把真实 skill 软链进 `.pi/skills/`，因此**直接在 `arena/` 里启动 pi 即可发现**。

真实 skill 源仍在 `../<skill-name>/`，改一处、测试处即时同步。

```bash
# 在 arena 里启动 pi（此时 arena 是被信任的项目根）
cd skills-dev/arena
pi
```

> **首次信任**：pi 对项目有信任机制。若第一次在 `arena/` 跑 pi 提示不受信任，
> 需要在知识/信任确认后重开会话，才会加载 `.pi/skills/` 下的技能。

### 2. 触发 skill

- **自动触发**：在对话里提出与 skill `description` 匹配的任务，模型会按需 `read` 加载 SKILL.md。
- **强制加载**（推荐用于测试确定性）：用命令 `/skill:<name>`，例如：

```
/skill:vision-augment
```

### 3. 验证效果

按 skill 自身文档准备输入、调用脚本、检查输出。例如 vision-augment：

```bash
mkdir -p .pi/tmp/image
cp ../assets/sample.png .pi/tmp/image/     # 放一张测试图
# 让 pi 调用 skill 描述这张图，或用 --json 看原始返回以排查
```

## ⚠️ 调用规范：配置缺失时由 pi agent 在对话里向用户提问并持久化

> **这是测试 vision-augment 最需要遵守的一条**，否则会卡住。

**问题**：`describe.py` 在视觉模型配置缺失时会走 `input()` **交互式询问，阻塞进程**。
在 pi 的自动化/对话上下文里，这会卡死而拿不到任何结果。

**正确做法**（约定给 pi agent）：

1. 调用前先跑探测脚本，判断配置是否就绪：

   ```bash
   bash arena/vision-config.sh
   ```

2. **已配置完整**（退出码 0）→ 直接以 **`-y` 非交互**方式调用，绝不阻塞：

   ```bash
   python3 vision-augment/scripts/describe.py -y vision-augment/demo.png --mode detailed
   ```

3. **未配置**（退出码 2）→ **不要**直接跑 describe.py 让它卡在 `input()` 上，
   而是由 **pi agent 在对话里向用户提问**，拿到配置后**持久化**，再继续：

   - 在对话中询问用户两项（可带默认值/示例）：
     - 视觉模型网关地址 `api_base`（如 `http://host:port/v1`）
     - 视觉模型名 `model`（如 `glm-5.2`）
     - （可选）`api_key`，默认 `dummy`
   - 拿到后持久化，任选其一：
     - 临时（仅本次会话）：设置环境变量再调用
       ```bash
       export VISION_API_BASE="<地址>" VISION_MODEL="<模型>" VISION_API_KEY="dummy"
       ```
     - 持久化（推荐，下次复用）：`python3 vision-augment/scripts/setup.py --set` 交互写入
     - 或手动写 `~/.config/vision-augment/settings.json`
   - 配置就绪后，一律带 `-y` 调用 describe.py。

> 一句话：**配置缺失 → agent 用对话问用户 → 持久化 → `-y` 调用**。
> 不要让 `describe.py` 自己在子进程里 `input()`，那会阻塞。依赖 `vision-config.sh`
> 探测，用退出码驱动 agent 的分支（问用户 / 直接跑）。

### 测试脚本一览（arena）

| 脚本 | 作用 | 退出码 |
|------|------|--------|
| `setup.sh` | 为仓库所有 skill 建软链到 `.pi/skills/` | - |
| `vision-config.sh` | 探测 vision-augment 配置是否就绪 | 0=就绪 / 2=需问用户 |

### 一次完整的 dialog 示例（给 pi agent 的剧本）

```
用户: 请描述这张图 vision-augment/demo.png

agent: bash arena/vision-config.sh        # 先探测
       → 退出码 2（未配置）

agent: 需要先配置视觉模型才能描述图片。
       请提供：
         1) 视觉模型网关地址(api_base)，如 http://host:port/v1
         2) 视觉模型名(model)，如 glm-5.2
       （api_key 可留空，默认 dummy）

用户: 用 http://10.0.0.5:8000/v1  模型 glm-5.2

agent: python3 vision-augment/scripts/setup.py --set   # 持久化（或写 settings.json）
       python3 vision-augment/scripts/describe.py -y vision-augment/demo.png --mode detailed
       → 返回描述先验，结合用户问题作答。
```

## 新增一个 skill 到 arena

```bash
# 在 arena 下做软链即可（真实 skill 保持在仓库主目录，单一事实源）
cd arena/.pi/skills
ln -s ../../../my-skill my-skill
```

或者运行一次自动脚本 `./setup.sh`（会自动为 `../` 下所有含 SKILL.md 的目录建链，
并顺带把每个 skill 下 `extension/*.ts` 软链进 `arena/.pi/extensions/`）。

> **关于「主动型 skill」（如监控智能体）**：技能（SKILL.md）是**被动**的，只有模型按需
> `read` 才加载；而像监控这种需要**定时巡检、监听事件、注册自定义工具、推送告警**的
> 主动行为，必须放在 **extension**（`.pi/extensions/monitor.ts`）里。`setup.sh` 已自动把
> skill 的 `extension/` 目录软链进 `arena/.pi/extensions/`，因此**在 arena 里启动 pi 即可**
> 同时发现技能（领域知识）和扩展（主动能力）。

## 注意事项

- **软链与 Git**：Windows 下 `git` 对符号链接支持有限。若 clone 后软链丢失，
  重跑 `./setup.sh` 一键重建即可（软链本身不提交，脚本提交）。
- **运行时产物不提交**：`.pi/tmp/`、测试图片、描述缓存都属于运行时数据，
  保持 git ignore 干净，只提交测试脚本/样例输入。
- 每个 skill 的测试请尽量沉淀成 `tests/<skill-name>/` 下的用例与预期结果，
  方便回归。
