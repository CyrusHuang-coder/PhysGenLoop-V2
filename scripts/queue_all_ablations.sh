#!/usr/bin/env bash
# ==============================================================================
# PhysGenLoop V2 全自动消融实验接力队列 (Queue Runner)
# 功能：
# 1. 自动等待正在后台运行的 M3 (Full) 实验顺利完成；
# 2. 依次自动启动 M0 (Direct) -> M1 (Prompt-only) -> M2 (Local-only)；
# 3. 每步之间预留显存彻底释放时间；
# 4. 全部完成后，自动调用 plot_ablation_results.py 绘制 300 DPI 图表与学术对比报告！
# ==============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "PhysGenLoop V2 自动接力调度器已就绪"
echo "工作目录: $PROJECT_ROOT"
echo "=========================================================="

# 等待指定 PID 进程彻底结束
wait_for_pid() {
    local pid_file="$1"
    local name="$2"
    echo "[Queue] 正在监控 $name 运行状态..."
    sleep 5
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo "[Queue] $name 目标进程 PID: $pid"
        while kill -0 "$pid" 2>/dev/null; do
            sleep 15
        done
        echo "[Queue] $name (PID: $pid) 已顺利执行完毕！"
    else
        echo "[Queue] 未找到 PID 文件 $pid_file，等待任何运行中的 V2 任务退出..."
        while pgrep -f "agents/wanphysics/run_videophy2_loop_v2.py" > /dev/null; do
            sleep 15
        done
    fi
    # 显存安全缓冲，等待 PyTorch 与驱动彻底回收显存
    echo "[Queue] 预留 15 秒显存彻底回收缓冲时间..."
    sleep 15
}

# ------------------------------------------------------------------------------
# 阶段 1: 等待当前正在跑的 M3 (Full)
# ------------------------------------------------------------------------------
echo ">>> [阶段 1/4] 正在等待当前的 M3 (Full) 20 样本全闭环完成..."
wait_for_pid "$PROJECT_ROOT/outputs/ablation_m3_full/process.pid" "M3_Full"

# ------------------------------------------------------------------------------
# 阶段 2: 启动并等待 M0 (Direct 基线直出)
# ------------------------------------------------------------------------------
echo ">>> [阶段 2/4] 启动 M0 (Direct) 直出无闭环基线评测..."
bash scripts/run_ablation.sh direct 20
wait_for_pid "$PROJECT_ROOT/outputs/ablation_m0_direct/process.pid" "M0_Direct"

# ------------------------------------------------------------------------------
# 阶段 3: 启动并等待 M1 (Prompt-only 纯提示词修复消融)
# ------------------------------------------------------------------------------
echo ">>> [阶段 3/4] 启动 M1 (Prompt-only) 纯提示词修复消融实验..."
bash scripts/run_ablation.sh prompt_only 20
wait_for_pid "$PROJECT_ROOT/outputs/ablation_m1_prompt_only/process.pid" "M1_PromptOnly"

# ------------------------------------------------------------------------------
# 阶段 4: 启动并等待 M2 (Local-only 纯局部编辑消融)
# ------------------------------------------------------------------------------
echo ">>> [阶段 4/4] 启动 M2 (Local-only) 纯局部编辑消融实验..."
bash scripts/run_ablation.sh local_only 20
wait_for_pid "$PROJECT_ROOT/outputs/ablation_m2_local_only/process.pid" "M2_LocalOnly"

# ------------------------------------------------------------------------------
# 阶段 5: 自动统计四组数据，绘制 300 DPI 高清对比图与学术报表
# ------------------------------------------------------------------------------
echo "=========================================================="
echo ">>> [阶段 5/5] 四组消融实验全部顺利跑完！开始全自动分析出图..."
echo "=========================================================="

export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
python scripts/plot_ablation_results.py --outputs-dir outputs

echo "=========================================================="
echo "🎉 恭喜！全部消融实验与论文级图表全部生成成功！"
echo "图表与报告保存在: outputs/figures/"
echo "=========================================================="

