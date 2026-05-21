# level-design-deck webapp — 综合开发指引

> 读者：后端工具组（接管 AgentRunner）+ 未来开发者（加新功能）。
> 工具组交接细节（ABC 契约 / SpecStore / 认证方案 / 环境变量完整表）见 `webapp/HANDOFF.md`，本文不重复。

---

## 1. 入口速读（30 秒）

```bash
# 本地一键启动（后端 :8766 + 前端 :5173）
bash webapp/start-webapp.command
```

| 用途 | URL |
|---|---|
| 前端入口（开发） | http://localhost:5173/ |
| 后端直连（prod / 测试） | http://127.0.0.1:8766/ |
| Health check | `GET http://127.0.0.1:8766/api/health` |

`/api/health` 返回：

```json
{
  "status": "ok",
  "agent_backend": "local",
  "namespace_default": "default",
  "project_root": "/Users/.../level-design-deck",
  "write_tools": true,
  "remote_gateway_url": null
}
```

`start-webapp.command` 会等 health check 通过才打开浏览器。日志在 `/tmp/level-design-deck-webapp.log`。

---

## 2. 后端 API 全览

### sessions — 会话管理

前缀 `/api/sessions`，路由文件 `backend/api/sessions.py`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| POST | `/api/sessions` | 创建 session | `client_id?`, `namespace?`, `cc_session_id?`（恢复历史） |
| GET | `/api/sessions` | 列出所有活跃 session | — |
| GET | `/api/sessions/{client_id}` | 查单个 session | `client_id` |
| DELETE | `/api/sessions/{client_id}` | 结束 session（同时清理附件） | `client_id` |

### chat — 消息投递 + WebSocket 事件流

路由文件 `backend/api/chat.py`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| POST | `/api/sessions/{client_id}/messages` | 投递用户消息（202 入队） | `text` |
| WS | `/ws/chat/{client_id}` | 事件流（agent 输出实时推送） | — |

WS 端点协议：client 发 `{"type":"ping"}` / `{"type":"interrupt"}`；server 推 AgentEvent envelope，格式见 `HANDOFF.md` 第 4 节。

### specs — Spec CRUD

前缀 `/api/specs`，路由文件 `backend/api/specs.py`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| GET | `/api/specs` | 列出 spec | `namespace?=default` |
| GET | `/api/specs/{spec_id}` | 读单 spec | `namespace?=default` |
| PUT | `/api/specs/{spec_id}` | 保存 spec | `content: dict` |
| DELETE | `/api/specs/{spec_id}` | 删除 spec | `namespace?=default` |

### modules — Module 元数据

路由文件 `backend/api/modules.py`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| GET | `/api/modules` | 列所有 module | — |
| GET | `/api/modules/{name}/schema` | 读 module JSON Schema | `name` |
| GET | `/api/paths` | 老兼容：从 spec_id 推断文件路径 | `spec=<spec_id>` |

### check — 校验

路由文件 `backend/api/check.py`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| POST | `/api/check` | 机械校验单个 spec | `spec_id`, `namespace?` |
| POST | `/api/cross-check` | 跨 module 校验整个关卡 | `level_id` |

### render — 渲染

路由文件 `backend/api/render.py`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| POST | `/api/render` | 渲染单 spec 为 HTML | `spec_id`, `namespace?` |
| POST | `/api/render-level` | 渲染关卡所有 module | `level_id`, `render_missing?=true` |
| POST | `/api/render-deck` | 渲染横向翻页 deck | `level_id` |

### files — Chat 附件

路由文件 `backend/api/files.py`。附件存 `uploads_dir/<client_id>/`，会话结束时清理。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| POST | `/api/sessions/{client_id}/files` | 上传附件（multipart） | `file` |
| GET | `/api/sessions/{client_id}/files` | 列当前 session 附件 | — |
| DELETE | `/api/sessions/{client_id}/files/{file_id}` | 删单个附件 | — |

docx / pptx / xlsx / html 自动调 `~/scripts/*2text.py` 提取为 `.extracted.txt`，cc 通过 Read 工具读取。

