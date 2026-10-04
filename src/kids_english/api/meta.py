"""元数据路由（M02.F02 角色库 / M03.F01 故事库）。"""
from __future__ import annotations

from fastapi import APIRouter

from kids_english.characters import CHARACTERS
from kids_english.content import seed_stories

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/characters")
def list_characters():
    return {"ok": True, "characters": CHARACTERS}


@router.get("/stories")
def list_stories():
    stories = [
        {
            "id": s["id"],
            "title_en": s["title_en"],
            "title_cn": s["title_cn"],
            "character_id": s["character_id"],
            "theme": s["theme"],
            "total_pages": len(s["pages"]),
        }
        for s in seed_stories()
    ]
    return {"ok": True, "stories": stories}
