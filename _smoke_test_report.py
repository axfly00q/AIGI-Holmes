"""Quick smoke test for report export."""
from backend.report.exporter import export_pdf, export_excel

report = {
    "id": 1,
    "conclusion": "该图片为 AI 生成内容",
    "label": "FAKE",
    "confidence": 92.5,
    "probs": [
        {"label": "FAKE", "label_zh": "AI 生成", "score": 92.5},
        {"label": "REAL", "label_zh": "真实照片", "score": 7.5},
    ],
    "suggestion": "建议进一步核实图片来源。",
    "model_version": "86ab57a1",
    "image_hash": "abc123def456",
    "image_url": None,
    "created_at": "2026-03-30T10:00:00",
}

pdf_bytes = export_pdf(report)
print(f"PDF: {len(pdf_bytes)} bytes, starts with %PDF: {pdf_bytes[:5]}")

xlsx_bytes = export_excel(report)
print(f"Excel: {len(xlsx_bytes)} bytes, starts with PK: {xlsx_bytes[:2]}")

print("OK: report export works")
