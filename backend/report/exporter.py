"""
AIGI-Holmes backend — export detection reports to PDF / Excel.
"""

import io

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _register_chinese_font() -> str:
    """Try to register a Chinese-capable font; fall back to Helvetica."""
    import os
    candidates = [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "msyh.ttc"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "simsun.ttc"),
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", path))
                return "ChineseFont"
            except Exception:
                continue
    return "Helvetica"


def export_pdf(report: dict) -> bytes:
    """Generate a PDF report and return raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)

    font_name = _register_chinese_font()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CN", fontName=font_name, fontSize=11, leading=16))
    styles.add(ParagraphStyle(name="CNTitle", fontName=font_name, fontSize=16, leading=22, spaceAfter=10))

    elements: list = []
    elements.append(Paragraph("AIGI-Holmes 检测报告", styles["CNTitle"]))
    elements.append(Spacer(1, 6 * mm))

    rows = [
        ["检测结论", report.get("conclusion", "")],
        ["标签", report.get("label", "")],
        ["置信度", f'{report.get("confidence", 0):.1f}%'],
        ["审核建议", report.get("suggestion", "")],
        ["模型版本", report.get("model_version", "")],
        ["图片哈希", report.get("image_hash", "")[:16] + "..."],
        ["检测时间", report.get("created_at", "")],
    ]

    table = Table(rows, colWidths=[100, 350])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.93, 0.93, 0.93)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    doc.build(elements)
    return buf.getvalue()


def export_excel(report: dict) -> bytes:
    """Generate an Excel report and return raw bytes."""
    wb = Workbook()
    ws = wb.active
    ws.title = "检测报告"

    ws.append(["字段", "值"])
    ws.append(["检测结论", report.get("conclusion", "")])
    ws.append(["标签", report.get("label", "")])
    ws.append(["置信度", f'{report.get("confidence", 0):.1f}%'])
    ws.append(["审核建议", report.get("suggestion", "")])
    ws.append(["模型版本", report.get("model_version", "")])
    ws.append(["图片哈希", report.get("image_hash", "")])
    ws.append(["图片 URL", report.get("image_url", "") or "N/A"])
    ws.append(["检测时间", report.get("created_at", "")])

    # probabilities
    ws.append([])
    ws.append(["类别", "类别(中文)", "概率(%)"])
    for p in report.get("probs", []):
        ws.append([p.get("label", ""), p.get("label_zh", ""), f'{p.get("score", 0):.1f}'])

    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 50

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
