@echo off
REM AIGI-Holmes 启动器
REM 支持第一次安装 Docker，后续直接启动应用

setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1

title AIGI-Holmes 启动器

REM 检查 PowerShell 版本
powershell -Command "Exit" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ 错误：PowerShell 不可用
    pause
    exit /b 1
)

REM 执行启动脚本（绕过执行策略）
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-aigi.ps1"
