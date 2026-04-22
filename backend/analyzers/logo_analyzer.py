"""
Logo / media-institution analyser  (Phase 3)

Uses CLIP zero-shot classification to detect whether an image contains a
recognisable logo or watermark from a major news/media organisation.
Acts as a *supplementary* credibility signal — not part of the 6-dimension
composite score.

Prompt vocabulary informed by the Logo-2k+ "Institution" category (238 classes,
17 k images) and cross-referenced with Xinhua/CCTV/BBC visual branding.

Returns:
    {
        "score":            float,        # 50 (neutral) – 90 (strong signal)
        "detected_logo":    str | None,   # human-readable media name, or None
        "logo_confidence":  float,        # 0–100 confidence for detected logo
        "details":          str,
    }

score semantics:
    50  = no recognisable logo found (neutral)
    60–90 = known media logo detected; higher = more confident
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

logger = logging.getLogger(__name__)

_NEUTRAL = {
    "score": 50.0,
    "detected_logo": None,
    "logo_confidence": 0.0,
    "details": "未检测到已知媒体机构Logo",
}

# ── Media institution registry ───────────────────────────────────────────────
# Each entry: (display_name, CLIP description)
# Ordered roughly by expected frequency in Chinese news images.
_MEDIA_REGISTRY: list[tuple[str, str]] = [
    # ── Chinese official & major media ──────────────────────────────────
    ("新华社",      "Xinhua News Agency logo, Chinese official news agency watermark or branding"),
    ("人民日报",    "People's Daily newspaper logo or masthead, Chinese Communist Party newspaper"),
    ("CCTV 央视",   "CCTV China Central Television logo or watermark, Chinese state broadcaster"),
    ("CGTN",        "CGTN China Global Television Network logo or watermark"),
    ("环球时报",    "Global Times Chinese newspaper logo or branding"),
    ("澎湃新闻",    "The Paper Chinese online news media logo or watermark"),
    ("财新传媒",    "Caixin Media financial news logo or watermark, Chinese financial journalism"),
    ("光明日报",    "Guangming Daily Chinese newspaper logo or masthead"),
    ("经济日报",    "Economic Daily Chinese newspaper logo or branding"),
    ("新京报",      "Beijing News Chinese newspaper logo or watermark"),
    # ── International wire services & broadcasters ───────────────────
    ("BBC",         "BBC British Broadcasting Corporation logo or watermark, red BBC logo"),
    ("CNN",         "CNN Cable News Network logo or watermark, red CNN logo"),
    ("Reuters 路透社", "Reuters news agency logo, Thomson Reuters branding or watermark"),
    ("AP 美联社",   "AP Associated Press news agency logo or watermark"),
    ("AFP 法新社",  "AFP Agence France-Presse news agency logo or watermark"),
    ("《纽约时报》","New York Times newspaper logo or masthead, NYT branding"),
    ("《华盛顿邮报》","Washington Post newspaper logo or masthead, WashPost branding"),
    ("《卫报》",    "The Guardian newspaper logo or masthead, British newspaper branding"),
    ("半岛电视台",  "Al Jazeera news network logo or watermark, Qatar-based broadcaster"),
    ("NHK",         "NHK Japan Broadcasting Corporation logo or watermark"),
    ("DW 德国之声", "Deutsche Welle DW German international broadcaster logo"),
    ("法国国际广播", "RFI Radio France Internationale logo or watermark"),
    ("《经济学人》","The Economist magazine logo or masthead, British weekly branding"),
]

# CLIP cosine-similarity threshold for a confident logo match
# (typical CLIP image-text cos-sim for relevant matches: 0.24–0.32)
_DETECTION_THRESHOLD = 0.24

# Normalisation range for raw CLIP similarity → confidence %
_SIM_LOW  = 0.20   # maps to 0 %
_SIM_HIGH = 0.34   # maps to 100 %


def _analyze_sync(pil_image: "PILImage.Image") -> dict:
    """Synchronous logo analysis (runs in a thread-pool executor)."""
    try:
        import torch
        import clip as clip_lib
        from backend import clip_classify as cc

        cc._load_clip()
        if cc._clip_model is None or cc._clip_preprocess is None or cc._device is None:
            logger.debug("CLIP not available; logo analysis skipped")
            return _NEUTRAL

        # Encode the image once
        img_tensor = cc._clip_preprocess(pil_image.convert("RGB")).unsqueeze(0).to(cc._device)
        with torch.no_grad():
            img_feat = cc._clip_model.encode_image(img_tensor)
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)

        # Encode all media descriptions and compute similarities
        descriptions = [desc for _, desc in _MEDIA_REGISTRY]
        tokens = clip_lib.tokenize(descriptions, truncate=True).to(cc._device)

        with torch.no_grad():
            txt_feat = cc._clip_model.encode_text(tokens)
            txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat @ txt_feat.T).squeeze(0).cpu().float()

        best_idx  = int(sims.argmax().item())
        best_sim  = float(sims[best_idx].item())
        best_name = _MEDIA_REGISTRY[best_idx][0]

        if best_sim < _DETECTION_THRESHOLD:
            return _NEUTRAL

        # Normalise similarity to 0–100 confidence
        confidence = max(0.0, min(100.0,
            (best_sim - _SIM_LOW) / (_SIM_HIGH - _SIM_LOW) * 100))
        confidence = round(confidence, 1)

        # Map confidence to supplementary score (50 neutral → max 90)
        score = round(50.0 + confidence * 0.40, 1)
        score = min(90.0, score)

        details = f"检测到疑似 {best_name} Logo（置信度 {confidence:.0f}%），图片可能来源于该媒体机构"
        return {
            "score":           score,
            "detected_logo":   best_name,
            "logo_confidence": confidence,
            "details":         details,
        }

    except Exception as exc:
        logger.warning("logo_analyzer error: %s", exc)
        return _NEUTRAL


async def analyze(pil_image: "PILImage.Image") -> dict:
    """Async entry point — runs CPU-bound work in the thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
