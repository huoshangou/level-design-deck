"""Chat 附件上传 + 自动转 text 格式（调 ~/scripts/*2text.py）。

存储路径：<uploads_dir>/<client_id>/<file_id>__<safe_name>
转换：docx/pptx/xlsx/html → 同目录下 <stem>.extracted.txt
text 类（md/txt/json/py 等）原文件即给 cc Read。
binary（图片/zip/PDF 等）暂不支持，cc Read 二进制会失败。
"""

from __future__ import annotations
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.agent.base import AgentRunner
from backend.deps import get_agent, get_settings

router = APIRouter(tags=["files"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024     # 20 MB 硬限制（更大 cc 装不进 context）
EXTRACT_TRUNCATE_CHARS = 200_000        # 提取产物 > 200K 字符截断（≈ 50K token）

SCRIPTS_DIR = Path.home() / "scripts"
EXTRACTORS = {
    ".docx": "docx2text.py",
    ".pptx": "pptx2text.py",
    ".xlsx": "xlsx2text.py",
    ".html": "html2text.py",
    ".htm":  "html2text.py",
}
TEXT_DIRECT_OK = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".py", ".ts", ".tsx",
    ".js", ".jsx", ".css", ".csv", ".log", ".sh", ".toml", ".ini",
}

_session_files: dict[str, list[dict]] = {}

_SAFE_FN_RE = re.compile(r"[^a-zA-Z0-9_.\-一-鿿]")


def _safe_name(name: str) -> str:
    s = _SAFE_FN_RE.sub("_", name)
    return s.lstrip(".") or "file"


def _classify(suffix: str) -> tuple[str, bool]:
    """suffix → (kind, needs_conversion)"""
    suffix = suffix.lower()
    if suffix in EXTRACTORS:
        return (suffix.lstrip("."), True)
    if suffix in TEXT_DIRECT_OK:
        return ("text", False)
    return ("binary", False)


def _convert(src: Path, dst_dir: Path, suffix: str) -> Path | None:
    script = SCRIPTS_DIR / EXTRACTORS[suffix.lower()]
    if not script.exists():
        return None
    out_path = dst_dir / (src.stem + ".extracted.txt")
    python_cmd = "python3" if shutil.which("python3") else "python"
    try:
        subprocess.run(
            [python_cmd, str(script), str(src), str(out_path)],
            check=True, capture_output=True, timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    if not out_path.exists():
        return None
    # 超 200K 字符截断（防止 cc Read 进去爆 context）
    try:
        text = out_path.read_text(encoding="utf-8", errors="replace")
        if len(text) > EXTRACT_TRUNCATE_CHARS:
            warning = (
                f"\n\n[⚠️ 文件已截断：原 {len(text):,} 字符 → 截断至 {EXTRACT_TRUNCATE_CHARS:,} 字符。"
                f"如需完整内容请拆分文件或在对话中具体指明要看哪段]\n"
            )
            out_path.write_text(text[:EXTRACT_TRUNCATE_CHARS] + warning, encoding="utf-8")
    except OSError:
        pass
    return out_path


class AttachedFileModel(BaseModel):
    file_id: str
    original_name: str
    stored_path: str
    text_path: str | None
    size_bytes: int
    kind: str
    uploaded_at: float


@router.post("/api/sessions/{client_id}/files", response_model=AttachedFileModel)
async def upload_file(
    client_id: str,
    file: UploadFile = File(...),
    agent: AgentRunner = Depends(get_agent),
):
    if not agent.has_session(client_id):
        raise HTTPException(404, f"session not found: {client_id}")

    s = get_settings()
    sess_dir = s.uploads_dir / client_id
    sess_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex[:12]
    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower()
    safe = _safe_name(original_name)
    stored = sess_dir / f"{file_id}__{safe}"

    # 流式写入并卡 20MB 上限；超限删半成品 → 413
    total = 0
    with stored.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                f.close()
                stored.unlink(missing_ok=True)
                raise HTTPException(
                    413,
                    f"文件过大（>{MAX_UPLOAD_BYTES // (1024*1024)}MB），请拆分后再传。"
                    f"超大附件会让 AI 处理时上下文爆掉。",
                )
            f.write(chunk)

    kind, needs_conv = _classify(suffix)
    text_path: Path | None = None
    if needs_conv:
        text_path = _convert(stored, sess_dir, suffix)
    elif kind == "text":
        text_path = stored

    record = {
        "file_id": file_id,
        "original_name": original_name,
        "stored_path": str(stored),
        "text_path": str(text_path) if text_path else None,
        "size_bytes": stored.stat().st_size,
        "kind": kind,
        "uploaded_at": time.time(),
    }
    _session_files.setdefault(client_id, []).append(record)
    return record


@router.get("/api/sessions/{client_id}/files")
def list_files(client_id: str, agent: AgentRunner = Depends(get_agent)):
    if not agent.has_session(client_id):
        raise HTTPException(404, f"session not found: {client_id}")
    return {"files": _session_files.get(client_id, [])}


@router.delete("/api/sessions/{client_id}/files/{file_id}")
def delete_file(client_id: str, file_id: str, agent: AgentRunner = Depends(get_agent)):
    if not agent.has_session(client_id):
        raise HTTPException(404, f"session not found: {client_id}")
    files = _session_files.get(client_id, [])
    for i, f in enumerate(files):
        if f["file_id"] == file_id:
            try:
                Path(f["stored_path"]).unlink(missing_ok=True)
                if f["text_path"] and f["text_path"] != f["stored_path"]:
                    Path(f["text_path"]).unlink(missing_ok=True)
            except OSError:
                pass
            files.pop(i)
            return {"ok": True}
    raise HTTPException(404, f"file not found: {file_id}")


def get_attached_files(client_id: str) -> list[dict]:
    """供 chat.py 调用：当前 session 的附件列表，cc 可主动 Read 的优先。"""
    return _session_files.get(client_id, [])


def clear_session_files(client_id: str) -> None:
    """session 结束时清理。"""
    files = _session_files.pop(client_id, [])
    for f in files:
        try:
            Path(f["stored_path"]).unlink(missing_ok=True)
            if f.get("text_path") and f["text_path"] != f["stored_path"]:
                Path(f["text_path"]).unlink(missing_ok=True)
        except OSError:
            pass
