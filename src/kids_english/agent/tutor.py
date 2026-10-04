"""角色对话 Agent 循环（M02.F01）：SSE 事件流 + 工具调用 + 学习事件记录。

reply() 是 generator，边生成边产出事件（API 层逐条转 SSE，前端实时逐字显示）：
session / delta / reasoning / tool / word_focus / done / error
"""
from __future__ import annotations

import json
from datetime import date
from typing import Iterator

from kids_english.agent.prompts import build_system_prompt
from kids_english.agent.tools import TOOL_SPECS, ToolContext, execute_tool
from kids_english.characters import get_character
from kids_english.llm import LLMClient, tool_msg
from kids_english.progress import MasteryEngine
from kids_english.store import Store

_HISTORY_LIMIT = 20
_MAX_ROUNDS = 4


class ChatTutor:
    def __init__(
        self,
        llm: LLMClient,
        store: Store,
        engine: MasteryEngine,
        child_id: str,
        today: date | None = None,
    ):
        self.llm = llm
        self.store = store
        self.engine = engine
        self.child_id = child_id
        self.today = today or date.today()

    # ---- public ----

    def reply(self, session_id: str | None, text: str) -> Iterator[dict]:
        """处理一轮孩子发言，逐个产出事件（generator）。"""
        child = self.store.get_child(self.child_id)
        if child is None:
            yield {"type": "error", "message": "孩子档案不存在"}
            return
        if session_id is None or self.store.get_session(session_id) is None:
            session_id = self.store.create_session(self.child_id, child["character_id"])

        yield {"type": "session", "session_id": session_id}
        self.store.append_message(session_id, self.child_id, "user", text)

        messages = self._build_messages(session_id, child)
        ctx = ToolContext(
            store=self.store,
            engine=self.engine,
            child_id=self.child_id,
            session_id=session_id,
            today=self.today,
        )

        try:
            for _round in range(_MAX_ROUNDS):
                final: dict = {}
                for ev in self._stream_round(messages):
                    if ev["type"] == "final":
                        final = ev["message"]
                    else:
                        yield ev
                if not final.get("tool_calls"):
                    assistant_text = final.get("content") or ""
                    self.store.append_message(session_id, self.child_id, "assistant", assistant_text)
                    for ev in self._word_focus_events(assistant_text):
                        yield ev
                    break
                messages.append(final)
                results = []
                for call in final["tool_calls"]:
                    result = execute_tool(call.name, call.arguments, ctx)
                    yield {"type": "tool", "name": call.name, "brief": _tool_brief(call.name, result)}
                    results.append((call, json.dumps(result, ensure_ascii=False)))
                for call, payload in results:
                    messages.append(tool_msg(call.id, payload))
            else:
                yield {"type": "error", "message": "这轮对话太长了，我们休息一下再继续好嘛？"}
        except Exception as exc:  # LLM 网络异常等——对孩子说人话
            yield {"type": "error", "message": f"AI 走神了：{exc}"}
        yield {"type": "done"}

    def end_session(self, session_id: str, notes: str = "家长手动结束") -> dict:
        session = self.store.get_session(session_id)
        if session is None or session["child_id"] != self.child_id:
            return {"ok": False, "error": "session 不存在"}
        if session["ended_at"] is not None:
            return {"ok": True, "streak_days": self.engine.streak(self.child_id, self.today), "already_ended": True}
        self.store.end_session(session_id, notes, self.today)
        return {"ok": True, "streak_days": self.engine.streak(self.child_id, self.today)}

    # ---- internals ----

    def _build_messages(self, session_id: str, child: dict) -> list[dict]:
        character = get_character(child["character_id"])
        card = self.engine.progress_card(self.child_id, child["name"], self.today)
        system = build_system_prompt(
            child["character_id"], child["name"], child["age"], card
        )
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in self.store.get_messages(session_id, limit=_HISTORY_LIMIT)
        ]
        return [{"role": "system", "content": system}, *history]

    def _stream_round(self, messages: list[dict]) -> Iterator[dict]:
        """跑一轮流式请求：逐个产出 delta/reasoning，最后产出 final 消息事件。"""
        final: dict = {}
        for ev in self.llm.chat_stream(messages=messages, tools=TOOL_SPECS):
            if ev["type"] == "final":
                final = ev["message"]
            else:
                yield ev
        yield {"type": "final", "message": final}

    def _word_focus_events(self, text: str) -> list[dict]:
        """角色回复里出现的词库词 → 前端高亮（最多 3 个）。"""
        lowered = f" {text.lower()} "
        events: list[dict] = []
        for word in self.store.list_words():
            token = f" {word['text'].lower()} "
            if token in lowered or f"{word['text'].lower()}!" in lowered:
                m = self.store.get_mastery(self.child_id, word["id"])
                events.append(
                    {
                        "type": "word_focus",
                        "word": word["text"],
                        "meaning": word["meaning_cn"],
                        "status": _status_cn(m),
                    }
                )
                if len(events) >= 3:
                    break
        return events


def _status_cn(m: dict | None) -> str:
    from kids_english.progress import STATUS_CN, status_of

    if m is None:
        return "新词"
    return STATUS_CN[status_of(m["box"])]


def _tool_brief(name: str, result: dict) -> str:
    if name == "record_word_event":
        if result.get("ok"):
            return f"{result['word']} → {result['status']}"
        return f"记录失败：{result.get('error', '')}"
    if name == "get_progress":
        return "读取了学习进度"
    if name == "end_session":
        return f"会话结束，连击 {result.get('streak_days', 0)} 天"
    return name
