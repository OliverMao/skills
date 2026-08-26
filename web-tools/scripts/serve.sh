#!/usr/bin/env bash
# 开启 Obscura 无头浏览器（CDP over HTTP+WebSocket），端口可 PORT=xxxx 覆盖
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BIN="$SCRIPT_DIR/bin/obscura"
PORT="${PORT:-9222}"

[ -x "$BIN" ] || { echo "缺少二进制：先 bash scripts/download.sh" >&2; exit 1; }

mkdir -p "$ROOT_DIR/logs"

if curl -s -m 1 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo ">> 端口 $PORT 已有 Obscura 服务，跳过启动"
else
  nohup "$BIN" serve --port "$PORT" --allow-private-network \
    > "$ROOT_DIR/logs/serve.log" 2>&1 &
  echo ">> 已后台启动 serve (pid $!)"
  sleep 1
fi

curl -s "http://127.0.0.1:$PORT/json/version"; echo
echo ">> 浏览器 CDP WebSocket: ws://127.0.0.1:$PORT/devtools/browser"
echo ">> HTTP 信息:            http://127.0.0.1:$PORT/json"
