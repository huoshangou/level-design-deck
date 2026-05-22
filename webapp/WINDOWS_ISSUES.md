# Windows 部署 troubleshooting

> 2026-05-21 同事 Python 3.14.3 / Windows 10 x64 部署调试记录。
> 报告里的三个问题在 commit `5fa9b16` 之前的 main 分支都还在，之后已修复。
> 留存此文档供未来 Windows 同事自查 / 回归对照。

## 为什么 Mac 能跑、Windows 不行？

不是 "Windows 不兼容"，而是 **Mac 上走的是 dev 模式（Vite :5173 + API :8766 分离），Windows 上走的是 prod 模式（前端 :8766 和后端一体）**。两条路径的差异导致了一些问题：

| | Mac（dev 模式） | Windows（prod 模式） |
|---|---|---|
| 前端 | Vite dev server :5173 | uvicorn 托管 `frontend/dist/` |
| API/WS | uvicorn :8766 | 同一个 uvicorn :8766 |
| WS 连接 | 浏览器在 :5173，Vite proxy 转发 WS 到 :8766 → **直达 FastAPI 路由** | 浏览器在 :8766，WS 请求和静态资源在同一进程 → **曾被 catch-all mount 拦截** |

---

## P0 · WebSocket 被 StaticFiles 拦截 ✅ 已修

**现象**：Chat 提示灯红色，错误信息弹 "WebSocket 未连接"

**验证**：移走 `frontend/dist/` → WS 立即正常；放回 → WS 又 404

**原因**：`app.py` 末尾 `app.mount("/", StaticFiles(html=True))` 在 Starlette 1.0.0 中，`html=True` 的 catch-all mount 会吞掉 WebSocket scope，哪怕 `@router.websocket("/ws/chat/{client_id}")` 路由在前面已注册。

**修复**：用 `@app.get` catch-all 替换 mount。HTTP route 不会被 WS scope 触发，根治。详见 `backend/app.py` 末尾的 `_spa_root` / `_spa_fallback`。

---

## P1 · start-webapp.bat 无法启动 ✅ 已修

**现象**：双击显示乱码，uvicorn 未启动，浏览器没打开

**原因**：
1. bat 文件 UTF-8 编码但缺 `chcp 65001`，cmd.exe 默认 GBK 显示中文乱码
2. `start /B` 配相对路径在部分 Windows cmd 环境路径解析失败
3. health check 用 `curl`，Windows 上不一定有

**修复**：`start-webapp.bat` 加 `chcp 65001`、所有路径用 `%~dp0` 绝对、health check 改用 PowerShell `Invoke-WebRequest`。

## P1b · 中文乱码 + uvicorn 启动失败二次出现 ✅ 已修（2026-05-22）

**现象**：双击 bat 看到中文乱码（[INFO] / webapp 已启动 等），按任意键浏览器弹出但显示"无法访问此网站" / ERR_CONNECTION_REFUSED。uvicorn 子窗口闪一下就关。

**原因**（两个叠加）：
1. **bat 文件 UTF-8 无 BOM**。`chcp 65001` 只切换控制台**输出**码页，cmd.exe 解析 bat 文件字节时仍按系统 ACP（中文 Windows = CP936）读取。UTF-8 字节被错读为 CP936 → 中文 echo 乱码。
   修法：bat 加 UTF-8 BOM（`EF BB BF`），Win10 1903+ 的 cmd 识别 BOM 后按 UTF-8 解析。
2. **`cmd /c "cd /d %~dp0 && uvicorn..."` 的 `%~dp0` 没加引号**。如果 Windows 用户名是中文（`C:\Users\张三\...`）或含空格（`C:\Users\Joe Bloggs\...`），`cd /d %~dp0` 在空格处截断、cd 失败、`&&` 后的 uvicorn 永不执行。健康检查 10 秒超时后给 WARN 兜底通过，但 server 实际没起。

**修复**（`start-webapp.bat`）：
- 文件加 UTF-8 BOM
- 去掉 `cmd /c "cd /d %~dp0 && uvicorn..."` 这层包装，直接 `start "title" /min "%~dp0.venv\Scripts\uvicorn.exe" backend.app:app ...`。绝对引号路径不会被空格 / 中文截断；cwd 由父 bat 顶部的 `cd /d "%~dp0"` 设好继承下去
- 启动前加 `python -c "import backend.app"` 自检：依赖缺失这类错误显示在主窗口，不会被 `/min` 子窗口藏掉
- 加 `set PYTHONUTF8=1` / `set PYTHONIOENCODING=utf-8`：uvicorn / cc 等 Python 子进程一律 UTF-8 stdio，避免 stream-json 写成 cp936 乱码
- WARN 改 ERROR + 列出排查思路（去 /min 看子窗口、firewall、依赖版本）

