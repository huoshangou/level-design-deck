@echo off
chcp 65001 >nul
REM level-design-deck webapp 启动脚本（Windows）
REM 用法：双击此文件，或在 cmd / PowerShell 里 cd 到 webapp\ 后运行 start-webapp.bat
REM 行为对齐 start-webapp.command（mac 版）：端口被占自动 kill 老进程，重新拉起。

setlocal enabledelayedexpansion
cd /d "%~dp0"

set BACKEND_PORT=8766

REM 检查 .venv 是否已建
if not exist "%~dp0.venv\Scripts\uvicorn.exe" (
    echo [ERROR] 缺 .venv\Scripts\uvicorn.exe。请先建 venv 并装依赖：
    echo.
    echo   cd %~dp0
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install --no-index --find-links wheels\ fastapi uvicorn pydantic pydantic-settings python-multipart watchfiles pytest httpx python-dotenv
    echo.
    echo 注意：Windows 不用 uvicorn[standard]（uvloop 不支持 Windows）
    pause
    exit /b 1
)

REM -- 释放端口：占用 %BACKEND_PORT% 的 PID 全部 kill --
REM netstat -ano 输出第 5 列是 PID。findstr ":PORT " 末尾空格避免匹配到 :87660 这种。
echo [INFO] 检查端口 %BACKEND_PORT% 占用情况 ...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr LISTENING') do (
    echo [INFO]   端口 %BACKEND_PORT% 被 PID %%P 占用，kill ...
    taskkill /F /PID %%P >nul 2>&1
)

REM 给 TIME_WAIT 一点缓冲再起
timeout /t 1 /nobreak >nul

echo [INFO] 启动 webapp (port %BACKEND_PORT%) ...

REM 用 start "title" 起一个独立子窗口跑 uvicorn（前台、可见输出、关窗即停 server）。
REM "%~dp0.venv\Scripts\uvicorn.exe" 用绝对路径，避免双击启动时工作目录漂移。
start "level-design-deck webapp" /min cmd /c "cd /d %~dp0 && .venv\Scripts\uvicorn.exe backend.app:app --host 127.0.0.1 --port %BACKEND_PORT%"

echo [INFO] 等待 server 启动（最多 10 秒）...
set /a tries=0
:wait_loop
timeout /t 1 /nobreak >nul
set /a tries+=1
REM Windows 不一定有 curl，用 PowerShell Invoke-WebRequest 做 health check
powershell -NoProfile -Command "try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:%BACKEND_PORT%/api/health' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 goto ready
if %tries% lss 10 goto wait_loop
echo [WARN] Server 可能还没准备好，请稍后手动刷新浏览器

:ready
echo.
echo =========================================
echo  webapp 已启动 -- http://127.0.0.1:%BACKEND_PORT%
echo  老 editor:  http://127.0.0.1:%BACKEND_PORT%/legacy/editor.html
echo =========================================
echo.
echo 前端 dev 模式（可选，需要 Node 24+）：
echo   cd frontend ^&^& npm install ^&^& npm run dev
echo   浏览器打开 http://127.0.0.1:5173
echo.
echo 按任意键打开浏览器...
pause >nul
start http://127.0.0.1:%BACKEND_PORT%/

endlocal
