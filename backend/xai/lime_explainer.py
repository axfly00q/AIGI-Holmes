"""
AIGI-Holmes — LIME 文本解释器

使用 LIME (Local Interpretable Model-agnostic Explanations) 算法
对文本 AI 生成检测结果进行特征归因，标注出影响模型判决的关键词汇。
"""

import re
from typing import Callable, Optional

import numpy as np

try:
    from lime.lime_text import LimeTextExplainer
except ImportError:
    raise ImportError(
        "LIME is required for text explanations. "
        "Install it with: pip install lime"
    )


class TextLimeExplainer:
    """基于 LIME 的文本可解释性分析器"""

    def __init__(self, predict_fn: Callable[[list[str]], np.ndarray]):
        """
        Args:
            predict_fn: 接收文本列表，返回 (N, 2) 的概率矩阵
                        列顺序为 [REAL, FAKE]
        """
        self._predict_fn = predict_fn
        self._explainer = LimeTextExplainer(
            class_names=["REAL", "FAKE"],
            split_expression=r'\s+',
            bow=True,
            random_state=42,
        )

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def explain(
        self,
        text: str,
        num_features: int = 20,
        num_samples: int = 500,
        target_class: int = 1,      # 1 = FAKE
    ) -> dict:
        """
        对一段文本执行 LIME 解释。

        Args:
            text:          待解释文本
            num_features:  返回的重要特征数量上限
            num_samples:   LIME 扰动采样次数（越大越准、越慢）
            target_class:  解释目标类别索引（1=FAKE）

        Returns:
            {
                "method": "LIME",
                "text": str,
                "tokens": [
                    {
                        "token": "词语",
                        "weight": 0.15,
                        "contribution": 0.15,
                        "is_supporting_fake": True
                    }, ...
                ],
                "top_positive": [...],   # 支持 FAKE 的关键词
                "top_negative": [...],   # 支持 REAL 的关键词
                "intercept": float,
                "model_score": float,
                "prediction_local": float,
                "r2_score": float,
            }
        """
        # 运行 LIME 解释
        explanation = self._explainer.explain_instance(
            text,
            self._predict_fn,
            num_features=num_features,
            num_samples=num_samples,
            labels=(target_class,),
        )

        # 提取特征权重
        feature_weights = explanation.as_list(label=target_class)

        tokens = []
        for word, weight in feature_weights:
            tokens.append({
                "token": word,
                "weight": round(float(weight), 6),
                "contribution": round(float(weight), 6),
                "is_supporting_fake": weight > 0,
            })

        # 按贡献度绝对值排序
        tokens.sort(key=lambda t: abs(t["weight"]), reverse=True)

        top_positive = [t for t in tokens if t["is_supporting_fake"]]
        top_negative = [t for t in tokens if not t["is_supporting_fake"]]

        # 模型在原始文本上的预测
        orig_probs = self._predict_fn([text])
        model_score = float(orig_probs[0][target_class])

        # LIME 局部线性模型信息
        intercept = float(explanation.intercept.get(target_class, 0.0))
        r2_score = float(explanation.score) if hasattr(explanation, "score") else 0.0

        return {
            "method": "LIME",
            "text": text,
            "tokens": tokens,
            "top_positive": top_positive[:10],
            "top_negative": top_negative[:10],
            "intercept": round(intercept, 6),
            "model_score": round(model_score, 6),
            "prediction_local": round(intercept + sum(t["weight"] for t in tokens), 6),
            "r2_score": round(r2_score, 6),
        }

    def explain_segments(
        self,
        segments: list[dict],
        num_features: int = 15,
        num_samples: int = 300,
    ) -> list[dict]:
        """
        对多个文本段落分别执行 LIME 解释。

        Args:
            segments: [{"segment": str, "start": int, "end": int, ...}, ...]

        Returns:
            每个段落的 LIME 解释结果列表
        """
        results = []
        for seg in segments:
            text = seg.get("segment", "")
            if not text.strip():
                continue
            exp = self.explain(text, num_features=num_features, num_samples=num_samples)
            exp["start"] = seg.get("start", 0)
            exp["end"] = seg.get("end", len(text))
            results.append(exp)
        return results
