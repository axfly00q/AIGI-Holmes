# AIGI-Holmes macOS 快速启动指南

适用于 macOS 用户。当前项目的 `快速启动指南.txt` 主要面向 Windows 的 `.vbs` / `.bat` / PowerShell 启动方式；在 Mac 上建议使用下面的“源码启动”或“Docker 启动”。

## 方式一：源码启动（推荐开发调试）

### 1. 进入项目目录

```bash
cd /Users/axfly/AIGI-Holmes
```

### 2. 启用已有虚拟环境

```bash
source venv/bin/activate
```

如果本机没有 `venv`，可以重新创建：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-app.txt
```

### 3. 可选：创建环境变量文件

项目没有 `.env` 也能本地启动；如果要配置密钥或第三方 API，可以执行：

```bash
cp .env.example .env
```

然后按需编辑 `.env`：

- `SECRET_KEY`：建议填一个随机字符串，避免重启后登录状态全部失效。
- `ADMIN_ROLE_PASSWORD`：需要使用角色管理功能时填写。
- `DOUBAO_API_KEY` / `SERPER_API_KEY`：需要豆包分析或搜索能力时填写。

### 4. 启动服务

```bash
python run_server.py
```

看到类似下面的输出，说明启动成功：

```text
Uvicorn running on http://0.0.0.0:7860
```

### 5. 打开应用

浏览器访问：

```text
http://127.0.0.1:7860/app
```

API 文档：

```text
http://127.0.0.1:7860/docs
```

### 6. 停止服务

在启动服务的终端按：

```text
Control + C
```

## 方式二：Docker 启动

适合希望一次性启动 App、PostgreSQL、Redis 的用户。

### 1. 安装并启动 Docker Desktop

确认 Docker 可用：

```bash
docker --version
docker compose version
```

### 2. 进入项目目录

```bash
cd /Users/axfly/AIGI-Holmes
```

### 3. 准备 `.env`

Docker Compose 文件引用了 `.env`，建议先创建：

```bash
cp .env.example .env
```

### 4. 启动服务

```bash
docker compose up -d
```

查看日志：

```bash
docker compose logs -f app
```

访问应用：

```text
http://127.0.0.1:7860/app
```

停止服务：

```bash
docker compose down
```

## 常见问题

### 端口 7860 被占用

查看占用：

```bash
lsof -iTCP:7860 -sTCP:LISTEN
```

如果只是想换端口，可以用：

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 7861
```

然后访问：

```text
http://127.0.0.1:7861/app
```

### 启动时提示 SECRET_KEY 或 ADMIN_ROLE_PASSWORD 未配置

这是安全提醒，不影响本地普通使用。需要登录稳定性或管理功能时，在 `.env` 里补上：

```text
SECRET_KEY=替换成一段随机字符串
ADMIN_ROLE_PASSWORD=替换成管理员角色密码
```

### CLIP 或文本模型下载失败

应用主页面仍可启动，但相关 AI 模型能力可能降级。通常是网络连接到模型源不稳定导致，可以稍后重启服务，或提前配置可用的模型缓存。

### Mac 上不要运行哪些文件

这些文件是 Windows 启动入口，Mac 上不需要运行：

- `AIGI-Holmes-Start.vbs`
- `AIGI-Holmes-Start.bat`
- `start-aigi.ps1`

