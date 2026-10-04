"""MockLLM（M06.F01.I03）：无 Key 离线演示件的行为形状。"""
from __future__ import annotations

from datetime import date

from kids_english.agent.mock_llm import MockLLM

TODAY = date(2026, 10, 4)


def _mock(store, engine, child_id) -> MockLLM:
    return MockLLM(store, engine, child_id)


def test_known_word_in_text_triggers_free_use_tool_call(store, engine, child_id):
    engine.record_event(child_id, "w_apple", "echo_attempt", True, "", today=TODAY)  # apple 已学
    llm = _mock(store, engine, child_id)
    msg = llm.chat(messages=[{"role": "user", "content": "I like apple!"}], tools=[{"fake": "spec"}])
    calls = msg.get("tool_calls")
    assert calls and calls[0].name == "record_word_event"
    assert calls[0].arguments == {"word": "apple", "kind": "free_use", "success": True}


def test_same_text_not_recorded_twice(store, engine, child_id):
    engine.record_event(child_id, "w_apple", "echo_attempt", True, "", today=TODAY)
    llm = _mock(store, engine, child_id)
    messages = [{"role": "user", "content": "I like apple!"}]
    first = llm.chat(messages=messages, tools=[{"fake": "spec"}])
    second = llm.chat(messages=messages, tools=[{"fake": "spec"}])
    assert first.get("tool_calls")
    assert second.get("tool_calls") is None  # 防重复记录


def test_unknown_words_get_roleplay_reply_with_review_word(store, engine, child_id):
    engine.record_event(child_id, "w_banana", "echo_attempt", False, "", today=TODAY)  # banana 到期
    llm = _mock(store, engine, child_id)
    msg = llm.chat(messages=[{"role": "user", "content": "哇！！"},], tools=[{"fake": "spec"}])
    assert msg["tool_calls"] is None
    content = msg["content"] or ""
    assert "banana" in content  # 织入到期复习词
    assert "\n" in content  # 英文 + 中文行


def test_chat_without_tools_plain_reply(store, engine, child_id):
    llm = _mock(store, engine, child_id)
    msg = llm.chat(messages=[{"role": "user", "content": "hello"}], tools=None)
    content = msg["content"] or ""
    assert content and "\n" in content


def test_chat_stream_yields_deltas_then_final(store, engine, child_id):
    llm = _mock(store, engine, child_id)
    events = list(llm.chat_stream(messages=[{"role": "user", "content": "hi"}]))
    types = [e["type"] for e in events]
    assert "delta" in types and types[-1] == "final"
    assert events[-1]["message"]["role"] == "assistant"
