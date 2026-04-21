"""
AIGI-Holmes — XAI 统一服务

提供 LIME 和 SHAP 两种解释方法的统一入口，
支持长文本分段解释和结果合并。
"""

import asyncio
from functools import partial
from typing import Optional

import numpy as np
import torch

from backend.xai.lime_explainer import TextLimeExplainer
from backend.xai.shap_explainer import TextShapExplainer
from backend.xai.visualizer import generate_highlighted_html, generate_visualization_data


class XAIService:
    """统一的可解释性 AI 服务"""

    def __init__(self):
        self._lime: Optional[TextLimeExplainer] = None
        self._shap: Optional[TextShapExplainer] = None
        self._model = None
        self._tokenizer = None

    def _ensure_model(self):
        """懒加载文本检测模型"""
        if self._model is not None:
            return

        from backend.text_detect import _model, _tokenizer, DEVICE, TEXT_MAX_LENGTH

        self._model = _model
        self._tokenizer = _tokenizer
        self._device = DEVICE
        self._max_length = TEXT_MAX_LENGTH

    def _predict_proba(self, texts: list[str]) -> np.ndarray:
        """
        批量预测函数——供 LIME/SHAP 调用。

        Args:
            texts: 文本列表

        Returns:
            (N, 2) 概率矩阵，列顺序 [REAL, FAKE]
        """
        self._ensure_model()

        all_probs = []
        # 分小批处理，避免显存溢出
        batch_size = 8
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            with torch.no_grad():
                inputs = self._tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    max_length=self._max_length,
                    truncation=True,
                    padding=True,
                ).to(self._device)

                outputs = self._model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1).cpu().numpy()
                all_probs.append(probs)

        return np.vstack(all_probs)

    @property
    def lime_explainer(self) -> TextLimeExplainer:
        if self._lime is None:
            self._lime = TextLimeExplainer(self._predict_proba)
        return self._lime

    @property
    def shap_explainer(self) -> TextShapExplainer:
        if self._shap is None:
            self._shap = TextShapExplainer(self._predict_proba)
        return self._shap

    # ------------------------------------------------------------------ #
    # 同步接口
    # ------------------------------------------------------------------ #

    def explain(
        self,
        text: str,
        method: str = "lime",
        num_features: int = 20,
    ) -> dict:
        """
        执行 XAI 解释（同步版本）。

        Args:
            text:          待解释文本
            method:        "lime", "shap", 或 "both"
            num_features:  LIME 特征数量上限

        Returns:
            {
                "detection": {label, confidence, ...},
                "explanations": {
                    "lime": {...},    # 如果 method 包含 lime
                    "shap": {...},    # 如果 method 包含 shap
                },
                "highlighted_html": str,
                "visualization_data": {...},
            }
        """
        self._ensure_model()

        # 1. 先运行检测
        from backend.text_detect import detect_text
        detection = detect_text(text)

        # 2. 运行解释
        explanations = {}

        if method in ("lime", "both"):
            lime_result = self.lime_explainer.explain(
                text, num_features=num_features
            )
            explanations["lime"] = lime_result

        if method in ("shap", "both"):
            shap_result = self.shap_explainer.explain(text)
            explanations["shap"] = shap_result

        # 3. 选择主要解释方法生成可视化
        primary_method = "lime" if "lime" in explanations else "shap"
        primary_exp = explanations.get(primary_method, {})
        tokens = primary_exp.get("tokens", [])

        highlighted_html = generate_highlighted_html(
            text, tokens, method=primary_method.upper()
        )
        vis_data = generate_visualization_data(
            text, tokens, method=primary_method.upper()
        )

        return {
            "detection": detection,
            "explanations": explanations,
            "highlighted_html": highlighted_html,
            "visualization_data": vis_data,
        }

    def explain_long_text(
        self,
        text: str,
        method: str = "lime",
        num_features: int = 15,
    ) -> dict:
        """
        对长文本进行分段解释。

        Returns:
            {
                "detection": {label, confidence, segments: [...]},
                "segment_explanations": [{...}, ...],
                "highlighted_html": str,
                "visualization_data": {...},
            }
        """
        self._ensure_model()

        from backend.text_detect import detect_text_with_segments

        # 1. 分段检测
        detection = detect_text_with_segments(text)
        segments = detection.get("segments", [])

        # 2. 对每个段落解释
        segment_explanations = []
        all_tokens = []

        for seg in segments:
            seg_dict = {"segment": seg["segment"], "start": seg["start"], "end": seg["end"]}

            if method in ("lime", "both"):
                exp = self.lime_explainer.explain(
                    seg["segment"], num_features=num_features, num_samples=300
                )
                exp["start"] = seg["start"]
                exp["end"] = seg["end"]
                segment_explanations.append(exp)
                all_tokens.extend(exp.get("tokens", []))
            elif method == "shap":
                exp = self.shap_explainer.explain(seg["segment"], max_evals=150)
                exp["start"] = seg["start"]
                exp["end"] = seg["end"]
                segment_explanations.append(exp)
                all_tokens.extend(exp.get("tokens", []))

        # 3. 对完整文本生成可视化
        primary_method = method if method != "both" else "lime"
        highlighted_html = generate_highlighted_html(
            text, all_tokens, method=primary_method.upper()
        )
        vis_data = generate_visualization_data(
            text, all_tokens, method=primary_method.upper()
        )

        return {
            "detection": detection,
            "segment_explanations": segment_explanations,
            "highlighted_html": highlighted_html,
            "visualization_data": vis_data,
        }

    # ------------------------------------------------------------------ #
    # 异步接口（用于 FastAPI）
    # ------------------------------------------------------------------ #

    async def async_explain(
        self,
        text: str,
        method: str = "lime",
        num_features: int = 20,
    ) -> dict:
        """异步版本的 explain"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(self.explain, text=text, method=method, num_features=num_features),
        )

    async def async_explain_long_text(
        self,
        text: str,
        method: str = "lime",
        num_features: int = 15,
    ) -> dict:
        """异步版本的 explain_long_text"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(self.explain_long_text, text=text, method=method, num_features=num_features),
        )


# 全局单例
_xai_service: Optional[XAIService] = None


def get_xai_service() -> XAIService:
    """获取 XAI 服务单例"""
    global _xai_service
    if _xai_service is None:
        _xai_service = XAIService()
    return _xai_service
