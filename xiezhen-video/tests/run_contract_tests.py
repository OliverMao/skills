#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def ok(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


skill = read("SKILL.md")
reshoot = read("references/production-reshoot.md")
logic = read("references/prompt-logic.md")
readme = read("README.md")
source = read("SOURCE.md")
changelog = read("CHANGELOG.md")
license_text = read("LICENSE")

ok(skill.startswith("---\n"), "missing frontmatter")
ok("name: kagnet-xiezhen-video" in skill, "name mismatch")
ok("视频企划复拍工作流" in skill, "video reshoot route missing")
ok("只有用户明确要求生成视频" in skill, "generation authorization boundary missing")
ok("不绑定具体视频平台或模型" in skill, "platform-neutral boundary missing")
ok("同系列视频变体关键词链" in skill, "ordinary variant route regressed")
ok("视频系列母版" in skill and "抽卡短视频关键词" in skill, "legacy output modes regressed")
ok("不检查组内是否为同一张脸" in skill, "no-identity consistency boundary missing")
ok("每一轮都从原始人物素材" in skill, "original-input reset missing from entrypoint")
ok("上一轮生成视频只用于诊断问题" in skill, "generated-video input boundary missing from entrypoint")
ok("比上一轮更顺滑更有风格" in skill and "不能替代原作保真" in skill, "absolute-fidelity gate missing from entrypoint")
ok("去商业抛光层" in skill and "精致 editorial 视频原作不套用" in skill, "commercial-polish boundary missing from entrypoint")
ok("跨镜头与跨段一致性" in skill, "cross-segment consistency boundary missing from entrypoint")
ok("默认不添加任何署名或水印" in skill, "opt-in signature boundary missing from entrypoint")
ok("Eagle 只在当前环境可用时作为附加归档" in skill, "optional Eagle boundary missing from entrypoint")
ok("完整 Prompt、参考职责、质量状态与追溯记录" in skill, "portable conversation delivery missing from entrypoint")
ok(len(skill) < 7500, f"SKILL.md too heavy: {len(skill)} chars")

frontmatter = skill.split("---", 2)[1]
ok(set(re.findall(r"^([a-z_]+):", frontmatter, re.M)) == {"name", "description", "license", "metadata"}, "frontmatter keys drifted")
ok("license: MIT" in frontmatter, "public MIT license metadata missing")
ok('version: "0.1.0"' in frontmatter, "public version must be 0.1.0")
ok('source: "https://github.com/kagnet-ai-works/kagnet-xiezhen-video"' in frontmatter, "public source metadata missing")

required = [
    "AGENTS.md",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "SOURCE.md",
    "references/prompt-logic.md",
    "references/production-reshoot.md",
    "evals/skin_reflection_cases.json",
    "evals/production_reshoot_cases.json",
    "evals/trigger_cases.json",
    "evals/semantic_config.json",
]
for relative in required:
    ok((ROOT / relative).is_file(), f"missing {relative}")

ok(license_text.startswith("MIT License"), "LICENSE is not MIT")
ok("## 0.1.0" in changelog, "CHANGELOG missing 0.1.0")
ok("公开发行仓库" in source and "0.1.0" in source, "SOURCE public release relationship missing")
ok("视频写真提示词" in source, "SOURCE video re-theme missing")

for marker in [
    "共同写真套餐",
    "布光子方案",
    "运动与时间子语法",
    "运动光照拓扑重建",
    "事件弧",
    "人物事件与动作弧因果",
    "背景信息层级",
    "光源—遮挡—落点—反射—曝光—时间",
    "机位变化和镜头运动都不能带着光源一起旋转",
    "拓扑预测",
    "光源证据不足",
    "1 份主参考",
    "最多 2 份辅助参考",
    "辅助参考不是配额",
    "不能仅因多段都明亮",
    "商业摄影升级",
    "未指定时默认 5 段",
    "不生成校准段",
    "不自动重试",
    "写真套餐",
    "布光曝光",
    "色彩关系",
    "成像质感",
    "事件弧与表情因果",
    "镜头运动一致性",
    "主体清晰区",
    "连续低细节区或留白",
    "不能判为通过",
    "不得标记为 `adopted` 或 `final`",
    "原始输入重置合同",
    "上一轮生成视频只用于诊断问题",
    "generated_video_inputs: none",
    "重新编译的一条完整新视频 Prompt",
    "原作绝对保真",
    "相对改善",
    "去商业抛光层",
    "连续暖色发丝轮廓光",
    "焦点可以落在前方栏杆、飞动发丝或邻近物体",
    "服装若在原作中主要作为黑色大形",
    "不要把低机位、环绕或缓推自动组织成英雄式时装广告",
    "精致 editorial",
    "完成核心交付后，才检测可选 Eagle 集成",
    "未归档到 Eagle",
    "不承诺任何具体平台",
]:
    ok(marker in reshoot, f"reshoot contract missing {marker}")

