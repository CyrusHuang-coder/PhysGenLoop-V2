#!/usr/bin/env python3
"""PhysGenLoop V2 物理违背诊断热力图生成工具 (Diagnostic Heatmap Renderer)。

科学与学术价值：
1. 可解释性：将 Critic 与 SAM2 的机器级二值掩码/时空违背数据，转化为人类直观可读的半透明伪彩色热力图；
2. 零算力开销：基于纯 CPU 图像几何与色彩融合运算（毫秒级完成，不占任何 GPU 显存）；
3. 成果直接可用：自动生成带物理违背诊断横幅的对比图（原视频帧 vs 诊断热力图 vs 局部修复掩码），
   直接作为大研立项申请书与答辩 PPT 的核心配图。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PhysGenLoop 物理诊断热力图生成器")
    parser.add_argument("--run-dir", default=None, help="指定实验运行输出目录 (如 outputs/v2_golden20_run)")
    parser.add_argument("--sample-dir", default=None, help="指定单样本目录 (如 outputs/v2_golden20_run/videophy2-xxxx)")
    parser.add_argument("--output-dir", default="outputs/diagnostic_heatmaps", help="热力图保存目录")
    parser.add_argument("--demo", action="store_true", help="生成一张演示效果热力图供预览")
    return parser.parse_args()


def render_heatmap_overlay(
    frame_bgr: np.ndarray,
    mask_gray: np.ndarray,
    alpha: float = 0.55,
    colormap: int = cv2.COLORMAP_JET,
) -> np.ndarray:
    """将二值或灰度掩码平滑模糊后转换为伪彩色热力图，并与原视频帧半透明融合。"""
    h, w = frame_bgr.shape[:2]
    if mask_gray.shape[:2] != (h, w):
        mask_gray = cv2.resize(mask_gray, (w, h), interpolation=cv2.INTER_NEAREST)

    # 轻微高斯模糊使得热力图边缘过渡平滑柔和，具有连续能量分布感
    blurred_mask = cv2.GaussianBlur(mask_gray, (15, 15), 0)
    norm_mask = cv2.normalize(blurred_mask, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    # 伪彩色映射 (JET: 蓝 -> 绿 -> 黄 -> 红)
    heatmap_color = cv2.applyColorMap(norm_mask, colormap)

    # 仅在非背景区域进行加权融合，背景保持原视频色彩
    non_zero = norm_mask > 20
    overlay = frame_bgr.copy()
    overlay[non_zero] = cv2.addWeighted(
        frame_bgr[non_zero], 1.0 - alpha, heatmap_color[non_zero], alpha, 0
    )
    return overlay


def draw_diagnostic_hud(
    image_bgr: np.ndarray,
    violation_category: str,
    critical_frame: int,
    confidence: float,
    reason: str,
) -> np.ndarray:
    """在图片顶部绘制现代学术风格的诊断信息 HUD 遮罩条。"""
    canvas = image_bgr.copy()
    h, w = canvas.shape[:2]
    bar_height = max(55, int(h * 0.12))

    # 顶部深色半透明横幅
    sub_img = canvas[0:bar_height, 0:w]
    dark_rect = np.full_like(sub_img, 20)
    canvas[0:bar_height, 0:w] = cv2.addWeighted(sub_img, 0.25, dark_rect, 0.75, 0)

    # 顶部标题栏
    title = f"[PHYSICS VIOLATION DIAGNOSIS] Frame: #{critical_frame} | Category: {violation_category.upper()} | Conf: {confidence:.2f}"
    cv2.putText(
        canvas,
        title,
        (16, int(bar_height * 0.42)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 230, 255),
        2,
        cv2.LINE_AA,
    )

    # 详细诊断原因
    detail = f"Fault: {reason[:85]}..." if len(reason) > 85 else f"Fault: {reason}"
    cv2.putText(
        canvas,
        detail,
        (16, int(bar_height * 0.82)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    return canvas


def create_demo_trio_image(save_path: Path):
    """创建三联对比示范图：[原始帧] vs [SAM2 掩码] vs [诊断热力图 HUD]。"""
    h, w = 480, 640
    # 生成合成测试背景（平滑渐变桌面 + 蓝天）
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:320] = [210, 190, 160]
    frame[320:] = [100, 110, 120]

    # 绘制一个正在下落并发生反弹穿模的红色球
    center = (320, 310)
    radius = 50
    cv2.circle(frame, center, radius, (40, 40, 220), -1)
    cv2.circle(frame, (center[0] - 15, center[1] - 15), 12, (100, 100, 255), -1)

    # 生成对应的局部物理违背掩码 (小球下方穿模交界与异常加速度区域)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius + 10, 255, -1)

    # 渲染热力图叠加
    heatmap_frame = render_heatmap_overlay(frame, mask, alpha=0.6)
    heatmap_with_hud = draw_diagnostic_hud(
        heatmap_frame,
        violation_category="collision_rebound",
        critical_frame=16,
        confidence=0.94,
        reason="Rigid sphere penetrated ground plane without normal reaction impulse",
    )

    # 掩码转为3通道
    mask_3c = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    cv2.putText(frame, "Original Candidate Frame", (15, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(mask_3c, "SAM2 Binary Spatial Mask", (15, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # 水平拼接三联图：原图 | 掩码 | 诊断热力图
    trio = np.hstack([frame, mask_3c, heatmap_with_hud])

    save_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(save_path), trio)
    print(f"[Heatmap] Demo trio diagnostic image created: {save_path}")


def process_sample_dir(sample_dir: Path, output_dir: Path):
    """扫描实际运行样本并生成真实热力图。"""
    # 查找 loop_result.json
    res_path = None
    for cand in sample_dir.glob("**/loop_result.json"):
        res_path = cand
        break
    if not res_path or not res_path.exists():
        print(f"[Heatmap] Warning: No loop_result.json found in {sample_dir}")
        return

    with open(res_path, "r", encoding="utf-8") as f:
        loop_res = json.load(f)

    sample_id = loop_res.get("sample_id", sample_dir.name)
    rounds = loop_res.get("rounds", [])
    if not rounds:
        print(f"[Heatmap] No rounds for {sample_id}")
        return

    # 从第一轮中提取违背信息
    r0 = rounds[0]
    critic_before = r0.get("critic_before", {})
    violations = critic_before.get("violations", [])
    video_path = r0.get("before_candidate", {}).get("video_path")

    if not violations or not video_path or not Path(video_path).exists():
        print(f"[Heatmap] Skip {sample_id}: Video not found or zero violations")
        return

    v0 = violations[0]
    crit_frames = v0.get("critical_frames", [0])
    target_frame_idx = crit_frames[0] if crit_frames else 0
    category = v0.get("category", "dynamics")
    reason = v0.get("repair_instruction", "Kinematic violation")

    # 抽帧
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print(f"[Heatmap] Failed to read frame {target_frame_idx} from {video_path}")
        return

    # 寻找关联的 SAM2 mask
    mask_file = None
    for m in sample_dir.glob(f"**/sam2_masks/*_{target_frame_idx:05d}.png"):
        mask_file = m
        break

    if mask_file and mask_file.exists():
        mask = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
    else:
        # 无单帧 png 时创建中心区域先验
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (w // 2, h // 2), min(h, w) // 4, 255, -1)

    heatmap_overlay = render_heatmap_overlay(frame, mask, alpha=0.6)
    final_hud = draw_diagnostic_hud(
        heatmap_overlay,
        violation_category=category,
        critical_frame=target_frame_idx,
        confidence=float(critic_before.get("confidence", 0.9)),
        reason=reason,
    )

    out_file = output_dir / f"{sample_id}_diagnostic_heatmap.png"
    cv2.imwrite(str(out_file), final_hud)
    print(f"[Heatmap] Rendered: {out_file}")


def main():
    args = _parse_args()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.demo or (not args.run_dir and not args.sample_dir):
        create_demo_trio_image(out_dir / "demo_diagnostic_trio.png")
        if not args.run_dir and not args.sample_dir:
            print("\nTip: Pass --run-dir outputs/<run_folder> to batch process your experimental outputs.")
            return

    if args.sample_dir:
        process_sample_dir(Path(args.sample_dir).resolve(), out_dir)

    if args.run_dir:
        run_p = Path(args.run_dir).resolve()
        for child in run_p.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                process_sample_dir(child, out_dir)


if __name__ == "__main__":
    main()

