"""
Face deepfake indicator analyser.

Uses OpenCV Haar cascade to locate faces, then for each face:
  • Runs an FFT and checks the power-spectrum symmetry
  • Looks for blending boundary artefacts via Laplacian variance

If no face is found, returns a neutral score (50) —
the dimension is "not applicable" rather than "suspicious".

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

# Lazy-loaded cascade classifier
_cascade = None


def _get_cascade():
    global _cascade
    if _cascade is None:
        import cv2
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _cascade = cv2.CascadeClassifier(cascade_path)
    return _cascade


def _face_score(face_gray: np.ndarray) -> float:
    """Score a single face crop.  Higher = more likely authentic."""
    import cv2

    h, w = face_gray.shape
    if h < 32 or w < 32:
        return 50.0

    # 1. FFT power-spectrum symmetry
    f = np.fft.fft2(face_gray.astype(np.float64))
    f_shifted = np.fft.fftshift(f)
    mag = np.log1p(np.abs(f_shifted))
    # Compare left/right halves
    left = mag[:, :w // 2]
    right = np.flip(mag[:, w // 2:w // 2 + left.shape[1]], axis=1)
    if left.shape == right.shape and left.size > 0:
        diff = np.abs(left - right)
        sym_ratio = 1 - float(diff.mean() / (mag.mean() + 1e-8))
    else:
        sym_ratio = 0.5

    # 2. Boundary Laplacian — look at a ring around the face crop
    pad = max(2, min(h, w) // 8)
    inner = face_gray[pad:-pad, pad:-pad] if pad * 2 < min(h, w) else face_gray
    outer_lap = cv2.Laplacian(face_gray, cv2.CV_64F).var()
    inner_lap = cv2.Laplacian(inner, cv2.CV_64F).var()
    if inner_lap > 1e-6:
        boundary_ratio = outer_lap / inner_lap
    else:
        boundary_ratio = 1.0

    # 3. Local contrast uniformity (stddev in 4 quadrants)
    qh, qw = h // 2, w // 2
    quads = [
        face_gray[:qh, :qw],
        face_gray[:qh, qw:],
        face_gray[qh:, :qw],
        face_gray[qh:, qw:],
    ]
    q_stds = [float(np.std(q)) for q in quads if q.size > 0]
    if q_stds:
        q_cv = np.std(q_stds) / (np.mean(q_stds) + 1e-8)
    else:
        q_cv = 0.0

    # Combine sub-scores
    sym_score = np.clip(sym_ratio * 100, 0, 100)
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

        scores = []
        for (x, y, w, h) in faces:
            face_crop = gray[y:y + h, x:x + w]
            scores.append(_face_score(face_crop))

        avg_score = round(float(np.mean(scores)), 1)
        n = len(scores)

        if avg_score >= 70:
            detail = f"检测到 {n} 张人脸，特征符合真实照片"
        elif avg_score >= 40:
            detail = f"检测到 {n} 张人脸，存在轻微异常"
        else:
            detail = f"检测到 {n} 张人脸，存在深度伪造迹象"

        return {"score": avg_score, "faces_found": n, "details": detail}

    except Exception as exc:
        logger.warning("face_analyzer error: %s", exc)
        return _NEUTRAL


async def analyze(pil_image: "PILImage.Image") -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
