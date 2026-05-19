@echo off
REM level-design-deck webapp 启动脚本（Windows）
REM 用法：双击此文件，或在 cmd/PowerShell 里 cd 到 webapp\ 后运行 start-webapp.bat

setlocal enabledelayedexpansion
cd /d "%~dp0"

set PORT=8766

REM 检查 .venv
if not exist ".venv\Scripts\uvicorn.exe" (
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
    netstat -ano | findstr ":8767 " | findstr LISTENING >nul 2>&1
    if !errorlevel!==0 (
        echo [ERROR] 端口 8767 也被占用，请手动 kill 旧进程后重试
        pause
        exit /b 1
    )
)

echo [INFO] 启动 webapp (port %PORT%) ...

REM 启动 uvicorn（后台运行，日志写到 %TEMP%\level-design-deck-webapp.log）
set LOG=%TEMP%\level-design-deck-webapp.log
start /B .venv\Scripts\uvicorn backend.app:app --host 127.0.0.1 --port %PORT% > "%LOG%" 2>&1

echo [INFO] 等待 server 启动（最多 10 秒）...
set /a tries=0
:wait_loop
timeout /t 1 /nobreak >nul
set /a tries+=1
curl -sf -o nul "http://127.0.0.1:%PORT%/api/health" >nul 2>&1
if %errorlevel%==0 goto ready
if %tries% lss 10 goto wait_loop
echo [WARN] Server 可能还没准备好，请稍后刷新浏览器

:ready
echo.
echo =========================================
echo  webapp 已启动 —— http://127.0.0.1:%PORT%
echo  老 editor:  http://127.0.0.1:%PORT%/legacy/editor.html
echo  日志文件:   %LOG%
echo =========================================
echo.
echo 前端 dev 模式（可选）：
echo   cd frontend
echo   npm install
echo   npm run dev
echo   浏览器打开 http://127.0.0.1:5173
echo.
echo 按任意键打开浏览器...
pause >nul
start http://127.0.0.1:%PORT%/api/health

endlocal
