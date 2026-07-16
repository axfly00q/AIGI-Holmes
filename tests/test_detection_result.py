from types import SimpleNamespace

from backend.detection_result import (
    INCONCLUSIVE,
    LIKELY_AI_GENERATED,
    LIKELY_AUTHENTIC,
    build_verdict,
    enrich_detection_result,
    record_presentation,
)


def _probs(fake_score: float):
    return [
        {"label": "FAKE", "label_zh": "AI 生成", "score": fake_score},
        {"label": "REAL", "label_zh": "真实照片", "score": 100 - fake_score},
    ]


def test_three_state_boundaries():
    assert build_verdict(_probs(20))["code"] == LIKELY_AUTHENTIC
    assert build_verdict(_probs(50))["code"] == INCONCLUSIVE
    assert build_verdict(_probs(80))["code"] == LIKELY_AI_GENERATED


def test_enrichment_preserves_legacy_fields():
    original = {"label": "FAKE", "confidence": 80.0, "probs": _probs(80)}
    result = enrich_detection_result(original)
    assert result["label"] == original["label"]
    assert result["confidence"] == original["confidence"]
    assert result["result_version"] == "2.0"
    assert result["signals"][0]["used_for_verdict"] is True


def test_old_record_is_explicitly_legacy():
    record = SimpleNamespace(result_version=None, label="FAKE")
    result = record_presentation(record)
    assert result["model_status"] == "legacy"
    assert result["verdict_label_zh"].startswith("旧模型")
