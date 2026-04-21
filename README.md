<div align="center">

<h1>🔍 AIGI-Holmes</h1>

<p><strong>新闻图片 AI 生成检测系统</strong> &nbsp;|&nbsp; <em>AI-Generated Image Detection for News Media</em></p>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-MIT-brightgreen)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-0078D6?logo=windows&logoColor=white)](https://github.com/axfly00q/AIGI-Holmes)
[![GitHub Stars](https://img.shields.io/github/stars/axfly00q/AIGI-Holmes?style=social)](https://github.com/axfly00q/AIGI-Holmes/stargazers)

<br/>

**一款面向新闻媒体核查场景的 AI 生成图片检测工具**  
基于微调 ResNet-50 + CLIP 多模态分析，集成豆包 AI 可解释分析报告

<br/>

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [系统架构](#-系统架构) · [API 文档](#-api-文档) · [部署指南](#-部署与打包) · [常见问题](#-常见问题)

</div>

---

## 📖 项目介绍

随着 AIGC 技术迅速普及，AI 伪造图片在社交媒体与新闻报道中大量出现，给信息真实性鉴别带来严峻挑战。

**AIGI-Holmes** 提供了一套完整的检测工作流：

- 🧠 **深度学习检测**：基于 ResNet-50 微调模型，对图片进行 FAKE/REAL 二分类，输出置信度与 Grad-CAM 热力图
- 🖼️ **多模态分析**：集成 CLIP ViT-B/32，支持零样本内容分类与图文一致性评分
- 💬 **AI 辅助解读**：对接字节跳动豆包 AI，流式输出检测结果自然语言分析，支持多轮追问
- 📄 **报告导出**：一键生成带水印、判定横幅的正式 PDF / Excel 报告

---

## ✨ 功能特性

| 功能模块 | 描述 |
|---|---|
| **单图检测** | 拖拽或上传图片，输出 AI生成/真实照片 判定 + 置信度 + Grad-CAM 热力图 |
| **URL 批量检测** | 输入新闻页面 URL，自动抓取页面全部图片并批量检测 |
| **文件批量检测** | 上传多张图片，WebSocket 实时推送进度与结果 |
| **CLIP 内容分类** | 零样本多标签分类（人物、建筑、风景等 7 类）+ 图文一致性评分 |
| **豆包 AI 分析** | SSE 流式输出检测分析报告，支持自定义追问 |
| **报告导出** | 导出 PDF（带水印）/ Excel（颜色编码）两种格式 |
| **用户权限系统** | JWT 认证 + 三级角色（user / auditor / admin）权限管理 |
| **管理后台** | 统计仪表盘、用户管理、检测记录查询、误判反馈集成 |
| **误判反馈** | 用户提交误判样本，管理员一键集成到训练数据集 |
| **桌面窗口** | pywebview 桌面端，无需手动打开浏览器 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    AIGI-Holmes 应用                      │
│                                                         │
│   ┌──────────────┐       ┌───────────────────────────┐  │
│   │  PyWebView   │◄─────►│  uvicorn (127.0.0.1:7860) │  │
│   │  桌面窗口    │       │  FastAPI 后端              │  │
│   └──────────────┘       └──────────┬────────────────┘  │
└──────────────────────────────────────┼──────────────────┘
                                       │
               ┌───────────────────────┼─────────────────┐
               │                       │                 │
        ┌──────▼──────┐   ┌────────────▼──────┐   ┌──────▼─────┐
        │  ResNet-50  │   │   CLIP ViT-B/32   │   │  豆包 AI   │
        │  真伪检测   │   │  内容 / 图文分析  │   │  辅助分析  │
        │  Grad-CAM   │   └────────────┬──────┘   └──────┬─────┘
        └──────┬──────┘                │                 │
               └───────────┬───────────┘                 │
                      ┌────▼────┐                        │
                      │ SQLite  │◄───────────────────────┘
                      │ (默认)  │
                      └─────────┘
```

**技术栈一览**

| 层次 | 技术选型 |
|---|---|
| 后端框架 | FastAPI 0.110+ / uvicorn |
| 图像检测 | PyTorch 2.0+ / ResNet-50（微调）/ Grad-CAM |
| 多模态分析 | CLIP ViT-B/32 |
| 数据库 | SQLite（默认）/ PostgreSQL（生产） |
| 缓存 | Redis（可选） |
| 认证 | JWT (python-jose) + bcrypt |
| 报告生成 | reportlab（PDF）/ openpyxl（Excel） |
| AI 分析 | 字节跳动豆包 AI（ARK 平台 SSE） |
| 桌面窗口 | pywebview + Microsoft Edge WebView2 |
| 打包 | PyInstaller + Inno Setup 6 |

---

## 🚀 快速开始

### 方式一：安装包（推荐，无需 Python）

> 适合普通用户、记者、内容审核人员

1. 前往 [Releases](https://github.com/axfly00q/AIGI-Holmes/releases) 下载最新 `AIGI-Holmes-Setup.exe`
2. 双击运行安装向导（默认安装到 `C:\Program Files\AIGI-Holmes\`）
3. 点击桌面快捷方式启动程序

**系统要求：**
- Windows 10 1809 (Build 17763) 及以上
- Microsoft Edge WebView2（Windows 10/11 通常已内置）
- 首次启动需 10～20 秒加载模型

---

### 方式二：源码运行（开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/axfly00q/AIGI-Holmes.git
cd AIGI-Holmes

# 2. 创建虚拟环境（推荐 Python 3.10）
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate    # Linux/macOS

# 3. 安装依赖
pip install -r requirements-app.txt

# 4. 配置环境变量
copy .env.example .env
# 按需编辑 .env（默认 SQLite，开箱即用）

# 5. 启动服务
uvicorn backend.main:app --host 127.0.0.1 --port 7860 --reload

# 访问：http://127.0.0.1:7860
```

---

### 方式三：桌面窗口模式

```bash
pip install pywebview
python desktop_launcher.py
```

---

### 方式四：Docker 部署

```bash
# 启动（含 PostgreSQL + Redis）
docker compose up -d

# 访问：http://localhost:7860
```

---

## 📋 使用说明

### 图片检测

| 操作 | 步骤 |
|---|---|
| **单张检测** | 拖拽图片到检测区域，或点击「上传图片」，点击「开始检测」 |
| **URL 检测** | 粘贴新闻页面 URL，系统自动抓取页面内所有图片并检测 |
| **批量检测** | 需 auditor 权限；点击「批量上传」选择多张图片，实时查看进度 |

### 检测结果说明

| 指标 | 含义 |
|---|---|
| 判定结果 | `AI生成` / `真实照片` |
| 置信度 | 模型对当前判定的把握程度（0～100%） |
| 热力图 | Grad-CAM 可视化，高亮显示影响判定的图像区域 |
| 内容标签 | CLIP 零样本分类结果（如：人物、新闻现场） |
| 图文一致性 | 图片与配文的语义匹配度评分 |
| AI 分析 | 豆包 AI 对检测结果的自然语言解读 |

### 账号与权限

| 角色 | 获取方式 | 功能 |
|---|---|---|
| `user` | 自助注册 | 单图检测、URL 检测、查看记录 |
| `auditor` | 管理员分配 | 以上全部 + 批量检测、导出报告 |
| `admin` | 初始配置 | 以上全部 + 用户管理、系统统计、反馈集成 |

> 单图检测与 URL 检测支持匿名使用，无需注册账号。

---

## 📡 API 文档

启动服务后访问：

- **Swagger UI**：[http://127.0.0.1:7860/docs](http://127.0.0.1:7860/docs)
- **ReDoc**：[http://127.0.0.1:7860/redoc](http://127.0.0.1:7860/redoc)

**主要接口**

```
POST  /api/detect                  # 单图检测
POST  /api/detect-url              # URL 页面图片检测
POST  /api/detect-batch            # 多图批量检测（同步）
POST  /api/detect-batch-init       # 创建批量任务（异步）
GET   /api/detection/{id}/analyze  # 豆包 AI 分析（SSE 流式）
GET   /api/report/{id}/export      # 导出 PDF / Excel 报告
POST  /api/auth/register           # 用户注册
POST  /api/auth/login              # 用户登录
WS    /ws/detect/{job_id}          # 批量检测进度推送
```

---

## 📦 部署与打包

> 需要 Python 3.10+、PyInstaller、Inno Setup 6

```bash
# 打包可执行文件
pip install pyinstaller
pyinstaller AIGI_Holmes.spec

# 编译 Windows 安装包（需已安装 Inno Setup 6）
iscc installer.iss
# 输出：dist\AIGI-Holmes-Setup.exe
```

详细说明见 [docs/packaging.md](docs/packaging.md)。

---

## 🗂️ 项目结构

```
AIGI-Holmes/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口，注册所有路由
│   ├── config.py               # 配置管理（读取 .env）
│   ├── auth.py                 # JWT 认证工具
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── routers/                # API 路由（detect/auth/report/admin）
│   ├── report/                 # PDF / Excel 报告生成
│   └── llm/                    # 豆包 AI 客户端
├── static/
│   ├── css/style.css           # 全局样式
│   └── js/app.js               # 前端交互逻辑
├── templates/
│   ├── index.html              # 检测主页
│   └── admin.html              # 管理后台
├── CLIP/                       # CLIP 模型代码
├── detect.py                   # 核心检测逻辑（ResNet-50 推理）
├── desktop_launcher.py         # 桌面应用启动器
├── finetuned_fake_real_resnet50.pth  # 微调模型权重（必需）
├── AIGI_Holmes.spec            # PyInstaller 打包配置
├── installer.iss               # Inno Setup 安装脚本
├── docker-compose.yml          # Docker 编排
├── requirements-app.txt        # 运行依赖
└── .env.example                # 环境变量示例
```

---

## ❓ 常见问题

| 现象 | 原因 | 解决方法 |
|---|---|---|
| 启动后白屏 | WebView2 未安装 | 下载 [Edge WebView2 运行时](https://developer.microsoft.com/zh-cn/microsoft-edge/webview2/) |
| 启动超时（>60s） | 模型文件缺失 | 确认 `finetuned_fake_real_resnet50.pth` 在程序目录 |
| 检测结果报错 | `.env` 配置缺失 | 检查 `MODEL_PATH` 配置是否正确 |
| 无法写入数据库 | 权限不足 | 以管理员身份运行，或检查安装目录写入权限 |
| AI 分析不可用 | API Key 未配置 | 在 `.env` 填写 `DOUBAO_API_KEY` |

更多问题见 [USAGE.md](USAGE.md)。

---

## 🧪 开发与测试

```bash
# 代码格式化
pip install ruff && ruff format .

# 基础连通性测试
python _smoke_test.py

# 接口集成测试
python _integration_test.py

# 认证流程测试
python _smoke_test_auth.py
```

---

## 🙏 致谢

- [ResNet](https://arxiv.org/abs/1512.03385) — 图像特征提取骨干网络
- [CLIP](https://github.com/openai/CLIP) — 多模态图文理解模型
- [FastAPI](https://fastapi.tiangolo.com) — 高性能 Python Web 框架
- [pywebview](https://pywebview.app) — Python 桌面 WebView 库
- 字节跳动 [豆包 AI](https://www.volcengine.com/product/ark) — 自然语言分析能力

---

<div align="center">

Made with ❤️ for News Media Fact-Checking

[⭐ Star this repo](https://github.com/axfly00q/AIGI-Holmes) · [🐛 Report Bug](https://github.com/axfly00q/AIGI-Holmes/issues) · [💡 Request Feature](https://github.com/axfly00q/AIGI-Holmes/issues)

</div>
