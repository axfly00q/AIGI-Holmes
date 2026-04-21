"""
Composite scorer — merges all six dimensions into a single overall score.

Dimension weights (matching plan):
  authenticity   0.25
  confidence     0.20
  consistency    0.20
  seal           0.15
  frequency      0.10
  edge           0.10

Also provides a descriptive verdict string.
"""

from __future__ import annotations

_WEIGHTS = {
    "authenticity": 0.25,
    "confidence":   0.20,
    "consistency":  0.20,
    "seal":         0.15,
    "frequency":    0.10,
    "edge":         0.10,
}


def compute_overall(
    *,
    authenticity: float,
    confidence: float,
    consistency: float,
    seal: float,
    frequency: float,
    edge: float,
) -> dict:
    """
    Parameters are each 0-100 scores.
    Returns {"overall_score": float, "verdict": str, "level": str}
    """
    raw = (
        authenticity * _WEIGHTS["authenticity"]
        + confidence * _WEIGHTS["confidence"]
        + consistency * _WEIGHTS["consistency"]
        + seal * _WEIGHTS["seal"]
        + frequency * _WEIGHTS["frequency"]
        + edge * _WEIGHTS["edge"]
    )
    overall = round(max(0.0, min(100.0, raw)), 1)

    if overall >= 70:
        level = "credible"
        verdict = "该页面图片整体可信度较高，多维度检测未发现明显异常。"
    elif overall >= 40:
        level = "suspicious"
        verdict = "该页面图片存在可疑之处，建议进一步人工核实。"
    else:
        level = "unreliable"
        verdict = "该页面图片可信度较低，多项检测维度显示异常，请谨慎采信。"

    return {"overall_score": overall, "verdict": verdict, "level": level}
