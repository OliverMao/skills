#!/usr/bin/env bash
# 下载 Obscura 官方发布二进制（含 render）到 scripts/bin/
# 用法：bash scripts/download.sh [VERSION]   (缺省 latest；可传 tag 如 v0.2.1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
VERSION="${1:-latest}"
mkdir -p "$BIN_DIR"

detect() {
  local os arch
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  case "$os" in
    linux*)  os=linux ;;
    darwin*) os=macos ;;
    *) echo "不支持的系统: $os (Windows 请下载 zip 后手动放入 scripts/bin/)" >&2; exit 1 ;;
  esac
  case "$arch" in
    x86_64|amd64)    arch=x86_64 ;;
    aarch64|arm64)   arch=aarch64 ;;
    *) echo "不支持的架构: $arch" >&2; exit 1 ;;
  esac
  echo "$os $arch"
}

read -r os arch <<< "$(detect)"

if [ "$VERSION" = "latest" ]; then
  URL="https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-${arch}-${os}.tar.gz"
else
  URL="https://github.com/h4ckf0r0day/obscura/releases/download/${VERSION}/obscura-${arch}-${os}.tar.gz"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo ">> 下载 ${URL}"
curl -sL -o "$TMP/obs.tgz" "$URL" || { echo "下载失败" >&2; exit 1; }
tar xzf "$TMP/obs.tgz" -C "$TMP"

install -m755 "$TMP/obscura" "$BIN_DIR/obscura"
[ -f "$TMP/obscura-worker" ] && install -m755 "$TMP/obscura-worker" "$BIN_DIR/obscura-worker"
echo ">> 完成: $BIN_DIR"
"$BIN_DIR/obscura" --version
