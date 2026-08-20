#!/usr/bin/env bash
# 在 arena 下为仓库中所有 skill 建立 pi 可发现的软链。
# 用法：bash arena/setup.sh
# 效果：为 ../ 下每个含 SKILL.md 的目录，在 arena/.pi/skills/ 下创建同名软链。

set -euo pipefail

ARENA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_ROOT="$(dirname "$ARENA_DIR")"           # ../ = skills-dev 仓库根
TARGET_DIR="$ARENA_DIR/.pi/skills"

mkdir -p "$TARGET_DIR"

linked=0
for dir in "$SKILLS_ROOT"/*/; do
  name="$(basename "$dir")"
  [ "$name" = "arena" ] && continue
  [ -f "$dir/SKILL.md" ] || continue
  # 相对软链：arena/.pi/skills/<name> -> ../../../<name>
  ln -sfn "../../../$name" "$TARGET_DIR/$name"
  printf 'linked  %s -> %s\n' "$name" "../../../$name"
  linked=$((linked + 1))
done

if [ "$linked" -eq 0 ]; then
  echo "未发现任何 skill（缺 SKILL.md 的目录已跳过）。"
else
  echo "完成：共链接 $linked 个 skill 到 $TARGET_DIR"
fi
