@echo off
chcp 65001 >nul
REM level-design-deck webapp 启动脚本（Windows）
REM 用法：双击此文件，或在 cmd / PowerShell 里 cd 到 webapp\ 后运行 start-webapp.bat
REM 行为对齐 start-webapp.command（mac 版）：端口被占自动 kill 老进程，重新拉起。

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM uvicorn 子进程一律 UTF-8 I/O，避免 Python 默认 cp936 把 stream-json 写成乱码
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

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

REM 启动前 import 自检：把 ModuleNotFoundError 这类错误显示在主窗口，
REM 不让它消失在 start /min 的子窗口里、用户只看到 health check WARN 就懵了。
echo [INFO] 自检 backend 导入 ...
"%~dp0.venv\Scripts\python.exe" -c "import backend.app" 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] backend.app 导入失败，看上面 traceback。
    echo 常见原因：缺依赖（重新 pip install）/ Python 版本不对 / 工作目录漂移
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

REM start "title" [options] "exe" args：第一个引号串是 title（必须），
REM 这样 uvicorn.exe 的绝对路径才能正确带引号。
REM 之前用 `cmd /c "cd /d %%~dp0 && uvicorn..."` 包装，%%~dp0 含空格或中文用户名
REM 就会让 cd /d 失败、uvicorn 永不启动。现在直接 spawn uvicorn.exe，cwd 由
REM 父 bat 的 `cd /d "%%~dp0"` 已设好继承下去。
start "level-design-deck webapp" /min "%~dp0.venv\Scripts\uvicorn.exe" backend.app:app --host 127.0.0.1 --port %BACKEND_PORT%

echo [INFO] 等待 server 启动（最多 10 秒）...
set /a tries=0
:wait_loop
timeout /t 1 /nobreak >nul
set /a tries+=1
REM Windows 不一定有 curl，用 PowerShell Invoke-WebRequest 做 health check
powershell -NoProfile -Command "try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:%BACKEND_PORT%/api/health' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 goto ready
if %tries% lss 10 goto wait_loop
echo.
echo [ERROR] Server 没起来。常见原因：
echo   - 子窗口 uvicorn 启动失败但被 /min 藏了
echo     → 改成可见调试：把上面 start 行的 /min 去掉重跑
echo   - 端口 %BACKEND_PORT% 被 firewall/AV 拦了
echo   - .venv 装的依赖版本和 backend 不匹配
pause
exit /b 1

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
