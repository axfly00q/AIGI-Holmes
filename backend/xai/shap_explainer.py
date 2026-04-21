"""
AIGI-Holmes — SHAP 文本解释器

使用 SHAP (SHapley Additive exPlanations) 算法
基于 Shapley 值理论对文本检测进行精确的特征归因分析。
"""

from typing import Callable

import numpy as np

try:
    import shap
except ImportError:
    raise ImportError(
        "SHAP is required for text explanations. "
        "Install it with: pip install shap"
    )


class TextShapExplainer:
    """基于 SHAP 的文本可解释性分析器"""

    def __init__(self, predict_fn: Callable[[list[str]], np.ndarray]):
        """
        Args:
            predict_fn: 接收文本列表，返回 (N, 2) 的概率矩阵
                        列顺序为 [REAL, FAKE]
        """
        self._predict_fn = predict_fn
        # 使用 masker 把文本按空格分词，SHAP 会自动遮蔽词语来计算贡献
        self._masker = shap.maskers.Text(tokenizer=r"\s+")

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def explain(
        self,
        text: str,
        max_evals: int = 200,
        target_class: int = 1,   # 1 = FAKE
    ) -> dict:
        """
        对一段文本执行 SHAP 解释。

        Args:
            text:          待解释文本
            max_evals:     最大评估次数（越大越精确，越慢）
            target_class:  解释目标类别索引（1=FAKE）

        Returns:
            {
                "method": "SHAP",
                "text": str,
                "tokens": [
                    {
                        "token": "词语",
                        "shap_value": 0.12,
                        "base_value": 0.45,
                        "is_important": True
                    }, ...
                ],
                "base_value": float,
                "model_output": float,
                "top_positive": [...],
                "top_negative": [...],
            }
        """
        # 构建解释器
        explainer = shap.Explainer(
            self._predict_fn,
            self._masker,
            output_names=["REAL", "FAKE"],
        )

        # 计算 SHAP 值
        shap_values = explainer(
            [text],
            max_evals=max_evals,
            batch_size=10,
        )

        # 提取目标类别的 SHAP 值
        sv = shap_values[0]  # 第一个样本

        # 获取 token 列表和对应的 SHAP 值
        if hasattr(sv, "data") and sv.data is not None:
            raw_tokens = sv.data
        else:
            raw_tokens = text.split()

        if hasattr(sv, "values") and sv.values is not None:
            if sv.values.ndim == 2:
                values = sv.values[:, target_class]
            else:
                values = sv.values
        else:
            values = np.zeros(len(raw_tokens))

        base_value = float(sv.base_values[target_class]) if hasattr(sv.base_values, "__len__") else float(sv.base_values)

        # 构建 token 信息
        tokens = []
        for i, (token, val) in enumerate(zip(raw_tokens, values)):
            token_str = str(token).strip()
            if not token_str:
                continue
            shap_val = float(val)
            tokens.append({
                "token": token_str,
                "shap_value": round(shap_val, 6),
                "base_value": round(base_value, 6),
                "is_important": abs(shap_val) > 0.01,
            })

        # 按绝对值排序
        tokens.sort(key=lambda t: abs(t["shap_value"]), reverse=True)

        top_positive = [t for t in tokens if t["shap_value"] > 0][:10]
        top_negative = [t for t in tokens if t["shap_value"] < 0][:10]

        # 模型在原文上的输出
        orig_probs = self._predict_fn([text])
        model_output = float(orig_probs[0][target_class])

        return {
            "method": "SHAP",
            "text": text,
            "tokens": tokens,
            "base_value": round(base_value, 6),
            "model_output": round(model_output, 6),
            "top_positive": top_positive,
            "top_negative": top_negative,
        }

    def explain_segments(
        self,
        segments: list[dict],
        max_evals: int = 150,
    ) -> list[dict]:
        """
        对多个文本段落分别执行 SHAP 解释。

        Args:
            segments: [{"segment": str, "start": int, "end": int, ...}, ...]

        Returns:
            每个段落的 SHAP 解释结果列表
        """
        results = []
        for seg in segments:
            text = seg.get("segment", "")
            if not text.strip():
                continue
            exp = self.explain(text, max_evals=max_evals)
            exp["start"] = seg.get("start", 0)
            exp["end"] = seg.get("end", len(text))
            results.append(exp)
        return results
