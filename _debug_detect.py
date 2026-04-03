"""Debug the /api/detect response."""
import io, requests
import numpy as np
from PIL import Image

BASE = "http://127.0.0.1:7861"
img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)

r = requests.post(f"{BASE}/api/detect", files={"image": ("test.png", buf, "image/png")})
print(f"Status: {r.status_code}")
print(f"Headers: {dict(r.headers)}")
print(f"Body: {r.text[:500]}")
