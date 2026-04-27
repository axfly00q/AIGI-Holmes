"""
AIGI-Holmes — EXIF 元数据分析器

通过读取图像 EXIF/XMP 元数据判断图像来源：
- 若 Software/Comment 字段中含已知 AI 生成工具签名 → 可疑
- 若含摄像头 Make/Model 字段 → 真实相机可能性大
- 若缺少所有元数据 → 中性（许多平台会剥离 EXIF）

返回 {"score": 0-100, "ai_software": str|None, "details": str}
score 含义与其他分析器一致：越高 = 越可能真实。
"""

import asyncio
import io
import logging
from functools import partial
from typing import Optional

from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AI 生成工具在 EXIF Software 字段中的已知签名（大小写不敏感匹配）
# ---------------------------------------------------------------------------
_AI_SOFTWARE_SIGNATURES = [
    "stable diffusion",
    "stablediffusion",
    "comfyui",
    "invokeai",
    "invoke ai",
    "automatic1111",
    "webui",
    "novelai",
    "novel ai",
    "midjourney",
    "dall-e",
    "dalle",
    "adobe firefly",
    "firefly",
    "diffusers",
    "hugging face",
    "imagen",
    "deepfloyd",
    "kandinsky",
    "wuerstchen",
    "flux",
    "sora",
    "runwayml",
    "runway",
    "kling",
    "pika",
]

# ExifTags 字段 ID → 名称 反查表
_TAG_IDS: dict[str, int] = {v: k for k, v in ExifTags.TAGS.items()}

_SOFTWARE_TAG    = _TAG_IDS.get("Software", 305)
_MAKE_TAG        = _TAG_IDS.get("Make", 271)
_MODEL_TAG       = _TAG_IDS.get("Model", 272)
_USER_COMMENT    = _TAG_IDS.get("UserComment", 37510)
_IMAGE_DESC      = _TAG_IDS.get("ImageDescription", 270)
_ARTIST          = _TAG_IDS.get("Artist", 315)
_GPS_INFO        = _TAG_IDS.get("GPSInfo", 34853)
_DATE_TIME       = _TAG_IDS.get("DateTime", 306)


def _safe_str(val) -> str:
    """将任意 EXIF 值安全转换为 str（UserComment 为 bytes，需要处理）"""
    if isinstance(val, bytes):
        # UserComment 前 8 字节是字符集标识
        try:
            return val[8:].decode("utf-8", errors="replace").strip("\x00 ")
        except Exception:
            return val.decode("latin-1", errors="replace").strip("\x00 ")
    return str(val).strip()


def _analyze_sync(pil_image: Image.Image) -> dict:
    """同步 EXIF 分析，运行在线程池中"""
    try:
        exif = pil_image.getexif()
    except Exception:
        exif = {}

    if not exif:
        return {
            "score": 45,
            "ai_software": None,
            "details": "图像不含 EXIF 元数据（常见于截图或经平台处理的图片）",
        }

    software_raw = exif.get(_SOFTWARE_TAG, "")
    make_raw     = exif.get(_MAKE_TAG, "")
    model_raw    = exif.get(_MODEL_TAG, "")
    comment_raw  = exif.get(_USER_COMMENT, "")
    desc_raw     = exif.get(_IMAGE_DESC, "")
    has_gps      = _GPS_INFO in exif
    has_datetime = _DATE_TIME in exif

    software_str = _safe_str(software_raw).lower()
    comment_str  = _safe_str(comment_raw).lower()
    desc_str     = _safe_str(desc_raw).lower()
    make_str     = _safe_str(make_raw)
    model_str    = _safe_str(model_raw)

    # 检查是否含 AI 工具签名
    combined_text = f"{software_str} {comment_str} {desc_str}"
    detected_tool: Optional[str] = None
    for sig in _AI_SOFTWARE_SIGNATURES:
        if sig in combined_text:
            # 取原始字段值做展示
            if sig in software_str:
                detected_tool = _safe_str(software_raw)
            elif sig in comment_str:
                detected_tool = _safe_str(comment_raw)[:80]
            else:
                detected_tool = _safe_str(desc_raw)[:80]
            break

    if detected_tool:
        return {
            "score": 8,
            "ai_software": detected_tool,
            "details": f"EXIF Software 字段含 AI 生成工具签名：「{detected_tool}」",
        }

    # 真实摄像头标志
    has_camera = bool(make_str.strip() and model_str.strip())
    if has_camera:
        score = 88
        if has_gps:
            score = min(95, score + 5)
        details = f"检测到真实相机信息：{make_str} {model_str}"
        if has_gps:
            details += "（含 GPS 定位）"
        return {"score": score, "ai_software": None, "details": details}

    # 有时间戳但无摄像头（截图、社交媒体等）
    if has_datetime:
        return {
            "score": 50,
            "ai_software": None,
            "details": "含时间戳但无相机信息，可能为截图或经过二次处理",
        }

    # 有 EXIF 但字段极少
    return {
        "score": 40,
        "ai_software": None,
        "details": "EXIF 元数据不完整，无法判断来源",
    }


async def analyze(pil_image: Image.Image) -> dict:
    """异步 EXIF 分析（在线程池中运行，不阻塞事件循环）"""
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, partial(_analyze_sync, pil_image))
    except Exception as exc:
        logger.warning("EXIF 分析失败: %s", exc)
        return {"score": 50, "ai_software": None, "details": "EXIF 分析异常"}
