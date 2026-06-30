"""
Edge-consistency / splicing detector.

Divides the image into a 4×4 grid, computes the Laplacian standard
deviation in each cell, then measures how uniformly the sharpness is
distributed.  A high coefficient of variation (CV) across cells suggests
compositing or AI inpainting artefacts.

Returns {"score": 0-100, "edge_cv": float, "details": str}
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PIL import Image as PILImage

logger = logging.getLogger(__name__)

_NEUTRAL = {"score": 50.0, "edge_cv": 0.0, "details": "边缘一致性分析不可用"}


def _analyze_sync(pil_image: "PILImage.Image") -> dict:
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python-headless not installed; edge analysis skipped")
        return _NEUTRAL

    try:
        img = pil_image.convert("RGB")
        # Down-sample for speed
        if max(img.size) > 512:
            img.thumbnail((512, 512))

        np_img = np.array(img)
        if np_img.size == 0:
            return _NEUTRAL

        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        if h < 32 or w < 32:
            return _NEUTRAL

        # 4×4 grid
        rows, cols = 4, 4
        cell_h, cell_w = h // rows, w // cols

        lap_stds: list[float] = []
        for r in range(rows):
            for c in range(cols):
                cell = gray[r * cell_h:(r + 1) * cell_h, c * cell_w:(c + 1) * cell_w]
                lap = cv2.Laplacian(cell, cv2.CV_64F)
                lap_stds.append(float(np.std(lap)))

        arr = np.array(lap_stds)
        mean_std = arr.mean()
        if mean_std < 1e-6:
            return {"score": 50.0, "edge_cv": 0.0, "details": "图像过于平坦，无法评估边缘一致性"}

        cv = float(arr.std() / mean_std)  # coefficient of variation

        # Also compute global ELA-like metric:
        # Compare Laplacian energy of brightest vs. darkest quartile of cells
        sorted_stds = np.sort(arr)
        q1_mean = sorted_stds[:4].mean()
        q4_mean = sorted_stds[-4:].mean()
        ratio = q4_mean / q1_mean if q1_mean > 1e-6 else 1.0

        # Scoring ────────────────────────────────────────────────────
        # Low CV (< 0.3) → uniform edges → likely authentic
        # High CV (> 0.6) → inconsistent → suspicious
        if cv < 0.25:
            score = 90.0 + (0.25 - cv) / 0.25 * 10  # 90-100
        elif cv < 0.45:
            score = 60.0 + (0.45 - cv) / 0.20 * 30  # 60-90
        elif cv < 0.70:
            score = 30.0 + (0.70 - cv) / 0.25 * 30  # 30-60
        else:
            score = max(5.0, 30.0 - (cv - 0.70) * 50)

        # Penalise extreme quartile ratio
        if ratio > 4.0:
            penalty = min(20.0, (ratio - 4.0) * 5)
            score -= penalty

        score = round(max(0.0, min(100.0, score)), 1)

        if score >= 70:
            detail = f"边缘锐度分布均匀，未见拼接痕迹 (CV={cv:.2f})"
        elif score >= 40:
            detail = f"边缘锐度分布存在轻微不均 (CV={cv:.2f})"
        else:
            detail = f"边缘锐度分布不一致，疑似合成/拼接 (CV={cv:.2f})"

        return {"score": score, "edge_cv": round(cv, 3), "details": detail}

    except Exception as exc:
        logger.warning("edge_analyzer error: %s", exc)
        return _NEUTRAL


async def analyze(pil_image: "PILImage.Image") -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
