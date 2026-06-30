"""
Seal / Logo anomaly detector  — v2 (CLIP-enhanced)

Stage 1 (geometric):  HSV colour filtering → contour circularity / solidity /
                      boundary sharpness.  (unchanged from v1)
Stage 2 (semantic):   For each detected seal crop, CLIP zero-shot scoring
                      compares authentic-stamp prompts vs. AI-generated-stamp
                      prompts.  Uses the DocBank Seal dataset vocabulary as the
                      basis for prompt engineering.
Combined score:       semantic × 0.6 + geometric × 0.4.
Falls back to geometric-only when CLIP is unavailable.

Returns {"score": 0-100, "regions_found": int, "details": str}
  score 100 = looks perfectly normal (no suspicious seals, or stamps look real)
  score   0 = strong evidence of fabricated / AI-generated seal
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

# ── CLIP prompt banks ────────────────────────────────────────────────────────
# Authentic stamp characteristics: clear text, uniform ink, precise circle
_SEAL_AUTHENTIC_PROMPTS = [
    "an authentic official document seal with sharp text and uniform circular ink",
    "a real government stamp with clear characters and precise circular border",
    "a genuine official red seal with readable text and uniform color distribution",
]
# AI-generated / forged stamp characteristics: blurry, distorted, irregular
_SEAL_FAKE_PROMPTS = [
    "an AI-generated or digitally manipulated stamp with blurry distorted text",
    "a forged document seal with irregular edges and uneven ink distribution",
    "a fake or synthetic stamp with unclear characters and imperfect circular shape",
]


def _clip_score_seal_crop(pil_crop: "PILImage.Image") -> "float | None":
    """Run CLIP zero-shot scoring on a seal crop.

    Returns a score in [0, 100] where 100 means authentic-looking,
    or None if CLIP is unavailable or inference fails.
    """
    try:
        import torch
        import clip as clip_lib  # openai/CLIP
        from backend import clip_classify as cc  # lazy import to avoid circulars

        cc._load_clip()
        if cc._clip_model is None or cc._clip_preprocess is None or cc._device is None:
            return None

        all_prompts = _SEAL_AUTHENTIC_PROMPTS + _SEAL_FAKE_PROMPTS
        tokens = clip_lib.tokenize(all_prompts, truncate=True).to(cc._device)
        img_tensor = cc._clip_preprocess(pil_crop.convert("RGB")).unsqueeze(0).to(cc._device)

        with torch.no_grad():
            img_feat = cc._clip_model.encode_image(img_tensor)
            txt_feat = cc._clip_model.encode_text(tokens)
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
            txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat @ txt_feat.T).squeeze(0).cpu().float()

        n_auth = len(_SEAL_AUTHENTIC_PROMPTS)
        authentic_mean = float(sims[:n_auth].mean().item())
        fake_mean = float(sims[n_auth:].mean().item())

        # gap > 0  → looks authentic;  gap < 0 → looks fake
        # Map gap ∈ [-0.20, +0.20] → [0, 100]
        gap = authentic_mean - fake_mean
        score = max(0.0, min(1.0, (gap + 0.15) / 0.30)) * 100
        return round(score, 1)

    except Exception as exc:
        logger.debug("CLIP seal scoring failed: %s", exc)
        return None


def _analyze_sync(pil_image: "PILImage.Image") -> dict:
    try:
        import cv2
        from PIL import Image as PIL_Image  # local import to avoid top-level dependency
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
        mask_b  = cv2.inRange(hsv, np.array([100, 80, 80]), np.array([130, 255, 255]))

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

        # ── 2. Per-candidate geometric analysis ───────────────────────
        geo_scores:  list[float] = []
        crop_images: list = []  # PIL.Image crops for CLIP

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
            roi_gray = cv2.cvtColor(bgr[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
            lap_var = cv2.Laplacian(roi_gray, cv2.CV_64F).var()

            # Geometric sub-scores ─────────────────────────────────────
            circ_score = 100.0
            if circularity > 0.92:
                circ_score = max(20.0, 100 - (circularity - 0.92) * 1000)
            elif circularity < 0.3:
                circ_score = max(30.0, circularity / 0.3 * 70)

            sol_score = (solidity * 100 if solidity < 0.98
                         else max(40.0, 100 - (solidity - 0.98) * 3000))

            sharp_score = 100.0
            if lap_var > 3000:
                sharp_score = max(20.0, 100 - (lap_var - 3000) / 100)
            elif lap_var < 50:
                sharp_score = max(30.0, lap_var / 50 * 70)

            geo = circ_score * 0.4 + sol_score * 0.3 + sharp_score * 0.3
            geo_scores.append(max(0.0, min(100.0, geo)))

            # Extract colour crop (with small padding for context) ─────
            pad = 8
            y1 = max(0, y - pad)
            y2 = min(h_img, y + h + pad)
            x1 = max(0, x - pad)
            x2 = min(w_img, x + w + pad)
            crop_rgb = np_img[y1:y2, x1:x2]
            if crop_rgb.size > 0:
                crop_images.append(PIL_Image.fromarray(crop_rgb))

        if not geo_scores:
            return _NEUTRAL

        # ── 3. CLIP semantic scoring on each crop ─────────────────────
        clip_scores: list[float] = []
        for crop_pil in crop_images:
            cs = _clip_score_seal_crop(crop_pil)
            if cs is not None:
                clip_scores.append(cs)

        # ── 4. Combine geometric + semantic ───────────────────────────
        avg_geo = float(np.mean(geo_scores))
        if clip_scores:
            avg_clip = float(np.mean(clip_scores))
            avg_score = round(avg_clip * 0.6 + avg_geo * 0.4, 1)
            method = "CLIP语义+几何"
        else:
            avg_score = round(avg_geo, 1)
            method = "几何分析"

        n_regions = len(geo_scores)
        if avg_score >= 70:
            detail = f"检测到 {n_regions} 个印章/标识区域，{method}分析符合真实印章特征"
        elif avg_score >= 40:
            detail = f"检测到 {n_regions} 个印章/标识区域，{method}分析发现部分可疑特征"
        else:
            detail = f"检测到 {n_regions} 个印章/标识区域，{method}分析存在明显伪造迹象"

        return {"score": avg_score, "regions_found": n_regions, "details": detail}

    except Exception as exc:
        logger.warning("seal_detector error: %s", exc)
        return _NEUTRAL


async def analyze(pil_image: "PILImage.Image") -> dict:
    """Async entry point — runs CPU-bound work in the thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
