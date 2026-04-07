# ✅ AIGI-Holmes 最终完整指南

## 🎯 三种方式使用 AIGI-Holmes

根据你的需求选择一种方式：

---

## 方式 1️⃣：最快 - 直接运行源代码（推荐✨）

**用这个方式最快**（3 分钟内启动应用）

### 步骤：

```bash
# 1. 进入项目目录
cd d:\aigi修改\AIGI-Holmes-main

# 2. 创建虚拟环境（可选但推荐）
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements-app.txt

# 4. 启动应用
python desktop_launcher.py
```

### 结果：
- ✅ 10-20 秒后自动打开窗口
- ✅ 或提示用浏览器访问 `http://127.0.0.1:7860`
- ✅ **所有功能立即可用**

### 优点：
- 🚀 最快启动
- 📝 可直接看到日志和错误信息
- 🔧 方便开发调试
- ✨ **最推荐**

### 缺点：
- 需要 Python 环境
- 需要安装依赖

---

## 方式 2️⃣：生成 Windows EXE（分发给他人）

**用这个方式生成可分发的 EXE**

### 步骤：

```bash
# 1. 进入项目目录
cd d:\aigi修改\AIGI-Holmes-main

# 2. 一键打包
python build_standalone.py
```

或手动：
```bash
python -m PyInstaller AIGI_Holmes.spec -y
```

### 结果：
- ✅ 生成 `dist/AIGI-Holmes/` 文件夹（~846 MB）
- ✅ 包含 `AIGI-Holmes.exe`
- ✅ 所有依赖都已包含

### 使用方式：
```
双击 → dist\AIGI-Holmes\AIGI-Holmes.exe
```

### 优点：
- ✅ 无需 Python 环境
- ✅ 可分发给他人
- ✅ 开箱即用

### 缺点：
- ⏱️ 首次打包需 5-10 分钟
- 💾 文件较大（~846 MB）

---

## 方式 3️⃣：生成 Windows 安装程序

**用这个方式创建正式的安装包**

### 前置条件：
- 需要安装 Inno Setup 6
  下载：https://jrsoftware.org/isdl.php

### 步骤：

```bash
# 1. 先生成 EXE（如果还没有）
python build_standalone.py

# 2. 生成安装程序
iscc installer.iss
```

### 结果：
- ✅ 生成 `dist/AIGI-Holmes-Setup.exe`
- ✅ 标准 Windows 安装流程
- ✅ 自动创建桌面快捷方式

### 使用方式：
```
双击 → dist\AIGI-Holmes-Setup.exe → 按步骤安装
```

### 优点：
- 📦 正式安装包
- 🎀 包含快捷方式
- 🗑️ 支持卸载

### 缺点：
- 需要 Inno Setup
- 文件仍然较大

---

## 🚀 立即开始（推荐方式 1）

**最快的方式 - 直接运行**：

```bash
cd d:\aigi修改\AIGI-Holmes-main
python desktop_launcher.py
```

然后：
1. 等待 10-20 秒
2. 自动打开窗口或浏览器
3. 上传图片开始检测
4. 🎉 完成！

---

## ✨ 所有功能都可用

无论选择哪种方式，你都能获得**完整的功能**：

✅ **检测功能**
- 单张和批量图片检测
- URL 采集检测
- 图文一致性分析
- Grad-CAM 热力图

✅ **用户功能**
- 用户注册和登录
- 用户权限管理
- 检测记录存储
- 反馈管理

✅ **高级功能**
- AI 多轮分析（豆包 AI）
- 报告导出（PDF/Excel）
- 管理后台
- 完整的 REST API

✅ **技术功能**
- SQLite/PostgreSQL 数据库
- Redis 缓存
- JWT 认证
- WebSocket 实时推送

---

## 🎯 快速对比

| 特性 | 方式1<br>源码运行 | 方式2<br>EXE | 方式3<br>安装包 |
|-----|-----------------|-----------|-------------|
| 启动时间 | 3 分钟 | 5-10 分钟¹ | 5-10 分钟¹ |
| 运行速度 | 快 | 快 | 快 |
| 所需依赖 | Python 3.9+ | 无 | 无 |
| 文件大小 | 小 | 846 MB | 846 MB |
| 易用性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 可分发性 | ❌ | ✅ | ✅ |
| 推荐度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

¹ 仅需第一次打包，后续直接使用

---

## 📖 获取帮助

如遇到问题，查看以下文件：

| 文件 | 内容 |
|-----|-----|
| `INSTALLATION_GUIDE.md` | 📦 安装和使用详细步骤 |
| `QUICK_START.md` | ⚡ 快速开始指南 |
| `USAGE.md` | 📚 完整功能说明 |
| `FIX_REPORT.md` | 🔧 技术修复说明 |
| `readme.txt` | 📋 文件夹结构说明 |
| `README.md` | 📖 项目总体说明 |

启动后访问 `/docs` 查看 API 文档

---

## 🎉 现在就开始吧！

### 最快方式（推荐）：

```bash
# 3 步启动应用
cd d:\aigi修改\AIGI-Holmes-main
python desktop_launcher.py

# 然后浏览器访问或等待窗口打开
# http://127.0.0.1:7860
```

### 或如果要生成 EXE：

```bash
# 一键打包（首次需 5-10 分钟）
python build_standalone.py

# 后续直接使用
dist\AIGI-Holmes\AIGI-Holmes.exe
```

---

**祝使用愉快！** 🚀
