"""Quick smoke test for detect.py changes."""
from detect import detect_image, detect_batch, MODEL_VERSION
from PIL import Image
import numpy as np

img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))

r = detect_image(img)
print("detect_image:", r["label"], f'{r["confidence"]:.1f}%')

results = detect_batch([img, img])
print(f"detect_batch: {len(results)} results")
print("  [0]:", results[0]["label"], f'{results[0]["confidence"]:.1f}%')
print("  [1]:", results[1]["label"], f'{results[1]["confidence"]:.1f}%')
print("MODEL_VERSION:", MODEL_VERSION)

assert abs(r["confidence"] - results[0]["confidence"]) < 0.01, "Results differ!"
print("OK: single and batch results match")
