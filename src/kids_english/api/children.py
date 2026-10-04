"""孩子档案（M00.F01）与进度看板数据（M01.F03.I02）。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from kids_english.api.helpers import child_or_404, get_engine, get_store
from kids_english.characters import get_character

router = APIRouter(prefix="/api/children", tags=["children"])


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    age: int = Field(ge=2, le=9)
    character_id: str


@router.post("")
def create_child(body: ChildIn, request: Request):
    if get_character(body.character_id) is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"角色不存在: {body.character_id}")
    child_id = get_store(request).create_child(body.name, body.age, body.character_id)
    return {"ok": True, "child": get_store(request).get_child(child_id)}


@router.get("")
def list_children(request: Request):
    store = get_store(request)
    engine = get_engine(request)
    children = []
    for row in store.list_children():
        child = dict(row)
        child["streak_days"] = engine.streak(child["id"])
        children.append(child)
    return {"ok": True, "children": children}


@router.get("/{child_id}/progress")
def get_progress(child_id: str, request: Request):
    child_or_404(request, child_id)
    return {"ok": True, "dashboard": get_engine(request).dashboard(child_id)}
