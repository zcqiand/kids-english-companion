"""对话 Agent 循环（M02.F01）：generator 事件序列 + 工具轮 + 历史落库。"""
from __future__ import annotations

from datetime import date

from kids_english.agent.tutor import ChatTutor
from kids_english.llm import FakeLLM, ToolCall, assistant_msg

TODAY = date(2026, 10, 4)


def _tutor(store, engine, child_id, llm) -> ChatTutor:
    return ChatTutor(llm=llm, store=store, engine=engine, child_id=child_id, today=TODAY)


def _types(events) -> list[str]:
    return [e["type"] for e in events]


def test_plain_reply_streams_deltas_and_focus(store, engine, child_id):
    llm = FakeLLM(turns=[assistant_msg("Look at the red balloon! 哇，红气球！")])
    events = list(_tutor(store, engine, child_id, llm).reply(None, "你好波波"))

    types = _types(events)
    assert types[0] == "session"
    assert "delta" in types and "done" == types[-1]
    focus = [e for e in events if e["type"] == "word_focus"]
    assert focus and focus[0]["word"] == "red"
    assert focus[0]["status"] == "新词"
    # 用户与助手消息都落库
    msgs = store.get_messages(events[0]["session_id"], limit=10)
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_tool_round_records_event_and_returns_payload(store, engine, child_id):
    llm = FakeLLM(
        turns=[
            assistant_msg(tool_calls=[ToolCall(
                id="call_1", name="record_word_event",
                arguments={"word": "apple", "kind": "free_use", "success": True},
            )]),
            assistant_msg("Great job saying apple! 你说了 apple，真棒！"),
        ]
    )
    events = list(_tutor(store, engine, child_id, llm).reply(None, "I like apple!"))

    types = _types(events)
    assert "tool" in types
    tool_ev = next(e for e in events if e["type"] == "tool")
    assert tool_ev["name"] == "record_word_event"
    assert "apple" in tool_ev["brief"]
    m = store.get_mastery(child_id, "w_apple")
    assert m is not None and m["correct"] == 1  # 工具真实记录了
    # FakeLLM 第二轮收到完整消息链（含 tool 消息）
    second_call = llm.calls[1]
    roles = [m["role"] for m in second_call["messages"]]
    assert "tool" in roles


def test_session_reuse_when_given(store, engine, child_id):
    sid = store.create_session(child_id, "maisy")
    llm = FakeLLM(turns=[assistant_msg("Hello! 你好呀！")])
    events = list(_tutor(store, engine, child_id, llm).reply(sid, "Hi"))
    assert events[0] == {"type": "session", "session_id": sid}
    assert len(llm.calls) == 1


def test_llm_failure_becomes_child_friendly_error(store, engine, child_id):
    llm = FakeLLM(turns=[])  # 脚本耗尽 → AssertionError
    events = list(_tutor(store, engine, child_id, llm).reply(None, "你好"))
    assert events[-2]["type"] == "error"
    assert "AI 走神了" in events[-2]["message"]
    assert events[-1] == {"type": "done"}


def test_unknown_child_yields_error_only(store, engine):
    llm = FakeLLM(turns=[assistant_msg("Hi")])
    events = list(ChatTutor(llm, store, engine, "c_missing", today=TODAY).reply(None, "hi"))
    assert events == [{"type": "error", "message": "孩子档案不存在"}]


def test_word_focus_caps_at_three(store, engine, child_id):
    text = "red and blue and pink and yellow! 好多颜色呀！"
    llm = FakeLLM(turns=[assistant_msg(text)])
    events = list(_tutor(store, engine, child_id, llm).reply(None, "colors!"))
    assert len([e for e in events if e["type"] == "word_focus"]) == 3


def test_end_session_flow(store, engine, child_id):
    sid = store.create_session(child_id, "maisy")
    tutor = _tutor(store, engine, child_id, FakeLLM(turns=[]))
    result = tutor.end_session(sid, notes="今天很开心")
    assert result["ok"] is True
    again = tutor.end_session(sid)
    assert again.get("already_ended") is True


def test_reply_survives_mid_tool_round_crash(store, engine, child_id):
    """Review Focus 2：第 1 轮工具已执行（副作用已落库），第 2 轮 ask 崩溃 →
    仍 error+done 收尾，已记事件不回滚。"""
    llm = FakeLLM(turns=[
        assistant_msg(tool_calls=[ToolCall(
            id="call_1", name="record_word_event",
            arguments={"word": "apple", "kind": "encounter", "success": True},
        )]),
        # 脚本耗尽 → 第 2 轮 ask 抛 AssertionError
    ])
    events = list(_tutor(store, engine, child_id, llm).reply(None, "I like apple!"))
    types = [e["type"] for e in events]
    assert types.count("tool") == 1
    assert store.get_mastery(child_id, "w_apple") is not None  # 副作用已在
    assert types[-2] == "error" and "AI 走神了" in events[-2]["message"]
    assert types[-1] == "done"
