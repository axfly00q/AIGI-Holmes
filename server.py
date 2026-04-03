"""
AIGI-Holmes: Flask web server — API endpoints for the new HTML/JS frontend.
"""

import base64
import io
import os
import sys

from flask import Flask, jsonify, render_template, request
from PIL import Image

from detect import detect_image, download_image, fetch_image_urls

# ---------------------------------------------------------------------------
# Base directory — compatible with plain Python and PyInstaller .exe
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(__file__)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/detect")
def api_detect():
    """Accept a multipart/form-data image, return detection result as JSON."""
    if "image" not in request.files:
        return jsonify({"error": "未上传图片"}), 400
    file = request.files["image"]
    try:
        img = Image.open(file.stream)
    except Exception:
        return jsonify({"error": "无法解析图片文件，请上传有效的图片。"}), 400

    want_cam = request.args.get("cam", "0") == "1"
    result = detect_image(img, with_cam=want_cam)
    return jsonify(result)


@app.post("/api/detect-url")
def api_detect_url():
    """Accept JSON {url}, scrape images, run detection, return results as JSON."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "请输入有效的新闻页面 URL（以 http 或 https 开头）。"}), 400

    try:
        img_urls = fetch_image_urls(url)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"无法访问该页面：{exc}"}), 400

    if not img_urls:
        return jsonify({"error": "未在页面中找到图片（尝试直接上传图片）。"}), 404

    results = []
    for i, img_url in enumerate(img_urls, 1):
        img = download_image(img_url)
        if img is None:
            continue
        det = detect_image(img)

        # Encode a 400-px thumbnail for display in the frontend
        buf = io.BytesIO()
        thumb = img.copy()
        thumb.thumbnail((400, 400))
        thumb.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode()

        results.append({
            "index": i,
            "url": img_url,
            "label": det["label"],
            "label_zh": det["label_zh"],
            "confidence": round(det["confidence"], 1),
            "probs": [
                {**p, "score": round(p["score"], 1)}
                for p in det["probs"]
            ],
            "thumbnail": f"data:image/jpeg;base64,{b64}",
        })

    if not results:
        return jsonify({"error": "下载图片失败，请检查网络或尝试直接上传图片。"}), 404

    return jsonify({"count": len(results), "results": results})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860, debug=False)
