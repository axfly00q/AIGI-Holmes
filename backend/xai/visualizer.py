"""
AIGI-Holmes — XAI 可视化工具

将 LIME/SHAP 解释结果转换为前端可用的 HTML 高亮标注。
"""

import html
import re
from typing import Optional


def _importance_color(weight: float, max_abs: float) -> str:
    """
    根据特征权重生成 RGBA 颜色字符串。
    正值（支持 FAKE）→ 红色
    负值（支持 REAL）→ 绿色
    """
    if max_abs == 0:
        return "rgba(128,128,128,0.1)"

    normalized = weight / max_abs  # [-1, 1]
    alpha = min(abs(normalized) * 0.6 + 0.1, 0.7)

    if normalized > 0:
        # 红色系（AI生成特征）
        return f"rgba(255, 60, 60, {alpha:.2f})"
    else:
        # 绿色系（真实文本特征）
        return f"rgba(60, 180, 60, {alpha:.2f})"


def generate_highlighted_html(
    text: str,
    tokens: list[dict],
    method: str = "LIME",
) -> str:
    """
    将文本 + 特征权重转换为带高亮的 HTML 字符串。

    Args:
        text:    原始文本
        tokens:  [{"token": str, "weight"/"shap_value": float, ...}, ...]
        method:  "LIME" 或 "SHAP"（决定取哪个字段作为权重）

    Returns:
        HTML 字符串，关键词被 <span> 标签包裹并着色
    """
    # 构建 token -> weight 映射
    weight_key = "weight" if method == "LIME" else "shap_value"
    token_weights: dict[str, float] = {}
    for t in tokens:
        token_str = t["token"].strip()
        if token_str:
            token_weights[token_str] = t.get(weight_key, t.get("contribution", 0.0))

    if not token_weights:
        return html.escape(text)

    max_abs = max(abs(v) for v in token_weights.values()) or 1.0

    # 按 token 长度降序排列（优先匹配长的 token，避免短 token 干扰）
    sorted_tokens = sorted(token_weights.keys(), key=len, reverse=True)

    # 构建正则：匹配所有已知 token
    pattern = "|".join(re.escape(t) for t in sorted_tokens)
    if not pattern:
        return html.escape(text)

    regex = re.compile(f"({pattern})")

    # 分段替换
    parts = []
    last_end = 0
    for match in regex.finditer(text):
        # 匹配前的普通文本
        if match.start() > last_end:
            parts.append(html.escape(text[last_end:match.start()]))

        word = match.group()
        weight = token_weights.get(word, 0.0)
        color = _importance_color(weight, max_abs)
        weight_label = f"{weight:+.4f}" if abs(weight) > 0.001 else ""

        escaped_word = html.escape(word)
        parts.append(
            f'<span style="background:{color};padding:1px 3px;border-radius:3px;'
            f'cursor:pointer" title="{method} {weight_label}">'
            f"{escaped_word}</span>"
        )
        last_end = match.end()

    # 剩余文本
    if last_end < len(text):
        parts.append(html.escape(text[last_end:]))

    return "".join(parts)


def generate_visualization_data(
    text: str,
    tokens: list[dict],
    method: str = "LIME",
) -> dict:
    """
    生成前端可视化所需的结构化数据。

    Returns:
        {
            "text": str,
            "method": str,
            "highlights": [
                {
                    "token": str,
                    "weight": float,
                    "start": int,
                    "end": int,
                    "color": str
                }, ...
            ],
            "legend": {
                "positive_label": "支持 AI 生成",
                "negative_label": "支持 真实文本",
                "positive_color": "rgba(255, 60, 60, 0.5)",
                "negative_color": "rgba(60, 180, 60, 0.5)"
            }
        }
    """
    weight_key = "weight" if method == "LIME" else "shap_value"
    token_weights: dict[str, float] = {}
    for t in tokens:
        token_str = t["token"].strip()
        if token_str:
            token_weights[token_str] = t.get(weight_key, t.get("contribution", 0.0))

    max_abs = max((abs(v) for v in token_weights.values()), default=1.0) or 1.0

    highlights = []
    for token_str, weight in token_weights.items():
        # 查找 token 在原文中的所有位置
        start = 0
        while True:
            idx = text.find(token_str, start)
            if idx == -1:
                break
            highlights.append({
                "token": token_str,
                "weight": round(weight, 6),
                "start": idx,
                "end": idx + len(token_str),
                "color": _importance_color(weight, max_abs),
            })
            start = idx + len(token_str)

    # 按位置排序
    highlights.sort(key=lambda h: h["start"])

    return {
        "text": text,
        "method": method,
        "highlights": highlights,
        "legend": {
            "positive_label": "支持 AI 生成",
            "negative_label": "支持 真实文本",
            "positive_color": "rgba(255, 60, 60, 0.5)",
            "negative_color": "rgba(60, 180, 60, 0.5)",
        },
    }
