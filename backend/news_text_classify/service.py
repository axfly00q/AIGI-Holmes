"""Inference service for news text classification."""

from __future__ import annotations

import hashlib
import logging
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import joblib
import torch
import yaml

from backend.config import get_settings
from backend.news_text_classify.constants import (
    CATEGORY_LABELS,
    DEFAULT_MODEL_VERSION,
    MODEL_DISPLAY_NAMES,
)
from backend.news_text_classify.textcnn import TextCNN, encode_chars

logger = logging.getLogger(__name__)


def build_model_input(title: str, content: str | None = None, strategy: str | None = None) -> str:
    """Title-first input used consistently by training and inference."""
    clean_title = " ".join((title or "").strip().split())
    clean_content = " ".join((content or "").strip().split())
    compact_title = clean_title.replace(" ", "")

    if strategy == "title_only":
        return clean_title or compact_title

    if strategy == "title_weighted_content":
        title_signal = "。".join(part for part in (clean_title, compact_title, clean_title) if part)
        if clean_content:
            return f"{title_signal}。{clean_content[:500]}"
        return title_signal

    title_parts: list[str] = []
    for item in (clean_title, compact_title, " ".join(compact_title[:120]) if compact_title else ""):
        if item and item not in title_parts:
            title_parts.append(item)
    title_signal = "。".join(title_parts)
    if clean_content:
        return f"{title_signal}。{title_signal}。{clean_content[:800]}"
    return title_signal


