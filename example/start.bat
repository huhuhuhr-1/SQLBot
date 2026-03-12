@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >nul 2>nul
if %errorlevel% neq 0 (
  echo 未检测到 Node.js，请先安装: https://nodejs.org/
  pause
  exit /b 1
)
if not defined PORT set PORT=3000
echo.
echo  启动示例服务 (端口: %PORT%)
echo  启动后请将 SQLBot 小助手跨域设置包含: http://localhost:%PORT%
echo.
node server.js
pause
