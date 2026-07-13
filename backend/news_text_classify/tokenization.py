"""Tokenizers used by persisted news classification vectorizers."""

from __future__ import annotations


def jieba_tokens(text: str) -> list[str]:
    """Importable jieba tokenizer for joblib-persisted sklearn pipelines."""
    try:
        import jieba

        return [token for token in jieba.lcut(text or "") if token.strip()]
    except Exception:
        return [text] if text else []
