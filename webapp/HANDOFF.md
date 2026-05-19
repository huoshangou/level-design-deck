# level-design-deck webapp — 工具组交接文档

> 版本：v1.0（2026-05-19）  
> 交接方：Steve（关卡设计师）  
> 接收方：工具组（后端接管 + 局域网部署）

---

## 1. 快速定位

```
webapp/
├── backend/
│   ├── agent/
│   │   ├── base.py        ← AgentRunner ABC（接口契约，不要改）
│   │   ├── events.py      ← AgentEvent 类型体系（WS 数据格式）
│   │   ├── local_cc.py    ← 当前实现（subprocess + claude CLI）
│   │   └── remote.py      ← Phase 4 stub（你们填这里）
│   ├── store/
│   │   ├── base.py        ← SpecStore ABC（接口契约，不要改）
│   │   └── file_store.py  ← 当前实现（读写本地 specs/*.spec.json）
│   ├── api/               ← FastAPI 路由（业务层，接管后无需改）
│   ├── config.py          ← 环境变量配置表
│   └── deps.py            ← DI 工厂（切换实现只改这里）
├── frontend/              ← React/Vite/TS 前端（工具组不接管）
└── HANDOFF.md             ← 本文件
```

---

## 2. 接管目标

**你们只需实现两件事**，业务层无需改动：

1. `RemoteAgentRunner`（`backend/agent/remote.py`）— 替换 `NotImplementedError`
2. 可选：`RemoteSpecStore` 或 `NamespacedFileStore`（多用户 specs 隔离）

切换方式：在部署环境的 `.env` 里改两行：

```bash
DECK_AGENT=remote
DECK_REMOTE_GATEWAY_URL=https://your-cc-gateway.internal
DECK_REMOTE_GATEWAY_TOKEN=<bearer-token>
```

---

## 3. AgentRunner ABC

```python
# backend/agent/base.py
class AgentRunner(ABC):
    def start_session(self, client_id: str, namespace: str = "default") -> dict:
        # Returns: {client_id, namespace, started_at, cc_session_id: None}

    def has_session(self, client_id: str) -> bool: ...
    def get_session(self, client_id: str) -> dict | None: ...
    def list_sessions(self) -> list[dict]: ...
    def end_session(self, client_id: str) -> None: ...

    async def send_message(self, client_id: str, text: str) -> AsyncIterator[AgentEvent]:
        # 异步流出事件序列，格式见第 4 节
```

**关键约束：**
- `start_session` 是同步的（不调远端），只在本地注册 session 元数据
- `send_message` 是 async generator，逐个 yield AgentEvent
- `client_id` 是前端生成的 UUID，与 cc_session_id（cc 内部 session）解耦

---

## 4. AgentEvent 类型体系

所有事件经 `events.event_to_dict(ev)` 序列化后推到 WebSocket。

| event type | 触发时机 | 关键字段 |
|---|---|---|
| `session_started` | 第一次 send_message 收到 cc init | `client_id`, `cc_session_id` |
| `cc_output_delta` | cc 文字输出（当前 turn-level，非 token-level） | `text`, `message_id` |
| `cc_thinking` | cc 思考块（thinking model） | `text` |
| `tool_use_start` | cc 调用工具时 | `tool`, `args`, `tool_use_id` |
| `tool_use_end` | 工具调用完成 | `tool`, `ok`, `summary` |
| `cc_message_complete` | assistant turn 结束 | `text`, `cost_usd`, `duration_ms`, `cc_session_id` |
| `spec_updated` | spec 文件写入（Watcher 推送） | `spec_id`, `mtime`, `source` |
| `agent_error` | 任何错误 | `code`, `message`, `recoverable` |
| `session_ended` | session 被终止 | `reason` |

**WebSocket envelope（server → client）：**

```json
{
  "type": "cc_output_delta",
  "ts": 1748000000.0,
  "session_id": "<client_id>",
  "payload": { "text": "...", "message_id": "msg_xxx" }
}
```

---

## 5. WebSocket 协议

**端点：** `ws://host:8766/ws/chat/{client_id}`

**Client → Server：**
```json
{ "type": "ping" }
{ "type": "interrupt" }
```

**Server → Client：** 见第 4 节 envelope 格式

**连接生命周期：**
1. 前端连接时，backend 校验 `client_id` 是否已有活跃 session
2. session 不存在时 server 推 `agent_error {code: "session_not_found"}` 后关闭
3. `end_session` API 不自动关闭 WS，前端自行断开

---

## 6. SpecStore ABC

```python
# backend/store/base.py
class SpecStore(ABC):
    def list(self, namespace: str = "default") -> list[SpecInfo]: ...
    def get(self, spec_id: str, namespace: str = "default") -> SpecRecord: ...
    def save(self, spec_id: str, content: dict, namespace: str = "default") -> SaveResult: ...
    def delete(self, spec_id: str, namespace: str = "default") -> None: ...
```

