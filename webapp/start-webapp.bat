@echo off
chcp 65001 >nul
REM level-design-deck webapp 启动脚本（Windows）
REM 用法：双击此文件，或在 cmd / PowerShell 里 cd 到 webapp\ 后运行 start-webapp.bat

setlocal enabledelayedexpansion
cd /d "%~dp0"

set PORT=8766

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

REM 检查端口是否被占（Windows 用 netstat）
netstat -ano | findstr ":%PORT% " | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
    echo [WARN] 端口 %PORT% 已被占用，尝试 8767 ...
    set PORT=8767
    netstat -ano | findstr ":!PORT! " | findstr LISTENING >nul 2>&1
    if !errorlevel!==0 (
        echo [ERROR] 端口 8767 也被占用，请手动 kill 旧进程后重试
        pause
        exit /b 1
    )
)

echo [INFO] 启动 webapp (port %PORT%) ...

REM 用 start "title" 起一个独立子窗口跑 uvicorn（前台、可见输出、关窗即停 server）。
REM 不用 start /B 是因为后台 + > 重定向在部分 Windows cmd 环境路径解析失败。
REM "%~dp0.venv\Scripts\uvicorn.exe" 用绝对路径，避免双击启动时工作目录漂移。
start "level-design-deck webapp" /min cmd /c "cd /d %~dp0 && .venv\Scripts\uvicorn.exe backend.app:app --host 127.0.0.1 --port %PORT%"

echo [INFO] 等待 server 启动（最多 10 秒）...
set /a tries=0
:wait_loop
timeout /t 1 /nobreak >nul
set /a tries+=1
REM Windows 不一定有 curl，用 PowerShell Invoke-WebRequest 做 health check
powershell -NoProfile -Command "try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/api/health' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 goto ready
if %tries% lss 10 goto wait_loop
echo [WARN] Server 可能还没准备好，请稍后手动刷新浏览器

:ready
echo.
echo =========================================
echo  webapp 已启动 -- http://127.0.0.1:%PORT%
echo  老 editor:  http://127.0.0.1:%PORT%/legacy/editor.html
echo =========================================
echo.
echo 前端 dev 模式（可选，需要 Node 24+）：
echo   cd frontend ^&^& npm install ^&^& npm run dev
echo   浏览器打开 http://127.0.0.1:5173
echo.
echo 按任意键打开浏览器...
pause >nul
start http://127.0.0.1:%PORT%/

endlocal
