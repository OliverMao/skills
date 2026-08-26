#!/usr/bin/env bash
# 对 URL 截图并返回：shot.sh <url> [out.png]
# 环境变量：WAIT=load|domcontentloaded|networkidle0 (默认 networkidle0)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BIN="$SCRIPT_DIR/bin/obscura"
WAIT="${WAIT:-networkidle0}"

[ -x "$BIN" ] || { echo "缺少二进制：先 bash scripts/download.sh" >&2; exit 1; }
[ $# -ge 1 ] || { echo "用法: $0 <url> [out.png]" >&2; exit 2; }

URL="$1"
OUT="${2:-$ROOT_DIR/screenshots/$(date +%Y%m%d-%H%M%S).png}"
mkdir -p "$(dirname "$OUT")"

"$BIN" fetch "$URL" --wait-until "$WAIT" -s "$OUT" --allow-private-network
echo ">> $OUT"
