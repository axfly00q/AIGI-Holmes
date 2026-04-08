<div align="center">

# AIGI-Holmes

**新闻图片 AI 生成检测系统**

*AI-Generated Image Detection for News Media*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com)

</div>

---

## 项目简介

AIGI-Holmes 是一款面向**新闻媒体核查场景**的 AI 生成图片检测系统。随着 AIGC 技术的迅速普及，AI 伪造图片在社交媒体和新闻报道中大量出现，给信息真实性鉴别带来严峻挑战。

AIGI-Holmes 通过微调的 ResNet-50 模型结合 CLIP 多模态分析，对图片进行真实性检测，并集成豆包 AI 提供可解释的自然语言分析报告，帮助记者、编辑和内容审核人员快速鉴别图片真实性。

---

## 核心功能

| 功能 | 说明 |
|------|------|
| **单图检测** | 上传图片，输出 FAKE/REAL 判定 + 置信度 + Grad-CAM 热力图 |
| **URL 批量检测** | 输入新闻页面 URL，自动抓取页面所有图片并批量检测 |
| **文件批量检测** | 上传多张图片，WebSocket 实时推送检测进度 |
| **CLIP 内容分类** | 零样本多标签分类（人物/建筑/风景等 7 类）+ 图文一致性评分 |
| **AI 辅助分析** | 豆包 AI 流式输出检测结果分析，支持多轮对话追问 |
| **报告导出** | 一键导出 PDF / Excel 检测报告（含水印、判定横幅） |
| **用户系统** | JWT 认证，三级角色（user / auditor / admin）权限管理 |
| **管理后台** | 统计仪表盘、用户管理、检测记录查询、误判反馈集成 |
| **误判反馈** | 用户可提交误判样本，管理员一键集成到训练数据集 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                  AIGI-Holmes 桌面应用                 │
│  desktop_launcher.py                                 │
│  ┌─────────────┐    ┌──────────────────────────────┐ │
│  │  pywebview  │◄───│   uvicorn  (127.0.0.1:7860)  │ │
│  │  桌面窗口    │    │   FastAPI backend             │ │
│  └─────────────┘    └──────────┬───────────────────┘ │
└─────────────────────────────────┼───────────────────┘
                                  │
            ┌─────────────────────┼──────────────────┐
            │                     │                  │
     ┌──────▼──────┐   ┌──────────▼───────┐   ┌─────▼──────┐
     │ ResNet-50   │   │   CLIP 分类器     │   │  豆包 AI   │
     │ 真伪检测    │   │  内容/图文分析    │   │  辅助分析  │
     └──────┬──────┘   └──────────┬───────┘   └─────┬──────┘
            └──────────┬──────────┘                  │
                 ┌─────▼──────┐                      │
                 │  SQLite /  │◄─────────────────────┘
                 │ PostgreSQL │
                 └────────────┘
```

---

## 快速开始

### 方式一：安装包（推荐，无需 Python 环境）

> 适合普通用户和评审人员

1. 下载 `AIGI-Holmes-Setup.exe`
2. 双击运行，按向导完成安装（默认安装到 `C:\Program Files\AIGI-Holmes\`）
3. 点击桌面快捷方式启动程序

**系统要求：**
- Windows 10 1809 (17763) 及以上
- Microsoft Edge WebView2（Windows 10/11 已内置；如未安装见[故障排查](#故障排查)）
- 首次启动约需 10～20 秒加载模型

---

### 方式二：源码运行（开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/AIGI-Holmes/AIGI-Holmes.git
cd AIGI-Holmes

# 2. 创建虚拟环境（推荐 Python 3.10）
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 3. 安装依赖
pip install -r requirements-app.txt

# 4. 配置环境变量（复制示例文件）
copy .env.example .env
# 按需修改 .env（默认使用 SQLite，开箱即用）

# 5. 启动服务
uvicorn backend.main:app --host 127.0.0.1 --port 7860 --reload

# 浏览器访问：http://127.0.0.1:7860
```

---

### 方式三：桌面窗口模式

```bash
# 安装 pywebview
pip install pywebview

# 启动桌面应用（不需要打开浏览器）
python desktop_launcher.py
```

---

## 使用说明

### 图片检测

