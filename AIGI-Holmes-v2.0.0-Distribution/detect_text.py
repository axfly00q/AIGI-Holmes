"""
AIGI-Holmes — extract images from text-based files (HTML, TXT, PDF, DOCX).

Each extractor returns a list of PIL Images ready for detection.
The unified entry point is ``extract_images_from_file(filename, content)``.
"""

import io
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from PIL import Image

# ---------------------------------------------------------------------------
# Shared constants (mirrors detect.py but avoids circular import)
# ---------------------------------------------------------------------------
_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    )
}
_IMG_URL_RE = re.compile(
    r'https?://[^\s"<>\')]+\.(?:jpg|jpeg|png|webp|gif|bmp)',
    re.IGNORECASE,
)
_MAX_EXTRACT = 20  # safety cap per file


# ---------------------------------------------------------------------------
# HTML parser (same logic as detect._ImgSrcParser)
# ---------------------------------------------------------------------------
class _ImgSrcParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        d = dict(attrs)
        for key in ("src", "data-src", "data-lazy-src"):
            val = d.get(key, "")
            if val:
                self.srcs.append(val)
                break


# ---------------------------------------------------------------------------
# Async image downloader (small helper, SSRF-safe via detect.validate_public_url)
# ---------------------------------------------------------------------------
async def _download(url: str) -> Image.Image | None:
    from detect import validate_public_url

    try:
        validate_public_url(url)
    except ValueError:
        return None
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10, follow_redirects=True) as c:
            resp = await c.get(url)
            resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        if img.width < 64 or img.height < 64:
            return None
        return img
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Per-format extractors
# ---------------------------------------------------------------------------

async def extract_images_from_html(content: bytes, base_url: str = "") -> list[Image.Image]:
    """Parse HTML, find <img> tags, download and return images."""
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        return []

    parser = _ImgSrcParser()
    parser.feed(text)

    images: list[Image.Image] = []
    seen: set[str] = set()
    for src in parser.srcs:
        if src.startswith("data:"):
            continue
        full = urljoin(base_url, src) if base_url else src
        if full in seen:
            continue
        seen.add(full)
        img = await _download(full)
        if img is not None:
            images.append(img)
        if len(images) >= _MAX_EXTRACT:
            break
    return images


async def extract_images_from_txt(content: bytes) -> list[Image.Image]:
    """Extract image URLs from plain text and download them."""
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        return []

    urls = _IMG_URL_RE.findall(text)
    images: list[Image.Image] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        img = await _download(url)
        if img is not None:
            images.append(img)
        if len(images) >= _MAX_EXTRACT:
            break
    return images


def extract_images_from_pdf(content: bytes) -> list[Image.Image]:
    """Extract embedded images from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return []

    images: list[Image.Image] = []
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        for page in doc:
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if not base_image or not base_image.get("image"):
                    continue
                try:
                    pil = Image.open(io.BytesIO(base_image["image"])).convert("RGB")
                    if pil.width >= 64 and pil.height >= 64:
                        images.append(pil)
                except Exception:
                    continue
                if len(images) >= _MAX_EXTRACT:
                    break
            if len(images) >= _MAX_EXTRACT:
                break
        doc.close()
    except Exception:
        pass
    return images


def extract_images_from_docx(content: bytes) -> list[Image.Image]:
    """Extract embedded images from a DOCX file."""
    try:
        import docx
    except ImportError:
        return []

    images: list[Image.Image] = []
    try:
        document = docx.Document(io.BytesIO(content))
        for rel in document.part.rels.values():
            if "image" in rel.reltype:
                blob = rel.target_part.blob
                try:
                    pil = Image.open(io.BytesIO(blob)).convert("RGB")
                    if pil.width >= 64 and pil.height >= 64:
                        images.append(pil)
                except Exception:
                    continue
                if len(images) >= _MAX_EXTRACT:
                    break
    except Exception:
        pass
    return images


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

async def extract_images_from_file(filename: str, content: bytes) -> list[Image.Image]:
    """Dispatch to the correct extractor based on file extension.

    Returns an empty list for unsupported file types.
    """
    name = filename.lower()
    if name.endswith((".html", ".htm")):
        return await extract_images_from_html(content)
    if name.endswith(".txt"):
        return await extract_images_from_txt(content)
    if name.endswith(".pdf"):
        return extract_images_from_pdf(content)
    if name.endswith(".docx"):
        return extract_images_from_docx(content)
    return []
