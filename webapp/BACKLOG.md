# level-design-deck webapp — 待优化清单

> 截至 2026-05-22。主题：**用户控制权 + 反馈可见度 + 跨平台稳定性**。
> 每条带：**问题描述 / 影响面 / 候选修法**。优先级 P0（用户当下痛）/ P1（恢复路径不明）/ P2（改善但非阻塞）。
> 已完成的项移到 [CHANGELOG](#已完成-changelog) 区。

---

## P0 · 失控感很强 / 用户当下痛

### P0-2 · 关掉 cmd 子窗口 = uvicorn 死、server 没了（未修）

**问题**：Windows `start-webapp.bat` 用 `start /min "uvicorn"` 把 uvicorn 跑在一个独立的（最小化的）子窗口里。这个子窗口就 = uvicorn 进程。用户看到主 bat 显示「webapp 已启动」后，会自然以为可以关掉任何黑窗口——一关 uvicorn 子窗口，server 立刻死，浏览器里 webapp 还开着但 API 全部 502。

**影响**：
- 同事不知道哪个窗口是「服务器」哪个是「启动器」，乱关一通
- 浏览器 UI 此时没有任何 server 死亡指示，操作一会儿才发现保存按钮转圈不响应
- 已经发生过：[fix(webapp/bat) c973216 端口被占自动 kill 老进程] 就是因为关错窗口导致的副作用

**候选修法**（按改动量从小到大）：

1. **浏览器 UI 加 server 心跳指示器**（小改）：前端 useChatSocket 之外加一个 `useServerHeartbeat` hook，每 10s GET `/api/health`，失败 2 次后顶部弹一个红色 banner「server 已断开，请重启 start-webapp.bat」
2. **bat 启 detached uvicorn**（中改）：把 `start /min cmd /c uvicorn` 换成 `pythonw.exe -m uvicorn`（pythonw 不带 console），写 PID 到 `.uvicorn.pid`，提供 `stop-webapp.bat` 读 PID kill。优点：彻底不依赖任何窗口；缺点：报错日志看不见，要 tail `.uvicorn.log`
3. **NSSM / Windows Service 包一层**（大改）：装 NSSM 把 uvicorn 注册为 Windows 服务，开机自启，用 services.msc 管。最干净但要装额外工具

**推荐**：1 + 2 组合。1 给立刻可见的反馈，2 彻底消除"关窗口=死"的可能。3 等多用户/局域网部署再说。

---

## P1 · 恢复路径不明

### P1-1 · WS 断了只有红点、没自动重连 / 手动重连按钮（未修）

**问题**：[useChatSocket.ts](frontend/src/hooks/useChatSocket.ts) `ws.onclose` 只 setWsState("closed") 把 header 上的圆点变红。用户不知道怎么办，目前唯一出路是点「+ 新建」开新 session（丢上下文）。

**候选修法**：
- 加自动重连（指数退避，3 次后停）：onclose 后 setTimeout 重连同一个 clientId 的 WS，最多 3 次每次间隔 1s/3s/9s
- 失败后头部 banner 「连接已断开 [重连]」按钮手动触发
- 注意 backend 那边 session 还在，重连只是新开 WS pipe，cc 历史不丢

### P1-2 · 发送失败 / cc 报错后没"重发"按钮（未修）

**问题**：`markSendFailed` / `agent_error` 都把错误塞进消息流，但用户得自己复制粘贴上一条 user 消息重发。

**候选修法**：
- error 消息气泡上加「重发上条」按钮，记一下最后发的 text，点击 → re-call `addUserMessage + api.sendMessage`
- 或者更稳：在 user 消息气泡 hover 时显示「重发」action button，所有 user 消息都能点

### P1-3 · Windows uvicorn 报错被 /min 子窗口藏掉（半修）

**问题**：现在 `start-webapp.bat` 起 uvicorn 用 `start /min`，子窗口最小化。uvicorn 启动失败（依赖缺失、import 错误）会立刻退、窗口关掉，用户看到的就是健康检查 ERROR + 一句「去 /min 看子窗口」。但子窗口已经关了。

**当前状态**：[start-webapp.bat](start-webapp.bat) 加了 `python -c "import backend.app"` 自检——能挡住绝大多数导入错误。但 uvicorn 启动后的 runtime 失败（端口冲突、SSL、监听问题）仍然不可见。

**候选修法**：
- 把 uvicorn stdout/stderr `tee` 或 redirect 到 `webapp/.uvicorn.log`，主 bat health-check 失败时 `type .uvicorn.log` 显示出来
- 或者起 uvicorn 时去掉 `/min`，让子窗口正常显示——副作用是任务栏多一个图标

---

## P2 · 改善但非阻塞

### P2-1 · cost / duration 在前端展示不够显眼

**当前**：MessageBubble assistant 气泡底部小字显示 `$0.0123 234ms`，但只在该条 assistant 消息上。整 session 累加的 cost 不展示，长 session 看不出花了多少钱。

**候选修法**：header 加一个 `Σ $0.45 / 12.3s` 计数器，每次 cc_message_complete 时累加。

### P2-2 · 历史 session 无搜索 / 无 pin

**当前**：[ChatSidebar.tsx 历史下拉](frontend/src/components/chat/ChatSidebar.tsx) 显示最近 30 个，按 mtime 排序，每条前 8 位 cc_session_id + first_user 截断 2 行。要找一周前那次设计 boss 战的对话只能肉眼翻。

**候选修法**：下拉顶部加搜索框（client-side filter first_user 文本）；加 pin 标记（store 在 localStorage `pinned_cc_sessions`，pin 的固定在顶部）。

### P2-3 · 附件区不显示 token 估算

**当前**：用户拖 5 个 docx 进来不知道总共要占 cc 多少 token。memory 提到已有 size guard，但是 byte size 跟 token 数差很多。

**候选修法**：上传后 backend 估个 token 数（用 anthropic SDK 的 `count_tokens` 或者粗略 `char_count // 2.5`），返回 `estimated_tokens` 字段，前端汇总显示 `合计 ~12k tokens` 警告 ≥ 100k。

### P2-4 · 长 stream-json 行有 overflow 风险

**位置**：[local_cc.py:206](backend/agent/local_cc.py#L206) `LimitOverrunError` 已加 catch，limit 调到 10MB（之前 64KB 直接吞）。50KB+ 的 PROJECT.md 这种 tool_result 不会再爆，但更极端的（导一个大 spec JSON）还是会触发。

**候选修法**：换 `readuntil` + chunked accumulation 替代 `readline`，没有单行 limit 限制；或者直接转 stream-json v2（NDJSON 切分外加 length-prefix）。

---

## 已完成（CHANGELOG）

### 2026-05-22

- ✅ **P0-1** 对话中途可以 Stop：WS 推 `{type:"interrupt"}` 帧 → backend `AgentRunner.interrupt()` 杀 cc 子进程 → 前端发新 `CcInterrupted` 事件区分受控终止 vs error；ChatSidebar 发送按钮在 streaming/awaiting 时变 ⏹ 停止按钮（红色），支持 Esc 快捷键
- ✅ **P0-3** awaiting 占位气泡显示最近动静：thinking / tool_use / streaming 都更新 `lastActivityTs + lastActivityLabel`，气泡里显示「最近: 🔧 Read · 3s 前」让用户区分 cc 卡死 vs 还在跑
- ✅ Windows bat 启动失败 + 中文乱码（commit `f756c27`）：BOM、PYTHONUTF8、去掉 `cmd /c "cd /d %~dp0..."` 包装、import 自检
- ✅ Windows cc 子进程认证失败（commit `365b807`）：按平台分 env.pop，Win 保留继承让 cc CLI 读到 ANTHROPIC_*

### 更早

详见 git log，关键节点：
- `0722325` Windows 跑不通 cc CLI：npm shim 是 .cmd 不是 .exe → asyncio shell mode
- `9c7874a` Windows prod 模式三连修：WS 被 catch-all mount 拦截、bat 乱码、硬编码 mac 路径
- `5b55477` 附件 size guard + 设计者档案自动注入
- `2b4089b` workspace + 历史会话恢复 + 视觉重构 + skill 路径修复
- `d4561bf` INTEGRATION 明确 webapp 不绑定 cc 认证

---

## 下次 session 入口

1. **看 P0-2**（关窗 = 死服务）—— 这条是同事接管后最容易踩、最难发现、最破坏体验的隐性 bug
2. 看 P1-1 / P1-3 —— 都是 Windows 体验问题，同事在 Windows 上做 web 项目结构优化时一并改
3. P1-2 / P2-* 可以攒一波小迭代时统一做
