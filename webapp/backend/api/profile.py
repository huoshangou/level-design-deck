"""设计者档案 API：让用户填一次"我叫什么"，之后 chat 自动注入到 cc。

存储位置：~/Documents/level-design-workspace/_profile.json（跟 workspace 一起，重装 webapp 不丢）
"""

from __future__ import annotations
import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/profile", tags=["profile"])

PROFILE_PATH = Path.home() / "Documents" / "level-design-workspace" / "_profile.json"


class DesignerProfile(BaseModel):
    designer_cn: str = ""           # 公司用名（如「芬里尔」），AI 写文档署名用这个
    designer_en_short: str = ""     # 英文缩写（如「FNR」），资产命名 / 文件名用
    designer_full_en: str = ""      # 英文全名（可选）
    notes: str = Field("", description="给 AI 看的额外人物 context（如「我主攻关卡设计」），可选")
    updated_at: float = 0


def _read_profile() -> DesignerProfile:
    if not PROFILE_PATH.exists():
        return DesignerProfile()
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        return DesignerProfile(**{k: data.get(k, "") for k in DesignerProfile.model_fields})
    except (OSError, json.JSONDecodeError, ValueError):
        return DesignerProfile()


def _write_profile(p: DesignerProfile) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(p.model_dump_json(indent=2), encoding="utf-8")


@router.get("", response_model=DesignerProfile)
def get_profile():
    return _read_profile()


@router.put("", response_model=DesignerProfile)
def update_profile(body: DesignerProfile):
    body.updated_at = time.time()
    _write_profile(body)
    return body


def profile_prompt_block() -> str:
    """给 chat.py 用：生成注入到用户消息前缀的一段 context。空 profile 返回空串。"""
    p = _read_profile()
    parts = []
    if p.designer_cn:
        parts.append(f"中文名「{p.designer_cn}」")
    if p.designer_en_short:
        parts.append(f"英文缩写「{p.designer_en_short}」")
    if p.designer_full_en:
        parts.append(f"英文全名「{p.designer_full_en}」")
    if not parts:
        return ""
    header = "当前设计者：" + "、".join(parts)
    if p.notes:
        header += f"。备注：{p.notes}"
    return header + "。涉及署名 / 资产命名时直接使用这些值，不要再问用户也不要用其他名字。\n\n"
