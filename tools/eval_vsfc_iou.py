"""
eval_vsfc_iou.py — VSFC IoU evaluation script.

Compares single-layer (no cam_regions) vs two-layer (evidence-anchored)
豆包 LLM responses for a directory of test images.

For each image:
  1. Run detect_image() → cam_regions (ground-truth high-activation bbox list).
  2. Parse the LLM evidence-anchored text for coordinate / directional phrases
     and map them to a text-derived bbox.
  3. Compute IoU between cam_regions[0] and the text-derived bbox.
  4. Accumulate mean IoU for single-layer (baseline) vs two-layer (VSFC).

Usage:
    python tools/eval_vsfc_iou.py --image-dir data/test_images \
        [--api-key YOUR_KEY] [--model doubao-pro-32k] [--out results.json]

If --api-key is omitted the script reads DOUBAO_API_KEY from the environment.
"""

import argparse
import asyncio
import json
import math
import os
import re
import sys
from pathlib import Path

# Allow running from project root without installing the package
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PIL import Image

from detect import detect_image
from backend.llm.doubao_client import DoubaoClient


# ---------------------------------------------------------------------------
# IoU helpers
# ---------------------------------------------------------------------------

def _iou(a: dict, b: dict) -> float:
    """Axis-aligned IoU between two {x,y,w,h} dicts. Returns 0 if no overlap."""
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["w"], ay1 + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["w"], by1 + b["h"]

    inter_x = max(0, min(ax2, bx2) - max(ax1, bx1))
    inter_y = max(0, min(ay2, by2) - max(ay1, by1))
    inter_area = inter_x * inter_y
    if inter_area == 0:
        return 0.0

    union_area = a["w"] * a["h"] + b["w"] * b["h"] - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


# ---------------------------------------------------------------------------
# Text-bbox extraction (heuristic regex over LLM output)
# ---------------------------------------------------------------------------

_RE_PIXEL = re.compile(
    r"x[=\s:：]+(\d+)[,，\s]+y[=\s:：]+(\d+)[,，\s]+w(?:idth)?[=\s:：]+(\d+)[,，\s]+h(?:eight)?[=\s:：]+(\d+)",
    re.IGNORECASE,
)

_RE_PERCENT = re.compile(r"(\d{1,3})\s*%.*?(\d{1,3})\s*%.*?(\d{1,3})\s*%.*?(\d{1,3})\s*%")

_DIRECTION_MAP = {
    "左上": (0.0, 0.0, 0.4, 0.4),
    "右上": (0.6, 0.0, 0.4, 0.4),
    "左下": (0.0, 0.6, 0.4, 0.4),
    "右下": (0.6, 0.6, 0.4, 0.4),
    "左侧": (0.0, 0.25, 0.35, 0.5),
    "右侧": (0.65, 0.25, 0.35, 0.5),
    "上方": (0.25, 0.0, 0.5, 0.35),
    "下方": (0.25, 0.65, 0.5, 0.35),
    "中央": (0.25, 0.25, 0.5, 0.5),
    "中间": (0.25, 0.25, 0.5, 0.5),
}


def _text_to_bbox(text: str, img_w: int, img_h: int) -> dict | None:
    """Attempt to extract a bounding box from LLM response text.

    Priority:
      1. Explicit pixel coordinates x=…,y=…,w=…,h=…
      2. Percentage-based coordinates (x%,y%,w%,h%)
      3. Directional keywords (左上, 右侧, 中央, …)

    Returns {x,y,w,h} in image pixel coordinates, or None if nothing found.
    """
    # 1. Explicit pixel coords
    m = _RE_PIXEL.search(text)
    if m:
        x, y, w, h = (int(v) for v in m.groups())
        return {"x": x, "y": y, "w": w, "h": h}

    # 2. Percentage-based
    m = _RE_PERCENT.search(text)
    if m:
        xp, yp, wp, hp = (float(v) / 100 for v in m.groups())
        return {
            "x": round(xp * img_w),
            "y": round(yp * img_h),
            "w": round(wp * img_w),
            "h": round(hp * img_h),
        }

    # 3. Directional keyword (first match wins)
    for keyword, (rx, ry, rw, rh) in _DIRECTION_MAP.items():
        if keyword in text:
            return {
                "x": round(rx * img_w),
                "y": round(ry * img_h),
                "w": round(rw * img_w),
                "h": round(rh * img_h),
            }

    return None


