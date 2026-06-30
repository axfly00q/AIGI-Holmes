AIGI-Holmes docs/ 文档目录
==========================

【文件夹作用】
本目录包含 AIGI-Holmes 系统的技术文档，供开发人员参考，涵盖桌面运行指南和打包发布流程。

【各文件说明】

  desktop-windows.md        Windows 桌面运行指南
                            说明如何以桌面窗口模式（无需浏览器）运行 AIGI-Holmes，
                            包括依赖安装、启动步骤和常见问题排查。

  packaging.md              打包与发布指南
                            完整说明如何将项目打包为独立 Windows 安装程序的两步流程：
                            1. 使用 PyInstaller 生成可执行文件目录
                            2. 使用 Inno Setup 编译 .exe 安装包
                            包含前提条件、命令示例和故障排查表。

  make.bat                  Windows 文档构建辅助脚本