1. **单张检测**：点击「上传图片」或拖拽图片到检测区域，点击「开始检测」
2. **URL 检测**：在输入框粘贴新闻页面 URL，系统自动抓取并检测页面中的图片
3. **批量检测**（需 auditor 权限）：点击「批量上传」，选择多张图片，实时查看检测进度

### 检测结果解读

| 指标 | 说明 |
|------|------|
| **判定结果** | `AI生成` / `真实照片` |
| **置信度** | 模型对当前判定的把握程度（0~100%） |
| **热力图** | Grad-CAM 可视化，高亮显示影响判定的图像区域 |
| **内容标签** | CLIP 零样本分类结果（如：人物、新闻现场） |
| **图文一致性** | 图片与配文的语义匹配度评分 |
| **AI 分析** | 豆包 AI 对检测结果的自然语言解读 |

### 账号与权限

| 角色 | 注册方式 | 功能权限 |
|------|----------|----------|
| `user` | 自助注册 | 单图检测、URL 检测、查看记录 |
| `auditor` | 管理员分配 | + 批量检测、导出报告 |
| `admin` | 初始配置 | + 用户管理、系统统计、反馈集成 |

> 首次使用可直接体验，无需注册账号（单图/URL 检测支持匿名使用）。

### 导出报告

登录后，在检测结果页面点击「导出报告」，选择格式：
- **PDF**：带水印和判定横幅的正式报告
- **Excel**：带颜色编码的批量检测数据表

---

## 项目结构与文件说明

```
AIGI-Holmes/
│
├── 🚀 启动与配置
│   ├── desktop_launcher.py ✨   # ⭐⭐⭐ 应用主启动器（启动 FastAPI + 打开窗口）
│   ├── AIGI_Holmes.spec        # PyInstaller 打包配置
│   ├── installer.iss           # Inno Setup 安装程序脚本
│   ├── .env.example ✨          # ⭐⭐⭐ 环境变量配置示例（必须复制为 .env）
│   └── requirements-app.txt    # ⭐⭐ 推荐依赖列表（打包和运行）
│
├── 🔧 后端核心代码 (FastAPI + uvicorn)
│   └── backend/
│       ├── main.py ✨          # ⭐⭐ FastAPI 主入口（启动命令：uvicorn backend.main:app）
│       ├── config.py           # 配置管理（从 .env 读取数据库 URL、Redis、JWT 密钥）
│       ├── auth.py             # JWT 认证工具（密码验证、Token 生成）
│       ├── database.py         # SQLAlchemy 异步数据库引擎
│       ├── dependencies.py     # FastAPI 依赖注入（鉴权中间件）
│       ├── exceptions.py       # 自定义异常 + 全局错误处理
│       ├── cache.py            # Redis 缓存层（可选）
│       ├── clip_classify.py    # CLIP 零样本分类（内容标签 + 图文一致性）
│       ├── job_store.py        # 批量检测任务队列（内存存储）
│       ├── session_store.py    # AI 多轮对话会话存储
│       │
│       ├── models/             # 📊 数据库 ORM 模型
│       │   ├── user.py         # User 表（用户认证）
│       │   ├── detection.py    # DetectionRecord 表（检测记录）
│       │   └── feedback.py     # FeedbackRecord 表（用户反馈）
│       │
│       ├── routers/            # 🌐 API 路由（按功能分类）
│       │   ├── auth.py         # /api/auth/*（注册/登录/刷新令牌）
│       │   ├── detect.py ✨    # ⭐ /api/detect*（单张/批量/URL 检测）
│       │   ├── report.py       # /api/report/*（PDF/Excel 导出）
│       │   ├── admin.py        # /api/admin/*（管理后台）
│       │   ├── ws.py           # /ws/detect/{job_id}（WebSocket 实时推送）
│       │   └── feedback.py     # /api/feedback（误判反馈）
│       │
│       ├── report/             # 📄 报告生成和导出
│       │   ├── generator.py    # 报告数据生成
│       │   └── exporter.py     # PDF/Excel 导出
│       │
│       └── llm/                # 🤖 AI 分析客户端
│           └── doubao_client.py # 豆包 AI 流式客户端
│
├── 🎯 检测和处理
│   ├── detect.py ✨            # ⭐⭐ 核心检测逻辑（ResNet50 推理）
│   ├── detect_text.py          # 文本文档图片提取（PDF/Word）
│   ├── finetune.py             # 模型微调脚本（开发者用）
│   ├── finetuned_fake_real_resnet50.pth ✨ # ⭐⭐⭐ ResNet50 微调模型（80 MB，必需）
│   └── CLIP/                   # CLIP 模型代码
│       ├── clip/
│       ├── model_card.md
│       └── README.md
│
├── 🎨 前端代码
│   ├── templates/              # Jinja2 HTML 模板
│   │   ├── index.html          # 前端主页（检测页面）
│   │   └── admin.html          # 管理后台页面
│   ├── static/                 # 前端静态资源
│   │   ├── css/style.css       # 全局样式
│   │   └── js/app.js           # 前端逻辑
│   └── asset/                  # 应用图标、水印等
│
├── 📚 文档
│   ├── README.md ✨            # ⭐⭐ 项目说明（本文件）
│   ├── USAGE.md ✨             # ⭐⭐ 详细使用教程（含故障排查）
│   ├── DESIGN_PLAN.md          # 设计文档
│   ├── readme.txt ✨           # ⭐ 文件夹内所有文件的用途说明
│   ├── docs/
│   │   ├── desktop-windows.md  # Windows 桌面启动指南
│   │   ├── packaging.md        # 打包发布指南
│   │   └── (Sphinx 文档目录)
│   └── docs/make.bat           # Sphinx 编译脚本
│
├── 🐳 容器和发布
│   ├── Dockerfile              # Docker 镜像定义
│   ├── docker-compose.yml      # Docker Compose 编排（PostgreSQL + Redis）
│   └── dist/                   # 📦 打包输出目录
│       ├── AIGI-Holmes/        # 绿色版（解压即用，846 MB）
│       │   ├── AIGI-Holmes.exe # 主程序可执行文件（80.8 MB）
│       │   ├── python.exe      # Python 运行环境
│       │   └── _internal/      # 所有依赖库和数据文件
│       └── AIGI-Holmes-Setup.exe # 安装版（标准 Windows 安装向导）
│
├── 🧪 测试和工具
│   ├── tests/                  # 单元测试
│   ├── scripts/                # 辅助脚本
│   ├── tools/                  # 工具脚本
│   └── multi-node/             # 多节点训练脚本
│
├── 📊 数据和资源
│   ├── data/                   # 训练数据集（FAKE/REAL 分类）
│   ├── data 1/
│   ├── data 3/
│   ├── resources/              # 附加资源
│   └── examples/               # 示例代码
│
├── 📦 依赖管理
│   ├── requirements-app.txt ✨ # ⭐⭐ 应用运行依赖（推荐）
│   ├── requirements.txt        # 完整依赖（包括开发工具）
│   ├── setup.py                # Python 包安装脚本
│   └── aigi_holmes.db          # SQLite 数据库（运行时自动创建）
│
└── 📄 项目元数据
    ├── .gitignore
    └── LICENSE
```

