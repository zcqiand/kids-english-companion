"""跟读（M03）与发音练习（M04）路由。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from kids_english.agent import practice
from kids_english.api.helpers import child_or_404, get_engine, get_store, judge_llm

router = APIRouter(prefix="/api", tags=["practice"])


class ReadalongEvaluateIn(BaseModel):
    story_id: str
    page_index: int = Field(ge=0)
    transcript: str = Field(min_length=1, max_length=500)


class PronunciationEvaluateIn(BaseModel):
    word: str = Field(min_length=1, max_length=40)
    transcript: str = Field(min_length=1, max_length=200)


@router.get("/children/{child_id}/readalong/next")
def next_readalong(child_id: str, request: Request, story_id: str | None = None):
    child_or_404(request, child_id)
    result = practice.next_readalong(
        get_store(request), get_engine(request), child_id, story_id=story_id
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "story 不存在"))
    return result


@router.get("/stories/{story_id}/pages/{page_index}")
def get_story_page(story_id: str, page_index: int, request: Request):
    got = practice.get_page(get_store(request), story_id, page_index)
    if got is None:
        raise HTTPException(status_code=404, detail="story 或页码不存在")
    story = got["story"]
    return {
        "ok": True,
        "story": {
            "id": story["id"],
            "title_en": story["title_en"],
            "title_cn": story["title_cn"],
            "character_id": story["character_id"],
            "theme": story["theme"],
            "total_pages": len(story["pages"]),
        },
        "page_index": page_index,
        "page": got["page"],
    }


@router.post("/children/{child_id}/readalong/evaluate")
def evaluate_readalong(child_id: str, body: ReadalongEvaluateIn, request: Request):
    child_or_404(request, child_id)
    result = practice.evaluate_readalong(
        judge_llm(request),
        get_store(request),
        get_engine(request),
        child_id,
        body.story_id,
        body.page_index,
        body.transcript,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "story 或页码不存在"))
    return result


@router.get("/children/{child_id}/pronunciation/words")
def pronunciation_words(child_id: str, request: Request, k: int = 5):
    child_or_404(request, child_id)
    return {"ok": True, "words": practice.pronunciation_words(
        get_store(request), get_engine(request), child_id, k=max(1, min(k, 10))
    )}


@router.post("/children/{child_id}/pronunciation/evaluate")
def evaluate_pronunciation(child_id: str, body: PronunciationEvaluateIn, request: Request):
    child_or_404(request, child_id)
    result = practice.evaluate_pronunciation(
        judge_llm(request),
        get_store(request),
        get_engine(request),
        child_id,
        body.word,
        body.transcript,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "word 不在词库"))
    return result
