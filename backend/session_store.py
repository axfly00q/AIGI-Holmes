"""
会话存储 — 用于临时存储AI分析历史。

设计思路：
- 在内存中维护会话字典
- 每个会话有TTL（30分钟），过期后自动删除
- sessionId由前端生成：'session_{timestamp}_{random}'
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("backend.session_store")

# 全局会话存储
_sessions: Dict[str, "AnalysisSession"] = {}


class AnalysisSession:
    """AI分析会话"""

    def __init__(self, session_id: str, ttl: int = 1800):
        """
        Args:
            session_id: 会话ID（客户端生成）
            ttl: 会话生存时间（秒），默认30分钟
        """
        self.session_id = session_id
        self.history: List[dict] = []  # [{detection_id, question, answer, timestamp}]
        self.created_at = datetime.utcnow()
        self.ttl = ttl
        self._expiry_handle = None
        self._schedule_expiry()

    def add_entry(self, detection_id: int, question: str, answer: str):
        """添加一条分析记录"""
        self.history.append(
            {
                "detection_id": detection_id,
                "question": question,
                "answer": answer,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_history(self) -> List[dict]:
        """获取会话历史"""
        return self.history.copy()

    def get_history_for_detection(self, detection_id: int) -> List[dict]:
        """获取特定检测ID的历史记录（支持多轮对话上下文）"""
        return [h for h in self.history if h["detection_id"] == detection_id]

    def _schedule_expiry(self):
        """调度会话过期"""
        try:
            loop = asyncio.get_event_loop()
            if self._expiry_handle:
                loop.call_soon_threadsafe(self._expiry_handle.cancel)
            self._expiry_handle = loop.call_later(self.ttl, self._expire)
        except RuntimeError:
            # 如果事件循环已关闭，直接调用过期处理
            self._expire()

    def _expire(self):
        """过期处理"""
        logger.info(f"Session {self.session_id[:16]}... expired")
        if self.session_id in _sessions:
            del _sessions[self.session_id]


def get_session(session_id: str) -> Optional[AnalysisSession]:
    """获取会话"""
    return _sessions.get(session_id)


def get_or_create_session(session_id: str, ttl: int = 1800) -> AnalysisSession:
    """获取或创建会话"""
    if session_id not in _sessions:
        _sessions[session_id] = AnalysisSession(session_id, ttl=ttl)
        logger.info(f"Session {session_id[:16]}... created")
    return _sessions[session_id]


def delete_session(session_id: str) -> bool:
    """删除会话"""
    if session_id in _sessions:
        session = _sessions[session_id]
        if session._expiry_handle:
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(session._expiry_handle.cancel)
            except RuntimeError:
                pass
        del _sessions[session_id]
        return True
    return False


def get_session_stats() -> dict:
    """获取会话统计信息（用于调试）"""
    return {
        "total_sessions": len(_sessions),
        "sessions": [
            {
                "session_id": sid[:16] + "...",
                "created_at": s.created_at.isoformat(),
                "entries": len(s.history),
            }
            for sid, s in _sessions.items()
        ],
    }