### docs — 已生成设计文档

前缀 `/api/docs`，路由文件 `backend/api/docs.py`。文档落地在 `project_root/docs/*.html`，不进 git。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| GET | `/api/docs` | 列所有生成文档，按 mtime 倒序 | — |
| PUT | `/api/docs/{filename}` | 回写编辑后的文档内容（50MB 上限） | body=HTML bytes |

### doc_templates — 文档模板

前缀 `/api/doc-templates`，路由文件 `backend/api/doc_templates.py`。模板在 `templates/html/*.html`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| GET | `/api/doc-templates` | 列模板（含 kind / version） | — |
| GET | `/api/doc-templates/{filename}/fields` | 读模板字段定义 JSON | `filename` 必须 `.html` 结尾 |

### cc_history — CC 历史对话恢复

前缀 `/api/cc-history`，路由文件 `backend/api/cc_history.py`。从 `~/.claude/projects/<encoded-cwd>/*.jsonl` 读。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| GET | `/api/cc-history` | 列最近 N 个历史 session | `limit?=30` |
| GET | `/api/cc-history/{cc_session_id}/generated-docs` | 找 transcript 中生成的文档列表 | — |
| GET | `/api/cc-history/{cc_session_id}/messages` | 解析 transcript 为消息列表 | — |

### workspace — 设计文件管理树

前缀 `/api/workspace`，路由文件 `backend/api/workspace.py`。根目录 `~/Documents/level-design-workspace/`。

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| GET | `/api/workspace` | 读整棵任务树 | — |
| POST | `/api/workspace/tasks` | 创建任务节点 | `name`, `kind`（poi/gameplay/prop）, `desc?`, `parent_path?` |
| DELETE | `/api/workspace/tasks/{task_path:path}` | 删除任务（递归） | — |
| GET | `/api/workspace/tasks/{task_path:path}` | 读任务详情（docs/materials/sessions） | — |
| POST | `/api/workspace/tasks/{task_path:path}/link-doc` | 把 docs/ 下文件移入任务 | `src_filename`, `move?=true` |
| POST | `/api/workspace/tasks/{task_path:path}/materials` | 上传素材到任务 materials/ | `file`（multipart） |
| POST | `/api/workspace/tasks/{task_path:path}/link-session` | 把 cc session 关联到任务 | `cc_session_id`, `note?` |
| POST | `/api/workspace/import-specs` | 批量从 specs/ 导入到 workspace | — |
| POST | `/api/workspace/import-docs` | 批量从 docs/ 导入到 workspace | — |

---

## 3. 静态路由 mount

`backend/app.py` 中 mount 的所有静态路径（按存在检查，缺目录则跳过）：

| URL 前缀 | 源目录 | 说明 |
|---|---|---|
| `/legacy` | `project_root/editor/` | 老 editor.html，过渡期兜底 |
| `/outputs` | `project_root/outputs/` | render 产出的 HTML |
| `/lib` | `project_root/lib/` | 共享 JS 库 |
| `/tools/levelcraft` | `project_root/tools/levelcraft/` | LevelCraft 2D 编辑器 |
| `/templates/html` | `project_root/templates/html/` | gameplay/prop 文档模板 |
| `/docs` | `project_root/docs/` | cc 生成的设计文档 |
| `/workspace-file` | `~/Documents/level-design-workspace/` | workspace 资源文件直链 |
| `/` | `project_root/webapp/frontend/dist/` | 前端 build 产物（prod） |

---

## 4. 环境变量配置

