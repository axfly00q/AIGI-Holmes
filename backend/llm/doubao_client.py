"""
豆包AI API 客户端 — 用于AI检测结果分析。
"""

import httpx
import asyncio
import logging
from typing import AsyncGenerator, List, Dict, Optional

logger = logging.getLogger("backend.llm.doubao")


class DoubaoClient:
    """豆包AI 流式客户端"""

    def __init__(self, api_key: str, model: str = "doubao-pro-32k"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.timeout = 30

    async def stream_analysis(
        self,
        user_question: str,
        detection_result: dict,
        image_info: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        基于检测结果和用户提问，生成AI分析。支持多轮对话。

        Args:
            user_question: 用户的提问
            detection_result: 检测结果 {label, confidence, probs, ...}
            image_info: 图片信息描述（可选）
            conversation_history: 之前的对话历史 [{"role": "user"|"assistant", "content": "..."}, ...]

        Yields:
            分析结果的文本块
        """
        # 构建提示词
        system_prompt = """你是一位专业的AI图片检测分析师。用户已经通过机器学习模型检测了一张图片，
需要你根据检测结果和用户的问题来提供深入的分析和解释。

请：
1. 准确理解检测结果的含义
2. 用通俗易懂的语言解释为什么这张图片被判定为AI生成或真实
3. 指出可能的关键特征或线索
4. 保持客观和专业的态度"""

        detection_summary = f"""
检测结果：
- 判定：{detection_result.get('label_zh', '未知')}
- 置信度：{detection_result.get('confidence', 0) * 100:.1f}%
- 详细概率：{detection_result.get('probs', [])}
"""

        if image_info:
            detection_summary += f"- 图片信息：{image_info}\n"

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 如果有对话历史，添加到消息列表中
        if conversation_history:
            messages.extend(conversation_history)

        # 添加当前用户提问（仅在没有历史或首次提问时包含检测摘要）
        user_message = f"""{detection_summary}

用户提问：{user_question}"""
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
                ) as response:
                    if response.status_code != 200:
                        body_text = await response.aread()
                        err_body = body_text.decode(errors="replace")[:300]
                        logger.error(f"Doubao API HTTP {response.status_code}: {err_body}")
                        # 大量空行来确保这个错误被识别出来
                        raise Exception(f"API error {response.status_code}: {err_body[:100]}")

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield "[DONE]"
                                break

                            try:
                                import json
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                # 跳过无效的行
                                pass

        except asyncio.TimeoutError:
            logger.error("Doubao API timeout")
            yield "❌ 请求超时，请重试"
        except httpx.HTTPStatusError as e:
            logger.error(f"Doubao API HTTP error {e.response.status_code}: {e.response.text[:500]}")
            yield f"❌ API错误: {e.response.status_code}"
        except httpx.RequestError as e:
            logger.error(f"Doubao API request error: {e}")
            yield f"❌ 网络错误: {str(e)[:100]}"
        except Exception as e:
            logger.error(f"Doubao API exception: {type(e).__name__}: {e}")
            yield f"❌ 分析失败：{str(e)[:150]}"

    async def generate_vsfc_report(
        self,
        detection_result: dict,
        cam_regions: list[dict],
        image_info: str = "",
    ) -> dict:
        """Two-layer VSFC evidence-anchored report (non-streaming).

        Layer 1: global authenticity analysis.
        Layer 2: region-specific artifact description anchored to cam_regions bbox.
        Both calls are issued concurrently via asyncio.gather.

        Returns {"global": str, "evidence_anchored": str}.
        """
        import json as _json

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        detection_summary = (
            f"判定：{detection_result.get('label_zh', '未知')}，"
            f"置信度：{detection_result.get('confidence', 0):.1f}%"
        )
        if image_info:
            detection_summary += f"，{image_info}"

        msgs_l1 = [
            {
                "role": "system",
                "content": (
                    "你是一位专业的AI图片检测分析师。请根据检测结果，"
                    "对图片的真实性给出简明的全局分析（不超过150字）。"
                ),
            },
            {"role": "user", "content": detection_summary},
        ]

        msgs_l2 = None
        if cam_regions:
            coords_str = "; ".join(
                f"区域{i + 1}(x={b['x']},y={b['y']},w={b['w']},h={b['h']},强度={b['strength']})"
                for i, b in enumerate(cam_regions)
            )
            msgs_l2 = [
                {
                    "role": "system",
                    "content": (
                        "你是一位专业的AI图片取证分析师。"
                        "模型Grad-CAM已标记出以下可疑伪影热点坐标区域，"
                        "请仅针对这些区域描述其具体视觉异常（不超过120字），"
                        "不要描述热点以外的区域。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"检测结果：{detection_summary}\n热点区域：{coords_str}",
                },
            ]

        async def _call(messages: list) -> str:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        json={"model": self.model, "messages": messages},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        return (
                            resp.json()
                            .get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
            except Exception as e:
                logger.error(f"VSFC API call error: {e}")
            return ""

        if msgs_l2:
            global_text, evidence_text = await asyncio.gather(
                _call(msgs_l1), _call(msgs_l2)
            )
        else:
            global_text = await _call(msgs_l1)
            evidence_text = ""

        return {"global": global_text, "evidence_anchored": evidence_text}

    async def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效。

        Returns:
            密钥是否有效
        """
        if not self.api_key:
            return False

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Hi"}],
        }

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False
