#!/usr/bin/env bash
# 注册本 skill 为 pi 全局技能（注册名 web-tools）。
# 关键：Windows/WSL 下必须用 Windows 原生 junction（mklink /J），
#       否则 WSL 的 ln -s 建出的 Linux 符号链接 Windows pi 读不到（EACCES）。
# 用法：bash scripts/install.sh [目标目录]   (默认自动定位 pi 全局 skills 目录)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
NAME="web-tools"

# 定位真正的 pi 全局 skills 目录
if [ -n "${1:-}" ]; then
  TARGET_ROOT="$1"
elif [ -d /mnt/c/Users ]; then
  TARGET_ROOT="$(ls -d /mnt/c/Users/*/.pi/agent/skills 2>/dev/null | head -1)"
  [ -n "$TARGET_ROOT" ] || TARGET_ROOT="$HOME/.pi/agent/skills"
else
  TARGET_ROOT="$HOME/.pi/agent/skills"
fi

TARGET="$TARGET_ROOT/$NAME"
mkdir -p "$TARGET_ROOT"

# 清理旧目标（目录 / 软链 / junction 都可 rm -rf 处理）
[ -e "$TARGET" ] && rm -rf "$TARGET"

if [ -x "$(command -v cmd.exe)" ] && [ -d /mnt/c ]; then
  # Windows/WSL：用 Windows 原生 junction（WSL 的 ln -s 建的软链 Windows pi 读不到 EACCES）
  win_target="$(wslpath -w "$TARGET")"
  win_src="$(wslpath -w "$SKILL_DIR")"
  cmd.exe /c "mklink /J $win_target $win_src" >/dev/null
  echo ">> 已注册(junction): $TARGET -> $SKILL_DIR"
else
  # Linux/macOS：普通软链
  ln -s "$SKILL_DIR" "$TARGET"
  echo ">> 已注册(软链): $TARGET -> $SKILL_DIR"
fi

# 清理旧版同名残留（曾以 web-tool 安装）
if [ -e "$TARGET_ROOT/web-tool" ]; then
  rm -rf "$TARGET_ROOT/web-tool"
  echo ">> 已清理旧技能: $TARGET_ROOT/web-tool"
fi

# 保证二进制可用：skill 要求 scripts/bin/obscura 在；缺失时幂等自动下载（约 200MB，仅首次）
BIN="$SKILL_DIR/scripts/bin/obscura"
if [ ! -x "$BIN" ]; then
  echo ">> 检测到缺少无头浏览器二进制，自动下载中（bash scripts/download.sh）..."
  ( cd "$SKILL_DIR" && bash scripts/download.sh ) || echo "!! 下载失败，可稍后手动运行 bash scripts/download.sh"
else
  echo ">> 二进制就绪: $BIN"
fi

echo ">> 重新打开 pi 会话后可用 /skill:$NAME 或自动按描述加载"
