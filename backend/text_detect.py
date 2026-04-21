"""
AIGI-Holmes 文本AI生成检测模块

支持使用预训练模型（BERT/RoBERTa）进行文本AI生成检测。
返回结构与 detect.py 保持一致，用于统一的数据库存储和报告生成。
"""

import hashlib
import os
import sys
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# ---------------------------------------------------------------------------
# 基础配置
# ---------------------------------------------------------------------------
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_NAME = "openai-community/roberta-base-openai-detector"
CLASSES = ["FAKE", "REAL"]  # 模型输出: 0=Fake, 1=Real
TEXT_MAX_LENGTH = 512  # RoBERTa最大输入长度

MODEL_VERSION = "text-v1.0"


def _load_model():
    """加载预训练的文本检测模型"""
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        model.to(DEVICE)
        model.eval()
        return tokenizer, model
    except Exception as e:
        raise RuntimeError(f"Failed to load model {MODEL_NAME}: {e}")


try:
    _tokenizer, _model = _load_model()
except Exception as e:
    print(f"[TEXT_DETECT] FATAL: Failed to load model: {e}", flush=True)
    raise


def _compute_model_version() -> str:
    """计算模型版本哈希（用于追踪）"""
    return MODEL_VERSION


MODEL_VERSION_HASH = _compute_model_version()


# ---------------------------------------------------------------------------
# 文本检测核心逻辑
# ---------------------------------------------------------------------------

def detect_text(text: str, return_tokens: bool = False) -> dict:
    """
    检测文本是否为AI生成内容

    Args:
        text: 输入文本
        return_tokens: 是否返回token级别信息（用于LIME/SHAP）

    Returns:
        {
            "label": "FAKE" | "REAL",
            "label_zh": "AI 生成" | "真实文本",
            "confidence": 0-100,
            "probs": [{"label": str, "label_zh": str, "score": float}, ...],
            "raw_logits": [float, float],
            "tokens": [{"token": str, "id": int}, ...] if return_tokens
        }
    """
    if not text or len(text.strip()) == 0:
        raise ValueError("输入文本不能为空")

    # 编码和推理（由 tokenizer 的 truncation=True 保证不超过模型上限）
    with torch.no_grad():
        inputs = _tokenizer(
            text,
            return_tensors="pt",
            max_length=TEXT_MAX_LENGTH,
            truncation=True,
            padding="max_length"
        ).to(DEVICE)

        outputs = _model(**inputs)
        logits = outputs.logits[0].cpu().numpy()
        probs = torch.softmax(torch.tensor(logits), dim=0).numpy()

    # 预测结果
    pred_idx = int(np.argmax(probs))
    pred_label = CLASSES[pred_idx]
    pred_confidence = float(probs[pred_idx] * 100)

    # 两个类别的概率
    results = [
        {
            "label": cls,
            "label_zh": "真实文本" if cls == "REAL" else "AI 生成",
            "score": float(probs[i] * 100)
        }
        for i, cls in enumerate(CLASSES)
    ]
    results.sort(key=lambda x: x["score"], reverse=True)

    result = {
        "label": pred_label,
        "label_zh": results[0]["label_zh"],
        "confidence": pred_confidence,
        "probs": results,
        "raw_logits": logits.tolist(),
    }

    # 可选：返回token信息（用于LIME/SHAP）
    if return_tokens:
        token_ids = inputs["input_ids"][0].cpu().numpy()
        tokens = []
        for tid in token_ids:
            token_str = _tokenizer.decode([tid])
            tokens.append({"token": token_str, "id": int(tid)})
        result["tokens"] = tokens

    return result


def detect_batch(texts: list[str]) -> list[dict]:
    """
    批量检测文本

    Args:
        texts: 文本列表

    Returns:
        检测结果列表（每个结果结构同 detect_text）
    """
    if not texts:
        return []

    results = []
    for text in texts:
        try:
            result = detect_text(text, return_tokens=False)
            results.append(result)
        except Exception as e:
            # 单个文本失败不影响整体
            results.append({
                "label": "UNKNOWN",
                "label_zh": "检测失败",
                "confidence": 0.0,
                "probs": [],
                "error": str(e)
            })

    return results


# ---------------------------------------------------------------------------
# 异步包装（用于FastAPI）
# ---------------------------------------------------------------------------

import asyncio
from functools import partial


async def async_detect_text(text: str, return_tokens: bool = False) -> dict:
    """异步文本检测（适配FastAPI）"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(detect_text, text=text, return_tokens=return_tokens)
    )


async def async_detect_batch(texts: list[str]) -> list[dict]:
    """异步批量检测"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(detect_batch, texts=texts))


