"""
Face deepfake indicator analyser — v2 (CLIP-enhanced)

Stage 1 (signal-processing):  OpenCV Haar cascade detects faces; per-crop:
  • FFT power-spectrum symmetry  (AI faces tend to be more bilaterally symmetric)
  • Boundary Laplacian variance  (blending artefacts from inpainting / splicing)
  • Quadrant contrast uniformity (over-smoothed regions common in diffusion faces)

Stage 2 (CLIP semantic):  Each face crop is scored against authentic-photo
  prompts vs. AI/deepfake prompts, using the already-loaded CLIP model.
  VGGFace2 & PubFig vocabulary informed the prompt engineering.

Combined score: CLIP × 0.55 + signal × 0.45.
Falls back to signal-only when CLIP is unavailable.

Returns {"score": 0-100, "faces_found": int, "details": str}
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

_NEUTRAL = {"score": 50.0, "faces_found": 0, "details": "未检测到人脸，该维度不适用"}

# Lazy-loaded Haar cascade classifier
_cascade = None

# ── CLIP prompt banks ────────────────────────────────────────────────────────
# Authentic face: natural skin texture, genuine lighting, real photo details
_FACE_AUTHENTIC_PROMPTS = [
    "a real photograph of a human face with natural skin texture and genuine expression",
    "an authentic candid photo of a person with natural lighting and realistic facial details",
    "a genuine portrait photo of a person with visible skin pores and natural hair",
]
# AI / deepfake face: over-smooth skin, synthetic appearance, GAN/diffusion artefacts
_FACE_DEEPFAKE_PROMPTS = [
    "an AI-generated or deepfake face with artificially smooth skin and unnatural features",
    "a computer-generated portrait with synthetic appearance and GAN artefacts",
    "a diffusion model or deepfake image with overly perfect or distorted facial features",
]


def _get_cascade():
    global _cascade
    if _cascade is None:
        import cv2
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _cascade = cv2.CascadeClassifier(cascade_path)
    return _cascade


def _clip_score_face_crop(pil_crop: "PILImage.Image") -> "float | None":
    """Run CLIP zero-shot deepfake scoring on a face crop.

    Returns a score in [0, 100] where 100 = authentic-looking,
    or None if CLIP is unavailable or the crop is too small.
    """
    # Skip very small crops — CLIP won't produce reliable results
    if pil_crop.width < 60 or pil_crop.height < 60:
        return None
    try:
        import torch
        import clip as clip_lib
        from backend import clip_classify as cc

        cc._load_clip()
        if cc._clip_model is None or cc._clip_preprocess is None or cc._device is None:
            return None

        all_prompts = _FACE_AUTHENTIC_PROMPTS + _FACE_DEEPFAKE_PROMPTS
        tokens = clip_lib.tokenize(all_prompts, truncate=True).to(cc._device)
        img_tensor = cc._clip_preprocess(pil_crop.convert("RGB")).unsqueeze(0).to(cc._device)

        with torch.no_grad():
            img_feat = cc._clip_model.encode_image(img_tensor)
            txt_feat = cc._clip_model.encode_text(tokens)
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
            txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat @ txt_feat.T).squeeze(0).cpu().float()

        n_auth = len(_FACE_AUTHENTIC_PROMPTS)
        authentic_mean = float(sims[:n_auth].mean().item())
        fake_mean      = float(sims[n_auth:].mean().item())

        # gap > 0 → looks authentic;  gap < 0 → looks deepfake
        # Map gap ∈ [-0.20, +0.20] → [0, 100]
        gap = authentic_mean - fake_mean
        score = max(0.0, min(1.0, (gap + 0.15) / 0.30)) * 100
        return round(score, 1)

    except Exception as exc:
        logger.debug("CLIP face scoring failed: %s", exc)
        return None


def _signal_score(face_gray: np.ndarray) -> float:
    """Score a single face crop via FFT + Laplacian + contrast uniformity.
    Higher = more likely authentic.  (Renamed from _face_score for clarity.)
    """
    import cv2

    h, w = face_gray.shape
    if h < 32 or w < 32:
        return 50.0

    # 1. FFT power-spectrum symmetry
    f = np.fft.fft2(face_gray.astype(np.float64))
    f_shifted = np.fft.fftshift(f)
    mag = np.log1p(np.abs(f_shifted))
    left  = mag[:, :w // 2]
    right = np.flip(mag[:, w // 2:w // 2 + left.shape[1]], axis=1)
    if left.shape == right.shape and left.size > 0:
        diff = np.abs(left - right)
        sym_ratio = 1 - float(diff.mean() / (mag.mean() + 1e-8))
    else:
        sym_ratio = 0.5

    # 2. Boundary Laplacian — ring around the face crop
    pad = max(2, min(h, w) // 8)
    inner = face_gray[pad:-pad, pad:-pad] if pad * 2 < min(h, w) else face_gray
    outer_lap = cv2.Laplacian(face_gray, cv2.CV_64F).var()
    inner_lap = cv2.Laplacian(inner, cv2.CV_64F).var()
    boundary_ratio = outer_lap / inner_lap if inner_lap > 1e-6 else 1.0

    # 3. Local contrast uniformity (stddev in 4 quadrants)
    qh, qw = h // 2, w // 2
    quads = [
        face_gray[:qh, :qw],
        face_gray[:qh, qw:],
        face_gray[qh:, :qw],
        face_gray[qh:, qw:],
    ]
    q_stds = [float(np.std(q)) for q in quads if q.size > 0]
    q_cv = np.std(q_stds) / (np.mean(q_stds) + 1e-8) if q_stds else 0.0

    # Sub-scores
    sym_score = float(np.clip(sym_ratio * 100, 0, 100))
    boundary_score = 100.0
    if boundary_ratio > 2.0:
        boundary_score = max(10.0, 100 - (boundary_ratio - 2.0) * 20)
    elif boundary_ratio < 0.5:
        boundary_score = max(10.0, boundary_ratio / 0.5 * 60)

    cv_score = 100.0
    if q_cv > 0.5:
        cv_score = max(10.0, 100 - (q_cv - 0.5) * 100)

    combined = sym_score * 0.4 + boundary_score * 0.35 + cv_score * 0.25
    return float(np.clip(combined, 0, 100))


def _analyze_sync(pil_image: "PILImage.Image") -> dict:
    try:
        import cv2
        from PIL import Image as PIL_Image
    except ImportError:
        logger.warning("opencv-python-headless not installed; face analysis skipped")
        return _NEUTRAL

    try:
        img = pil_image.convert("RGB")
        # Limit resolution for Haar speed
        if max(img.size) > 640:
            img.thumbnail((640, 640))
        np_img = np.array(img)
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

        cascade = _get_cascade()
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30),
        )

        if len(faces) == 0:
            return _NEUTRAL

        combined_scores: list[float] = []
        for (x, y, w, h) in faces:
            # Signal-processing score (grayscale crop)
            face_gray = gray[y:y + h, x:x + w]
            sig_score = _signal_score(face_gray)

            # CLIP deepfake score (colour crop)
            face_rgb  = np_img[y:y + h, x:x + w]
            face_pil  = PIL_Image.fromarray(face_rgb)
            clip_score = _clip_score_face_crop(face_pil)

            if clip_score is not None:
                final = round(clip_score * 0.55 + sig_score * 0.45, 1)
            else:
                final = sig_score

            combined_scores.append(final)

        avg_score = round(float(np.mean(combined_scores)), 1)
        n = len(combined_scores)

        if avg_score >= 70:
            detail = f"检测到 {n} 张人脸，CLIP+信号分析特征符合真实照片"
        elif avg_score >= 40:
            detail = f"检测到 {n} 张人脸，存在轻微异常（可能为深度伪造）"
        else:
            detail = f"检测到 {n} 张人脸，CLIP+信号分析存在深度伪造迹象"

        return {"score": avg_score, "faces_found": n, "details": detail}

    except Exception as exc:
        logger.warning("face_analyzer error: %s", exc)
        return _NEUTRAL


async def analyze(pil_image: "PILImage.Image") -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
