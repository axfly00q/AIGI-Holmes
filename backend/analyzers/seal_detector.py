"""
Seal / Logo anomaly detector.

Locates candidate seal regions via HSV colour filtering (red / blue),
then scores their geometric regularity and boundary sharpness.

Returns {"score": 0-100, "regions_found": int, "details": str}
- score 100 = looks perfectly normal (no suspicious seals found, or seals
              look consistent with real stamps)
- score   0 = strong evidence of fabricated / AI-generated seal
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

_NEUTRAL = {"score": 50.0, "regions_found": 0, "details": "未检测到明显公章/标识区域"}


def _analyze_sync(pil_image: "PILImage.Image") -> dict:
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python-headless not installed; seal analysis skipped")
        return _NEUTRAL

    try:
        np_img = np.array(pil_image.convert("RGB"))
        if np_img.size == 0:
            return _NEUTRAL

        bgr = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        # ── 1. Colour-based candidate masks (red + blue) ───────────────
        # Red range 1: H 0–10
        mask_r1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([10, 255, 255]))
        # Red range 2: H 170–180
        mask_r2 = cv2.inRange(hsv, np.array([170, 80, 80]), np.array([180, 255, 255]))
        # Blue range: H 100–130
        mask_b = cv2.inRange(hsv, np.array([100, 80, 80]), np.array([130, 255, 255]))

        mask = cv2.bitwise_or(mask_r1, mask_r2)
        mask = cv2.bitwise_or(mask, mask_b)

        # Morphological close to merge nearby blobs
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return _NEUTRAL

        h_img, w_img = np_img.shape[:2]
        img_area = h_img * w_img
        min_area = img_area * 0.002   # at least 0.2% of image
        max_area = img_area * 0.40    # at most 40%

        candidates = [c for c in contours if min_area <= cv2.contourArea(c) <= max_area]
        if not candidates:
            return _NEUTRAL

        # ── 2. Per-candidate analysis ─────────────────────────────────
        scores: list[float] = []
        for cnt in candidates:
            area = cv2.contourArea(cnt)
            peri = cv2.arcLength(cnt, True)
            if peri == 0:
                continue

            # Circularity: 4π·A / P²  (1.0 = perfect circle)
            circularity = (4 * np.pi * area) / (peri * peri)

            # Solidity: area / convex-hull area
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0

            # Boundary sharpness (Laplacian variance on the bounding rect)
            x, y, w, h = cv2.boundingRect(cnt)
            roi_gray = cv2.cvtColor(bgr[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
            lap_var = cv2.Laplacian(roi_gray, cv2.CV_64F).var()

            # Scoring heuristic ────────────────────────────────────────
            # Real stamps: slightly irregular circularity (0.6-0.85),
            # moderate sharpness.  AI-generated: overly perfect circle
            # (>0.9) or overly uniform sharpness.
            circ_score = 100.0
            if circularity > 0.92:
                # Suspiciously perfect circle
                circ_score = max(20.0, 100 - (circularity - 0.92) * 1000)
            elif circularity < 0.3:
                circ_score = max(30.0, circularity / 0.3 * 70)

            sol_score = solidity * 100 if solidity < 0.98 else max(40.0, 100 - (solidity - 0.98) * 3000)

            sharp_score = 100.0
            if lap_var > 3000:
                # Overly sharp boundary (AI artefact)
                sharp_score = max(20.0, 100 - (lap_var - 3000) / 100)
            elif lap_var < 50:
                # Overly blurry
                sharp_score = max(30.0, lap_var / 50 * 70)

            region_score = circ_score * 0.4 + sol_score * 0.3 + sharp_score * 0.3
            scores.append(max(0.0, min(100.0, region_score)))

        if not scores:
            return _NEUTRAL

        avg_score = round(float(np.mean(scores)), 1)
        n_regions = len(scores)
        if avg_score >= 70:
            detail = f"检测到 {n_regions} 个印章/标识区域，特征符合真实印章"
        elif avg_score >= 40:
            detail = f"检测到 {n_regions} 个印章/标识区域，部分特征可疑（规则性或锐度异常）"
        else:
            detail = f"检测到 {n_regions} 个印章/标识区域，存在明显伪造迹象"

        return {"score": avg_score, "regions_found": n_regions, "details": detail}

    except Exception as exc:
        logger.warning("seal_detector error: %s", exc)
        return _NEUTRAL


async def analyze(pil_image: "PILImage.Image") -> dict:
    """Async entry point — runs CPU-bound work in the thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
