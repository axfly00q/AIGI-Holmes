# AIGI-Holmes 使用教程

## 目录
1. [快速开始](#快速开始)
2. [安装方式](#安装方式)
3. [功能说明](#功能说明)
4. [常见问题](#常见问题)

---

## 快速开始

### 方式一：直接运行（最简单）

1. **解压程序包**
   - 将 `dist/AIGI-Holmes/` 文件夹复制到任意位置
   - 或双击 `AIGI-Holmes-Setup.exe` 安装程序

2. **启动程序**
   - 双击 `AIGI-Holmes.exe`
   - 等待 10-20 秒，程序自动打开桌面窗口

3. **开始使用**
   - 上传图片进行 AI 生成检测
   - 支持单张上传、批量上传、URL 采集等模式

---

## 安装方式

### 方式 1️⃣：绿色版（无需安装）

**优点**：即解即用，无需安装依赖

**步骤**：
```
1. 将 dist/AIGI-Holmes/ 复制到本地
2. 双击 AIGI-Holmes.exe
3. 完成！
```

**文件说明**：
```
dist/AIGI-Holmes/
├── AIGI-Holmes.exe          ← 主程序
├── python.exe               ← Python 运行环境
├── _internal/               ← 依赖库和模型
│   ├── torch/               ← PyTorch（检测引擎）
│   ├── torchvision/         ← 视觉模型库
│   ├── backend/             ← FastAPI 后端代码
│   └── ...
├── finetuned_fake_real_resnet50.pth  ← AI 检测模型（80 MB）
└── templates/               ← Web 前端模板
```

---

### 方式 2️⃣：安装程序（推荐）

**优点**：标准 Windows 安装向导，自动创建快捷方式，支持卸载

**步骤**：
```
1. 双击 AIGI-Holmes-Setup.exe
2. 按照安装向导选择安装路径
3. 完成安装，桌面/开始菜单出现快捷方式
4. 点击快捷方式启动程序
```

**安装特性**：
- ✅ 自动检测 Windows 版本（10/11）
- ✅ 自动安装 WebView2 运行时（首次启动）
- ✅ 支持 Add/Remove Programs 卸载
- ✅ 快捷方式自动创建

---

### 方式 3️⃣：源代码运行（开发者）

**适用场景**：需要修改源代码或进行二次开发

**前置要求**：
- Python 3.9+
- CUDA 11.8（推荐，用于 GPU 加速）或 CPU 模式

**安装步骤**：

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd AIGI-Holmes-main
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   # 或
   source venv/bin/activate       # Linux/macOS
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements-app.txt
   ```

4. **启动程序**

   **选项 A：桌面窗口模式**（推荐）
   ```bash
   python desktop_launcher.py
   ```

   **选项 B：Web 浏览器模式**
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 7860 --reload
   ```
   然后在浏览器打开：`http://127.0.0.1:7860`

---

## 功能说明

### 核心功能

#### 1. 单张图片检测
- **路径**：首页"上传检测"
- **输入**：单张 JPG/PNG 图片（<500MB）
- **输出**：
  - 🔴 **FAKE**（AI 生成图片）/ 🟢 **REAL**（真实图片）
  - 置信度百分比
  - Grad-CAM 热力图（标记 AI 生成迹象）
  - 图片内容分类（人物/动物/建筑等）

#### 2. 批量检测
- **路径**：管理员后台 → "批量检测"
- **输入**：多张图片（ZIP 或单个文件夹）
- **输出**：实时进度 + 检测报告
- **特性**：
  - 异步处理，支持 WebSocket 实时推送
  - 可导出为 PDF 或 Excel 报告

#### 3. URL 采集
- **路径**：首页"URL 检测"
- **输入**：新闻页面 URL
- **功能**：
  - 自动爬取页面所有图片
  - 图文一致性检测（检查图片与标题是否匹配）
  - 批量检测图片真伪
- **应用场景**：快速检测新闻媒体真假稿

#### 4. AI 多轮分析
- **路径**：检测结果 → "AI 分析"
- **功能**：
  - 豆包 AI 流式分析检测结果
  - 支持多轮对话追问
  - 解释 AI 为何判定该图为生成/真实

#### 5. 报告导出
- **路径**：检测记录 → "生成报告"
- **支持格式**：
  - 📄 **PDF**（含水印、中文字体适配）
  - 📊 **Excel**（含颜色编码的判定行）
- **包含内容**：
  - 检测结论 + 置信度
  - 概率分布图表
  - 图片缩略图
  - 建议意见

#### 6. 用户反馈
- **路径**：检测结果 → "反馈纠正"
- **功能**：
  - 报告模型误判（FAKE 被判 REAL 或反之）
  - 管理员批准后自动集成到训练数据
  - 持续迭代改进模型精度

---

### 用户角色

| 角色 | 权限 | 适用场景 |
|-----|-----|---------|
| **游客** | ✅ 单张检测、URL 检测、查看分析 | 快速验证图片真伪 |
| **注册用户** | ✅ 所有游客权限 + ✅ 反馈纠正、查看历史 | 专业检测人员 |
| **审核员** | ✅ 所有权限 + ✅ 批量检测 | 媒体审核团队 |
| **管理员** | ✅ 所有权限 + ✅ 用户管理、数据统计、集成反馈 | 系统维护人员 |

---

## 常见问题

### Q1：程序无法启动，提示找不到 Python

**原因**：EXE 丢失 `_internal/` 文件夹或环境变量损坏

**解决方案**：
1. 重新解压 `dist/AIGI-Holmes/` 完整文件夹
2. 运行安装程序 `AIGI-Holmes-Setup.exe`
3. 确保 `_internal/` 文件夹存在

---

### Q2：启动后卡在"等待服务器启动"

**原因**：
- 端口 7860 已被占用
- torch/torchvision 加载时间过长（GPU 初始化）
- 第一次启动需要加载模型权重，耗时较长

**解决方案**：
```bash
# 检查端口占用
netstat -ano | findstr :7860

# 杀死占用进程
taskkill /PID <PID> /F

# 重启程序
```

或修改 `desktop_launcher.py` 中的 `PORT` 和 `STARTUP_TIMEOUT`：
```python
PORT = 8080                    # 改为其他端口
STARTUP_TIMEOUT = 120          # 增加超时时间到 120 秒
```

---

### Q3：检测速度很慢

**原因**：未使用 GPU 加速，仅用 CPU 运行

**解决方案**：
- 安装 **CUDA 11.8** + **cuDNN 8.7**
- 或升级到支持更新 PyTorch 版本的 GPU（需要重新打包）

---

### Q4：怎样修改为 FastAPI 的完整功能？

**已支持所有 FastAPI 功能**，包括：
- ✅ JWT 用户认证
- ✅ 数据库存储检测记录
- ✅ Redis 缓存优化
- ✅ WebSocket 实时推送进度
- ✅ SQL 管理后台

**访问方式**：
- 在浏览器打开 `http://127.0.0.1:7860`
- 登录后进入管理后台
- 或 API 客户端访问 `http://127.0.0.1:7860/api/`

---

### Q5：怎样在 Linux/Mac 上运行？

**不支持**：当前仅提供 Windows EXE

**替代方案**：从源代码运行
```bash
# Linux/Mac
python desktop_launcher.py

# 或使用 uvicorn（开发模式）
uvicorn backend.main:app --host 0.0.0.0 --port 7860 --reload
```

---

### Q6：能不能部署到服务器？

**可以**，两种方案：

**方案 A：纯 API 模式**（推荐）
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 7860
# 然后用您自己的前端（React/Vue/Angular）调用 API
```

**方案 B：Docker 容器**
```bash
docker build -t aigi-holmes .
docker run -p 7860:7860 aigi-holmes
```

参考 `Dockerfile` 和 `docker-compose.yml`

---

### Q7：检测结果准确率是多少？

- **假图검测准确率**：~95%（ResNet50 微调模型）
- **真图误判率**：~5%
- **模型版本**：finetuned_fake_real_resnet50.pth

**影响因素**：
- 图片质量（高质量图检测准确率更高）
- AI 生成工具版本（全新工具生成的图可能准确率略低）
- 图片尺寸（建议 256x256 以上）

---

## 获取帮助

- 📖 **查看 API 文档**：启动后访问 `http://127.0.0.1:7860/docs`
- 🐛 **提交 issue**：GitHub Issues
- 💬 **讨论功能**：GitHub Discussions

---

## 许可证

MIT License - 详见 LICENSE 文件
