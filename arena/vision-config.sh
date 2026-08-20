#!/usr/bin/env bash
# arena / vision-config.sh
# =========================================================
# 供 **pi agent 在对话中**调用，判断 vision-augment 是否已配置。
#
# 设计意图：
#   describe.py 在配置缺失时会走 input() 交互询问 → 在 pi 的自动化上下文里
#   会【卡住/阻塞】。因此不要把"那次运行"交给 describe.py 去问，
#   而是由 pi agent 先跑本脚本探测：
#
#    - 已配置完整        → 直接调 describe.py -y（绝不阻塞）
#    - 缺 api_base/model → 由 pi agent 在**对话里向用户提问**，
#                          拿到后用 setup.py --set 持久化，再继续。
#
# 退出码：
#   0  已配置完整（可安全调用 describe.py -y）
#   2  未配置（需要 pi agent 向用户提问并持久化）
#   3  环境/脚本错误
# =========================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../vision-augment" && pwd)"
CONFIG_FILE="$HOME/.config/vision-augment/settings.json"
CFG_PY="$SKILL_DIR/scripts/config.py"

echo "== vision-augment 配置就绪检查 =="
echo "配置来源优先级: 命令行 > 环境变量(VISION_API_BASE/MODEL/KEY) > 配置文件($CONFIG_FILE)"
echo ""

# 1) 环境变量
ENV_BASE="${VISION_API_BASE:-}"
ENV_MODEL="${VISION_MODEL:-}"
ENV_KEY="${VISION_API_KEY:-}"
if [ -n "$ENV_BASE" ] || [ -n "$ENV_MODEL" ]; then
    echo "[来源] 检测到环境变量:"
    [ -n "$ENV_BASE" ] && echo "       VISION_API_BASE = $ENV_BASE"
    [ -n "$ENV_MODEL" ] && echo "       VISION_MODEL   = $ENV_MODEL"
fi

# 2) 配置文件
FILE_BASE=""; FILE_MODEL=""; FILE_KEY=""
if [ -f "$CONFIG_FILE" ]; then
    FILE_BASE="$(python3 -c "import json,sys;d=json.load(open('$CONFIG_FILE'));print(d.get('api_base',''))" 2>/dev/null || true)"
    FILE_MODEL="$(python3 -c "import json,sys;d=json.load(open('$CONFIG_FILE'));print(d.get('model',''))" 2>/dev/null || true)"
    echo "[来源] 配置文件存在: $CONFIG_FILE"
fi

BASE="${ENV_BASE:-$FILE_BASE}"
MODEL="${ENV_MODEL:-$FILE_MODEL}"

echo ""
if [ -n "$BASE" ] && [ -n "$MODEL" ]; then
    echo "✔ 已配置完整（api_base=$BASE, model=$MODEL）"
    echo "   可安全调用: python3 scripts/describe.py -y <image> （-y 防止任何输入阻塞）"
    exit 0
fi

echo "✘ 未配置完整，需要向用户提问。"
[ -z "$BASE" ]  && echo "   缺失: api_base（视觉模型网关地址，如 http://host:port/v1）"
[ -z "$MODEL" ] && echo "   缺失: model（视觉模型名，如 glm-5.2）"
echo ""
cat <<'EOF'
【pi agent 应做的动作】
  1) 在对话里询问用户以下两项（不要直接跑 describe.py 的交互询问，会阻塞）:
       - 视觉模型网关地址(api_base)
       - 视觉模型名(model)
     （可选） - API Key（默认 dummy）
  2) 拿到后持久化，二选一：
       A) 设置环境变量后再调用：
            export VISION_API_BASE="<地址>" VISION_MODEL="<模型>" VISION_API_KEY="dummy"
       B) 写入配置文件(持久化)：
            python3 scripts/setup.py --set     # 交互填写
         或手动写 $CONFIG_FILE
  3) 之后一律以「-y 非交互」方式调用 describe.py，避免 input() 阻塞:
            VISION_API_BASE=... VISION_MODEL=... python3 scripts/describe.py -y demo.png --mode detailed
EOF
exit 2
