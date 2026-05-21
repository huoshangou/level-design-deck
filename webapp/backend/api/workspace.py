"""Workspace 设计文件管理 API。

把用户的设计资产（最终文档 docs/ / 原始素材 materials/ / 关联对话 sessions.json）
按 POI → 玩法/物件 → 物件 的递归树结构组织在 ~/Documents/level-design-workspace/ 下。

任务可任意嵌套；每个任务文件夹含 _task.json 元数据 + materials/ + docs/ + sessions.json，
也可包含子任务文件夹（不带前缀名）。
"""

from __future__ import annotations
import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.deps import get_settings

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

WORKSPACE_ROOT = Path.home() / "Documents" / "level-design-workspace"
RESERVED_DIRS = {"materials", "docs"}      # 任务文件夹内的固定子目录，不算子任务
RESERVED_FILES = {"_task.json", "_workspace.json", "sessions.json"}

TaskKind = Literal["poi", "gameplay", "prop"]
VALID_KINDS = {"poi", "gameplay", "prop"}

# 任务名安全：禁路径分隔符、禁开头点（避免隐藏文件）
_VALID_NAME_RE = re.compile(r"^[^/\\:*?\"<>|\x00-\x1f][^/\\:*?\"<>|\x00-\x1f]*$")


def _ensure_workspace_root() -> Path:
    """惰性创建顶层目录 + _workspace.json"""
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    meta_path = WORKSPACE_ROOT / "_workspace.json"
    if not meta_path.exists():
        meta_path.write_text(json.dumps({
            "version": "0.1",
            "created_at": time.time(),
            "created_by": "level-design-deck webapp",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    return WORKSPACE_ROOT


def _validate_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        raise HTTPException(400, "name cannot be empty")
    if n.startswith(".") or n in RESERVED_DIRS:
        raise HTTPException(400, f"name forbidden: {n}")
    if not _VALID_NAME_RE.match(n):
        raise HTTPException(400, f"name contains illegal character: {n}")
    if len(n) > 80:
        raise HTTPException(400, "name too long (max 80)")
    return n


def _resolve_path(rel_path: str) -> Path:
    """把相对路径解析为安全的绝对路径，禁逃出 workspace。"""
    _ensure_workspace_root()
    rel = (rel_path or "").strip().strip("/")
    if not rel:
        return WORKSPACE_ROOT
    if ".." in rel.split("/"):
        raise HTTPException(400, "path traversal not allowed")
    p = (WORKSPACE_ROOT / rel).resolve()
    try:
        p.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        raise HTTPException(400, "path escapes workspace root")
    return p


def _read_task_meta(task_dir: Path) -> dict:
    meta_path = task_dir / "_task.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_task_meta(task_dir: Path, meta: dict) -> None:
    (task_dir / "_task.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _read_sessions(task_dir: Path) -> list[dict]:
    sp = task_dir / "sessions.json"
    if not sp.exists():
        return []
    try:
        data = json.loads(sp.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _list_materials(task_dir: Path) -> list[dict]:
    mat_dir = task_dir / "materials"
    if not mat_dir.exists():
        return []
    out = []
    for p in sorted(mat_dir.iterdir(), key=lambda x: x.name):
        if not p.is_file():
            continue
        st = p.stat()
        out.append({"filename": p.name, "size_bytes": st.st_size, "mtime": st.st_mtime})
    return out


def _list_docs(task_dir: Path) -> list[dict]:
    doc_dir = task_dir / "docs"
    if not doc_dir.exists():
        return []
    out = []
    for p in sorted(doc_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = p.stat()
        out.append({"filename": p.name, "size_bytes": st.st_size, "mtime": st.st_mtime})
    return out


def _is_task_dir(p: Path) -> bool:
    return p.is_dir() and (p / "_task.json").exists()


def _build_tree(task_dir: Path) -> dict:
    """递归构造一个任务子树。"""
    meta = _read_task_meta(task_dir)
    children: list[dict] = []
    for child in sorted(task_dir.iterdir(), key=lambda x: x.name):
        if child.name in RESERVED_DIRS or child.name in RESERVED_FILES:
            continue
        if _is_task_dir(child):
            children.append(_build_tree(child))
    rel = str(task_dir.relative_to(WORKSPACE_ROOT))
    return {
        "name": task_dir.name,
        "path": rel,
        "kind": meta.get("kind", "poi"),
        "desc": meta.get("desc", ""),
        "status": meta.get("status", ""),
        "created_at": meta.get("created_at", 0),
        "doc_count": len(_list_docs(task_dir)),
        "material_count": len(_list_materials(task_dir)),
        "session_count": len(_read_sessions(task_dir)),
        "children": children,
    }


# ─── API ─────────────────────────────────────────────────────────────────

class WorkspaceTree(BaseModel):
    root: Path
    initialized: bool
    tasks: list[dict]  # 顶级任务列表，每个含 children 递归


@router.get("", response_model=WorkspaceTree)
def get_workspace():
    """惰性 init + 返回整棵树。"""
    root = _ensure_workspace_root()
    tasks = []
    for child in sorted(root.iterdir(), key=lambda x: x.name):
        if child.name.startswith(".") or child.name in RESERVED_FILES:
            continue
        if _is_task_dir(child):
            tasks.append(_build_tree(child))
    return WorkspaceTree(root=root, initialized=True, tasks=tasks)


class CreateTaskRequest(BaseModel):
    name: str
    kind: TaskKind = "poi"
    desc: str = ""
    parent_path: str = ""  # 空 = 顶级


class CreateTaskResponse(BaseModel):
    path: str
    abs_path: Path


@router.post("/tasks", response_model=CreateTaskResponse, status_code=201)
def create_task(body: CreateTaskRequest):
    name = _validate_name(body.name)
    if body.kind not in VALID_KINDS:
        raise HTTPException(400, f"invalid kind: {body.kind}")

    parent = _resolve_path(body.parent_path) if body.parent_path else _ensure_workspace_root()
    if body.parent_path and not _is_task_dir(parent):
        raise HTTPException(404, f"parent task not found: {body.parent_path}")

    target = parent / name
    if target.exists():
        raise HTTPException(409, f"task already exists: {target.relative_to(WORKSPACE_ROOT)}")

    target.mkdir(parents=True)
    (target / "materials").mkdir()
    (target / "docs").mkdir()
    _write_task_meta(target, {
        "kind": body.kind,
        "name": name,
        "desc": body.desc,
        "status": "active",
        "created_at": time.time(),
        "parent": body.parent_path or None,
    })
    (target / "sessions.json").write_text("[]", encoding="utf-8")

    rel = str(target.relative_to(WORKSPACE_ROOT))
    return CreateTaskResponse(path=rel, abs_path=target)


@router.delete("/tasks/{task_path:path}")
def delete_task(task_path: str):
    p = _resolve_path(task_path)
    if p == WORKSPACE_ROOT or not _is_task_dir(p):
        raise HTTPException(404, f"task not found: {task_path}")
    shutil.rmtree(p)
    return {"ok": True, "deleted": task_path}


class TaskDetail(BaseModel):
    name: str
    path: str
    kind: str
    desc: str
    status: str
    created_at: float
    docs: list[dict]
    materials: list[dict]
    sessions: list[dict]


@router.get("/tasks/{task_path:path}", response_model=TaskDetail)
def get_task(task_path: str):
    p = _resolve_path(task_path)
    if not _is_task_dir(p):
        raise HTTPException(404, f"task not found: {task_path}")
    meta = _read_task_meta(p)
    return TaskDetail(
        name=p.name,
        path=task_path,
        kind=meta.get("kind", "poi"),
        desc=meta.get("desc", ""),
        status=meta.get("status", ""),
        created_at=meta.get("created_at", 0),
        docs=_list_docs(p),
        materials=_list_materials(p),
        sessions=_read_sessions(p),
    )


# ─── 文档归档 ─────────────────────────────────────────────────────────────

class LinkDocRequest(BaseModel):
    src_filename: str  # docs/ 顶层文件名
    move: bool = True  # True=移动到任务，False=复制


@router.post("/tasks/{task_path:path}/link-doc")
def link_doc(task_path: str, body: LinkDocRequest, settings=Depends(get_settings)):
    """把 webapp 顶层 docs/<filename> 归档到任务的 docs/ 下。"""
    p = _resolve_path(task_path)
    if not _is_task_dir(p):
        raise HTTPException(404, f"task not found: {task_path}")
    src = settings.project_root / "docs" / body.src_filename
    if not src.exists() or not src.is_file():
        raise HTTPException(404, f"source doc not found: {body.src_filename}")
    if not body.src_filename.endswith(".html"):
        raise HTTPException(400, "only .html allowed")
    dst = p / "docs" / body.src_filename
    if dst.exists():
        raise HTTPException(409, f"already exists in task: {dst.name}")
    if body.move:
        shutil.move(str(src), str(dst))
    else:
        shutil.copy2(str(src), str(dst))
    return {"ok": True, "task_path": task_path, "filename": body.src_filename, "moved": body.move}


# ─── 素材上传 ─────────────────────────────────────────────────────────────

@router.post("/tasks/{task_path:path}/materials")
async def upload_material(task_path: str, file: UploadFile = File(...)):
    p = _resolve_path(task_path)
    if not _is_task_dir(p):
        raise HTTPException(404, f"task not found: {task_path}")
    mat_dir = p / "materials"
    mat_dir.mkdir(exist_ok=True)
    raw_name = file.filename or "unnamed"
    safe_name = raw_name.replace("/", "_").replace("\\", "_")
    if safe_name.startswith("."):
        safe_name = "_" + safe_name
    target = mat_dir / safe_name
    # 重名加时间戳避免覆盖
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        target = mat_dir / f"{stem}_{int(time.time())}{suffix}"
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(413, "file too large (>100MB)")
    target.write_bytes(content)
    return {"ok": True, "filename": target.name, "size_bytes": len(content)}


# ─── 关联对话 ─────────────────────────────────────────────────────────────

class ImportSpecsResponse(BaseModel):
    created_tasks: list[str]
    imported_specs: list[dict]
    skipped: list[dict]


@router.post("/import-specs", response_model=ImportSpecsResponse)
def import_existing_specs(settings=Depends(get_settings)):
    """扫 specs/*.spec.json，按 level_id 聚类成 POI 任务，spec 文件复制到 task/materials/。
    不动原 specs/；重复导入跳过（filename 已存在）。
    """
    specs_dir = settings.project_root / "specs"
    if not specs_dir.exists():
        return ImportSpecsResponse(created_tasks=[], imported_specs=[], skipped=[])
    _ensure_workspace_root()

    buckets: dict[str, list[Path]] = {}
    for p in specs_dir.glob("*.spec.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
        level_id = meta.get("level_id") or data.get("level_id") or meta.get("poi_id") or "unsorted"
        if not isinstance(level_id, str) or not level_id.strip() or level_id == "[待对接]":
            level_id = "unsorted"
        buckets.setdefault(level_id, []).append(p)

    created: list[str] = []
    imported: list[dict] = []
    skipped: list[dict] = []
    for level_id, spec_files in buckets.items():
        task_name = level_id.replace("/", "_").replace("\\", "_")[:80] or "unsorted"
        if task_name.startswith("."):
            task_name = "_" + task_name
        task_dir = WORKSPACE_ROOT / task_name
        if not task_dir.exists():
            task_dir.mkdir()
            (task_dir / "materials").mkdir()
            (task_dir / "docs").mkdir()
            _write_task_meta(task_dir, {
                "kind": "poi",
                "name": task_name,
                "desc": f"从 specs/ 自动归档（{len(spec_files)} 个 spec）",
                "status": "imported",
                "created_at": time.time(),
                "parent": None,
                "source": "import-specs",
            })
            (task_dir / "sessions.json").write_text("[]", encoding="utf-8")
            created.append(task_name)

        mat_dir = task_dir / "materials"
        mat_dir.mkdir(exist_ok=True)
        for src in spec_files:
            dst = mat_dir / src.name
            if dst.exists():
                skipped.append({"spec_id": src.stem.replace(".spec", ""), "reason": "already exists"})
                continue
            try:
                shutil.copy2(str(src), str(dst))
                imported.append({
                    "spec_id": src.stem.replace(".spec", ""),
                    "level_id": level_id,
                    "dest_filename": src.name,
                    "task_path": task_name,
                })
            except OSError as e:
                skipped.append({"spec_id": src.stem.replace(".spec", ""), "reason": str(e)})

    return ImportSpecsResponse(created_tasks=created, imported_specs=imported, skipped=skipped)


class ImportDocsResponse(BaseModel):
    imported_docs: list[dict]
    skipped: list[dict]


@router.post("/import-docs", response_model=ImportDocsResponse)
def import_existing_docs(settings=Depends(get_settings)):
    """扫顶层 docs/*.html，按文件名"猜"应归到哪个任务（含 task_name 字符串 → 该任务）。
    无法判断的归到 unsorted POI。文件复制不移动。
    """
    docs_dir = settings.project_root / "docs"
    if not docs_dir.exists():
        return ImportDocsResponse(imported_docs=[], skipped=[])
    _ensure_workspace_root()

    # 收集现有顶级任务名做匹配候选
    existing_tasks: list[str] = []
    for child in WORKSPACE_ROOT.iterdir():
        if _is_task_dir(child):
            existing_tasks.append(child.name)
    # 长名优先，避免短前缀误命中
    existing_tasks.sort(key=len, reverse=True)

    imported: list[dict] = []
    skipped: list[dict] = []
    for src in docs_dir.glob("*.html"):
        matched_task = None
        for tn in existing_tasks:
            if tn in src.name:
                matched_task = tn
                break

        if matched_task is None:
            # 没匹配上 → 归到 unsorted POI
            matched_task = "unsorted"
            task_dir = WORKSPACE_ROOT / matched_task
            if not task_dir.exists():
                task_dir.mkdir()
                (task_dir / "materials").mkdir()
                (task_dir / "docs").mkdir()
                _write_task_meta(task_dir, {
                    "kind": "poi", "name": matched_task,
                    "desc": "未匹配到任务的文档自动归档处",
                    "status": "imported",
                    "created_at": time.time(),
                    "parent": None, "source": "import-docs",
                })
                (task_dir / "sessions.json").write_text("[]", encoding="utf-8")

        task_dir = WORKSPACE_ROOT / matched_task
        dst = task_dir / "docs" / src.name
        if dst.exists():
            skipped.append({"filename": src.name, "reason": "already exists in task"})
            continue
        try:
            shutil.copy2(str(src), str(dst))
            imported.append({"filename": src.name, "task_path": matched_task})
        except OSError as e:
            skipped.append({"filename": src.name, "reason": str(e)})

    return ImportDocsResponse(imported_docs=imported, skipped=skipped)


class LinkSessionRequest(BaseModel):
    cc_session_id: str
    note: str = ""


@router.post("/tasks/{task_path:path}/link-session")
def link_session(task_path: str, body: LinkSessionRequest):
    p = _resolve_path(task_path)
    if not _is_task_dir(p):
        raise HTTPException(404, f"task not found: {task_path}")
    if not re.match(r"^[a-fA-F0-9-]{36}$", body.cc_session_id):
        raise HTTPException(400, "invalid cc_session_id format")
    sessions = _read_sessions(p)
    # 去重
    for s in sessions:
        if s.get("cc_session_id") == body.cc_session_id:
            s["note"] = body.note or s.get("note", "")
            (p / "sessions.json").write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "updated": True}
    sessions.append({
        "cc_session_id": body.cc_session_id,
        "note": body.note,
        "linked_at": time.time(),
    })
    (p / "sessions.json").write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "added": True}
