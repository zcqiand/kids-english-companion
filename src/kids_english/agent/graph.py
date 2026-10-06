"""对话流程 LangGraph 图（M02.F01）：进度驱动对话的工具轮状态机。

v2 编排内核（书 ch9 流程视角，复制自 hr-interview 试点 §3 图模式）：
START→begin→(fatal?)→ask⇄execute_tools→exhausted|finish→END。
无 checkpointer：对话历史每回合从 store（SQLite）重建，状态单回合即弃。
SSE 事件经 config["configurable"]["events"] 队列旁路，形状与 v1 一致：
session / delta / reasoning / tool / word_focus / done / error。

v1 等价锚（源 tutor.py:40-87，迁移时逐行核对）：
session 先于用户落库与首次 LLM；history limit 20；工具轮上限 4、
第 4 轮工具执行完才报错；tool 事件逐 call 产出、消息链 final→tool_msgs；
无工具 final 先持久化再 word_focus（≤3）后 done；异常→error+done；
fatal（孩子不存在）→仅 error。
"""
from __future__ import annotations

import json
from datetime import date
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from kids_english.agent.prompts import build_system_prompt
from kids_english.agent.tools import TOOL_SPECS, ToolContext, execute_tool
from kids_english.characters import get_character
from kids_english.llm import LLMClient, tool_msg
from kids_english.progress import MasteryEngine
from kids_english.store import Store

__all__ = ["TutorState", "build_graph"]

_HISTORY_LIMIT = 20
_MAX_ROUNDS = 4


class TutorState(TypedDict, total=False):
    session_id: str | None
    text: str
    messages: list[dict]
    rounds: int
    final: dict
    fatal: bool


def _emit(config: dict, event: dict) -> None:
    events = config.get("configurable", {}).get("events")
    if events is not None:
        events.put(event)


def build_graph(
    llm: LLMClient,
    store: Store,
    engine: MasteryEngine,
    child_id: str,
    today: date | None = None,
):
    today = today or date.today()

    def begin(state: TutorState, config: dict) -> dict:
        """孩子校验 + 会话确保 + session 事件 + 用户落库 + 组装 messages。"""
        child = store.get_child(child_id)
        if child is None:
            _emit(config, {"type": "error", "message": "孩子档案不存在"})
            return {"fatal": True}
        session_id = state.get("session_id")
        if session_id is None or store.get_session(session_id) is None:
            session_id = store.create_session(child_id, child["character_id"])
        _emit(config, {"type": "session", "session_id": session_id})
        store.append_message(session_id, child_id, "user", state["text"])
        system = build_system_prompt(
            child["character_id"], child["name"], child["age"],
            engine.progress_card(child_id, child["name"], today),
        )
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in store.get_messages(session_id, limit=_HISTORY_LIMIT)
        ]
        return {
            "fatal": False,
            "session_id": session_id,
            "messages": [{"role": "system", "content": system}, *history],
            "rounds": 0,
        }

    def ask(state: TutorState, config: dict) -> dict:
        """一轮流式请求：delta/reasoning 旁路透传，final 进 State。"""
        final: dict = {}
        for ev in llm.chat_stream(messages=state["messages"], tools=TOOL_SPECS):
            if ev["type"] == "final":
                final = ev["message"]
            else:
                _emit(config, ev)
        return {"final": final}

    def execute_tools(state: TutorState, config: dict) -> dict:
        """执行本轮全部工具调用：先逐 call 发 tool 事件，再逐条补 tool 消息。"""
        final = state["final"]
        messages = [*state["messages"], final]
        ctx = ToolContext(
            store=store, engine=engine, child_id=child_id,
            session_id=state["session_id"], today=today,
        )
        results = []
        for call in final["tool_calls"]:
            result = execute_tool(call.name, call.arguments, ctx)
            _emit(config, {"type": "tool", "name": call.name, "brief": _tool_brief(call.name, result)})
            results.append((call, json.dumps(result, ensure_ascii=False)))
        for call, payload in results:
            messages.append(tool_msg(call.id, payload))
        return {"messages": messages, "rounds": state.get("rounds", 0) + 1}

    def exhausted(state: TutorState, config: dict) -> dict:
        """4 轮工具仍未收敛：对孩子说人话后收尾（v1 for-else 语义）。"""
        _emit(config, {"type": "error", "message": "这轮对话太长了，我们休息一下再继续好嘛？"})
        _emit(config, {"type": "done"})
        return {}

    def finish(state: TutorState, config: dict) -> dict:
        """持久化助手回复 + 词库词高亮（≤3）+ done。"""
        assistant_text = state["final"].get("content") or ""
        store.append_message(state["session_id"], child_id, "assistant", assistant_text)
        for ev in _word_focus_events(store, engine, child_id, assistant_text):
            _emit(config, ev)
        _emit(config, {"type": "done"})
        return {}

    def route_after_begin(state: TutorState) -> str:
        return "ask" if not state.get("fatal") else "fatal"

    def route_after_ask(state: TutorState) -> str:
        return "execute_tools" if state["final"].get("tool_calls") else "finish"

    def route_after_execute(state: TutorState) -> str:
        return "exhausted" if state.get("rounds", 0) >= _MAX_ROUNDS else "ask"

    graph = StateGraph(TutorState)
    graph.add_node("begin", begin)
    graph.add_node("ask", ask)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("exhausted", exhausted)
    graph.add_node("finish", finish)
    graph.add_edge(START, "begin")
    graph.add_conditional_edges("begin", route_after_begin, {"ask": "ask", "fatal": END})
    graph.add_conditional_edges("ask", route_after_ask, {"execute_tools": "execute_tools", "finish": "finish"})
    graph.add_conditional_edges("execute_tools", route_after_execute, {"ask": "ask", "exhausted": "exhausted"})
    graph.add_edge("exhausted", END)
    graph.add_edge("finish", END)
    return graph.compile()


def _word_focus_events(
    store: Store, engine: MasteryEngine, child_id: str, text: str
) -> list[dict]:
    """角色回复里出现的词库词 → 前端高亮（最多 3 个）。搬自 v1 tutor.py:122-140。"""
    from kids_english.progress import STATUS_CN, status_of

    lowered = f" {text.lower()} "
    events: list[dict] = []
    for word in store.list_words():
        token = f" {word['text'].lower()} "
        if token in lowered or f"{word['text'].lower()}!" in lowered:
            m = store.get_mastery(child_id, word["id"])
            events.append(
                {
                    "type": "word_focus",
                    "word": word["text"],
                    "meaning": word["meaning_cn"],
                    "status": STATUS_CN[status_of(m["box"])] if m else "新词",
                }
            )
            if len(events) >= 3:
                break
    return events


def _tool_brief(name: str, result: dict) -> str:
    """工具事件的一句话简报。搬自 v1 tutor.py:151-160，逐字保留。"""
    if name == "record_word_event":
        if result.get("ok"):
            return f"{result['word']} → {result['status']}"
        return f"记录失败：{result.get('error', '')}"
    if name == "get_progress":
        return "读取了学习进度"
    if name == "end_session":
        return f"会话结束，连击 {result.get('streak_days', 0)} 天"
    return name