for marker in [
    "生成人物与参考人物",
    "不要把上一段生成视频自动作为下一段输入",
    "不在后台多生成候选",
    "不能使用综合色彩分数",
]:
    ok(marker in reshoot, f"reshoot failure boundary missing {marker}")

for forbidden in ["三层 Look Control", "色彩比例与明度卡", "空间光场卡", "无身份材质受光卡", "批量生成前只做一张校准样张"]:
    ok(forbidden not in skill and forbidden not in logic and forbidden not in readme, f"retired default remains active: {forbidden}")

ok("上一段生成视频只用于判断哪里失败，不作为新一轮输入" in readme, "README original-input reset missing")
ok("默认不在视频中加入 `kagnet`" in readme, "README opt-in signature boundary missing")
ok("Eagle 只是检测可用后执行的可选归档" in readme, "README optional Eagle boundary missing")
ok("Eagle、个人知识库和其它本地 Skill 都不是使用本 Skill 的前提" in readme, "README portability boundary missing")
ok("不绑定具体视频平台或模型" in readme and "说明未执行生成" in readme, "README degradation boundary missing")
ok("没有视频生成工具时" in skill and "不得声称已经出视频" in skill, "entrypoint no-video-tool degradation missing")
ok("没有视频生成工具时" in readme and "不伪造结果" in readme, "README no-video-tool degradation missing")

text_suffixes = {".md", ".json", ".yaml", ".yml", ".txt", ".py"}
private_absolute_prefix = "/" + "Users/"
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or (path.suffix.lower() not in text_suffixes and path.name != "LICENSE"):
        continue
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(ROOT)
    ok(private_absolute_prefix not in text, f"absolute private path remains in {relative}")

for marker in ["皮肤纹理与皮肤反射分开写", "时间先于构图", "同系列视频变体关键词链", "详细视频提示词模板", "抽卡短视频关键词模板"]:
    ok(marker in logic, f"video prompt contract missing {marker}")

ok("不绑定具体视频平台或模型" in logic, "prompt logic platform-neutral boundary missing")
ok("默认不加任何署名或水印" in logic, "prompt logic opt-in signature boundary missing")
ok("视觉底座/" not in logic, "private knowledge-base dependency remains in prompt logic")
ok(private_absolute_prefix not in logic, "absolute package-external dependency remains in prompt logic")

cases = json.loads(read("evals/production_reshoot_cases.json"))
ok(len(cases.get("cases", [])) >= 18, "weak production reshoot cases")
case_ids = {case.get("id") for case in cases.get("cases", [])}
for case_id in [
    "video-reshoot-five-segments",
    "auxiliary-reference-is-not-a-quota",
    "video-reshoot-with-identity-image",
    "neutral-identity-action-arc-release",
    "reference-background-information-hierarchy",
    "no-event-stiff-video-quality-gate",
    "video-redo-from-original-inputs",
    "relative-improvement-is-not-original-fidelity",
    "raw-reference-commercial-polish-suppression",
    "polished-editorial-reference-keeps-polish",
    "ambiguous-person-image-role",
    "portable-delivery-without-eagle",
    "default-no-signature",
    "explicit-custom-signature",
    "no-platform-binding-degradation",
    "analysis-only-neighbor",
    "ordinary-variant-neighbor",
    "exact-count-and-failure",
    "camera-move-light-not-rotate",
    "low-angle-under-eaves-topology",
    "insufficient-light-source-evidence",
]:
    ok(case_id in case_ids, f"missing video reshoot case {case_id}")

cases_by_id = {case.get("id"): case for case in cases.get("cases", [])}
portable = cases_by_id.get("portable-delivery-without-eagle", {})
ok("在对话中交付每段完整视频 Prompt" in portable.get("mustCover", []), "portable eval must require complete prompts in conversation")
ok("因为缺少个人知识库而中断" in portable.get("mustAvoid", []), "portable eval must reject private knowledge-base dependency")
unsigned = cases_by_id.get("default-no-signature", {})
ok("默认不添加任何署名、水印或片尾文字" in unsigned.get("mustCover", []), "unsigned eval must enforce no default signature")
custom_signed = cases_by_id.get("explicit-custom-signature", {})
ok("kagnet" in custom_signed.get("mustAvoid", []), "custom-signature eval must reject inherited author name")
degraded = cases_by_id.get("no-platform-binding-degradation", {})
ok("不绑定任何具体平台或模型名词" in degraded.get("mustAvoid", []), "platform-neutral eval must reject bound wording")

triggers = json.loads(read("evals/trigger_cases.json"))
for bucket, minimum in {"should_trigger": 8, "should_not_trigger": 5, "near_neighbor": 5}.items():
    ok(len(triggers.get(bucket, [])) >= minimum, f"weak trigger bucket: {bucket}")

skin = json.loads(read("evals/skin_reflection_cases.json"))
ok(len(skin.get("cases", [])) >= 3, "weak skin reflection cases")

if errors:
    print("FAIL")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("kagnet-xiezhen-video video contract tests passed")