`backend/config.py` 解析以下 `DECK_*` 变量（可放 `webapp/.env`）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DECK_AGENT` | `local` | `local` 用 subprocess claude CLI；`remote` 用 RemoteAgentRunner |
| `DECK_REMOTE_GATEWAY_URL` | `""` | `DECK_AGENT=remote` 时必填 |
| `DECK_REMOTE_GATEWAY_TOKEN` | 空 | Bearer token |
| `DECK_HOST` | `127.0.0.1` | 局域网部署改 `0.0.0.0` |
| `DECK_PORT` | `8766` | 监听端口 |
| `DECK_NAMESPACE` | `default` | 默认 namespace |
| `DECK_WRITE_TOOLS` | `1` | `0` → cc 只能 Read；`1` → 完整白名单 |
| `DECK_ADD_DIRS` | `~/Desktop` | 逗号分隔，cc `--add-dir` 额外可读目录（local only） |
| `DECK_DEV_ORIGIN` | `http://localhost:5173` | CORS 允许的前端开发地址 |
| `DECK_UPLOADS_DIR` | `/tmp/deck-chat-uploads` | 附件临时目录 |
| `ANTHROPIC_BASE_URL` | 空 | cc gateway 覆盖，走 `webapp/.env` |
| `ANTHROPIC_API_KEY` | 空 | cc API key |
| `ANTHROPIC_CUSTOM_HEADERS` | 空 | 公司网关专用 header |

`load_settings()` 加载后通过 `get_settings()` DI 注入，`lru_cache` 单例。

---

## 5. AgentRunner 接入指南

### ABC 定义

`backend/agent/base.py` 定义 `AgentRunner` ABC，6 个方法：

```python
class AgentRunner(ABC):
    def start_session(self, client_id: str, namespace: str = "default",
                      cc_session_id: str | None = None) -> dict: ...
    def has_session(self, client_id: str) -> bool: ...
    def get_session(self, client_id: str) -> dict | None: ...
    def list_sessions(self) -> list[dict]: ...
    def end_session(self, client_id: str) -> None: ...
    async def send_message(self, client_id: str, text: str) -> AsyncIterator[AgentEvent]: ...
```

`start_session` 是同步的，只注册本地元数据；`send_message` 是 async generator，逐个 yield `AgentEvent`。

### LocalCcRunner 实现原理

`backend/agent/local_cc.py`：

1. `send_message` 每次调用 spawn 一个 `claude` CLI 子进程（`asyncio.create_subprocess_exec`）
2. 进程参数：`--output-format=stream-json --input-format=stream-json --permission-mode acceptEdits --allowed-tools <whitelist>`
3. 首次 turn 不带 `--resume`；cc 返回 `session_id` 后存 meta，后续 turn 带 `--resume <cc_session_id>`
4. stdout readline 解析 NDJSON → map 到 `AgentEvent` dataclass → yield
5. readline buffer 设为 10MB（防 LimitOverrunError，cc tool_result 含大文件内容）

工具白名单（`_WRITE_ALLOWED_TOOLS`）由 `DECK_WRITE_TOOLS` 控制：

```python
_WRITE_ALLOWED_TOOLS = [
    "Read", "Glob", "Grep", "Edit",
    "Write(specs/*)", "Write(docs/*)",
    "Bash(python3 tools/*)",
    "Bash(python3 /Users/mofashu/scripts/*)",
    "Bash(ls *)", "Bash(cp *)",
]
_READ_ONLY_TOOLS = ["Read", "Glob", "Grep"]
```

### 切换到 RemoteAgentRunner

`backend/agent/remote.py` 是 Phase 4 stub，所有方法抛 `NotImplementedError`。实现时的预期协议：

```
POST {gateway_url}/sessions/{client_id}/messages
→ SSE stream，每条 data 对应一个 AgentEvent JSON，type 字段同 events.py
```

切换方式：仅改 `.env`，业务层（api/sessions.py / api/chat.py）**无需改动**：

```bash
DECK_AGENT=remote
DECK_REMOTE_GATEWAY_URL=https://cc-gateway.internal
DECK_REMOTE_GATEWAY_TOKEN=<bearer-token>
```

`deps.py` 的 `_make_agent()` 根据 `DECK_AGENT` 自动选择实现：

```python
if s.agent_backend == "local":
    return LocalCcRunner(s.project_root, add_dirs=s.add_dirs)
if s.agent_backend == "remote":
    from backend.agent.remote import RemoteAgentRunner
    return RemoteAgentRunner(gateway_url=s.remote_gateway_url, token=s.remote_gateway_token)
```

---

## 6. 新增 API 的步骤

