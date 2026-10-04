"""function calling 工具表与执行（M02.F01.I02）。

工具只做三件事：记事件 / 读进度 / 收会话。任何失败都返回 {"ok": false, "error": ...}，
把错误交回给模型自己调整，绝不在循环里抛异常打断对话。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from kids_english.progress import STATUS_CN, MasteryEngine
from kids_english.store import Store

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "record_word_event",
            "description": "记录孩子的一次单词学习事件（掌握度会自动更新）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "英语单词，如 apple"},
                    "kind": {
                        "type": "string",
                        "enum": ["encounter", "free_use", "echo_attempt", "pronunciation_attempt"],
                        "description": "encounter=你带出了这个词; free_use=孩子主动说了; echo_attempt=跟读; pronunciation_attempt=发音练习",
                    },
                    "success": {"type": "boolean", "description": "孩子说得/用得对吗"},
                    "note": {"type": "string", "description": "一句话细节，如：读成了 bell"},
                },
                "required": ["word", "kind", "success"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_progress",
            "description": "获取孩子当前学习进度摘要（待复习/薄弱/建议新词/连击）。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "结束本次学习会话并保存总结（孩子告别或家长要求结束时调用）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "words_used": {"type": "array", "items": {"type": "string"}, "description": "孩子这次用到/练过的词"},
                    "words_struggled": {"type": "array", "items": {"type": "string"}, "description": "孩子还吃力的词"},
                    "notes": {"type": "string", "description": "给家长的一句话总结"},
                },
                "required": ["notes"],
            },
        },
    },
]

_KNOWN_TOOLS = {spec["function"]["name"] for spec in TOOL_SPECS}


@dataclass
class ToolContext:
    store: Store
    engine: MasteryEngine
    child_id: str
    session_id: str
    today: date


def execute_tool(name: str, arguments: dict, ctx: ToolContext) -> dict:
    if name not in _KNOWN_TOOLS:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        if name == "record_word_event":
            return _record_word_event(arguments, ctx)
        if name == "get_progress":
            return _get_progress(ctx)
        if name == "end_session":
            return _end_session(arguments, ctx)
    except Exception as exc:  # 工具失败回给模型，不打断对话
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"unhandled tool: {name}"}


def _record_word_event(args: dict, ctx: ToolContext) -> dict:
    word_text = str(args.get("word", "")).strip()
    kind = str(args.get("kind", "")).strip()
    success = bool(args.get("success"))
    note = str(args.get("note", ""))
    word = ctx.store.find_word(word_text)
    if word is None:
        return {"ok": False, "error": f"word 不在词库: {word_text}"}
    if kind not in ("encounter", "free_use", "echo_attempt", "pronunciation_attempt"):
        return {"ok": False, "error": f"kind 非法: {kind}"}
    snap = ctx.engine.record_event(ctx.child_id, word["id"], kind, success, note, today=ctx.today)
    return {"ok": True, "word": word["text"], "status": STATUS_CN[snap["status"]], "due_date": snap["due_date"]}


def _get_progress(ctx: ToolContext) -> dict:
    due = ctx.engine.due_words(ctx.child_id, ctx.today)
    weak = [w for w in ctx.engine.weak_words(ctx.child_id) if w not in due]
    fresh = ctx.engine.new_word_candidates(ctx.child_id, k=2)
    return {
        "due": [w["text"] for w in due],
        "weak": [w["text"] for w in weak],
        "fresh_suggestion": [{"word": w["text"], "meaning": w["meaning_cn"]} for w in fresh],
        "streak_days": ctx.engine.streak(ctx.child_id, ctx.today),
    }


def _end_session(args: dict, ctx: ToolContext) -> dict:
    session = ctx.store.get_session(ctx.session_id)
    if session is None:
        return {"ok": False, "error": "session 不存在"}
    if session["ended_at"] is not None:
        return {"ok": True, "streak_days": ctx.engine.streak(ctx.child_id, ctx.today), "already_ended": True}
    summary = json.dumps(
        {
            "words_used": [str(x) for x in args.get("words_used", [])],
            "words_struggled": [str(x) for x in args.get("words_struggled", [])],
            "notes": str(args.get("notes", "")),
        },
        ensure_ascii=False,
    )
    ctx.store.end_session(ctx.session_id, summary, ctx.today)
    return {"ok": True, "streak_days": ctx.engine.streak(ctx.child_id, ctx.today)}
