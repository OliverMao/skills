#!/usr/bin/env bash
# 停止本 skill 启动的 serve（按本 skill 的二进制路径过滤，不影响他处）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$SCRIPT_DIR/bin/obscura"

for pid in $(pgrep -f "$BIN" || true); do
  cmd="$(tr '\0' ' ' </proc/$pid/cmdline 2>/dev/null || true)"
  case "$cmd" in
    *"serve --port"*) kill "$pid" && echo ">> 已停 serve (pid $pid)" ;;
  esac
done
exit 0
