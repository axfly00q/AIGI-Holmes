"""
Tests for backend.analyzers — seal, frequency, edge, face, composite.

Run:  python -m pytest tests/test_analyzers.py -v
"""

import asyncio
import pytest
from PIL import Image
import numpy as np


# ── helpers ──────────────────────────────────────────────────────────────

def _make_image(w=256, h=256, mode="RGB", color=None):
    """Create a simple test image."""
    if color:
        return Image.new(mode, (w, h), color)
    arr = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


def _run(coro):
    """Helper to run async in sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── seal_detector ────────────────────────────────────────────────────────

class TestSealDetector:
    def test_no_seal_neutral(self):
        from backend.analyzers.seal_detector import analyze
        img = _make_image(256, 256, color=(200, 200, 200))  # plain grey
        result = _run(analyze(img))
        assert "score" in result
        assert "regions_found" in result
        assert "details" in result
        assert 0 <= result["score"] <= 100

    def test_random_image(self):
        from backend.analyzers.seal_detector import analyze
        img = _make_image(300, 300)
        result = _run(analyze(img))
        assert isinstance(result["score"], (int, float))
        assert result["score"] >= 0

    def test_red_circle_image(self):
        """Image with a red circle should detect at least one region."""
        from backend.analyzers.seal_detector import analyze
        try:
            import cv2
        except ImportError:
            pytest.skip("opencv not installed")
        # Draw a red circle on white background
        arr = np.ones((256, 256, 3), dtype=np.uint8) * 255
        cv2.circle(arr, (128, 128), 60, (0, 0, 255), -1)  # BGR red
        img = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
        result = _run(analyze(img))
        assert result["regions_found"] >= 1


# ── frequency_analyzer ───────────────────────────────────────────────────

class TestFrequencyAnalyzer:
    def test_basic(self):
        from backend.analyzers.frequency_analyzer import analyze
        img = _make_image(256, 256)
        result = _run(analyze(img))
        assert "score" in result
        assert "psd_slope" in result
        assert "r_squared" in result
        assert 0 <= result["score"] <= 100

    def test_uniform_image(self):
        from backend.analyzers.frequency_analyzer import analyze
        img = _make_image(128, 128, color=(100, 100, 100))
        result = _run(analyze(img))
        # Uniform image has very little frequency content
        assert isinstance(result["score"], (int, float))

    def test_small_image(self):
        from backend.analyzers.frequency_analyzer import analyze
        img = _make_image(16, 16)
        result = _run(analyze(img))
        assert "score" in result


# ── edge_analyzer ────────────────────────────────────────────────────────

class TestEdgeAnalyzer:
    def test_basic(self):
        from backend.analyzers.edge_analyzer import analyze
        img = _make_image(256, 256)
        result = _run(analyze(img))
        assert "score" in result
        assert "edge_cv" in result
        assert 0 <= result["score"] <= 100

    def test_uniform_image(self):
        from backend.analyzers.edge_analyzer import analyze
        img = _make_image(256, 256, color=(128, 128, 128))
        result = _run(analyze(img))
        assert isinstance(result["score"], (int, float))

    def test_tiny_image(self):
        from backend.analyzers.edge_analyzer import analyze
        img = _make_image(20, 20)
        result = _run(analyze(img))
        assert "score" in result  # should return neutral


# ── face_analyzer ────────────────────────────────────────────────────────

class TestFaceAnalyzer:
    def test_no_face(self):
        from backend.analyzers.face_analyzer import analyze
        img = _make_image(256, 256, color=(50, 120, 200))
        result = _run(analyze(img))
        assert result["faces_found"] == 0
        assert result["score"] == 50.0  # neutral

    def test_random_image(self):
        from backend.analyzers.face_analyzer import analyze
        img = _make_image(256, 256)
        result = _run(analyze(img))
        assert "score" in result
        assert "faces_found" in result
        assert 0 <= result["score"] <= 100


# ── composite ────────────────────────────────────────────────────────────

class TestComposite:
    def test_high_scores(self):
        from backend.analyzers.composite import compute_overall
        r = compute_overall(
            authenticity=90, confidence=85, consistency=80,
            seal=75, frequency=70, edge=65,
        )
        assert r["overall_score"] > 60
        assert r["level"] in ("credible", "suspicious", "unreliable")
        assert len(r["verdict"]) > 0

    def test_low_scores(self):
        from backend.analyzers.composite import compute_overall
        r = compute_overall(
            authenticity=10, confidence=20, consistency=15,
            seal=10, frequency=5, edge=10,
        )
        assert r["overall_score"] < 40
        assert r["level"] == "unreliable"

    def test_mid_scores(self):
        from backend.analyzers.composite import compute_overall
        r = compute_overall(
            authenticity=50, confidence=50, consistency=50,
            seal=50, frequency=50, edge=50,
        )
        assert r["overall_score"] == 50.0
        assert r["level"] == "suspicious"

    def test_boundary_clamp(self):
        from backend.analyzers.composite import compute_overall
        r = compute_overall(
            authenticity=100, confidence=100, consistency=100,
            seal=100, frequency=100, edge=100,
        )
        assert r["overall_score"] == 100.0

    def test_weights_sum_to_one(self):
        from backend.analyzers.composite import _WEIGHTS
        total = sum(_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