以 `workspace.py` 为参考例子（`/api/workspace` 前缀，任务树管理）。

**步骤一：在 `backend/api/` 新建模块**

```python
# backend/api/my_feature.py
from fastapi import APIRouter, Depends
from backend.deps import get_settings

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.get("")
def list_items(settings=Depends(get_settings)):
    ...
```

**步骤二：在 `backend/app.py` 注册**

```python
from backend.api import ..., my_feature   # 加到 import

app.include_router(my_feature.router)     # 加到 include_router 列表
```

**步骤三：前端 `frontend/src/api/client.ts` 加包装方法**

```typescript
export const api = {
  // ...已有方法
  listMyItems: () => request<MyItem[]>("/api/my-feature"),
  createMyItem: (body: { name: string }) =>
    request<MyItem>("/api/my-feature", { method: "POST", body: JSON.stringify(body) }),
};
```

所有路径用相对路径 `/api/*`，dev 走 Vite proxy 到 `:8766`，prod 同源。

**步骤四（如有 client state）：新建或扩展 store**

```typescript
// frontend/src/stores/myFeatureStore.ts
import { create } from "zustand";
import { api } from "../api/client";

type MyFeatureState = {
  items: MyItem[];
  refresh: () => Promise<void>;
};

export const useMyFeatureStore = create<MyFeatureState>((set) => ({
  items: [],
  refresh: async () => {
    const items = await api.listMyItems();
    set({ items });
  },
}));
```

如果数据是只读 server state（不需要复杂本地操作），用 TanStack Query 的 `useQuery` 比 Zustand store 更合适。

**步骤五：组件调用**

```tsx
import { useMyFeatureStore } from "../stores/myFeatureStore";

function MyComponent() {
  const { items, refresh } = useMyFeatureStore();
  useEffect(() => { void refresh(); }, [refresh]);
  return <ul>{items.map((i) => <li key={i.id}>{i.name}</li>)}</ul>;
}
```

---

## 7. 前端架构速读

**技术栈：** React 18 + Vite + TypeScript + Zustand（client state）+ TanStack Query（server state）

**目录结构：**

```
frontend/src/
├── api/
│   ├── client.ts       ← 所有 fetch 包装，统一 ApiError 处理
│   ├── types.ts        ← 通用类型（SpecInfo / CheckResult / RenderResult ...）
│   └── chat-types.ts   ← Chat/WS 专用类型
├── stores/
│   ├── editorStore.ts  ← 当前选中 spec、本地编辑副本、dirty 标记、toast
│   ├── chatStore.ts    ← session、消息列表、WS 连接状态、附件
│   └── workspaceStore.ts ← workspace 树缓存、展开折叠状态
├── hooks/
│   ├── useChatSocket.ts ← WebSocket 生命周期（clientId 变化自动 connect/disconnect）
│   ├── useChecks.ts    ← check / cross-check TanStack Query
│   └── useSpec.ts      ← spec CRUD TanStack Query
├── components/
│   ├── Topbar.tsx      ← 顶栏（spec 选择 / 操作按钮 / 模板入口）
│   ├── PreviewPane.tsx ← 预览区（spec HTML 渲染 / 文档模板 iframe）
│   ├── WorkspacePanel.tsx ← 右侧 workspace 面板
│   ├── AlertsSidebar.tsx  ← 校验告警侧边栏
│   ├── BubbleDiagramView.tsx ← Bubble 图视图
│   ├── SpatialLayoutView.tsx ← 空间布局视图
│   ├── SpecPicker.tsx  ← Spec 选择下拉
│   ├── chat/           ← ChatSidebar / MessageBubble / AttachmentArea / useChatSocket
│   └── form/           ← spec 字段编辑表单组件
└── pages/
    └── EditorPage.tsx  ← 主页面（组装所有组件）
```

**主要 store 职责：**

- `editorStore`：当前选中 spec + 本地编辑副本（TanStack Query 管服务器 state，dirty 副本存这里），`selectSpec` / `updateField` / `showToast`
- `chatStore`：session 生命周期 + 消息列表 + WS 状态 + 附件，`initSession` / `loadHistorySession` / `handleEvent`
- `workspaceStore`：workspace 树（API 拉取后缓存），`refresh` / `createTask` / `deleteTask`

