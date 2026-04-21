"""
Frequency-domain naturalness analyser.

Computes the radial power spectral density (PSD) of a greyscale image
and fits a line in log-log space.  Natural photographs follow a 1/f^α
distribution (α ≈ 2, R² > 0.85); AI-generated images deviate.

Returns {"score": 0-100, "psd_slope": float, "r_squared": float, "details": str}
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

_NEUTRAL = {"score": 50.0, "psd_slope": 0.0, "r_squared": 0.0, "details": "频率域分析不可用"}


def _radial_psd(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (frequencies, power) as 1-D arrays from a 2-D FFT."""
    from scipy.fft import fft2, fftshift

    h, w = gray.shape
    f = fft2(gray.astype(np.float64))
    f_shifted = fftshift(f)
    magnitude = np.abs(f_shifted) ** 2

    cy, cx = h // 2, w // 2
    max_radius = min(cy, cx)
    if max_radius < 4:
        return np.array([]), np.array([])

    # Build radius map
    Y, X = np.ogrid[:h, :w]
    R = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(int)

    # Bin by radius
    radii = np.arange(1, max_radius)
    psd = np.zeros(len(radii), dtype=np.float64)
    for i, r in enumerate(radii):
        ring = magnitude[R == r]
        if ring.size > 0:
            psd[i] = ring.mean()

    return radii.astype(np.float64), psd


def _analyze_sync(pil_image: "PILImage.Image") -> dict:
    try:
        from scipy.fft import fft2, fftshift  # noqa: F401 – validates availability
    except ImportError:
        logger.warning("scipy not installed; frequency analysis skipped")
        return _NEUTRAL

    try:
        img = pil_image.convert("L")
        # Resize large images for speed (frequency analysis is resolution-independent)
        if max(img.size) > 512:
            img.thumbnail((512, 512))
        gray = np.array(img, dtype=np.float64)
        if gray.size == 0:
            return _NEUTRAL

        freqs, psd = _radial_psd(gray)
        if freqs.size < 4:
            return _NEUTRAL

        # Remove zero-power bins
        valid = psd > 0
        freqs = freqs[valid]
        psd = psd[valid]
        if freqs.size < 4:
            return _NEUTRAL

        log_f = np.log10(freqs)
        log_p = np.log10(psd)

        # Least-squares linear fit  log_p = slope * log_f + intercept
        coeffs = np.polyfit(log_f, log_p, 1)
        slope = coeffs[0]

        # R² (coefficient of determination)
        predicted = np.polyval(coeffs, log_f)
        ss_res = np.sum((log_p - predicted) ** 2)
        ss_tot = np.sum((log_p - log_p.mean()) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        r_squared = max(0.0, r_squared)

        # Scoring ────────────────────────────────────────────────────
        # Ideal: slope ≈ -2, R² > 0.85
        if r_squared > 0.85:
            score = 80 + (r_squared - 0.85) / 0.15 * 20   # 80-100
        elif r_squared > 0.70:
            score = 50 + (r_squared - 0.70) / 0.15 * 30   # 50-80
        else:
            score = max(10.0, r_squared / 0.70 * 50)       # 10-50

        score = round(max(0.0, min(100.0, score)), 1)

        if score >= 70:
            detail = f"频率分布符合自然照片特征 (R²={r_squared:.2f}, slope={slope:.2f})"
        elif score >= 40:
            detail = f"频率分布存在轻微偏差 (R²={r_squared:.2f}, slope={slope:.2f})"
        else:
            detail = f"频率分布异常，可能为AI合成 (R²={r_squared:.2f}, slope={slope:.2f})"

        return {
            "score": score,
            "psd_slope": round(float(slope), 3),
            "r_squared": round(float(r_squared), 3),
            "details": detail,
        }
    except Exception as exc:
        logger.warning("frequency_analyzer error: %s", exc)
        return _NEUTRAL


async def analyze(pil_image: "PILImage.Image") -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
