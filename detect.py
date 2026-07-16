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

from backend.detection_result import enrich_detection_result, load_result_metadata

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
CLASSES = ["FAKE", "REAL"]


def _resolve_model_path() -> str:
    """Resolve MODEL_PATH from .env/environment, falling back to the repo root."""
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)
    except Exception:
        pass

    configured = os.environ.get("MODEL_PATH", "").strip()
    if configured:
        return configured if os.path.isabs(configured) else os.path.join(BASE_DIR, configured)
    return os.path.join(BASE_DIR, "finetuned_fake_real_resnet50.pth")


MODEL_PATH = _resolve_model_path()


def _load_model():
    if not os.path.isfile(MODEL_PATH):
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}\n"
            f"BASE_DIR={BASE_DIR}, CWD={os.getcwd()}"
        )
    model = models.resnet50(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES))
    state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    return model


try:
    _model = _load_model()
except Exception as _e:
    print(f"[DETECT] FATAL: Failed to load model: {_e}", flush=True)
    raise


def _compute_model_version() -> str:
    """Return first 8 chars of the SHA-256 hash of the model weights file."""
    h = hashlib.sha256()
    with open(MODEL_PATH, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()[:8]


MODEL_VERSION: str = _compute_model_version()
MODEL_TEMPERATURE: float = max(0.05, float(load_result_metadata().get("temperature", 1.0)))

_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

LABELS_ZH = {
    "FAKE": "AI 生成",
    "REAL": "真实照片",
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


def _build_cam_overlay(img_rgb: Image.Image, cam_np: np.ndarray) -> str:
    """Render a Grad-CAM heatmap over *img_rgb* and return a base64 JPEG URI.

    Accepts a precomputed *cam_np* (H, W) normalised to [0, 1] so the same
    activation map can be reused for both clue generation and visualisation
    without a second backward pass.
    """
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


def grad_cam_overlay(pil_image: Image.Image, class_idx: int) -> str:
    """Return a base64 data-URI JPEG of the image overlaid with the Grad-CAM
    heatmap for *class_idx*."""
    img_rgb = pil_image.convert("RGB")
    inp = _transform(img_rgb).unsqueeze(0).to(DEVICE)
    inp.requires_grad_(True)
    cam_np = _grad_cam(inp, class_idx)
    return _build_cam_overlay(img_rgb, cam_np)


# ---------------------------------------------------------------------------
# Grad-CAM region analysis & dynamic clue generation
# ---------------------------------------------------------------------------

def analyze_cam_regions(cam_np: np.ndarray, img_w: int, img_h: int) -> dict:
    """Analyse the spatial distribution of a Grad-CAM activation map.

    Args:
        cam_np: Normalised activation map (H, W) in [0, 1] from _grad_cam().
        img_w:  Original image width  (pixels) — reserved for future use.
        img_h:  Original image height (pixels) — reserved for future use.

    Returns a dict with keys:
        position           – Chinese spatial label, e.g. "左上方", "中央"
        h_pos              – Horizontal: "左" / "中" / "右"
        v_pos              – Vertical:   "上" / "中" / "下"
        concentration      – "高度集中" / "中等分布" / "大面积"
        concentration_ratio – High-activation pixels as % of total map area
        near_edge          – True if high-activation region touches image border
        activation_strength – Mean activation of the high-activation region
    """
    # Degenerate map (all zeros or flat) — return safe neutral defaults
    if cam_np.size == 0 or float(cam_np.max() - cam_np.min()) < 1e-6:
        return {
            "position": "中央",
            "h_pos": "中",
            "v_pos": "中",
            "concentration": "大面积",
            "concentration_ratio": 50.0,
            "near_edge": False,
            "activation_strength": 0.5,
        }

    # Adaptive threshold: top-25 % activations define the "high" region
    threshold = float(np.percentile(cam_np, 75))
    high_mask = cam_np > threshold
    total_pixels = cam_np.size
    high_pixels = int(high_mask.sum())
    concentration_ratio = round((high_pixels / total_pixels) * 100.0, 1)

    if concentration_ratio < 15:
        concentration = "高度集中"
    elif concentration_ratio < 40:
        concentration = "中等分布"
    else:
        concentration = "大面积"

    # Centroid of the high-activation region (normalised coordinates 0..1)
    h_map, w_map = cam_np.shape
    ys, xs = np.where(high_mask)
    if len(xs) == 0:
        cy_norm, cx_norm = 0.5, 0.5
    else:
        cy_norm = float(ys.mean()) / h_map   # 0 = top,  1 = bottom
        cx_norm = float(xs.mean()) / w_map   # 0 = left, 1 = right

    h_pos = "左" if cx_norm < 0.35 else ("右" if cx_norm > 0.65 else "中")
    v_pos = "上" if cy_norm < 0.35 else ("下" if cy_norm > 0.65 else "中")

    if v_pos == "中" and h_pos == "中":
        position = "中央"
    elif v_pos == "中":
        position = h_pos + "侧"
    elif h_pos == "中":
        position = v_pos + "方"
    else:
        position = h_pos + v_pos + "方"   # e.g. "左上方"、"右下方"

    # Edge proximity: any high-activation pixel within 10 % of shorter edge
    edge_band = max(1, int(min(h_map, w_map) * 0.10))
    near_edge = bool(
        len(ys) > 0 and (
            (ys < edge_band).any()
            or (ys > h_map - edge_band - 1).any()
            or (xs < edge_band).any()
            or (xs > w_map - edge_band - 1).any()
        )
    )

    activation_strength = round(
        float(cam_np[high_mask].mean()) if high_pixels > 0 else 0.5, 3
    )

    return {
        "position": position,
        "h_pos": h_pos,
        "v_pos": v_pos,
        "concentration": concentration,
        "concentration_ratio": concentration_ratio,
        "near_edge": near_edge,
        "activation_strength": activation_strength,
    }


def _extract_cam_boxes(cam_np: np.ndarray, img_w: int, img_h: int, threshold: float = 0.5) -> list[dict]:
    """Return bounding box of the high-activation region in image pixel coordinates."""
    high_mask = cam_np > threshold
    if not high_mask.any():
        return []
    h_map, w_map = cam_np.shape
    ys, xs = np.where(high_mask)
    scale_x = img_w / w_map
    scale_y = img_h / h_map
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    strength = round(float(cam_np[y0:y1 + 1, x0:x1 + 1].mean()), 3)
    return [{
        "x": round(x0 * scale_x),
        "y": round(y0 * scale_y),
        "w": round((x1 - x0 + 1) * scale_x),
        "h": round((y1 - y0 + 1) * scale_y),
        "strength": strength,
    }]


def generate_cam_clues(label: str, cam_np: np.ndarray, img_w: int, img_h: int) -> list[str]:
    """Generate spatially-aware, dynamic explanation clues from a Grad-CAM map.

    Analyses the activation distribution (position, concentration, edge
    proximity, strength) and selects matching sentence templates so each
    result carries clues specific to that image rather than a fixed list.

    Falls back gracefully to *_COMMON_FAKE_CLUES* on any analysis error.
    """
    try:
        ri = analyze_cam_regions(cam_np, img_w, img_h)
    except Exception:
        return _COMMON_FAKE_CLUES[:3] if label == "FAKE" else []

    clues: list[str] = []

    if label == "FAKE":
        # Primary clue — spatial focus & concentration level
        if ri["concentration"] == "高度集中":
            clues.append(
                f"模型重点关注了图像{ri['position']}的局部区域"
                f"（高激活面积占比 {ri['concentration_ratio']:.1f}%），"
                f"该区域呈现出典型的 AI 合成局部不一致特征"
            )
        elif ri["concentration"] == "中等分布":
            clues.append(
                f"模型在图像{ri['position']}检测到中等范围的纹理异常"
                f"（激活面积占比 {ri['concentration_ratio']:.1f}%），"
                f"常见于扩散模型生成图片的过渡区域"
            )
        else:
            clues.append(
                f"模型激活分布较广（覆盖图像 {ri['concentration_ratio']:.1f}% 的区域），"
                f"整体风格特征偏离真实场景，符合 AI 全局风格迁移的特征"
            )

        # Secondary clue — edge anomaly (only appended when relevant)
        if ri["near_edge"]:
            clues.append(
                f"图像{ri['position']}边缘区域存在高激活响应，"
                f"可能为 AI 生成时的拼接或内容补全边界痕迹"
            )

        # Third clue — activation strength hints at generator family
        if ri["activation_strength"] > 0.82:
            clues.append(
                "高激活强度（≥0.82）指向 GAN 风格的尖锐伪迹，"
                "模型对该区域的判定依据非常集中"
            )
        elif ri["activation_strength"] < 0.55:
            clues.append(
                "较低的激活强度梯度分布符合扩散模型的平滑生成特点，"
                "图像细节过渡可能过于均匀"
            )
        else:
            clues.append("图像纹理细节与真实相机噪点分布不匹配，存在人工合成痕迹")

    else:  # label == "REAL"
        if ri["concentration"] == "高度集中":
            clues.append(
                f"模型重点核查了图像{ri['position']}区域，"
                f"该区域激活集中但符合真实照片的局部特征分布"
            )
        elif ri["concentration"] == "大面积":
            clues.append(
                f"模型激活分布广泛（覆盖 {ri['concentration_ratio']:.1f}% 区域），"
                f"图像整体特征均匀，符合真实相机成像的自然规律"
            )
        else:
            clues.append(
                f"图像{ri['position']}的特征激活与周围区域协调一致，"
                f"未发现明显的 AI 合成边界或纹理突变"
            )

    return clues[:3]


def _make_batch_clues(label: str, confidence: float) -> list[str]:
    """Lightweight dynamic clues for batch detection (no Grad-CAM pass).

    Returns a concise confidence-aware hint; defers detailed spatial analysis
    to single-image detection mode so batch throughput is not impacted.
    """
    if label != "FAKE":
        return []
    if confidence >= 75:
        level_hint = "高置信度"
    elif confidence >= 60:
        level_hint = "中等置信度"
    else:
        level_hint = "低置信度"
    return [
        f"{level_hint}判定为 AI 生成（置信度 {confidence:.1f}%），"
        f"建议进行单张精细检测以获取 Grad-CAM 区域详细分析",
    ]


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


def explain_result(
    label: str,
    confidence: float,
    *,
    cam_clues: list[str] | None = None,
) -> dict:
    """Return a structured text explanation for the detection result.

    Args:
        label:      "FAKE" or "REAL".
        confidence: Top-class probability in [0, 100].
        cam_clues:  Dynamic clues from *generate_cam_clues()*; when provided
                    these replace the static *_COMMON_FAKE_CLUES* fallback.
    """
    rules = _FAKE_RULES if label == "FAKE" else _REAL_RULES
    level, summary = rules[-1][1], rules[-1][2]
    for threshold, lvl, desc in rules:
        if confidence >= threshold:
            level, summary = lvl, desc
            break

    if cam_clues is not None:
        clues = cam_clues
    else:
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

    Always performs a single Grad-CAM backward pass to power spatially-aware
    dynamic explanation clues.  When *with_cam* is True the same *cam_np* is
    reused to build the overlay image — there is no redundant second pass.

    Returns a dict:
        label       (str)   – "FAKE" or "REAL"
        label_zh    (str)   – localised label with emoji
        confidence  (float) – top-class probability in [0, 100]
        probs       (list)  – [{"label", "label_zh", "score"}, ...] sorted desc
        explanation (dict)  – {level, summary, clues, disclaimer}
        cam_image   (str|None) – base64 JPEG overlay (only when with_cam=True)
    """
    img_rgb = pil_image.convert("RGB")

    # ── Step 1: fast inference (no gradient tracking needed for probs) ──────
    img_tensor = _transform(img_rgb).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        output = _model(img_tensor)
        probs = torch.softmax(output / MODEL_TEMPERATURE, dim=1)[0]

    results = [
        {"label": cls, "label_zh": _label_zh(cls), "score": probs[i].item() * 100}
        for i, cls in enumerate(CLASSES)
    ]
    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[0]
    top_idx = CLASSES.index(top["label"])

    # ── Step 2: Grad-CAM (fresh tensor with requires_grad) ───────────────────
    # Runs once regardless of with_cam; cam_np drives both dynamic clues and
    # the optional overlay image so there is no second backward pass.
    inp_cam = _transform(img_rgb).unsqueeze(0).to(DEVICE)
    inp_cam.requires_grad_(True)
    cam_np = _grad_cam(inp_cam, top_idx)

    # ── Step 3: dynamic clues & explanation ──────────────────────────────────
    cam_clues = generate_cam_clues(top["label"], cam_np, *img_rgb.size)
    explanation = explain_result(top["label"], top["score"], cam_clues=cam_clues)

    # ── Step 4: optional overlay image — reuses cam_np, no extra backward ───
    cam_image = _build_cam_overlay(img_rgb, cam_np) if with_cam else None

    # ── Step 5: VSFC bbox extraction ────────────────────────────────────────
    cam_regions = _extract_cam_boxes(cam_np, *img_rgb.size)

    return enrich_detection_result({
        "label": top["label"],
        "label_zh": top["label_zh"],
        "confidence": top["score"],
        "probs": results,
        "explanation": explanation,
        "cam_image": cam_image,
        "cam_regions": cam_regions,
    })


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
        all_probs = torch.softmax(outputs / MODEL_TEMPERATURE, dim=1)

    results = []
    for probs in all_probs:
        items = [
            {"label": cls, "label_zh": _label_zh(cls), "score": probs[i].item() * 100}
            for i, cls in enumerate(CLASSES)
        ]
        items.sort(key=lambda x: x["score"], reverse=True)
        top = items[0]
        results.append(enrich_detection_result({
            "label": top["label"],
            "label_zh": top["label_zh"],
            "confidence": top["score"],
            "probs": items,
            "explanation": explain_result(
                top["label"], top["score"],
                cam_clues=_make_batch_clues(top["label"], top["score"]),
            ),
            "cam_image": None,
        }))
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


class _TextContentParser(HTMLParser):
    """HTML parser that extracts visible text content and page title."""

    _SKIP_TAGS = frozenset({"script", "style", "noscript", "iframe", "svg", "head"})

    def __init__(self):
        super().__init__()
        self.texts: list[str] = []
        self.title: str = ""
        self._skip_depth: int = 0
        self._in_title: bool = False
        self._title_parts: list[str] = []
        # og:title / og:description from meta tags
        self.og_title: str = ""
        self.og_description: str = ""

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag_lower == "title":
            self._in_title = True
        # Extract meta og:title/og:description
        if tag_lower == "meta":
            attr_dict = dict(attrs)
            prop = (attr_dict.get("property", "") or attr_dict.get("name", "")).lower()
            content = attr_dict.get("content", "")
            if prop == "og:title" and content:
                self.og_title = content.strip()
            elif prop in ("og:description", "description") and content:
                self.og_description = content.strip()

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag_lower == "title":
            self._in_title = False
            self.title = "".join(self._title_parts).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
        if self._skip_depth == 0:
            text = data.strip()
            if text and len(text) > 1:
                self.texts.append(text)

    def get_article_text(self) -> str:
        """Return concatenated visible text, deduplicated and filtered."""
        seen: set[str] = set()
        result: list[str] = []
        for t in self.texts:
            if t not in seen and len(t) > 4:
                seen.add(t)
                result.append(t)
        return "\n".join(result)

    def get_title(self) -> str:
        return self.og_title or self.title or ""

    def get_summary(self) -> str:
        """Extractive summary: up to 5 substantial sentences (~600 chars)."""
        desc = self.og_description
        if desc and len(desc) > 20:
            return desc[:600]
        article = self.get_article_text()
        # Pick sentences that look like article content (longer lines)
        sentences = [s for s in article.split("\n") if len(s) > 15]
        summary = " ".join(sentences[:5])
        return summary[:600] if summary else article[:600]


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

async def async_fetch_page_content(page_url: str) -> dict:
    """Fetch a page and return image URLs + extracted text content.

    Returns dict with keys: img_urls, title, summary, article_text
    """
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

    # Parse images
    img_parser = _ImgSrcParser()
    img_parser.feed(html_text)

    urls: list[str] = []
    seen: set[str] = set()
    for src in img_parser.srcs:
        if src.startswith("data:"):
            continue
        full = urljoin(page_url, src)
        if full not in seen:
            seen.add(full)
            urls.append(full)
        if len(urls) >= _MAX_IMAGES:
            break

    if len(urls) < _MAX_IMAGES:
        for raw_url in _IMG_URL_RE.findall(html_text):
            if raw_url not in seen:
                seen.add(raw_url)
                urls.append(raw_url)
            if len(urls) >= _MAX_IMAGES:
                break

    # Parse text content
    text_parser = _TextContentParser()
    text_parser.feed(html_text)

    return {
        "img_urls": urls,
        "title": text_parser.get_title(),
        "summary": text_parser.get_summary(),
        "article_text": text_parser.get_article_text()[:2000],
    }


async def async_fetch_image_urls(page_url: str) -> list[str]:
    """Same as fetch_image_urls but uses httpx for async HTTP."""
    content = await async_fetch_page_content(page_url)
    return content["img_urls"]


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
