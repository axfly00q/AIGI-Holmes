' AIGI-Holmes 隐藏启动器
' 作用：隐藏黑色命令窗口，直接启动应用
' 使用方式：双击此文件

Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

' 获取脚本所在目录
Dim scriptPath
scriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' 隐藏窗口执行 bat 文件
Dim command
command = "cmd.exe /c """ & scriptPath & "\AIGI-Holmes-Start.bat"""

WshShell.Run command, 0, False

' 等待 3 秒后弹出提示
WScript.Sleep 3000

Dim objShell
Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute "cmd.exe", "/c echo. && echo ✅ AIGI-Holmes 已启动！ && echo 请稍候，浏览器即将打开... && timeout /t 2", , "open", 1
