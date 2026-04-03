"""
AIGI-Holmes: Detection logic — model inference + URL scraping.

Extracted from app.py so it can be shared between Gradio (app.py) and
the new Flask frontend (server.py) without duplication.
"""

import base64
import hashlib
import ipaddress
import io
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
import numpy as np
import requests
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

# ---------------------------------------------------------------------------
# Base directory — compatible with both plain Python and PyInstaller .exe
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(__file__)

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = os.path.join(BASE_DIR, "finetuned_fake_real_resnet50.pth")
CLASSES = ["FAKE", "REAL"]


def _load_model():
    model = models.resnet50(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES))
    state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    return model


_model = _load_model()


def _compute_model_version() -> str:
    """Return first 8 chars of the SHA-256 hash of the model weights file."""
    h = hashlib.sha256()
    with open(MODEL_PATH, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()[:8]


MODEL_VERSION: str = _compute_model_version()

_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

LABELS_ZH = {
    "FAKE": "🤖 AI 生成",
    "REAL": "📷 真实照片",
}


def _label_zh(label: str) -> str:
    return LABELS_ZH.get(label.upper(), label)


# ---------------------------------------------------------------------------
# Grad-CAM (hooks on ResNet50 layer4)
# ---------------------------------------------------------------------------

def _grad_cam(img_tensor: torch.Tensor, class_idx: int) -> np.ndarray:
    """Return a Grad-CAM activation map (H, W) in [0, 1]."""
    gradients: list[torch.Tensor] = []
    activations: list[torch.Tensor] = []

    def fwd_hook(_, __, output):
        activations.append(output)

    def bwd_hook(_, __, grad_output):
        gradients.append(grad_output[0])

    handle_fwd = _model.layer4.register_forward_hook(fwd_hook)
    handle_bwd = _model.layer4.register_full_backward_hook(bwd_hook)

    try:
        output = _model(img_tensor)
        _model.zero_grad()
        output[0, class_idx].backward()

        grads = gradients[0]           # (1, C, H, W)
        acts = activations[0]          # (1, C, H, W)
        weights = grads.mean(dim=(2, 3), keepdim=True)
        cam = (weights * acts).sum(dim=1).squeeze(0)  # (H, W)
        cam = torch.relu(cam)
        cam_np = cam.detach().cpu().numpy()
        mn, mx = cam_np.min(), cam_np.max()
        if mx > mn:
            cam_np = (cam_np - mn) / (mx - mn)
        return cam_np
    finally:
        handle_fwd.remove()
        handle_bwd.remove()


def grad_cam_overlay(pil_image: Image.Image, class_idx: int) -> str:
    """Return a base64 data-URI JPEG of the image overlaid with the Grad-CAM
    heatmap for *class_idx*."""
    img_rgb = pil_image.convert("RGB")
    inp = _transform(img_rgb).unsqueeze(0).to(DEVICE)
    inp.requires_grad_(True)

    cam_np = _grad_cam(inp, class_idx)

    w, h = img_rgb.size
    cam_resized = np.array(
        Image.fromarray((cam_np * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR),
        dtype=np.float32,
    ) / 255.0

    # RGBA heat layer: red channel = activation, alpha follows activation
    heat_r = (cam_resized * 255).astype(np.uint8)
    heat_g = ((1 - cam_resized) * 80).astype(np.uint8)
    heat_b = np.zeros_like(heat_r)
    heat_a = (cam_resized * 180).astype(np.uint8)
    heat_pil = Image.fromarray(
        np.stack([heat_r, heat_g, heat_b, heat_a], axis=-1), mode="RGBA"
    )

    base = img_rgb.convert("RGBA")
    base.alpha_composite(heat_pil)
    result = base.convert("RGB")
    result.thumbnail((800, 800))

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------------------
# Rule-based text explanation
# ---------------------------------------------------------------------------

_FAKE_RULES = [
    (90, "极高置信度", "模型对该图片的 AI 生成特征高度确信（置信度 \u226590%），图像可能存在多处典型 AI 合成痕迹。"),
    (75, "高置信度",   "图像显示出较强的 AI 生成特征（置信度 75\u201390%），常见于扩散模型或 GAN 生成的内容。"),
    (60, "中等置信度", "模型认为该图像可能由 AI 生成（置信度 60\u201375%），但部分特征接近真实照片。"),
    ( 0, "低置信度",   "模型仅以较低确信度判定为 AI 生成（置信度 50\u201360%），建议结合其他信息综合判断。"),
]

_REAL_RULES = [
    (90, "极高置信度", "模型高度确认该图片为真实拍摄（置信度 \u226590%），未发现明显 AI 生成特征。"),
    (75, "高置信度",   "图像呈现出较强的真实照片特征（置信度 75\u201390%），噪点、光影和细节均符合相机成像规律。"),
    (60, "中等置信度", "模型倾向于认为该图像为真实拍摄（置信度 60\u201375%），但存在少量不确定因素。"),
    ( 0, "低置信度",   "模型以较低置信度判断为真实照片（置信度 50\u201360%），建议进一步核实。"),
]

_COMMON_FAKE_CLUES = [
    "人物手指/肢体比例可能存在异常（AI 常见缺陷）",
    "背景纹理或重复图案可能过于规整",
    "图像边缘可能存在模糊或过渡不自然",
    "光影方向可能与场景不一致",
    "文字或标识可能出现乱码或变形",
]


def explain_result(label: str, confidence: float) -> dict:
    """Return a structured text explanation for the detection result."""
    rules = _FAKE_RULES if label == "FAKE" else _REAL_RULES
    level, summary = rules[-1][1], rules[-1][2]
    for threshold, lvl, desc in rules:
        if confidence >= threshold:
            level, summary = lvl, desc
            break

    clues = _COMMON_FAKE_CLUES[:3] if label == "FAKE" else []
    return {
        "level": level,
        "summary": summary,
        "clues": clues,
        "disclaimer": "结果仅供参考，复杂或高质量 AI 图片可能难以被检测，请结合原始来源综合判断。",
    }


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------

def detect_image(pil_image: Image.Image, with_cam: bool = False) -> dict:
    """Run the detector on a PIL image.

    Returns a dict:
        label       (str)   – "FAKE" or "REAL"
        label_zh    (str)   – localised label with emoji
        confidence  (float) – top-class probability in [0, 100]
        probs       (list)  – [{"label", "label_zh", "score"}, ...] sorted desc
        explanation (dict)  – {level, summary, clues, disclaimer}
        cam_image   (str|None) – base64 JPEG overlay (only when with_cam=True)
    """
    img_rgb = pil_image.convert("RGB")
    img_tensor = _transform(img_rgb).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        output = _model(img_tensor)
        probs = torch.softmax(output, dim=1)[0]

    results = [
        {"label": cls, "label_zh": _label_zh(cls), "score": probs[i].item() * 100}
        for i, cls in enumerate(CLASSES)
    ]
    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[0]

    explanation = explain_result(top["label"], top["score"])

    cam_image = None
    if with_cam:
        top_idx = CLASSES.index(top["label"])
        cam_image = grad_cam_overlay(img_rgb, top_idx)

    return {
        "label": top["label"],
        "label_zh": top["label_zh"],
        "confidence": top["score"],
        "probs": results,
        "explanation": explanation,
        "cam_image": cam_image,
    }


def detect_batch(pil_images: list[Image.Image]) -> list[dict]:
    """Run detection on a batch of PIL images in a single forward pass.

    Returns a list of dicts identical to detect_image() output.
    """
    if not pil_images:
        return []
    tensors = [_transform(img.convert("RGB")) for img in pil_images]
    batch = torch.stack(tensors).to(DEVICE)
    with torch.no_grad():
        outputs = _model(batch)
        all_probs = torch.softmax(outputs, dim=1)

    results = []
    for probs in all_probs:
        items = [
            {"label": cls, "label_zh": _label_zh(cls), "score": probs[i].item() * 100}
            for i, cls in enumerate(CLASSES)
        ]
        items.sort(key=lambda x: x["score"], reverse=True)
        top = items[0]
        results.append({
            "label": top["label"],
            "label_zh": top["label_zh"],
            "confidence": top["score"],
            "probs": items,
            "explanation": explain_result(top["label"], top["score"]),
            "cam_image": None,
        })
    return results


# ---------------------------------------------------------------------------
# URL image scraping — with SSRF protection
# ---------------------------------------------------------------------------

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    ),
    "Referer": "https://www.msn.cn/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
_MAX_IMAGES = 10
_IMG_URL_RE = re.compile(
    r'https?://[^\s"<>\'）\\]+\.(?:jpg|jpeg|png|webp|gif|bmp)',
    re.IGNORECASE,
)


class _ImgSrcParser(HTMLParser):
    """HTML parser that collects image URLs from <img>, <source>, and <meta> tags."""

    def __init__(self):
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        tag_lower = tag.lower()

        if tag_lower == "img":
            for key in ("src", "data-src", "data-lazy-src", "data-original",
                        "data-img", "data-url", "data-original-src", "ng-src"):
                val = attr_dict.get(key, "")
                if val and not val.startswith("data:"):
                    self.srcs.append(val)
                    break

        elif tag_lower == "source":
            # <source srcset="url1 1x, url2 2x"> — 取最后一项（通常分辨率最高）
            srcset = attr_dict.get("srcset", "")
            if srcset:
                parts = [e.strip().split()[0] for e in srcset.split(",") if e.strip()]
                if parts and not parts[-1].startswith("data:"):
                    self.srcs.append(parts[-1])

        elif tag_lower == "meta":
            prop = attr_dict.get("property", "") or attr_dict.get("name", "")
            if prop.lower() in ("og:image", "twitter:image", "twitter:image:src"):
                val = attr_dict.get("content", "")
                if val and not val.startswith("data:"):
                    self.srcs.append(val)


def _has_image_ext(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _IMG_EXTS)


def validate_public_url(url: str) -> None:
    """Reject non-HTTP(S) schemes and private/loopback destinations (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("仅支持 http/https 协议的 URL。")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL 中未包含有效主机名。")
    if host.lower() in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("不允许访问本地地址。")
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise ValueError("不允许访问私有或保留 IP 地址。")
    except ValueError as exc:
        if "不允许" in str(exc) or "仅支持" in str(exc) or "有效" in str(exc):
            raise


def fetch_image_urls(page_url: str) -> list[str]:
    """Extract img src URLs from a news page using the stdlib HTML parser."""
    validate_public_url(page_url)
    try:
        resp = requests.get(page_url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ValueError("无法连接到该地址，请检查 URL 或网络连接。")
    except requests.exceptions.Timeout:
        raise ValueError("请求超时，服务器响应过慢。")
    except requests.exceptions.HTTPError as exc:
        raise ValueError(f"页面请求失败（HTTP {exc.response.status_code}）。")

    html_text = resp.text
    parser = _ImgSrcParser()
    parser.feed(html_text)

    urls: list[str] = []
    seen: set[str] = set()
    for src in parser.srcs:
        if src.startswith("data:"):
            continue
        full = urljoin(page_url, src)
        if full not in seen:
            seen.add(full)
            urls.append(full)
        if len(urls) >= _MAX_IMAGES:
            break

    # Regex fallback: 抓取内嵌在 JS/JSON 里的图片 URL
    if len(urls) < _MAX_IMAGES:
        for raw_url in _IMG_URL_RE.findall(html_text):
            if raw_url not in seen:
                seen.add(raw_url)
                urls.append(raw_url)
            if len(urls) >= _MAX_IMAGES:
                break

    return urls


def download_image(url: str) -> Image.Image | None:
    """Download and decode an image; returns None on failure or if too small."""
    try:
        validate_public_url(url)
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        if img.width < 64 or img.height < 64:
            return None
        return img
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Async variants (httpx) — used by the FastAPI backend
# ---------------------------------------------------------------------------

async def async_fetch_image_urls(page_url: str) -> list[str]:
    """Same as fetch_image_urls but uses httpx for async HTTP."""
    validate_public_url(page_url)
    async with httpx.AsyncClient(headers=_HEADERS, timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(page_url)
            resp.raise_for_status()
        except httpx.ConnectError:
            raise ValueError("无法连接到该地址，请检查 URL 或网络连接。")
        except httpx.TimeoutException:
            raise ValueError("请求超时，服务器响应过慢。")
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"页面请求失败（HTTP {exc.response.status_code}）。")

    html_text = resp.text
    parser = _ImgSrcParser()
    parser.feed(html_text)

    urls: list[str] = []
    seen: set[str] = set()
    for src in parser.srcs:
        if src.startswith("data:"):
            continue
        full = urljoin(page_url, src)
        if full not in seen:
            seen.add(full)
            urls.append(full)
        if len(urls) >= _MAX_IMAGES:
            break

    # Regex fallback: 抓取内嵌在 JS/JSON 里的图片 URL
    if len(urls) < _MAX_IMAGES:
        for raw_url in _IMG_URL_RE.findall(html_text):
            if raw_url not in seen:
                seen.add(raw_url)
                urls.append(raw_url)
            if len(urls) >= _MAX_IMAGES:
                break

    return urls


async def async_download_image(url: str) -> Image.Image | None:
    """Async variant of download_image using httpx."""
    try:
        validate_public_url(url)
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        if img.width < 64 or img.height < 64:
            return None
        return img
    except Exception:
        return None
