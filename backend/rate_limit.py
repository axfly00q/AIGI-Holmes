"""
AIGI-Holmes backend — 速率限制配置（基于 slowapi）

规则：
  /api/detect      — 匿名 20次/分钟；登录用户 60次/分钟
  /api/detect-url  — 匿名 10次/分钟；登录用户 30次/分钟
  /api/text/detect — 匿名 15次/分钟
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# 以客户端真实 IP 作为限流 key
limiter = Limiter(key_func=get_remote_address)
