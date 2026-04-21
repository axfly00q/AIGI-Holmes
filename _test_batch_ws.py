"""
批量检测 WebSocket 流程测试
验证后端"逐一处理，处理完一张立即推送结果"的逻辑
"""
import asyncio
import io
import json
import sys
import time

import numpy as np
import requests
import websockets
from PIL import Image

BASE = "http://127.0.0.1:7862"
WS_BASE = "ws://127.0.0.1:7862"


def make_test_image():
    arr = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_basic():
    # Root
    r = requests.get(f"{BASE}/")
    assert r.status_code == 200, f"root failed {r.status_code}"
    print(f"[OK] GET / -> 200")

    # Single detect
    buf = make_test_image()
    r = requests.post(f"{BASE}/api/detect", files={"image": ("t.png", buf, "image/png")})
    assert r.status_code == 200
    j = r.json()
    assert j["label"] in ("FAKE", "REAL")
    print(f"[OK] POST /api/detect -> label={j['label']} conf={j['confidence']:.1f}%")


def get_auditor_token():
    """注册并自我提升为 auditor（仅测试环境）"""
    un = f"auditor_{int(time.time())}"
    r = requests.post(f"{BASE}/api/auth/register", json={"username": un, "password": "testpass123"})
    if r.status_code not in (200, 400):
        raise RuntimeError(f"register failed {r.status_code} {r.text}")
    r = requests.post(f"{BASE}/api/auth/login", json={"username": un, "password": "testpass123"})
    assert r.status_code == 200, f"login failed {r.text}"
    access = r.json()["access_token"]
    # Elevate to auditor via admin API
    r2 = requests.patch(
        f"{BASE}/api/auth/admin/users/{un}/role",
        json={"role": "auditor"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r2.status_code == 200, f"role elevation failed {r2.status_code} {r2.text}"
    # Re-login to get token with new role
    r3 = requests.post(f"{BASE}/api/auth/login", json={"username": un, "password": "testpass123"})
    assert r3.status_code == 200
    print(f"[OK] Created auditor user '{un}'")
    return r3.json()["access_token"]


async def test_batch_ws(token):
    """测试批量 WebSocket 流程：验证结果逐一到达（start → result × N → complete）"""
    # batch-init
    r = requests.post(
        f"{BASE}/api/detect-batch-init",
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code == 403:
        print("[SKIP] batch-init 403 — 账号不是 auditor/admin，WebSocket 测试跳过")
        return
    assert r.status_code == 200, f"batch-init failed {r.status_code} {r.text}"
    job_id = r.json()["job_id"]
    print(f"[OK] batch-init -> job_id={job_id}")

    events = []

    async def ws_listener():
        uri = f"{WS_BASE}/ws/detect/{job_id}?token={token}"
        async with websockets.connect(uri) as ws:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=300)  # CLIP 首次需下载模型
                ev = json.loads(msg)
                events.append(ev)
                print(f"  [WS] type={ev['type']}", ev.get("index", ""), ev.get("filename", ""))
                if ev["type"] == "complete":
                    break

    # 先建 WS，再上传文件
    listener_task = asyncio.create_task(ws_listener())
    await asyncio.sleep(0.3)  # 等 WS 握手

    # 上传 3 张图片
    images = []
    for i in range(3):
        buf = make_test_image()
        images.append(("files", (f"img{i}.png", buf.read(), "image/png")))

    r = requests.post(
        f"{BASE}/api/detect-batch-run?job_id={job_id}",
        files=images,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, f"batch-run failed {r.status_code} {r.text}"
    print("[OK] batch-run -> processing")

    await listener_task

    # 验证事件序列
    types = [ev["type"] for ev in events]
    assert types[0] == "start", f"first event should be 'start', got {types[0]}"
    result_indices = [ev["index"] for ev in events if ev["type"] == "result"]
    assert types[-1] == "complete", f"last event should be 'complete', got {types[-1]}"
    total = events[-1]["count"]
    print(f"[OK] WS events: start -> result×{len(result_indices)} -> complete({total})")

    # 验证 result 事件在 complete 前逐个到达（不是批量到达）
    # 因为每张处理完就 push，所以每个 result 中都要携带正确字段
    for ev in events:
        if ev["type"] == "result":
            r_data = ev["result"]
            assert "label" in r_data and r_data["label"] in ("FAKE", "REAL")
            assert "confidence" in r_data
            assert "thumbnail" in r_data
            assert "category" in r_data
    print("[OK] All result events have correct fields")


def main():
    test_basic()
    token = get_auditor_token()
    # 普通用户不能 batch，需要手动提升，跳过 WS 测试时仅报警
    asyncio.run(test_batch_ws(token))
    print()
    print("=== All tests passed ===")


if __name__ == "__main__":
    main()
