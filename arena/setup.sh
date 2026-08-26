#!/usr/bin/env bash
# 在 arena 下为仓库中所有 skill 建立 pi 可发现的软链。
# 用法：bash arena/setup.sh
# 效果：
#   - 为 ../ 下每个含 SKILL.md 的目录，在 arena/.pi/skills/ 下创建同名软链。
#   - 为 ../ 下每个含 extension/*.ts 的 skill，把其 extension 软链进 arena/.pi/extensions/。
#     （这样在 arena 里跑 pi，主动能力（定时巡检/事件钩子/自定义工具）才能被加载）

set -euo pipefail

ARENA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_ROOT="$(dirname "$ARENA_DIR")"           # ../ = skills-dev 仓库根
SKILL_TARGET="$ARENA_DIR/.pi/skills"
EXT_TARGET="$ARENA_DIR/.pi/extensions"

mkdir -p "$SKILL_TARGET" "$EXT_TARGET"

linked=0
exts=0
for dir in "$SKILLS_ROOT"/*/; do
  name="$(basename "$dir")"
  [ "$name" = "arena" ] && continue

  # 1) skill 软链
  if [ -f "$dir/SKILL.md" ]; then
    ln -sfn "../../../$name" "$SKILL_TARGET/$name"
    printf 'linked  skill %s -> ../../../%s\n' "$name" "$name"
    linked=$((linked + 1))
  fi

  # 2) extension 软链（skill 下约定 extension/*.ts 为能力层）
  for ext in "$dir"/extension/*.ts; do
    [ -e "$ext" ] || continue
    ext_name="$(basename "$ext")"
    # arena/.pi/extensions -> ../../.. = 仓库根
    ln -sfn "../../../$name/extension/$ext_name" "$EXT_TARGET/$ext_name"
    printf 'linked  ext   %s -> ../../../%s/extension/%s\n' "$ext_name" "$name" "$ext_name"
    exts=$((exts + 1))
  done
done

[ "$linked" -eq 0 ] && echo "未发现任何 skill（缺 SKILL.md 的目录已跳过）。" || echo "完成：共链接 $linked 个 skill 到 $SKILL_TARGET"
[ "$exts" -eq 0 ] && echo "未发现任何 extension（缺 extension/*.ts 的 skill 已跳过）。" || echo "完成：共链接 $exts 个 extension 到 $EXT_TARGET"
