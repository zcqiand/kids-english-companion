"""对话流程图（M02.F01 v2 内核）：节点/条件边/护栏语义钉。"""
from __future__ import annotations

import queue
from datetime import date

from kids_english.agent.graph import build_graph
from kids_english.llm import FakeLLM, ToolCall, assistant_msg

TODAY = date(2026, 10, 4)


def _graph(store, engine, child_id, llm):
    return build_graph(llm, store, engine, child_id, today=TODAY)


def _run(store, engine, child_id, llm, text="你好", session_id=None):
    events = queue.SimpleQueue()
    state = {"session_id": session_id, "text": text}
    _graph(store, engine, child_id, llm).invoke(
        state, {"configurable": {"events": events}}
    )
    # 直连 invoke 无 worker 放 None 哨兵，用 get_nowait 排空（哨兵属接线层契约）
    out = []
    while True:
        try:
            out.append(events.get_nowait())
        except queue.Empty:
            return out


def _tool_turn(i):
    return assistant_msg(tool_calls=[ToolCall(
        id=f"call_{i}", name="record_word_event",
        arguments={"word": "apple", "kind": "encounter", "success": True},
    )])


def test_exhaustion_after_four_tool_rounds(store, engine, child_id):
    """Review Focus 1：第 4 轮工具执行完才报错（v1 range(4) for-else 语义）。"""
    llm = FakeLLM(turns=[_tool_turn(1), _tool_turn(2), _tool_turn(3), _tool_turn(4)])
    events = _run(store, engine, child_id, llm, text="apple apple apple apple")
    types = [e["type"] for e in events]
    assert types.count("tool") == 4
    assert types[-2] == "error" and "太长" in events[-2]["message"]
    assert types[-1] == "done"
    assert len(llm.calls) == 4
    assert store.get_mastery(child_id, "w_apple") is not None


def test_fatal_child_missing_never_reaches_llm(store, engine):
    """Review Focus 5：事件恰为 [error]，无 session 无 done，零 LLM 调用。"""
    llm = FakeLLM(turns=[assistant_msg("Hi")])
    events = _run(store, engine, "c_missing", llm, text="hi")
    assert events == [{"type": "error", "message": "孩子档案不存在"}]
    assert llm.calls == []


def test_empty_assistant_content_persists_empty_and_done(store, engine, child_id):
    """Review Focus 3：空 content 落 ""，word_focus 零条，done 正常。"""
    llm = FakeLLM(turns=[assistant_msg("")])
    events = _run(store, engine, child_id, llm)
    assert events[0]["type"] == "session"
    assert events[-1] == {"type": "done"}
    sid = events[0]["session_id"]
    msgs = store.get_messages(sid, limit=10)
    assert msgs[-1]["role"] == "assistant" and msgs[-1]["content"] == ""
    assert not [e for e in events if e["type"] == "word_focus"]


def test_deltas_pass_through_across_tool_rounds(store, engine, child_id):
    """Review Focus 4：两轮 delta 顺序透传，第 2 次请求消息链含 tool 消息。"""
    llm = FakeLLM(turns=[
        assistant_msg("first round", tool_calls=[ToolCall(
            id="c1", name="get_progress", arguments={},
        )]),
        assistant_msg("second round"),
    ])
    events = _run(store, engine, child_id, llm)
    types = [e["type"] for e in events]
    assert types[0] == "session" and types[-1] == "done"
    assert types.index("delta") < types.index("tool")
    assert "delta" in types[types.index("tool"):]
    assert len(llm.calls) == 2
    assert "tool" in [m["role"] for m in llm.calls[1]["messages"]]


def test_events_none_invoke_is_silent(store, engine, child_id):
    """events=None 静默通道（HR 试点同款）：同步 invoke 不炸、结构化结果在 State。"""
    llm = FakeLLM(turns=[assistant_msg("Hello")])
    result = _graph(store, engine, child_id, llm).invoke(
        {"session_id": None, "text": "hi"}, {"configurable": {"events": None}}
    )
    assert result["final"]["content"] == "Hello"
