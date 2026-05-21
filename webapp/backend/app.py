"""FastAPI factory + lifespan + static mount。

dev：Vite 跑 :5173 走 proxy 调本 server；prod：本 server 挂 frontend/dist。
"""

from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import cc_history, check, chat, doc_templates, docs, files, modules, profile, render, sessions, specs, workspace
from backend.deps import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Phase 2 会在这起 AgentRunner / Watcher；Phase 1 留空
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="level-design-deck webapp",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[s.cors_allow_dev_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(specs.router)
    app.include_router(modules.router)
    app.include_router(check.router)
    app.include_router(render.router)
    app.include_router(sessions.router)
    app.include_router(chat.router)
    app.include_router(files.router)
    app.include_router(doc_templates.router)
    app.include_router(docs.router)
    app.include_router(cc_history.router)
    app.include_router(workspace.router)
    app.include_router(profile.router)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "agent_backend": s.agent_backend,
            "namespace_default": s.namespace_default,
            "project_root": str(s.project_root),
            "write_tools": s.write_tools,
            "remote_gateway_url": s.remote_gateway_url or None,
        }

    # 老 editor.html 兜底（plan: /legacy/editor.html 过渡期可用）
    legacy_dir = s.project_root / "editor"
    if legacy_dir.exists():
        app.mount("/legacy", StaticFiles(directory=str(legacy_dir), html=True), name="legacy")

    # 静态资产（spec render 出的 HTML、lib/、tools/levelcraft/）
    outputs_dir = s.project_root / "outputs"
    if outputs_dir.exists():
        app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")
    lib_dir = s.project_root / "lib"
    if lib_dir.exists():
        app.mount("/lib", StaticFiles(directory=str(lib_dir)), name="lib")
    lc_dir = s.project_root / "tools" / "levelcraft"
    if lc_dir.exists():
        app.mount("/tools/levelcraft", StaticFiles(directory=str(lc_dir), html=True), name="levelcraft")

    # HTML 文档模板（gameplay/prop 等可编辑富文本模板）
    html_tmpl_dir = s.project_root / "templates" / "html"
    if html_tmpl_dir.exists():
        app.mount("/templates/html", StaticFiles(directory=str(html_tmpl_dir)), name="html-templates")

    # 已生成的设计文档（cc fill-gamedoc 产出，不进 git）
    docs_dir = s.project_root / "docs"
    docs_dir.mkdir(exist_ok=True)
    app.mount("/docs", StaticFiles(directory=str(docs_dir)), name="docs")

    # 用户 workspace 资源文件（docs/材料/任务下文件）
    from pathlib import Path as _Path
    workspace_dir = _Path.home() / "Documents" / "level-design-workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/workspace-file", StaticFiles(directory=str(workspace_dir)), name="workspace-file")

    # frontend build 产物（prod 模式：单端口 serve dist + API + WS）
    #
    # 为什么不用 app.mount("/", StaticFiles(...))：
    # starlette 1.0.0 + catch-all mount 会吞掉 WebSocket scope，即使 chat.router
    # 已在 mount 之前 include_router 注册。Mac 走 dev 模式（Vite :5173 + uvicorn :8766
    # 分离）所以没暴露，Windows 走 prod 模式直接被 WS 404 卡死。
    # 改用 @app.get catch-all：HTTP route 不会被 WS scope 触发，根治。
    # 详见 WINDOWS_ISSUES.md / 2026-05-21 同事 Windows 部署调试。
    dist_dir = s.project_root / "webapp" / "frontend" / "dist"
    if dist_dir.exists():
        from fastapi import HTTPException
        from fastapi.responses import FileResponse
        index_path = dist_dir / "index.html"
        dist_root = dist_dir.resolve()

        @app.get("/", include_in_schema=False)
        async def _spa_root():
            return FileResponse(index_path)

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _spa_fallback(full_path: str):
            candidate = (dist_dir / full_path).resolve()
            try:
                candidate.relative_to(dist_root)
            except ValueError:
                raise HTTPException(status_code=404)
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index_path)

    return app


app = create_app()
