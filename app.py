"""
AIGI-Holmes: AI-Generated Image Detection App
Detects whether photos (e.g., from news articles) are AI-generated or real.
"""

import ipaddress
import io
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import gradio as gr
import requests
import torch
from PIL import Image
from transformers import pipeline

# ---------------------------------------------------------------------------
# Model initialisation
# ---------------------------------------------------------------------------
DEVICE = 0 if torch.cuda.is_available() else -1
MODEL_ID = "umm-maybe/AI-image-detector"

detector = pipeline(
    "image-classification",
    model=MODEL_ID,
    device=DEVICE,
)

LABELS_ZH = {
    "artificial": "🤖 AI 生成",
    "real": "📷 真实照片",
}


def _label_zh(label: str) -> str:
    label_lower = label.lower()
    for key, zh in LABELS_ZH.items():
        if key in label_lower:
            return zh
    return label


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------

def detect_image(pil_image: Image.Image):
    """Run the detector on a PIL image and return formatted results."""
    results = detector(pil_image)
    top = results[0]
    label_zh = _label_zh(top["label"])
    confidence = top["score"] * 100

    rows = "\n".join(
        f"  {_label_zh(r['label'])}: {r['score']*100:.1f}%"
        for r in results
    )
    summary = f"**预测结果：{label_zh}**（置信度 {confidence:.1f}%）\n\n各类别概率：\n{rows}"
    return label_zh, confidence, summary


# ---------------------------------------------------------------------------
# Tab 1 – Upload image
# ---------------------------------------------------------------------------

def classify_uploaded(image):
    if image is None:
        return "", 0.0, "⚠️ 请上传一张图片。"
    label_zh, confidence, summary = detect_image(image)
    return label_zh, confidence, summary


# ---------------------------------------------------------------------------
# Tab 2 – News URL
# ---------------------------------------------------------------------------

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    )
}
_MAX_IMAGES = 10  # protect against pages with hundreds of images


class _ImgSrcParser(HTMLParser):
    """Minimal HTML parser that collects <img> src / data-src attributes."""

    def __init__(self):
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        attr_dict = dict(attrs)
        for key in ("src", "data-src", "data-lazy-src"):
            val = attr_dict.get(key, "")
            if val:
                self.srcs.append(val)
                break


def _has_image_ext(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _IMG_EXTS)


def _validate_public_url(url: str) -> None:
    """Reject non-HTTP(S) schemes and private/loopback destinations (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("仅支持 http/https 协议的 URL。")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL 中未包含有效主机名。")
    # Reject localhost / loopback names
    if host.lower() in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("不允许访问本地地址。")
    # Reject private IP ranges
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise ValueError("不允许访问私有或保留 IP 地址。")
    except ValueError as exc:
        # If it's not a valid IP address string it's a hostname — allow it,
        # but re-raise if we set the message ourselves
        if "不允许" in str(exc) or "仅支持" in str(exc) or "有效" in str(exc):
            raise


def _fetch_image_urls(page_url: str) -> list[str]:
    """Extract img src URLs from a news page using the stdlib HTML parser."""
    _validate_public_url(page_url)
    try:
        resp = requests.get(page_url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ValueError("无法连接到该地址，请检查 URL 或网络连接。")
    except requests.exceptions.Timeout:
        raise ValueError("请求超时，服务器响应过慢。")
    except requests.exceptions.HTTPError as exc:
        raise ValueError(f"页面请求失败（HTTP {exc.response.status_code}）。")

    parser = _ImgSrcParser()
    parser.feed(resp.text)

    urls: list[str] = []
    seen: set[str] = set()
    for src in parser.srcs:
        if src.startswith("data:"):  # skip base64 inline images
            continue
        full = urljoin(page_url, src)
        if full not in seen and _has_image_ext(full):
            seen.add(full)
            urls.append(full)
        if len(urls) >= _MAX_IMAGES:
            break
    return urls


def _download_image(url: str) -> Image.Image | None:
    try:
        _validate_public_url(url)
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        # skip tiny icons
        if img.width < 64 or img.height < 64:
            return None
        return img
    except Exception:
        return None


def classify_news_url(url: str):
    """Fetch images from a news URL and classify each one."""
    if not url or not url.startswith("http"):
        return [], "⚠️ 请输入有效的新闻页面 URL（以 http 或 https 开头）。"

    try:
        img_urls = _fetch_image_urls(url)
    except ValueError as exc:
        return [], f"❌ {exc}"
    except Exception as exc:
        return [], f"❌ 无法访问该页面：{exc}"

    if not img_urls:
        return [], "⚠️ 未在页面中找到图片（尝试直接上传图片）。"

    gallery = []
    report_lines = [f"共找到 **{len(img_urls)}** 张图片，检测结果如下：\n"]

    for i, img_url in enumerate(img_urls, 1):
        img = _download_image(img_url)
        if img is None:
            continue
        label_zh, confidence, _ = detect_image(img)
        caption = f"{i}. {label_zh}  {confidence:.1f}%"
        gallery.append((img, caption))
        report_lines.append(f"**图{i}**：{label_zh}（{confidence:.1f}%）  \n来源：{img_url}")

    if not gallery:
        return [], "⚠️ 下载图片失败，请检查网络或尝试直接上传图片。"

    return gallery, "\n\n".join(report_lines)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="AIGI-Holmes 新闻图片真实性检测") as demo:
    gr.Markdown(
        """
# 🔍 AIGI-Holmes — 新闻图片 AI 生成检测

判断照片是由 **AI 生成** 还是 **真实拍摄**。  
支持直接上传图片，或输入新闻页面 URL 批量检测。
        """
    )

    with gr.Tab("📤 上传图片"):
        with gr.Row():
            inp_img = gr.Image(type="pil", label="上传图片")
            with gr.Column():
                out_label = gr.Textbox(label="预测标签", interactive=False)
                out_conf = gr.Number(label="置信度（%）", interactive=False)
                out_detail = gr.Markdown(label="详细结果")
        btn_img = gr.Button("开始检测", variant="primary")
        btn_img.click(
            classify_uploaded,
            inputs=inp_img,
            outputs=[out_label, out_conf, out_detail],
        )

    with gr.Tab("🌐 新闻 URL 检测"):
        inp_url = gr.Textbox(
            label="新闻页面 URL",
            placeholder="https://example.com/news/article",
        )
        btn_url = gr.Button("抓取并检测图片", variant="primary")
        out_gallery = gr.Gallery(label="检测结果（标题 = 预测类别 + 置信度）", columns=3)
        out_report = gr.Markdown(label="汇总报告")
        btn_url.click(
            classify_news_url,
            inputs=inp_url,
            outputs=[out_gallery, out_report],
        )

    gr.Markdown(
        """
---
**模型**：[umm-maybe/AI-image-detector](https://huggingface.co/umm-maybe/AI-image-detector)（ViT 微调，基于 AI 生成 vs 真实图片数据集训练）  
**提示**：结果仅供参考，复杂或高质量 AI 图片可能难以被检测。
        """
    )

if __name__ == "__main__":
    demo.launch(share=False)