---

## P4 · Python subprocess 找不到 claude.cmd ✅ 已修

**现象**：Windows 上 chat 发消息后报 "Claude CLI not in PATH"（webapp 后端 `AgentError(code="claude_cli_missing")`），就算 cmd 里直接敲 `claude` 能跑也没用。

**原因**：两层叠加：
1. Python `asyncio.create_subprocess_exec("claude", ...)` 默认只搜 `claude.exe`，不搜 `claude.cmd`。但 Anthropic 的 Claude Code CLI 通过 npm 装出来是 `claude.cmd`（npm shim）。
2. 即使用 `shutil.which("claude")` 找到了完整的 `.cmd` 路径，Windows CreateProcess API 也直接拒绝执行 `.cmd` 文件（系统 API 限制，只接受 `.exe`）。

**修复**（`backend/agent/local_cc.py`）：
- 用 `shutil.which("claude")` 找全路径（会按 PATHEXT 试 `.exe / .cmd / .bat`）
- Windows + `.cmd` / `.bat` 后缀时，改用 `asyncio.create_subprocess_shell`（Windows 上等于 `cmd.exe /c ...`，能正确解释 shim）
- 给所有 args 强制 `""` quote，防止 cmd.exe 把 `Write(specs/*)` 这种白名单规则里的 `()` `*` 当 metachar 展开

错误信息也升级了，下次失败会带 resolved 路径，更易诊断。

## P3 · bat 端口被占时不自动 kill 老进程 ✅ 已修

**现象**：重新双击 `start-webapp.bat` 时，老 uvicorn 还占着 8766，新启的失败。Mac 版（`.command`）一直是自动 kill 老进程重启的，bat 之前只做了"尝试 8767 兜底，两个都占就放弃"，跟 mac 行为不一致。

**修复**：用 `for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":PORT " ^| findstr LISTENING') do taskkill /F /PID %%P` 把占用 8766 的进程全部 kill，再 sleep 1s 给 TIME_WAIT 缓冲，然后正常启动。行为对齐 mac 版 `.command`。

## P5 · cc 子进程报 "not logged in - please run /login" ✅ 已修（2026-05-21）

**现象**：Windows 上 webapp 启动成功，但 chat 发消息后 cc 子进程立刻退、显示 "not logged in - please run /login"。CLI 直接敲 `claude` 又能正常用。

**原因**：`backend/agent/local_cc.py` 之前一律 `env.pop("ANTHROPIC_API_KEY")` / `BASE_URL` / `CUSTOM_HEADERS`。这套在 mac/linux 没事 —— cc CLI 有 `~/.claude/.credentials.json` + keychain 兜底，pop 反而能避开父进程错的 BASE_URL（如老 yotta gateway）污染。但 Windows 上 cc CLI 完全靠 env 认证（没 keychain 等价物），pop 之后就裸奔。

**修复**：env.pop 加 `if sys.platform != "win32":` 守卫，Windows 上保留环境变量继承。同时给 stderr 解码加 cp936 兜底（之前 utf-8+replace 会把 Windows 中文报错变成 �，根本看不出问题）。

## P2 · local_cc.py 硬编码 Mac 路径 ✅ 已修

**位置**：`backend/agent/local_cc.py`

之前白名单写死 `Bash(python3 /Users/mofashu/scripts/*)`。

**修复**：改成读 `DECK_EXTRACTOR_SCRIPTS` env var，默认值 `~/scripts`。Windows 同事如果要用 pdf2text / xlsx2text 等提取脚本，设 env var 指到自己机器上的脚本目录即可；不用则跳过这条工具，不影响核心功能。

---

## 回归 checklist

每次改 webapp 后端或启动脚本后，请在 Windows 上至少跑一次：

1. 双击 `start-webapp.bat` → 应该在子窗口起 uvicorn，主窗显示 "webapp 已启动"
2. 浏览器自动打开 `http://127.0.0.1:8766/` → 看到 LDD 主界面
3. 起一个 chat → 看右侧 chat 顶部连接圆点是**绿色**（不是红色）
4. 发一条消息 → 应该立即出现 ⏳ 占位气泡，秒数累加，cc 回完气泡消失换成 assistant 文本