def text_hash(title: str, content: str | None = None) -> str:
    raw = f"{title}\n{content or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _softmax(values: list[float]) -> list[float]:
    if not values:
        return []
    m = max(values)
    exps = [math.exp(v - m) for v in values]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def extract_keywords(text: str, top_k: int = 10) -> list[dict[str, float]]:
    """Readable Chinese keyword extraction for result explanation."""
    text = (text or "").strip()
    if not text:
        return []
    try:
        import jieba.analyse

        tags = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
        return [
            {"word": str(word), "score": round(float(score), 4)}
            for word, score in tags
            if str(word).strip()
        ]
    except Exception as exc:  # pragma: no cover - fallback only
        logger.warning("jieba keyword extraction failed: %s", exc)
        seen: dict[str, int] = {}
        for ch in text:
            if ch.isspace() or ch in "，。！？、；：“”‘’（）()《》<>[]{}":
                continue
            seen[ch] = seen.get(ch, 0) + 1
        ranked = sorted(seen.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [{"word": word, "score": float(score)} for word, score in ranked]


@dataclass
class PredictionResult:
    category: str
    confidence: float
    probabilities: list[dict[str, float]]
    keywords: list[dict[str, float]]
    model_key: str
    model_name: str
    model_version: str


class ClassicModelAdapter:
    def __init__(self, model: Any, label_order: list[str]) -> None:
        self.model = model
        self.label_order = label_order
        self.classes_ = [str(c) for c in getattr(model, "classes_", [])]
        if not self.classes_ and hasattr(model, "named_steps"):
            final = list(model.named_steps.values())[-1]
            self.classes_ = [str(c) for c in getattr(final, "classes_", [])]

    def _align(self, row: list[float]) -> list[float]:
        if not self.classes_ or len(self.classes_) != len(row):
            return row
        by_class = {label: float(score) for label, score in zip(self.classes_, row)}
        return [by_class.get(label, 0.0) for label in self.label_order]

    def predict_proba(self, texts: list[str]) -> list[list[float]]:
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(texts)
            return [self._align([float(v) for v in row]) for row in probs]
        if hasattr(self.model, "decision_function"):
            scores = self.model.decision_function(texts)
            if len(scores.shape) == 1:
                rows = [[-float(s), float(s)] for s in scores]
            else:
                rows = [[float(v) for v in row] for row in scores]
            return [self._align(_softmax(row)) for row in rows]
        pred = self.model.predict(texts)
        return [
            [1.0 if label == p else 0.0 for label in self.label_order]
            for p in pred
        ]


class TextCNNAdapter:
    def __init__(self, artifact_path: str, label_order: list[str]) -> None:
        data = torch.load(artifact_path, map_location="cpu")
        self.vocab: dict[str, int] = data["vocab"]
        self.max_len: int = int(data.get("max_len", 96))
        self.label_order = list(data.get("label_order") or label_order)
        cfg = data.get("config", {})
        self.model = TextCNN(
            vocab_size=len(self.vocab),
            num_classes=len(self.label_order),
            embed_dim=int(cfg.get("embed_dim", 64)),
            num_filters=int(cfg.get("num_filters", 64)),
            kernel_sizes=tuple(cfg.get("kernel_sizes", (2, 3, 4))),
            dropout=float(cfg.get("dropout", 0.25)),
        )
        self.model.load_state_dict(data["model_state"])
        self.model.eval()

    def predict_proba(self, texts: list[str]) -> list[list[float]]:
        encoded = [encode_chars(text, self.vocab, self.max_len) for text in texts]
        x = torch.tensor(encoded, dtype=torch.long)
        with torch.no_grad():
            probs = torch.softmax(self.model(x), dim=1).cpu().tolist()
        return [[float(v) for v in row] for row in probs]


class NewsTextClassifierService:
    def __init__(self, artifact_dir: str | None = None) -> None:
        self.artifact_dir = artifact_dir or get_settings().NEWS_CLASSIFY_ARTIFACT_DIR
        self.metadata = self._load_metadata()
        self.label_order = list(self.metadata.get("label_order") or CATEGORY_LABELS)
        self.default_model = self.metadata.get("default_model", "svm")
        self.model_version = self.metadata.get("model_version", DEFAULT_MODEL_VERSION)
        self.input_strategy = (
            self.metadata.get("training_summary", {}).get("selected_input_strategy")
            or self.metadata.get("input_strategy")
            or "title_plus_summary"
        )
        self.models: dict[str, ClassicModelAdapter | TextCNNAdapter] = {}
        self._load_models()

    def _load_metadata(self) -> dict[str, Any]:
        meta_path = os.path.join(self.artifact_dir, "metadata.yaml")
        if not os.path.exists(meta_path):
            logger.warning("News classification metadata not found: %s", meta_path)
            return {
                "label_order": CATEGORY_LABELS,
                "default_model": "svm",
                "model_version": DEFAULT_MODEL_VERSION,
                "models": {},
            }
        with open(meta_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def _load_models(self) -> None:
        for key in ("nb", "lr", "svm"):
            path = os.path.join(self.artifact_dir, f"{key}.joblib")
            if os.path.exists(path):
                self.models[key] = ClassicModelAdapter(joblib.load(path), self.label_order)
        textcnn_path = os.path.join(self.artifact_dir, "textcnn.pt")
        if os.path.exists(textcnn_path):
            try:
                self.models["textcnn"] = TextCNNAdapter(textcnn_path, self.label_order)
            except Exception as exc:
                logger.warning("Failed to load TextCNN artifact: %s", exc)

    def model_options(self) -> dict[str, Any]:
        meta_models = self.metadata.get("models", {})
        models = []
        for key in ("nb", "lr", "svm", "textcnn"):
            item = dict(meta_models.get(key, {}))
            item.update({
                "key": key,
                "name": item.get("name") or MODEL_DISPLAY_NAMES.get(key, key),
                "available": key in self.models,
            })
            models.append(item)
        return {
            "default_model": self.default_model if self.default_model in self.models else self._first_model_key(),
            "model_version": self.model_version,
            "label_order": self.label_order,
            "models": models,
            "training_summary": self.metadata.get("training_summary", {}),
            "input_strategy": self.input_strategy,
        }

    def experiment_report(self) -> dict[str, Any]:
        metrics_path = os.path.join(self.artifact_dir, "metrics_full.yaml")
        metrics: dict[str, Any] = {}
        if os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as fh:
                metrics = yaml.safe_load(fh) or {}

        default_model = self.default_model if self.default_model in metrics else None
        if default_model is None and metrics:
            default_model = max(metrics.items(), key=lambda item: item[1].get("macro_f1", 0))[0]
        report = metrics.get(default_model or "", {}).get("classification_report", {})
        matrix = metrics.get(default_model or "", {}).get("confusion_matrix", [])
        per_class = []
        for label in self.label_order:
            row = report.get(label, {})
            per_class.append({
                "label": label,
                "precision": round(float(row.get("precision", 0)), 4),
                "recall": round(float(row.get("recall", 0)), 4),
                "f1": round(float(row.get("f1-score", 0)), 4),
                "support": int(float(row.get("support", 0))),
            })

        confusions = []
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                if i == j or not value:
                    continue
                confusions.append({
                    "actual": self.label_order[i] if i < len(self.label_order) else str(i),
                    "predicted": self.label_order[j] if j < len(self.label_order) else str(j),
                    "count": int(value),
                })
        confusions.sort(key=lambda item: item["count"], reverse=True)

        return {
            "default_model": default_model,
            "label_order": self.label_order,
            "models": self.model_options()["models"],
            "training_summary": self.metadata.get("training_summary", {}),
            "per_class": per_class,
            "confusion_matrix": matrix,
            "top_confusions": confusions[:8],
            "weak_classes": sorted(per_class, key=lambda item: item["f1"])[:3],
            "input_strategy_metrics": self.metadata.get("training_summary", {}).get("input_strategy_metrics", []),
            "training_history": metrics.get(default_model or "", {}).get("training_history", []),
            "textcnn_trials": metrics.get("textcnn", {}).get("tuning_trials", []),
        }

    def _resolve_model_key(self, model_key: str | None) -> str:
        key = (model_key or "best").strip().lower()
        if key == "best":
            key = self.default_model
        if key not in self.models:
            raise ValueError(f"模型 {model_key or 'best'} 不可用，请先训练或选择其他模型。")
        return key

    def _first_model_key(self) -> str:
        if self.models:
            return next(iter(self.models))
        raise ValueError("新闻分类模型尚未准备好，请先运行训练脚本。")

    def predict(self, title: str, content: str | None = None, model_key: str | None = None) -> PredictionResult:
        if not title or not title.strip():
            raise ValueError("新闻标题不能为空。")
        key = self._resolve_model_key(model_key)
        text = build_model_input(title, content, self.input_strategy)
        probs = self.models[key].predict_proba([text])[0]

        # Align potential binary/sorted estimator outputs back to configured labels.
        if len(probs) != len(self.label_order):
            probs = (probs + [0.0] * len(self.label_order))[: len(self.label_order)]

        best_idx = max(range(len(probs)), key=lambda i: probs[i])
        category = self.label_order[best_idx]
        probability_rows = [
            {"label": label, "score": round(float(score), 6)}
            for label, score in zip(self.label_order, probs)
        ]
        probability_rows.sort(key=lambda item: item["score"], reverse=True)
        return PredictionResult(
            category=category,
            confidence=round(float(probs[best_idx]) * 100, 2),
            probabilities=probability_rows,
            keywords=extract_keywords(text),
            model_key=key,
            model_name=MODEL_DISPLAY_NAMES.get(key, key),
            model_version=self.model_version,
        )


@lru_cache
def get_news_classifier_service() -> NewsTextClassifierService:
    return NewsTextClassifierService()


def reload_news_classifier_service() -> NewsTextClassifierService:
    get_news_classifier_service.cache_clear()
    return get_news_classifier_service()