**当前实现：** `FileSpecStore` — `namespace="default"` 硬映射到 `specs/` 目录，非 default 抛 `NotImplementedError`。

**多用户扩展路径：**
- 选项 A：`NamespacedFileStore(project_root, base="specs")` — 路径映射 `specs/{namespace}/{spec_id}.spec.json`
- 选项 B：远端 `RemoteSpecStore` — HTTP 调 spec 管理服务

---

## 7. 认证方案 sketch（待工具组实现）

### Bearer token + namespace 中间件

```python
# 示例 middleware（未合入，作为设计参考）
from fastapi import Request
from fastapi.responses import JSONResponse

async def auth_middleware(request: Request, call_next):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        namespace = "default"  # 本地开发无 token
    else:
        namespace = await verify_token(token)  # 你们实现
        if namespace is None:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    request.state.namespace = namespace
    return await call_next(request)
```

```python
# API 路由改造（只改 Depends 来源）
@router.get("/api/specs")
def list_specs(request: Request, store: SpecStore = Depends(get_store)):
    ns = getattr(request.state, "namespace", "default")
    return store.list(ns)
```

当前所有路由已有 `namespace: str = Query("default")` 参数位，可平滑切换到 `request.state.namespace`。

---

## 8. 环境变量完整表

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DECK_AGENT` | `local` | `local` 用 subprocess claude CLI；`remote` 用 RemoteAgentRunner |
| `DECK_REMOTE_GATEWAY_URL` | `""` | agent=remote 时必填，如 `https://cc-gateway.internal` |
| `DECK_REMOTE_GATEWAY_TOKEN` | （空）| Bearer token |
| `DECK_HOST` | `127.0.0.1` | 局域网部署改 `0.0.0.0` |
| `DECK_PORT` | `8766` | 监听端口 |
| `DECK_NAMESPACE` | `default` | 默认 namespace |
| `DECK_WRITE_TOOLS` | `1` | `0` → cc 只能 Read；`1` → 允许 Write(specs/*) + Bash(python3 tools/*) |
| `DECK_ADD_DIRS` | `~/Desktop` | 逗号分隔，cc --add-dir 参数（local only） |
| `DECK_DEV_ORIGIN` | `http://localhost:5173` | CORS 允许的前端开发地址 |
| `DECK_UPLOADS_DIR` | `/tmp/deck-chat-uploads` | 附件临时目录 |
| `ANTHROPIC_BASE_URL` | （空）| cc gateway 覆盖，走 webapp/.env |
| `ANTHROPIC_API_KEY` | （空）| cc API key |
| `ANTHROPIC_CUSTOM_HEADERS` | （空）| 公司网关专用 header |

---

## 9. 启动方式

```bash
# 开发（两进程）
cd webapp
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8766 --reload
cd frontend && npm run dev   # :5173 → proxy → :8766

# 生产（单进程，前端 build 产物由 FastAPI 挂载）
cd frontend && npm run build
cd ..
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8766 --workers 2

# 局域网访问：把 DECK_HOST=0.0.0.0 + DECK_DEV_ORIGIN= 对应前端地址写进 .env
```

---

## 10. 测试

```bash
cd webapp
PYTHONPATH=. .venv/bin/pytest backend/tests/ -v
# 32 / 32 通过（含 sessions / chat WS / specs CRUD / check / render）
```

测试用 `httpx.AsyncClient` + FastAPI `TestClient`，mock 了 `AgentRunner`，不需要真实 cc 进程。

---

## 11. 不需要接管的部分

- `tools/` — Python 工具脚本，Steve 维护
- `editor/` — 老 editor.html，过渡期保留，`/legacy/editor.html` 路由
- `frontend/` — React 前端，Steve 维护
- `cc-skills/design-deck.md` — cc skill，Steve 维护
- `specs/` — spec 数据真源，git 管控

---

## 12. 接管检查清单

- [ ] 实现 `RemoteAgentRunner`（`backend/agent/remote.py`），所有 `NotImplementedError` 替换为真实 HTTP/SSE 调用
- [ ] 验证 `AgentEvent` 序列化格式与你们 gateway 的 SSE 格式匹配（或在 `RemoteAgentRunner` 内转换）
- [ ] 实现 Bearer token 验证 + namespace 中间件（如需多用户隔离）
- [ ] 实现 `NamespacedFileStore` 或 `RemoteSpecStore`（如需多用户 spec 隔离）
- [ ] 局域网部署：`DECK_HOST=0.0.0.0`，前端 build，配 CORS
- [ ] 压测 WebSocket 并发连接（多设计师同时聊天场景）
