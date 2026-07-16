"""Versioned, backwards-compatible image detection result helpers.

The ResNet50 probability is the only input to the final verdict.  Forensic
analysers are deliberately exposed as supporting signals and never change it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


RESULT_VERSION = "2.0"
LIKELY_AI_GENERATED = "likely_ai_generated"
LIKELY_AUTHENTIC = "likely_authentic"
INCONCLUSIVE = "inconclusive"

_DEFAULT_THRESHOLDS = {"authentic_max": 35.0, "ai_min": 65.0}
_METADATA_PATH = Path(__file__).resolve().parents[1] / "resources" / "image_detector" / "metadata.yaml"


def load_result_metadata() -> dict[str, Any]:
    """Load release metadata, falling back safely before the first retrain."""
    metadata: dict[str, Any] = {
        "result_version": RESULT_VERSION,
        "thresholds": dict(_DEFAULT_THRESHOLDS),
        "release_status": "baseline",
    }
    try:
        import yaml
        stored = yaml.safe_load(_METADATA_PATH.read_text(encoding="utf-8")) or {}
        metadata.update(stored)
        metadata["thresholds"] = {**_DEFAULT_THRESHOLDS, **stored.get("thresholds", {})}
    except (OSError, ValueError, TypeError):
        pass
    return metadata


def fake_probability(probs: list[dict[str, Any]]) -> float:
    for item in probs:
        if str(item.get("label", "")).upper() == "FAKE":
            return max(0.0, min(100.0, float(item.get("score", 0.0))))
    return 0.0


def build_verdict(probs: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = load_result_metadata()
    thresholds = metadata["thresholds"]
    risk = fake_probability(probs)
    if risk >= float(thresholds["ai_min"]):
        code = LIKELY_AI_GENERATED
        label_zh = "较可能由 AI 生成"
        rationale = "ResNet50 的 AI 生成概率达到当前模型的高风险阈值。"
    elif risk <= float(thresholds["authentic_max"]):
        code = LIKELY_AUTHENTIC
        label_zh = "较可能为真实照片"
        rationale = "ResNet50 的 AI 生成概率低于当前模型的低风险阈值。"
    else:
        code = INCONCLUSIVE
        label_zh = "证据不足，暂无法判断"
        rationale = "模型概率处于灰区，现有证据不足以给出二元结论。"

    return {
        "code": code,
        "label_zh": label_zh,
        "risk_score": round(risk, 2),
        "decision_confidence": round(abs(risk - 50.0) * 2.0, 2),
        "thresholds": {
            "authentic_max": float(thresholds["authentic_max"]),
            "ai_min": float(thresholds["ai_min"]),
        },
        "rationale": rationale,
    }


def model_signal(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": "resnet50",
        "name": "ResNet50 图像分类模型",
        "role": "decision",
        "used_for_verdict": True,
        "status": "complete",
        "score": round(fake_probability(result.get("probs", [])), 2),
        "score_label": "AI 生成风险",
        "summary": "该信号是三态结论的唯一决策依据。",
    }


def enrich_detection_result(result: dict[str, Any]) -> dict[str, Any]:
    """Add v2 fields without removing or changing legacy response fields."""
    verdict = build_verdict(result.get("probs", []))
    return {
        **result,
        "verdict": verdict,
        "risk_score": verdict["risk_score"],
        "signals": [model_signal(result)],
        "result_version": RESULT_VERSION,
        "model_status": "current",
    }


def supporting_signal(
    key: str,
    name: str,
    score: float | None,
    summary: str,
    *,
    details: Any = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "role": "supporting",
        "used_for_verdict": False,
        "status": "complete" if score is not None else "unavailable",
        "score": round(float(score), 2) if score is not None else None,
        "score_label": "辅助真实性信号",
        "summary": summary,
        "details": details,
    }


def record_presentation(record: Any) -> dict[str, Any]:
    """Return safe display fields for both v2 and pre-migration records."""
    if not getattr(record, "result_version", None):
        old_label = "AI 生成" if getattr(record, "label", "") == "FAKE" else "真实照片"
        return {
            "verdict_code": None,
            "verdict_label_zh": f"旧模型：{old_label}",
            "risk_score": None,
            "result_version": None,
            "model_status": "legacy",
        }
    labels = {
        LIKELY_AI_GENERATED: "较可能由 AI 生成",
        LIKELY_AUTHENTIC: "较可能为真实照片",
        INCONCLUSIVE: "证据不足，暂无法判断",
    }
    code = getattr(record, "verdict_code", None) or INCONCLUSIVE
    return {
        "verdict_code": code,
        "verdict_label_zh": labels.get(code, "证据不足，暂无法判断"),
        "risk_score": getattr(record, "risk_score", None),
        "result_version": getattr(record, "result_version", None),
        "model_status": "current",
    }
