# 写真 Video Skill

写真视频写作与生成 Skill（`kagnet-xiezhen-video`）。支持完整中文视频 Prompt、系列母版、同系列变体、网页端抽卡短视频关键词、参考拆解，以及“换一位人物、按同一摄影企划重新拍摄新分镜视频”的视频企划复拍模式。本 Skill 不绑定具体视频平台或模型：真实视频生成由宿主智能体按当前可用工具执行，本 Skill 只负责把企划编译成任何平台都能消费的中文拍摄指令与可移植参数。

## 安装（pi）

本 Skill 按 Agent Skills 规范打包：发行仓库根目录就是技能目录（含 `SKILL.md`），pi 会在技能位置递归发现它。安装 = 把仓库放到 pi 能扫描到的位置，任选其一：

### 全局安装（推荐）

克隆到 pi 的全局技能目录：

```bash
git clone https://github.com/kagnet-ai-works/kagnet-xiezhen-video.git ~/.pi/agent/skills/kagnet-xiezhen-video
```

Windows 下等价于 `%USERPROFILE%\.pi\agent\skills\kagnet-xiezhen-video`。没有 Git 时，从 [知识站](https://knowledge.kagnetonline.com/skills/kagnet-xiezhen-video) 或发行仓库下载 ZIP，解压到该目录并保持文件夹名为 `kagnet-xiezhen-video`。

### 项目级安装

只在本项目内使用时可克隆到 `.pi/skills/`（首次启动会询问是否信任该项目）：

```bash
git clone https://github.com/kagnet-ai-works/kagnet-xiezhen-video.git .pi/skills/kagnet-xiezhen-video
```

### 通过 settings 引用任意目录

仓库想留在自己的工作区里、由 Git 统一管理时，在 `~/.pi/agent/settings.json`（全局）或 `.pi/settings.json`（项目）中加：

```json
{
  "skills": ["~/dev/kagnet-xiezhen-video"]
}
```

### 更新已有安装

```bash
cd ~/.pi/agent/skills/kagnet-xiezhen-video && git pull
```

按实际安装位置调整路径。更新后重启 pi 或新建会话，让新版指令进入上下文。

### 确认生效

新会话的可用技能列表中出现 `kagnet-xiezhen-video` 即安装成功；也可用 `/skill:kagnet-xiezhen-video` 强制加载（`/skill:` 命令默认开启）。

## 它解决什么

普通请求默认只交付视频 Prompt。只有用户明确要求生成视频时，视频企划复拍模式才会由环境提供的视频生成工具生成指定数量的短视频并逐段检查。完整 Prompt、参考职责、质量状态和追溯记录直接在对话中交付；Eagle 只是检测可用后执行的可选归档，未安装或不可用不会中断任务。

视频提示词强调“时间先于构图”：每段先确定一条真实发生的事件弧（发生—推进—结果），再匹配一次有起幅落幅的镜头运动，然后是随时间稳定的妆造、服装、主导光线与场景，最后才是成像质感。它把图片版的空间细节改写成“光线随事件演化”“动作从发生到结果”“跨镜头人物与光线一致性”这些视频特有的可观察机制。

视频企划复拍会把人物身份与本段动作弧分开控制：身份素材只提供稳定五官锚点，目标场景中的具体事件负责眉眼、呼吸、嘴角、视线和身体反应的时间推进；同时按参考重建主体清晰区、主导大形、次级细节和低细节留白，并保证机位运动时不把光源带着旋转。

用户要求重做时，每一轮都会回到原始人物素材与对应参考，从视频企划和本轮反馈重新编译完整 Prompt。上一段生成视频只用于判断哪里失败，不作为新一轮输入；新段也直接对照原作验收，不以“比上一轮顺滑”代替企划保真。

原作若依赖欠曝、失焦、堵黑和偶发抓拍，复拍会额外检查模型是否自行补入连续暖色轮廓光、稳定脸部焦点、皮革塑形、正面回填或英雄式运镜，并把这些商业抛光改写为原作支持的曝光与焦点关系；精致 editorial 视频原作不会被统一做脏。

这不是换脸工具，也不承诺像素级复刻。它重建的是可观察的视频拍摄方案：事件弧、镜头运动、光源、机位、曝光、背景信息层级、跨段一致性和成像质感。结果仍受宿主视频生成工具、参考质量与人物授权影响。

## 署名与归档

- 默认不在视频中加入 `kagnet` 或任何其他署名、水印、片尾文字。
- 只有用户明确要求并给出署名文字时，才把该文字写入 Prompt。
- Eagle、个人知识库和其它本地 Skill 都不是使用本 Skill 的前提；Eagle 归档成功时会额外返回 Eagle ID，失败时仍保留完整的对话交付。

## 普通提示词

```text
使用 $kagnet-xiezhen-video，为这个主题写一段视频写真提示词。
```

## 视频企划复拍

```text
使用 $kagnet-xiezhen-video。参考这组写真，换一位原创人物，像去同一家摄影店拍同一套企划那样重新设计 5 段新分镜视频，并直接生成。
```

## 文件结构

- `SKILL.md`：触发、授权、输出和跨环境边界。
- `references/`：视频提示词模板与视频企划复拍工作流。
- `evals/`：触发、皮肤反射和复拍回归案例。
- `tests/`：公开发行与行为合同测试。
- `CHANGELOG.md`：公开版本变化。

## 能力边界

- 只要视频 Prompt 时不会擅自生成视频。
- 明确要求生成但环境没有视频生成工具时，会交付完整 Prompt 与拍摄方案并说明未执行生成，不伪造结果。
- 不绑定任何具体视频平台或模型；平台适配由宿主智能体在生成环节完成。
- Eagle、个人知识库和其他本地 Skill 都不是运行前提。
- 使用参考素材和人物素材前，请自行确认版权、肖像权、商标与平台规则。

完整规则见 [SKILL.md](SKILL.md)。本项目采用 [MIT License](LICENSE)。
