@echo off
chcp 65001 > nul
cd /d "%~dp0"

:: 检测 Python 命令
set PYTHON=
where python > nul 2>&1 && python --version > nul 2>&1 && set PYTHON=python
if not defined PYTHON (
    where python3 > nul 2>&1 && python3 --version > nul 2>&1 && set PYTHON=python3
)
if not defined PYTHON (
    where py > nul 2>&1 && py --version > nul 2>&1 && set PYTHON=py
)
if not defined PYTHON (
    echo.
    echo [错误] 未找到 Python。
    echo 请先安装 Python：https://www.python.org/downloads/
    echo 安装时勾选 "Add Python to PATH"。
    echo.
    pause
    exit /b 1
)

:: 杀旧进程（占用 8766 端口）
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8766 "') do taskkill /F /PID %%a > nul 2>&1

:: 后台启动服务器
start "" /B %PYTHON% tools\serve_editor.py --port 8766

:: 等待服务器就绪
timeout /t 3 /nobreak > nul

:: 打开浏览器
start "" "http://127.0.0.1:8766/editor/editor.html"

echo.
echo ✓ Level Design Deck 已启动
echo   编辑器：http://127.0.0.1:8766/editor/editor.html
echo.
echo 提示：关闭此窗口不会停止服务器（后台运行）
echo 停止服务器：任务管理器 → 结束 python/python3 进程
echo.
pause
