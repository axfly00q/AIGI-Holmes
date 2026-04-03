"""
AIGI-Holmes backend — CLIP-based image content classification.

Uses OpenAI CLIP ViT-B/32 for zero-shot classification into 7 content categories.
The model is loaded once at module import time (~350 MB, auto-downloaded on first run).
Falls back to "其他" gracefully if the model cannot be loaded (offline / no CLIP installed).
"""

import logging

logger = logging.getLogger("backend.clip_classify")

# 7 categories: (Chinese label, English zero-shot prompt)
CATEGORIES = [
    ("人物", "a photo of a person or people"),
    ("动物", "a photo of an animal"),
    ("建筑", "a photo of buildings or architecture"),
    ("风景", "a photo of landscape or natural scenery"),
    ("食物", "a photo of food or drink"),
    ("交通", "a photo of vehicles or transportation"),
    ("其他", "a photo of other objects or abstract content"),
]

_clip_model = None
_clip_preprocess = None
_text_features = None
_device = None


def _load_clip() -> None:
    global _clip_model, _clip_preprocess, _text_features, _device
    if _clip_model is not None:
        return  # Already loaded
    try:
        import torch
        import clip  # openai/CLIP

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Loading CLIP ViT-B/32 on %s...", _device)
        _clip_model, _clip_preprocess = clip.load("ViT-B/32", device=_device)
        _clip_model.eval()

        # Pre-encode all text prompts once; reuse for every image
        texts = [prompt for _, prompt in CATEGORIES]
        text_tokens = clip.tokenize(texts).to(_device)
        with torch.no_grad():
            feats = _clip_model.encode_text(text_tokens)
            _text_features = feats / feats.norm(dim=-1, keepdim=True)

        logger.info("CLIP ViT-B/32 loaded successfully")
    except Exception as e:
        logger.warning(
            "Failed to load CLIP model (%s); content classification will return '其他'",
            str(e),
        )
        _clip_model = None
        _clip_preprocess = None
        _text_features = None


# 不在导入时加载，改为在第一次调用时懒加载
_loaded = False


def classify_image(pil_image) -> str:
    """Classify a PIL image into one of 7 content categories.

    Lazy-loads CLIP on first call.
    Returns the Chinese category label string.
    Returns "其他" if CLIP is unavailable or inference fails.
    """
    global _loaded
    
    # 首次调用时（且只调用一次）加载 CLIP
    if not _loaded:
        _load_clip()
        _loaded = True
    
    if _clip_model is None or _clip_preprocess is None or _text_features is None:
        return "其他"

    try:
        import torch

        img_tensor = _clip_preprocess(pil_image).unsqueeze(0).to(_device)
        with torch.no_grad():
            img_feats = _clip_model.encode_image(img_tensor)
            img_feats = img_feats / img_feats.norm(dim=-1, keepdim=True)
            # cosine similarity via dot product (both are unit vectors)
            logits = (img_feats @ _text_features.T).squeeze(0)
            idx = int(logits.argmax().item())
        return CATEGORIES[idx][0]
    except Exception as e:
        logger.warning("classify_image failed: %s", str(e))
        return "其他"
