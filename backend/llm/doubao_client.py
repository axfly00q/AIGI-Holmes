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

    def _build_image_content(self, image_ref: str, text: str) -> list:
        """构建多模态 content 列表 [image, text]。
        image_ref 可以是 data-URI（data:image/...）或 https URL。
        """
        return [
            {"type": "image_url", "image_url": {"url": image_ref}},
            {"type": "text", "text": text},
        ]

    async def stream_analysis(
        self,
        user_question: str,
        detection_result: dict,
        image_info: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        image_base64: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        基于检测结果和用户提问，生成AI分析。支持多轮对话。

        Args:
            user_question: 用户的提问
            detection_result: 检测结果 {label, confidence, probs, ...}
            image_info: 图片信息描述（可选，文字形式）
            conversation_history: 之前的对话历史 [{"role": "user"|"assistant", "content": "..."}, ...]
            image_base64: 图像数据，data-URI 或 https URL（可选）；传入后启用多模态视觉分析

        Yields:
            分析结果的文本块
        """
        # 构建提示词
        system_prompt = """你是一位专业的AI图片检测分析师。系统通过机器学习模型判断一张图片是否由「人工智能图像生成模型」（如 Midjourney、Stable Diffusion、DALL-E 等）生成。

重要定义（必须严格遵守）：
- 「真实 / 非AI生成」 = 未经过AI图像生成模型产出的内容。包括：真实拍摄的照片、游戏引擎渲染的截图、3D软件建模渲染图、手绘揔图、动画截图等，一律属于「非AI生成」。
- 「AI生成」 = 专門指 Midjourney、SD、DALL-E、Firefly 等AI绘画工具制作的图片。

请：
1. 严格遵守上述定义，不得把游戏截图、动画、绘画、CG渲染等误判为AI生成
2. 尊重检测模型给出的判定结果，在此基础上做解释，不要证明模型结论错误
3. 指出图像中支持该判定的视觉特征或线索
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

        # 添加当前用户提问（包含检测摘要）
        user_message = f"""{detection_summary}

用户提问：{user_question}"""
        # 若有图像，使用多模态格式（image + text）
        if image_base64:
            user_content = self._build_image_content(image_base64, user_message)
        else:
            user_content = user_message
        messages.append({"role": "user", "content": user_content})

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
        image_base64: str = "",
    ) -> dict:
        """Two-layer VSFC evidence-anchored report (non-streaming).

        Layer 1: global authenticity analysis.
        Layer 2: region-specific artifact description anchored to cam_regions bbox.
        Both calls are issued concurrently via asyncio.gather.

        Args:
            image_base64: Grad-CAM 叠加图的 data-URI 或原图 https URL（可选）；
                          传入后两层分析均可直接对图像做视觉检查（LVLM 模式）。

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

        # Layer 1: 全局分析
        l1_system = (
            "你是一位专业的AI图片检测分析师。"
            "【重要定义】「AI生成」专指 Midjourney、Stable Diffusion、DALL-E 等AI图像生成工具的产出；"
            "游戏截图、3D渲染、拍摄照片、手绘、动画等均属于「非AI生成」。"
            + ("请观察图像并结合检测结果，" if image_base64 else "请根据检测结果，")
            + "尊重模型判定，对图片的判定给出简明的全局分析（不超过150字）。"
        )
        l1_user_text = detection_summary
        l1_user_content = (
            self._build_image_content(image_base64, l1_user_text)
            if image_base64 else l1_user_text
        )
        msgs_l1 = [
            {"role": "system", "content": l1_system},
            {"role": "user", "content": l1_user_content},
        ]

        msgs_l2 = None
        if cam_regions:
            coords_str = "; ".join(
                f"区域{i + 1}(x={b['x']},y={b['y']},w={b['w']},h={b['h']},强度={b['strength']})"
                for i, b in enumerate(cam_regions)
            )
            # Layer 2: 证据锚定分析
            l2_system = (
                "你是一位专业的AI图片取证分析师。"
                "【重要定义】「AI生成」专指 Midjourney、SD、DALL-E 等AI图像生成工具的产出；游戏截图、3D渲染、拍摄照片等均属于「非AI生成」。"
                "模型Grad-CAM已在图像上标记出检测结果对应的热点区域（图中高亮部分），"
                + ("请直接观察图像中的高亮区域，" if image_base64 else "")
                + "尊重模型判定，描述这些热点区域对应的视觉特征（不超过120字），不要描述热点以外的区域。"
            )
            l2_user_text = f"检测结果：{detection_summary}\n热点区域坐标：{coords_str}"
            l2_user_content = (
                self._build_image_content(image_base64, l2_user_text)
                if image_base64 else l2_user_text
            )
            msgs_l2 = [
                {"role": "system", "content": l2_system},
                {"role": "user", "content": l2_user_content},
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
