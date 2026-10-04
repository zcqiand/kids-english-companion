"""工具执行（M02.F01.I02）：记事件 / 读进度 / 收会话，失败永远返回 dict 不抛。"""
from __future__ import annotations

from datetime import date

from kids_english.agent.tools import ToolContext, execute_tool

TODAY = date(2026, 10, 4)


def _ctx(store, engine, child_id, session_id="s_x") -> ToolContext:
    return ToolContext(store=store, engine=engine, child_id=child_id, session_id=session_id, today=TODAY)


def test_record_word_event_updates_mastery(store, engine, child_id):
    ctx = _ctx(store, engine, child_id)
    result = execute_tool("record_word_event", {"word": "apple", "kind": "free_use", "success": True}, ctx)
    assert result["ok"] is True
    assert result["word"] == "apple"
    assert result["status"] == "学习中"
    m = store.get_mastery(child_id, "w_apple")
    assert m is not None and m["box"] == 1


def test_record_unknown_word_returns_error_dict(store, engine, child_id):
    ctx = _ctx(store, engine, child_id)
    result = execute_tool("record_word_event", {"word": "flibbertigibbet", "kind": "free_use", "success": True}, ctx)
    assert result == {"ok": False, "error": "word 不在词库: flibbertigibbet"}


def test_record_bad_kind_rejected(store, engine, child_id):
    ctx = _ctx(store, engine, child_id)
    result = execute_tool("record_word_event", {"word": "apple", "kind": "magic", "success": True}, ctx)
    assert result["ok"] is False
    assert "kind 非法" in result["error"]


def test_unknown_tool_returns_error_dict(store, engine, child_id):
    result = execute_tool("launch_missile", {}, _ctx(store, engine, child_id))
    assert result["ok"] is False and "unknown tool" in result["error"]


def test_get_progress_shape(store, engine, child_id):
    engine.record_event(child_id, "w_apple", "echo_attempt", True, "", today=TODAY)
    result = execute_tool("get_progress", {}, _ctx(store, engine, child_id))
    assert result["due"] == []  # 刚学 due 在明天
    assert result["streak_days"] == 0  # streak 锚会话日期，无会话为 0
    assert result["fresh_suggestion"][0]["word"]


def test_end_session_persists_summary(store, engine, child_id):
    sid = store.create_session(child_id, "maisy")
    ctx = _ctx(store, engine, child_id, sid)
    result = execute_tool(
        "end_session", {"words_used": ["apple"], "words_struggled": ["banana"], "notes": "开心"}, ctx
    )
    assert result["ok"] is True
    session = store.get_session(sid)
    assert session["ended_at"] is not None
    assert "apple" in session["summary"] and "开心" in session["summary"]


def test_end_session_twice_is_idempotent(store, engine, child_id):
    sid = store.create_session(child_id, "maisy")
    ctx = _ctx(store, engine, child_id, sid)
    first = execute_tool("end_session", {"notes": "a"}, ctx)
    second = execute_tool("end_session", {"notes": "b"}, ctx)
    assert first["ok"] and second["ok"] and second.get("already_ended") is True
