"""API 端到端（mock 模式全链路：TestClient，无 Key 无网）。"""
from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from kids_english.config import Settings
from kids_english.main import create_app

TODAY = date(2026, 10, 4)


@pytest.fixture()
def client(tmp_path):
    settings = Settings(
        llm_mode="mock", llm_base_url="", llm_api_key="", llm_model="",
        db_path=str(tmp_path / "api.db"), app_port=8801,
    )
    return TestClient(create_app(settings))


def _make_child(client, name="乐乐") -> str:
    resp = client.post("/api/children", json={"name": name, "age": 5, "character_id": "maisy"})
    assert resp.status_code == 200
    return resp.json()["child"]["id"]


def _sse_events(resp) -> list[dict]:
    out = []
    for chunk in resp.text.split("\n\n"):
        chunk = chunk.strip()
        if chunk.startswith("data: "):
            out.append(json.loads(chunk[len("data: "):]))
    return out


# ---- 元数据与档案 ----

def test_health(client):
    assert client.get("/api/health").json() == {"ok": True, "mode": "mock"}


def test_meta(client):
    chars = client.get("/api/characters").json()["characters"]
    assert {c["id"] for c in chars} >= {"maisy", "peppa"}
    stories = client.get("/api/stories").json()["stories"]
    assert stories and all(s["total_pages"] >= 1 for s in stories)


def test_create_child_and_list(client):
    cid = _make_child(client)
    children = client.get("/api/children").json()["children"]
    assert [c["id"] for c in children] == [cid]
    assert children[0]["streak_days"] == 0


def test_create_child_bad_character(client):
    resp = client.post("/api/children", json={"name": "团团", "age": 4, "character_id": "mickey"})
    assert resp.status_code == 400


def test_progress_404(client):
    assert client.get("/api/children/c_missing/progress").status_code == 404


# ---- 对话（mock LLM 全链路 SSE）----

def test_chat_flow_records_and_closes_session(client):
    cid = _make_child(client)
    # 先让 apple 进入已学状态（模拟此前学过）
    client.post(f"/api/children/{cid}/pronunciation/evaluate", json={"word": "apple", "transcript": "apple"})

    resp = client.post(f"/api/children/{cid}/chat", json={"text": "I like apple!"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(resp)
    types = [e["type"] for e in events]
    assert types[0] == "session" and types[-1] == "done"
    assert "delta" in types
    session_id = events[0]["session_id"]

    # MockLLM 把 free_use 记进引擎 → 进度可查
    dashboard = client.get(f"/api/children/{cid}/progress").json()["dashboard"]
    assert dashboard["stats"]["total_known"] >= 1

    # 结束会话
    end = client.post(f"/api/sessions/{session_id}/end", json={"child_id": cid, "notes": "今天很开心"})
    assert end.status_code == 200 and end.json()["ok"] is True
    again = client.post(f"/api/sessions/{session_id}/end", json={"child_id": cid})
    assert again.json().get("already_ended") is True


def test_chat_unknown_child_404(client):
    resp = client.post("/api/children/c_missing/chat", json={"text": "hi"})
    assert resp.status_code == 404


# ---- 跟读 ----

def test_readalong_flow(client):
    cid = _make_child(client)
    nxt = client.get(f"/api/children/{cid}/readalong/next").json()
    assert nxt["ok"] is True and nxt["page_index"] == 0
    story_id = nxt["story"]["id"]

    page = client.get(f"/api/stories/{story_id}/pages/0").json()
    assert page["ok"] and page["page"]["en"]

    transcript = page["page"]["en"]
    result = client.post(
        f"/api/children/{cid}/readalong/evaluate",
        json={"story_id": story_id, "page_index": 0, "transcript": transcript},
    ).json()
    assert result["ok"] is True and all(r["ok"] for r in result["results"])

    assert client.get(f"/api/stories/{story_id}/pages/99").status_code == 404


def test_readalong_next_bad_story(client):
    cid = _make_child(client)
    assert client.get(f"/api/children/{cid}/readalong/next", params={"story_id": "st_nope"}).status_code == 404


# ---- 发音 ----

def test_pronunciation_flow(client):
    cid = _make_child(client)
    words = client.get(f"/api/children/{cid}/pronunciation/words").json()["words"]
    assert len(words) == 5
    assert all(w["phonetic"] for w in words)

    result = client.post(
        f"/api/children/{cid}/pronunciation/evaluate", json={"word": words[0]["text"], "transcript": words[0]["text"]}
    ).json()
    assert result["ok"] is True and result["correct"] is True

    miss = client.post(
        f"/api/children/{cid}/pronunciation/evaluate", json={"word": "banana", "transcript": "zebra"}
    ).json()
    assert miss["correct"] is False

    bad = client.post(
        f"/api/children/{cid}/pronunciation/evaluate", json={"word": "flibbertigibbet", "transcript": "x"}
    )
    assert bad.status_code == 400