### 📋 关键文件详解

| 文件/目录 | 用途 | 何时需要修改 |
|---|---|---|
| **desktop_launcher.py** | 应用主启动器，启动 FastAPI 后端 + PyWebView 窗口 | 🔴 不需要（除非自定义窗口大小/标题） |
| **backend/main.py** | FastAPI 应用入口，注册所有 API 路由 | 🟡 添加新 API 时 |
| **detect.py** | 核心检测逻辑，调用 ResNet50 进行推理 | 🟡 优化检测算法时 |
| **finetuned_fake_real_resnet50.pth** | AI 检测模型权重（80 MB） | 🔴 不需要（除非重新训练模型） |
| **.env.example** | 环境变量配置示例 | 🟡 复制为 .env 并填写数据库/API Key |
| **requirements-app.txt** | 运行依赖列表 | 🔴 不需要（预配置完成） |
| **AIGI_Holmes.spec** | PyInstaller 打包配置 | 🔴 不需要（已正确配置） |
| **installer.iss** | Inno Setup 安装程序脚本 | 🔴 不需要（已正确配置） |
| **dist/AIGI-Holmes/** | 打包输出的绿色版（解压即用） | ✅ 直接使用 |
| **dist/AIGI-Holmes-Setup.exe** | 打包输出的安装版 | ✅ 直接使用 |

### 🎯 常见操作对应文件

| 操作 | 相关文件 |
|---|---|
| **运行程序** | → desktop_launcher.py |
| **修改数据库配置** | → .env（复制自 .env.example） |
| **查看 API 文档** | → backend/main.py + backend/routers/* |
| **重新训练模型** | → finetune.py + data/ |
| **生成新的安装包** | → AIGI_Holmes.spec + installer.iss |
| **了解使用方法** | → USAGE.md |
| **查看故障排查** | → USAGE.md（常见问题部分）|
| **部署到服务器** | → backend/main.py + docker-compose.yml |

---

## 技术栈

| 层次 | 技术 |
|------|------|
| **后端框架** | FastAPI 0.110+ / uvicorn |
| **图像检测** | PyTorch 2.0+ / ResNet-50（微调） |
| **多模态分析** | CLIP ViT-B/32 |
| **可解释性** | Grad-CAM |
| **数据库** | SQLite（默认）/ PostgreSQL（生产） |
| **缓存** | Redis（可选） |
| **认证** | JWT (python-jose) + bcrypt |
| **报告生成** | reportlab（PDF）/ openpyxl（Excel） |
| **文档提取** | PyMuPDF / python-docx |
| **AI 分析** | 字节跳动豆包 AI（ARK 平台）|
| **桌面窗口** | pywebview + Microsoft Edge WebView2 |
| **打包** | PyInstaller + Inno Setup |

---

## API 文档

启动服务后访问：

- **Swagger UI**：[http://127.0.0.1:7860/docs](http://127.0.0.1:7860/docs)
- **ReDoc**：[http://127.0.0.1:7860/redoc](http://127.0.0.1:7860/redoc)

### 主要接口一览

```
POST   /api/detect                  # 单图检测
POST   /api/detect-url              # URL 页面图片检测
POST   /api/detect-batch            # 多图批量检测（同步）
POST   /api/detect-batch-init       # 创建批量任务（异步，配合 WebSocket）
POST   /api/detect-batch-run        # 提交文件到批量任务
GET    /api/detection/{id}/analyze  # 豆包 AI 分析（SSE 流式）
POST   /api/report/generate         # 生成检测报告
GET    /api/report/{id}/export      # 导出 PDF/Excel
POST   /api/auth/register           # 用户注册
POST   /api/auth/login              # 用户登录
WS     /ws/detect/{job_id}          # 批量检测进度推送
```

---

## 打包与发布

> 需要开发环境（Python 3.10+、PyInstaller、Inno Setup 6）

```bash
# 步骤一：生成可执行文件
pip install pyinstaller
pyinstaller AIGI_Holmes.spec

# 步骤二：编译安装包（需安装 Inno Setup 6）
iscc installer.iss

# 输出：dist\AIGI-Holmes-Setup.exe
```

详细说明见 [docs/packaging.md](docs/packaging.md)。

---

## 故障排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| 程序启动后白屏 | WebView2 未安装 | 下载安装 [Edge WebView2 运行时](https://developer.microsoft.com/zh-cn/microsoft-edge/webview2/) |
| 启动超时（>60s） | 模型文件缺失 | 确认 `finetuned_fake_real_resnet50.pth` 在程序目录中 |
| 检测结果报错 | 配置文件问题 | 检查程序目录下 `.env` 文件是否存在且 `MODEL_PATH` 正确 |
| 无法连接数据库 | SQLite 路径权限 | 以管理员身份运行程序，或检查安装目录写入权限 |
| AI 分析不可用 | 豆包 API Key 未配置 | 在 `.env` 中填写 `DOUBAO_API_KEY` |

---

## 开发环境配置

```bash
# 安装开发依赖
pip install -r requirements-app.txt

# 代码格式化
pip install ruff
ruff format .

# 运行测试
python _smoke_test.py           # 基础连通性测试
python _integration_test.py     # 接口集成测试
```

---

## 致谢

- [ResNet](https://arxiv.org/abs/1512.03385)：图像特征提取骨干网络
- [CLIP](https://github.com/openai/CLIP)：多模态图文理解模型
- [FastAPI](https://fastapi.tiangolo.com)：高性能 Python Web 框架
- [pywebview](https://pywebview.app)：Python 桌面 WebView 库
- 字节跳动 [豆包 AI](https://www.volcengine.com/product/ark)：自然语言分析能力

---

<div align="center">

Made with ❤️ for trustworthy news media

</div>
