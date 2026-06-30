AIGI-Holmes backend/ 后端目录
==============================

【文件夹作用】
本目录为 AIGI-Holmes 系统的 FastAPI 后端核心，包含所有业务逻辑、数据库模型、API 路由和辅助模块。
启动命令：uvicorn backend.main:app --host 127.0.0.1 --port 7860 --reload

【各文件说明】

■ 应用核心
  main.py                   FastAPI 应用主入口，注册所有路由、中间件和异常处理器
  config.py                 应用配置类，从 .env 文件加载数据库、Redis、JWT、模型等参数
  database.py               SQLAlchemy 异步数据库引擎和会话工厂
  auth.py                   JWT 令牌生成与验证、密码哈希工具函数
  dependencies.py           FastAPI 依赖注入（用户鉴权、角色权限检查）
  exceptions.py             自定义异常类和全局异常处理器

■ 功能模块
  cache.py                  Redis 缓存层（以图片 SHA256 为键，缓存检测结果 1 小时）
  clip_classify.py          CLIP 零样本图片内容分类（7 类标签 + 图文一致性评分）
  job_store.py              批量检测异步任务队列存储（配合 WebSocket 推送进度）
  session_store.py          AI 多轮对话会话存储（TTL 30 分钟）

■ routers/ — API 路由模块
  routers/auth.py           用户认证接口（注册/登录/刷新令牌）  /api/auth/*
  routers/detect.py         图片检测接口（单图/URL/批量）      /api/detect*
  routers/report.py         检测报告生成与导出接口             /api/report/*
  routers/admin.py          管理员后台接口（统计/用户/记录）    /api/admin/*
  routers/ws.py             WebSocket 实时推送接口             /ws/detect/{job_id}
  routers/feedback.py       用户误判反馈提交接口               /api/feedback

■ models/ — 数据库 ORM 模型
  models/user.py            用户表（id/username/password_hash/role/created_at）
  models/detection.py       检测记录表（image_hash/label/confidence/probs_json 等）
  models/feedback.py        用户反馈表（detection_id/correct_label/note 等）

■ report/ — 报告生成模块
  report/generator.py       从检测记录生成结构化报告数据字典
  report/exporter.py        将报告导出为 PDF（reportlab）或 Excel（openpyxl）

■ llm/ — AI 分析模块
  llm/doubao_client.py      字节跳动豆包 AI 流式客户端（SSE 流式分析 + 多轮对话）
