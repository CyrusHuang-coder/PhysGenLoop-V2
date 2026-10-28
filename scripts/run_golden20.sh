#!/usr/bin/env bash
# ==============================================================================
# PhysGenLoop V2 Golden-20 一键运行与自动化审计脚本
# ==============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUN_ROOT="${1:-$PROJECT_ROOT/outputs/v2_golden20_run}"
LOG_FILE="$RUN_ROOT/physgenloop.log"
STATUS_FILE="$RUN_ROOT/exit.status"
PID_FILE="$RUN_ROOT/process.pid"

MANIFEST="$PROJECT_ROOT/evaluation/manifests/videophy2_top20_golden.json"
LIMIT=20
MAX_ROUNDS=2

echo "=========================================================="
echo "PhysGenLoop V2 Golden-20 闭环实验启动"
echo "Project Root : $PROJECT_ROOT"
echo "Manifest     : $MANIFEST"
echo "Output Root  : $RUN_ROOT"
echo "Limit        : $LIMIT samples"
echo "Max Rounds   : $MAX_ROUNDS"
echo "=========================================================="

mkdir -p "$RUN_ROOT"

if [ -f "$RUN_ROOT/run_manifest.json" ]; then
    echo "Notice: Detected existing run_manifest.json. Using --resume to continue..."
    RESUME_FLAG="--resume"
else
    RESUME_FLAG=""
fi

export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"

# 默认优先使用 envs/main/bin/python，不存在时回退系统 python
if [ -x "$PROJECT_ROOT/envs/main/bin/python" ]; then
    PYTHON_EXEC="$PROJECT_ROOT/envs/main/bin/python"
else
    PYTHON_EXEC="python"
fi

echo "Using Python: $PYTHON_EXEC"
echo "Starting loop in background, logging to $LOG_FILE ..."

nohup "$PYTHON_EXEC" agents/wanphysics/run_videophy2_loop_v2.py \
    --enable \
    --manifest "$MANIFEST" \
    --limit "$LIMIT" \
    --max-rounds "$MAX_ROUNDS" \
    --output-root "$RUN_ROOT" \
    $RESUME_FLAG > "$LOG_FILE" 2>&1 &

PID=$!
echo "$PID" > "$PID_FILE"

echo "Process started with PID: $PID"
echo "Run tracking: tail -f $LOG_FILE"
echo "After run finishes, run: python scripts/analyze_golden20.py --run-dir $RUN_ROOT"