---

## 8. cc-skills 接入

当前 skill 文件在 `cc-skills/`：

| Skill | 文件 | 用途 |
|---|---|---|
| `design-deck` | `cc-skills/design-deck.md` | 主 spec 生成 / 编辑流程 |
| `fill-gamedoc` | `cc-skills/fill-gamedoc.md` | 从结构化数据填充 gameplay/prop 文档 |

**调用方式：** 前端在 chat 输入框发 `/design-deck` 或 `/fill-gamedoc <args>`，LocalCcRunner 把这条文字作为用户消息传给 cc CLI，cc 通过 skill 注入机制执行 skill 文件定义的流程。

**工具白名单约束：** skill 能用的工具受 `local_cc.py` 中 `_WRITE_ALLOWED_TOOLS` 限制。`--permission-mode acceptEdits` 允许 cc 直接写文件（无需逐个确认），`--allowed-tools` 白名单是第二道防线。

**加新 skill 的步骤：**

1. 在 `cc-skills/` 新建 `my-skill.md`，按 cc skill 格式写（参考 `design-deck.md`）
2. 确认 skill 需要的工具在 `_WRITE_ALLOWED_TOOLS` 白名单内；如需新工具，在 `local_cc.py` 的 `_WRITE_ALLOWED_TOOLS` 里追加
3. 如果新工具涉及写路径（如 `Write(reports/*)`），只加精确路径模式，不加通配 `Write(*)`
4. 前端无需改动——用户在 chat 里输入 `/my-skill <args>` 即可调用

---

## 9. 常见坑

**cc CLI 的 path-restricted `--allowed-tools` 不可靠**

`Write(specs/*)` 这种路径限制在 cc CLI 的实际执行中并不严格。必须同时配 `--permission-mode acceptEdits`，两者结合才能让 cc 写文件不弹确认框，同时限制写入范围。不要只靠路径模式做安全防线。

**前端所有 fetch 用相对路径**

`client.ts` 里所有请求路径是 `/api/*`（不带 host），dev 时 Vite proxy 转发到 `:8766`，prod 时同源。不要在前端代码里硬编码 `http://127.0.0.1:8766`，否则 build 后失效。

Vite proxy 配置在 `frontend/vite.config.ts`（`/api` → `http://127.0.0.1:8766`，`/ws` → `ws://127.0.0.1:8766`）。

**WebSocket 用 `location.host` 拼地址**

```typescript
// useChatSocket.ts
const url = `ws://${location.host}/ws/chat/${encodeURIComponent(clientId)}`;
```

本地开发时 `location.host` = `localhost:5173`，Vite proxy 负责转发 WS。prod 单进程时 `location.host` = `127.0.0.1:8766`，直连后端。不需要额外配置，但局域网部署时注意前端 build 后 `location.host` 变成内网 IP，WS 地址自动匹配。

**发消息前必须先建 WS 连接**

`POST /api/sessions/{client_id}/messages` 检查 `_ws_connected[client_id]`，没有活跃 WS 时返回 409。正确顺序：`createSession` → WS connect（`onopen` 触发）→ 才能 `sendMessage`。`chatStore.initSession` 已按此顺序封装。

**PreviewPane 里 `position:sticky` 在 iframe 内失效**

模板 HTML 里的 sticky 元素在 `PreviewPane.tsx` 的 `<iframe>` 里无法吸顶（iframe 内滚动容器和外层脱钩）。如需 sticky 行为，用 JavaScript scroll 监听或改为 fixed 定位。

**`_make_agent()` 是 `lru_cache` 单例**

`deps.py` 里 `_make_agent()` 用 `lru_cache(maxsize=1)` 缓存，进程生命周期内只实例化一次。切换 `DECK_AGENT` 后必须重启进程才生效；测试时用 `app.dependency_overrides[get_agent] = lambda: fake_runner` 覆盖。
