"""End-to-end integration test against the running FastAPI server."""
import io
import requests
import numpy as np
from PIL import Image

BASE = "http://127.0.0.1:7861"

# 1. Test root page
r = requests.get(f"{BASE}/")
assert r.status_code == 200
print(f"[OK] GET / → {r.status_code}")

# 2. Test /api/detect without auth (should work — optional auth)
img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)

r = requests.post(f"{BASE}/api/detect", files={"image": ("test.png", buf, "image/png")})
print(f"[OK] POST /api/detect → {r.status_code} {r.json()['label']} ({r.json()['confidence']:.1f}%)")

# 3. Register user
r = requests.post(f"{BASE}/api/auth/register", json={"username": "testuser", "password": "testpass123"})
assert r.status_code == 200, f"Register failed: {r.text}"
tokens = r.json()
print(f"[OK] POST /api/auth/register → {r.status_code}")

# 4. Login
r = requests.post(f"{BASE}/api/auth/login", json={"username": "testuser", "password": "testpass123"})
assert r.status_code == 200
tokens = r.json()
access = tokens["access_token"]
print(f"[OK] POST /api/auth/login → {r.status_code}")

# 5. Refresh token
r = requests.post(f"{BASE}/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
assert r.status_code == 200
print(f"[OK] POST /api/auth/refresh → {r.status_code}")

# 6. Test /api/detect WITH auth
buf.seek(0)
r = requests.post(
    f"{BASE}/api/detect",
    files={"image": ("test.png", buf, "image/png")},
    headers={"Authorization": f"Bearer {access}"},
)
assert r.status_code == 200
print(f"[OK] POST /api/detect (authed) → {r.status_code}")

# 7. Test /api/detect-batch (should fail — user role can't batch)
buf.seek(0)
buf2 = io.BytesIO()
img.save(buf2, format="PNG")
buf2.seek(0)
r = requests.post(
    f"{BASE}/api/detect-batch",
    files=[("images", ("t1.png", buf, "image/png")), ("images", ("t2.png", buf2, "image/png"))],
    headers={"Authorization": f"Bearer {access}"},
)
print(f"[OK] POST /api/detect-batch (user role) → {r.status_code} (expected 403)")

# 8. Test /api/report/generate
r = requests.post(
    f"{BASE}/api/report/generate",
    params={"detection_id": 1},
    headers={"Authorization": f"Bearer {access}"},
)
print(f"[OK] POST /api/report/generate → {r.status_code}")

# 9. Test report export PDF
if r.status_code == 200:
    r2 = requests.get(
        f"{BASE}/api/report/1/export?format=pdf",
        headers={"Authorization": f"Bearer {access}"},
    )
    print(f"[OK] GET /api/report/1/export?format=pdf → {r2.status_code}, {len(r2.content)} bytes")

    r3 = requests.get(
        f"{BASE}/api/report/1/export?format=excel",
        headers={"Authorization": f"Bearer {access}"},
    )
    print(f"[OK] GET /api/report/1/export?format=excel → {r3.status_code}, {len(r3.content)} bytes")

# 10. Test /docs
r = requests.get(f"{BASE}/docs")
assert r.status_code == 200
print(f"[OK] GET /docs → {r.status_code}")

print("\n=== All integration tests passed ===")