# ---------------------------------------------------------------------------
# Per-image evaluation
# ---------------------------------------------------------------------------

async def eval_image(
    image_path: Path,
    client: DoubaoClient | None,
) -> dict:
    """
    Returns a dict:
        path, img_w, img_h, cam_regions,
        iou_single (0.0 when no cam bbox or no LLM key),
        iou_vsfc   (IoU of VSFC evidence-anchored text vs cam bbox),
        global_text, evidence_text
    """
    img = Image.open(image_path).convert("RGB")
    img_w, img_h = img.size

    result = detect_image(img, with_cam=False)
    cam_regions = result.get("cam_regions", [])

    iou_single = 0.0
    iou_vsfc = 0.0
    global_text = ""
    evidence_text = ""

    if not cam_regions or client is None:
        return {
            "path": str(image_path),
            "img_w": img_w, "img_h": img_h,
            "cam_regions": cam_regions,
            "iou_single": iou_single,
            "iou_vsfc": iou_vsfc,
            "global_text": global_text,
            "evidence_text": evidence_text,
        }

    cam_box = cam_regions[0]  # primary bbox

    # Two-layer VSFC call
    report = await client.generate_vsfc_report(result, cam_regions)
    global_text = report.get("global", "")
    evidence_text = report.get("evidence_anchored", "")

    # Single-layer baseline: parse only the global text for spatial mentions
    single_bbox = _text_to_bbox(global_text, img_w, img_h)
    if single_bbox:
        iou_single = _iou(cam_box, single_bbox)

    # VSFC: parse evidence-anchored text
    vsfc_bbox = _text_to_bbox(evidence_text, img_w, img_h)
    if vsfc_bbox:
        iou_vsfc = _iou(cam_box, vsfc_bbox)

    return {
        "path": str(image_path),
        "img_w": img_w, "img_h": img_h,
        "cam_regions": cam_regions,
        "iou_single": round(iou_single, 4),
        "iou_vsfc": round(iou_vsfc, 4),
        "global_text": global_text,
        "evidence_text": evidence_text,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _collect_images(image_dir: Path) -> list[Path]:
    return sorted(p for p in image_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS)


async def run(args: argparse.Namespace) -> None:
    image_dir = Path(args.image_dir)
    if not image_dir.is_dir():
        print(f"[ERROR] {image_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    images = _collect_images(image_dir)
    if not images:
        print("[ERROR] No images found in directory", file=sys.stderr)
        sys.exit(1)

    api_key = args.api_key or os.environ.get("DOUBAO_API_KEY", "")
    client = DoubaoClient(api_key, model=args.model) if api_key else None
    if not client:
        print("[WARN] No DOUBAO_API_KEY — LLM calls skipped, IoU will be 0")

    print(f"Evaluating {len(images)} images …")
    records = []
    for img_path in images:
        print(f"  {img_path.name}", end=" ", flush=True)
        record = await eval_image(img_path, client)
        records.append(record)
        print(f"iou_single={record['iou_single']:.4f}  iou_vsfc={record['iou_vsfc']:.4f}")

    valid = [r for r in records if r["cam_regions"]]
    n = len(valid)
    mean_single = sum(r["iou_single"] for r in valid) / n if n else 0.0
    mean_vsfc = sum(r["iou_vsfc"] for r in valid) / n if n else 0.0

    summary = {
        "n_images": len(records),
        "n_with_cam": n,
        "mean_iou_single_layer": round(mean_single, 4),
        "mean_iou_vsfc_two_layer": round(mean_vsfc, 4),
        "delta": round(mean_vsfc - mean_single, 4),
        "records": records,
    }

    print()
    print(f"Results (n={n} images with Grad-CAM bbox)")
    print(f"  Mean IoU — single-layer : {mean_single:.4f}")
    print(f"  Mean IoU — VSFC 2-layer : {mean_vsfc:.4f}")
    print(f"  Δ IoU                   : {mean_vsfc - mean_single:+.4f}")

    out_path = Path(args.out)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate VSFC IoU improvement")
    parser.add_argument("--image-dir", required=True, help="Directory of test images")
    parser.add_argument("--api-key", default="", help="豆包 API key (fallback: env DOUBAO_API_KEY)")
    parser.add_argument("--model", default="doubao-pro-32k", help="豆包 model name")
    parser.add_argument("--out", default="vsfc_iou_results.json", help="Output JSON path")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
