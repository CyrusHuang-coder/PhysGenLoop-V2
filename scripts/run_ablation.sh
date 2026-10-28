#!/usr/bin/env bash
# ==============================================================================
# PhysGenLoop V2 科学消融实验一键运行脚本 (Ablation Runner)
# 支持受控对比: direct | prompt_only | local_only | full
# ==============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODE="${1:-full}"
LIMIT="${2:-20}"

case "$MODE" in
  direct)
    CONFIG="$PROJECT_ROOT/configs/ablation_m0_direct.yaml"
    MAX_ROUNDS=0
    RUN_ROOT="$PROJECT_ROOT/outputs/ablation_m0_direct"
    ;;
  prompt_only)
    CONFIG="$PROJECT_ROOT/configs/ablation_m1_prompt_only.yaml"
    MAX_ROUNDS=2
    RUN_ROOT="$PROJECT_ROOT/outputs/ablation_m1_prompt_only"
    ;;
  local_only)
    CONFIG="$PROJECT_ROOT/configs/ablation_m2_local_only.yaml"
    MAX_ROUNDS=2
    RUN_ROOT="$PROJECT_ROOT/outputs/ablation_m2_local_only"
    ;;
  full)
    CONFIG="$PROJECT_ROOT/configs/loop_v2.yaml"
    MAX_ROUNDS=2
    RUN_ROOT="$PROJECT_ROOT/outputs/ablation_m3_full"
    ;;
  *)
    echo "Usage: $0 [direct|prompt_only|local_only|full] [limit]"
    echo "  direct      : M0 无闭环直出基线 (max_rounds=0)"
    echo "  prompt_only : M1 纯 Prompt 修复消融 (local_editing 冻结)"
    echo "  local_only  : M2 纯局部编辑消融 (prompt_repair 冻结)"
    echo "  full        : M3 完整双算子协同闭环 (PhysGenLoop V2)"
    exit 1
    ;;
esac

MANIFEST="$PROJECT_ROOT/evaluation/manifests/videophy2_top20_golden.json"
LOG_FILE="$RUN_ROOT/physgenloop.log"
PID_FILE="$RUN_ROOT/process.pid"

mkdir -p "$RUN_ROOT"

echo "=========================================================="
echo "PhysGenLoop V2 消融实验启动: $MODE"
echo "Config      : $CONFIG"
echo "Manifest    : $MANIFEST"
echo "Output Root : $RUN_ROOT"
echo "Sample Limit: $LIMIT"
echo "Max Rounds  : $MAX_ROUNDS"
echo "=========================================================="

if [ -f "$RUN_ROOT/run_manifest.json" ]; then
    echo "Notice: Detected existing run_manifest.json. Using --resume to continue..."
    RESUME_FLAG="--resume"
else
    RESUME_FLAG=""
fi

export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"

if [ -x "$PROJECT_ROOT/envs/main/bin/python" ]; then
    PYTHON_EXEC="$PROJECT_ROOT/envs/main/bin/python"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_EXEC="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON_EXEC="python"
fi

echo "Using Python: $PYTHON_EXEC"
echo "Starting loop in background, logging to $LOG_FILE ..."

nohup "$PYTHON_EXEC" agents/wanphysics/run_videophy2_loop_v2.py \
    --enable \
    --config "$CONFIG" \
    --manifest "$MANIFEST" \
    --limit "$LIMIT" \
    --max-rounds "$MAX_ROUNDS" \
    --output-root "$RUN_ROOT" \
    $RESUME_FLAG > "$LOG_FILE" 2>&1 &

PID=$!
echo "$PID" > "$PID_FILE"

echo "Process started with PID: $PID"
echo "To track log: tail -f $LOG_FILE"
echo "After all finishes, run:"
echo "  python scripts/plot_ablation_results.py --outputs-dir outputs"

