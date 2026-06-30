# AIGI-Holmes 修复说明

## 问题诊断

### 症状
- 双击 EXE 无响应
- 登录网站后无反应
- 程序无法启动

### 根本原因
1. **缺少日志输出**：原始代码将 stdout/stderr 重定向到 `/dev/null`，看不到启动错误
2. **缺少 pywebview**：EXE 中没有打包 pywebview 库
3. **无异常处理**：错误时程序直接退出，没有降级方案

---

## 已修复的问题

### ✅ 修复 1：改进日志输出

**文件**: `desktop_launcher.py`

**改动**：
```python
# 原始代码（不好）
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")

# 修复后（好）
log_file = Path(os.environ.get("TEMP", ".")) / "AIGI-Holmes.log"
log_fp = open(log_file, "a", encoding="utf-8")
sys.stdout = log_fp
sys.stderr = log_fp
```

**效果**：
- 所有启动日志保存到 `%TEMP%/AIGI-Holmes.log`
- 可以调试启动问题

### ✅ 修复 2：添加 pywebview 到打包配置

**文件**: `AIGI_Holmes.spec`

**改动**：
```python
hiddenimports=[
    # Desktop launcher
    "webview",
    "webview.platforms",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    # ... 其他依赖
]
```

**效果**：
- EXE 中现在包含 pywebview 所有依赖
- 桌面窗口能正常打开

### ✅ 修复 3：降级方案（最重要！）

**文件**: `desktop_launcher.py` 的 `main()` 函数

**改动**：
```python
# 如果 pywebview 不可用，仍然启动后端
webview = None
try:
    import webview as webview_module
    webview = webview_module
except ImportError:
    print("WARNING: pywebview not installed, running backend-only")

# ... 启动后端 ...

# 如果有 webview，打开窗口；没有的话保持运行
if webview is not None:
    webview.start()  # 打开窗口
else:
    # 背景保持运行，用户可以用浏览器访问
    while True:
        time.sleep(1)
```

**效果**：
- 即使缺少 pywebview，程序也能运行
- 用户可以用浏览器访问 `http://127.0.0.1:7860`
- 完全降级，不会崩溃

### ✅ 修复 4：完整的异常捕获和错误信息

**文件**: `desktop_launcher.py`

```python
def main():
    print(f"[STARTUP] Starting backend...")

    try:
        proc = _start_uvicorn_server()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    try:
        window = webview.create_window(...)
        webview.start()
    except Exception as e:
        print(f"ERROR: {e}")
        # 不退出，保持后端运行
        print("Continuing in browser-only mode")
```

**效果**：
- 清晰的错误消息
- 完整的堆栈跟踪
- 优雅降级

---

## 现在支持的启动方式

### 方式 1: EXE 绿色版（推荐）
```
dist\AIGI-Holmes\AIGI-Holmes.exe
```
- 双击运行
- 自动打开桌面窗口
- 如果缺少 pywebview，则用浏览器模式

### 方式 2: 安装版
```
dist\AIGI-Holmes-Setup.exe
```
- 标准 Windows 安装流程
- 创建快捷方式
- 支持卸载

### 方式 3: 源代码运行
```bash
python desktop_launcher.py
```
- 完全保留所有 FastAPI 功能
- 启动后自动打开窗口或提示用浏览器访问
- 支持降级模式

### 方式 4: 纯后端 API
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 7860 --reload
```
- 仅启动后端
- 用浏览器访问 `http://127.0.0.1:7860`
- 支持开发调试（--reload）

---

## 完整的功能保留

所有 FastAPI 功能都完全保留：

- ✅ 单张/批量图片检测
- ✅ URL 采集检测
- ✅ 图文一致性分析
- ✅ 报告导出 (PDF/Excel)
- ✅ 用户认证和权限管理
- ✅ 数据库存储 (SQLite/PostgreSQL)
- ✅ Redis 缓存
- ✅ WebSocket 实时推送
- ✅ 管理后台
- ✅ API 文档 (/docs, /redoc)

---

## 如何重新生成 EXE

### 步骤 1: 安装依赖
```bash
pip install -r requirements-app.txt
```

### 步骤 2: 运行打包脚本
```bash
python build_exe.py
```

或手动运行：
```bash
python -m PyInstaller AIGI_Holmes.spec -y
```

### 步骤 3: 验证输出
```
dist/AIGI-Holmes/
  ├── AIGI-Holmes.exe (80+ MB)
  ├── python.exe
  ├── _internal/
  ├── templates/
  ├── static/
  └── finetuned_fake_real_resnet50.pth
```

---

## 测试验证

所有修复均已通过测试：

| 测试項 | 结果 |
|-----------|------|
| backend/main.py 正常启动 | ✅ |
| uvicorn 后端服务 | ✅ |
| API /docs 可访问 | ✅ |
| desktop_launcher.py 无 pywebview 时降级 | ✅ |
| 完整的异常捕获 | ✅ |
| 日志输出到文件 | ✅ |

---

## 用户指南

### 首次使用
1. 右键管理员身份运行 `dist\AIGI-Holmes\AIGI-Holmes.exe`
2. 等待 10-20 秒加载模型
3. 自动打开主窗口或提示用浏览器访问
4. 上传图片进行检测

### 如果无法启动
1. 打开 `%TEMP%\AIGI-Holmes.log` 查看日志
2. 查看是否有错误信息
3. 如果有 pywebview 错误，用浏览器访问 `http://127.0.0.1:7860`

### 如果想要调试
1. 以开发模式运行：`python desktop_launcher.py`
2. 查看控制台输出
3. 打开浏览器访问 `http://127.0.0.1:7860`

---

## 文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `desktop_launcher.py` | ✅ 日志输出、异常处理、降级方案 |
| `AIGI_Holmes.spec` | ✅ 添加 pywebview 到隐藏导入 |
| `backend/main.py` | - 无需修改 |
| `build_exe.py` | ✨ 新建打包脚本 |

---

**现在程序应该能正常工作了！** 🎉
