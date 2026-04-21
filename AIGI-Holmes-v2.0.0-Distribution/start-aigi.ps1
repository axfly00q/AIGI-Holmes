# AIGI-Holmes 智能启动器
# 功能：自动检测 Docker、初始化、启动应用、创建快捷方式

param([switch]$IsFirstRun = $false)

# 设置编码
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8

$ErrorActionPreference = "Continue"

# ========== 配置 ==========
$appName = "AIGI-Holmes"
$appVersion = "2.0.0"
$port = 7860
$appUrl = "http://localhost:7860"
$logFile = "$env:TEMP\aigi-holmes-start.log"

# 颜色定义
$colors = @{
    "success" = "Green"
    "error"   = "Red"
    "warning" = "Yellow"
    "info"    = "Cyan"
}

function Write-Log {
    param([string]$message, [string]$level = "info")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$timestamp] [$level] $message"
    Add-Content -Path $logFile -Value $logMsg -Encoding UTF8
    Write-Host $message -ForegroundColor $colors[$level]
}

function Show-Header {
    Clear-Host
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  $appName v$appVersion 启动器          ║" -ForegroundColor Cyan
    Write-Host "║  点击即安装，双击即启动            ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Check-Docker {
    Write-Host "[1/4] 检查 Docker 环境..." -ForegroundColor Yellow
    
    try {
        $dockerVer = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "✅ Docker 已安装: $dockerVer" "success"
            Write-Host "✅ Docker 已安装: $dockerVer" -ForegroundColor Green
            return $true
        }
    } catch {}
    
    Write-Log "❌ Docker 未安装" "warning"
    Write-Host "❌ Docker 未安装" -ForegroundColor Red
    
    Write-Host ""
    Write-Host "请选择："
    Write-Host "  [1] 自动打开 Docker 下载页面（1分钟快速安装）"
    Write-Host "  [2] 退出（稍后手动安装）"
    Write-Host ""
    
    $choice = Read-Host "请输入选择 (1 或 2)"
    
    if ($choice -eq '1') {
        Write-Host "🌐 正在打开下载页面..." -ForegroundColor Cyan
        Start-Process "https://www.docker.com/products/docker-desktop"
        Write-Host ""
        Write-Host "✅ 请安装 Docker Desktop，安装完成后再次运行此脚本"
        Write-Host ""
        Read-Host "按 Enter 键退出"
        exit 0
    } else {
        exit 0
    }
}

function Check-ProjectFiles {
    Write-Host "[2/4] 检查项目文件..." -ForegroundColor Yellow
    
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $requiredFiles = @(
        "docker-compose.yml",
        ".env",
        "Dockerfile"
    )
    
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $scriptDir $file
        if (-not (Test-Path $filePath)) {
            Write-Log "❌ 缺少文件: $file" "error"
            Write-Host "❌ 缺少文件: $file" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Log "✅ 所有文件已就绪" "success"
    Write-Host "✅ 所有文件已就绪" -ForegroundColor Green
}

function Start-Services {
    Write-Host "[3/4] 启动服务..." -ForegroundColor Yellow
    
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Push-Location $scriptDir
    
    try {
        # 检查容器是否已运行
        $running = docker-compose ps --quiet app 2>$null
        
        if ($running) {
            Write-Log "⏸️  容器已在运行，跳过启动" "info"
            Write-Host "⏸️  容器已在运行，跳过启动" -ForegroundColor Yellow
        } else {
            Write-Log "🚀 启动容器..." "info"
            Write-Host "🚀 启动容器..." -ForegroundColor Cyan
            
            docker-compose up -d
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "✅ 容器启动成功" "success"
                Write-Host "✅ 容器启动成功" -ForegroundColor Green
                
                Write-Host ""
                Write-Host "⏳ 等待应用初始化（约 15-30 秒）..." -ForegroundColor Yellow
                Start-Sleep -Seconds 10
            } else {
                Write-Log "❌ 容器启动失败" "error"
                Write-Host "❌ 容器启动失败" -ForegroundColor Red
                exit 1
            }
        }
    } finally {
        Pop-Location
    }
}

function Open-Browser {
    Write-Host "[4/4] 打开应用..." -ForegroundColor Yellow
    
    $maxRetries = 30
    $retryCount = 0
    
    while ($retryCount -lt $maxRetries) {
        try {
            $response = Invoke-WebRequest -Uri $appUrl -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Log "✅ 应用已就绪，打开浏览器" "success"
                Write-Host "✅ 应用已就绪，打开浏览器" -ForegroundColor Green
                
                Start-Process $appUrl
                return
            }
        } catch {}
        
        $retryCount++
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }
    
    Write-Log "⚠️  应用启动较慢，请手动打开浏览器访问: $appUrl" "warning"
    Write-Host ""
    Write-Host "⚠️  应用启动较慢，请手动打开浏览器访问: $appUrl" -ForegroundColor Yellow
}

function Create-Shortcut {
    Write-Host ""
    Write-Host "✨ 创建桌面快捷方式..." -ForegroundColor Cyan
    
    try {
        $scriptPath = $MyInvocation.MyCommand.Path
        $shortcutPath = [System.IO.Path]::Combine(
            [System.Environment]::GetFolderPath("Desktop"),
            "$appName.lnk"
        )
        
        $WshShell = New-Object -ComObject WScript.Shell
        $shortcut = $WshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "powershell.exe"
        $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
        $shortcut.WorkingDirectory = Split-Path $scriptPath
        $shortcut.IconLocation = "powershell.exe"
        $shortcut.WindowStyle = 7  # 隐藏窗口
        $shortcut.Save()
        
        Write-Log "✅ 桌面快捷方式已创建" "success"
        Write-Host "✅ 已在桌面创建快捷方式，下次可直接双击启动" -ForegroundColor Green
    } catch {
        Write-Log "⚠️  快捷方式创建失败: $_" "warning"
        Write-Host "⚠️  快捷方式创建失败（跳过）" -ForegroundColor Yellow
    }
}

# ========== 主执行 ==========
Show-Header

Check-Docker
Check-ProjectFiles
Start-Services
Open-Browser
Create-Shortcut

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ 启动完成！" -ForegroundColor Green
Write-Host ""
Write-Host "💡 快速命令："
Write-Host "  • 查看日志：      docker-compose logs -f app"
Write-Host "  • 停止服务：      docker-compose down"
Write-Host "  • 重启应用：      docker-compose restart app"
Write-Host ""
Write-Host "🖥️  应用地址：$appUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Enter 键关闭此窗口" -ForegroundColor Yellow
Read-Host

Write-Log "启动脚本运行完成" "info"
