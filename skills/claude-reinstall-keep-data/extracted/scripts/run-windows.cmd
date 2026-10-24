@echo off
chcp 65001 >nul
rem Windows 双击入口：运行卸载重装脚本
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo 未找到 node，请先安装 Node.js（https://nodejs.org）后重试。
  pause
  exit /b 1
)
node "%~dp0claude-reinstall.mjs" %*
echo.
pause