# ---------------------------------------------------------------------------
# 文本预处理和分段
# ---------------------------------------------------------------------------

def segment_text(text: str, max_length: int = 1800, overlap: int = 200) -> list[dict]:
    """
    将长文本分段（用于处理超长新闻文章）

    Args:
        text: 输入文本
        max_length: 每段最大长度（字符数）
        overlap: 段落之间的重叠字符数

    Returns:
        [{"segment": str, "start": int, "end": int}, ...]
    """
    if len(text) <= max_length:
        return [{"segment": text, "start": 0, "end": len(text)}]

    segments = []
    start = 0
    max_segments = 20  # 限制最多20个段落，防止内存溢出

    while start < len(text) and len(segments) < max_segments:
        end = min(start + max_length, len(text))
        segment_text_slice = text[start:end]
        segments.append({
            "segment": segment_text_slice,
            "start": start,
            "end": end
        })
        start = end - overlap
        if start <= end - max_length:  # 防止无限循环
            start = end

    return segments


def detect_text_with_segments(text: str) -> dict:
    """
    对长文本进行分段检测，综合评分

    Returns:
        {
            "label": "FAKE" | "REAL",
            "confidence": 0-100,
            "segments": [
                {
                    "segment": str,
                    "start": int,
                    "end": int,
                    "label": "FAKE" | "REAL",
                    "confidence": float
                },
                ...
            ],
            "overall_confidence": float
        }
    """
    segments_info = segment_text(text)
    segment_results = []
    fake_scores = []

    for seg_info in segments_info:
        seg_result = detect_text(seg_info["segment"], return_tokens=False)

        # 查找FAKE的得分
        fake_score = next(
            (p["score"] for p in seg_result["probs"] if p["label"] == "FAKE"),
            0.0
        )
        fake_scores.append(fake_score)

        segment_results.append({
            "segment": seg_info["segment"],
            "start": seg_info["start"],
            "end": seg_info["end"],
            "label": seg_result["label"],
            "confidence": seg_result["confidence"]
        })

    # 综合评分：用FAKE得分的平均值
    avg_fake_score = np.mean(fake_scores) if fake_scores else 0.0
    overall_label = "FAKE" if avg_fake_score > 50 else "REAL"

    return {
        "label": overall_label,
        "confidence": avg_fake_score,
        "segments": segment_results,
        "overall_confidence": avg_fake_score,
        "model_version": MODEL_VERSION_HASH
    }


# ---------------------------------------------------------------------------
# 文本哈希（用于去重和缓存）
# ---------------------------------------------------------------------------

def compute_text_hash(text: str) -> str:
    """计算文本的SHA256哈希"""
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 解释所需的辅助函数
# ---------------------------------------------------------------------------

def get_token_embeddings(text: str) -> dict:
    """
    获取文本的token级别嵌入和注意力权重
    用于LIME/SHAP解释

    Returns:
        {
            "tokens": [token_str, ...],
            "embeddings": np.ndarray (shape: num_tokens x hidden_size),
            "attention_weights": np.ndarray (shape: num_layers x num_heads x seq_len x seq_len)
        }
    """
    with torch.no_grad():
        inputs = _tokenizer(
            text,
            return_tensors="pt",
            max_length=TEXT_MAX_LENGTH,
            truncation=True,
            padding="max_length"
        ).to(DEVICE)

        # 获取模型输出和注意力权重
        outputs = _model(**inputs, output_attentions=True, output_hidden_states=True)

        # Token IDs
        token_ids = inputs["input_ids"][0].cpu().numpy()
        tokens = [_tokenizer.decode([tid]) for tid in token_ids]

        # 最后一层的隐藏状态（用作嵌入）
        last_hidden_state = outputs.hidden_states[-1][0].cpu().numpy()

        # 注意力权重
        attention_weights = [attn[0].cpu().numpy() for attn in outputs.attentions]

    return {
        "tokens": tokens,
        "embeddings": last_hidden_state,
        "attention_weights": np.array(attention_weights)
    }


if __name__ == "__main__":
    # 快速测试
    test_texts = [
        "这是一篇真实的新闻文章。今天天气很好。",
        "According to recent studies, artificial intelligence has revolutionized the way we process information.",
    ]

    print("[TEXT_DETECT] 快速测试")
    for i, text in enumerate(test_texts, 1):
        print(f"\n示例 {i}：{text[:50]}...")
        result = detect_text(text)
        print(f"  标签：{result['label_zh']}")
        print(f"  置信度：{result['confidence']:.1f}%")
        print(f"  概率：{result['probs']}")
