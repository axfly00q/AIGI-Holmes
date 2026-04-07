# AIGI-Holmes 打包脚本
# 作用：一键完成清理、提交、打包、上传
# 使用：在项目根目录运行 .\package-and-release.ps1

param(
    [string]$GitToken = "",
    [string]$GitUsername = "",
    [string]$Version = "2.0.0"
)

$ErrorActionPreference = "Stop"

function Write-Title {
    param([string]$text)
    Write-Host ""
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║ $text" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
}

function Write-Status {
    param([string]$text, [string]$status = "info")
    $color = @{
        "success" = "Green"
        "warning" = "Yellow"
        "error"   = "Red"
        "info"    = "Cyan"
    }[$status]
    Write-Host $text -ForegroundColor $color
}

# ========== 第一步：清理项目 ==========
Write-Title "第 1 步：清理项目编译产物"

$cleanItems = @(
    "build", "dist", "__pycache__", ".pytest_cache", 
    "venv", "*.log", "*.db", "*.tmp"
)

foreach ($item in $cleanItems) {
    Get-ChildItem -Path $item -ErrorAction SilentlyContinue | 
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

Get-ChildItem -Path "**/__pycache__" -Directory -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Status "✅ 项目已清理" "success"

# ========== 第二步：验证必要文件 ==========
Write-Title "第 2 步：验证必要文件"

$requiredFiles = @(
    "AIGI-Holmes-Start.vbs",
    "docker-compose.yml",
    "Dockerfile",
    ".env",
    "backend",
    "templates",
    "static",
    "detect.py"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Status "  ✓ $file" "success"
    } else {
        Write-Status "  ✗ 缺少 $file" "error"
        exit 1
    }
}

# ========== 第三步：创建分发包 ==========
Write-Title "第 3 步：打包分发文件"

$distDir = "AIGI-Holmes-v$Version-Distribution"
$zipFile = "AIGI-Holmes-v$Version-Windows.zip"

# 删除旧分发包
Remove-Item -Path $distDir, $zipFile -Recurse -Force -ErrorAction SilentlyContinue

# 创建新分发包
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

$itemsToCopy = @(
    "AIGI-Holmes-Start.vbs",
    "AIGI-Holmes-Start.bat",
    "start-aigi.ps1",
    "docker-compose.yml",
    "Dockerfile",
    ".dockerignore",
    ".env",
    "快速启动指南.txt",
    "README.md",
    "requirements-app.txt",
    "backend",
    "templates",
    "static",
    "CLIP",
    "detect.py",
    "detect_text.py",
    "finetuned_fake_real_resnet50.pth"
)

Write-Status "  正在复制文件..." "info"
foreach ($item in $itemsToCopy) {
    if (Test-Path $item -PathType Container) {
        Copy-Item -Path $item -Destination "$distDir\" -Recurse -Force -ErrorAction SilentlyContinue
    } elseif (Test-Path $item -PathType Leaf) {
        Copy-Item -Path $item -Destination "$distDir\" -Force -ErrorAction SilentlyContinue
    }
}

# 打包为 Zip
Write-Status "  正在压缩文件..." "info"
Compress-Archive -Path $distDir -DestinationPath $zipFile -Force

$size = [Math]::Round((Get-Item $zipFile).Length / 1MB, 2)
Write-Status "✅ 分发包已创建：$zipFile ($size MB)" "success"

# ========== 第四步：Git 提交 ==========
Write-Title "第 4 步：Git 提交代码"

if (-not (Test-Path ".git")) {
    Write-Status "  初始化 Git 仓库..." "info"
    git init
    git config user.name "AIGI-Holmes Bot"
    git config user.email "noreply@aigi-holmes.local"
}

Write-Status "  添加文件..." "info"
git add .

Write-Status "  提交代码..." "info"
git commit -m "chore(release): v$Version - Docker 完整版本

- 完全容器化方案
- 一键启动脚本
- 优化依赖

分发包：AIGI-Holmes-v$Version-Windows.zip" ^
    -ErrorAction SilentlyContinue

Write-Status "✅ Git 提交完成" "success"

# ========== 第五步：显示下一步说明 ==========
Write-Title "✅ 打包完成！"

Write-Host ""
Write-Status "📦 分发包已生成：$zipFile ($size MB)" "success"
Write-Host ""
Write-Host "📋 下一步操作：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1️⃣  推送到 GitHub（如果还没有）："
Write-Host "    git remote add origin git@github.com:YourUsername/AIGI-Holmes.git"
Write-Host "    git branch -M main"
Write-Host "    git push -u origin main"
Write-Host ""
Write-Host "2️⃣  创建 Release（手动）："
Write-Host "    访问：https://github.com/YourUsername/AIGI-Holmes/releases"
Write-Host "    点击 'Create a new release'"
Write-Host "    上传文件：$zipFile"
Write-Host ""
Write-Host "3️⃣  或使用 GitHub CLI 自动创建（如果已安装）："
Write-Host "    gh release create v$Version '$zipFile' --title 'AIGI-Holmes v$Version' --notes-file RELEASE_NOTES.md"
Write-Host ""

# ========== 可选：创建 Release notes 模板 ==========
$releaseNotesFile = "RELEASE_NOTES.md"
if (-not (Test-Path $releaseNotesFile)) {
    $releaseNotes = @"
# AIGI-Holmes v$Version 发布

## ✨ 新特性

- ✅ 完整的 Docker 容器化方案
- ✅ 一键安装启动器（自动检测 Docker）
- ✅ 支持 PostgreSQL + Redis 完整配置

## 🚀 快速开始

1. 解压 `AIGI-Holmes-v$Version-Windows.zip`
2. 双击 `AIGI-Holmes-Start.vbs`
3. 等待 15-30 秒，自动打开浏览器

## 📖 详细说明

参考 `快速启动指南.txt`

## 🔧 技术栈

- FastAPI + SQLAlchemy
- PostgreSQL + Redis
- PyTorch + CLIP + ResNet50
- Docker + Docker Compose

## ❓ 常见问题

**Q: 首次为什么这么慢？**
A: 首次需要下载 Docker 镜像（~2.5GB），预计 5-10 分钟。后续只需 15-30 秒。

**Q: 可以离线使用吗？**
A: 可以！启动后完全离线运行。

## 📞 反馈

发现问题？提交 Issue：https://github.com/YourUsername/AIGI-Holmes/issues
"@
    Set-Content -Path $releaseNotesFile -Value $releaseNotes -Encoding UTF8
    Write-Status "✅ 已创建 Release Notes 模板：$releaseNotesFile" "success"
}

Write-Host ""
Write-Host "═════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "打包完成！分发包已准备好，可以发送给用户了！" -ForegroundColor Green
Write-Host ""
