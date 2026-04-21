"""
AIGI-Holmes — Multi-dimension image analyzers.

Provides four independent analyzers for enhanced news-image forensics:
  - seal_detector:       Official-seal / logo anomaly detection
  - frequency_analyzer:  Frequency-domain naturalness (1/f^α)
  - edge_analyzer:       Edge-consistency / splicing detection
  - face_analyzer:       Face deepfake indicators (Haar + FFT)

Plus a composite scorer that merges all dimensions.
"""

from backend.analyzers.seal_detector import analyze as analyze_seal          # noqa: F401
from backend.analyzers.frequency_analyzer import analyze as analyze_frequency  # noqa: F401
from backend.analyzers.edge_analyzer import analyze as analyze_edge          # noqa: F401
from backend.analyzers.face_analyzer import analyze as analyze_face          # noqa: F401
from backend.analyzers.composite import compute_overall                      # noqa: F401
