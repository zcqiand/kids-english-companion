"""store.py：SQLite DAO 往返与约束。"""
from __future__ import annotations

import pytest

from kids_english.store import Store


def test_create_and_get_child(store):
    cid = store.create_child(name="乐乐", age=5, character_id="maisy")
    child = store.get_child(cid)
    assert child is not None
    assert child["name"] == "乐乐"
    assert child["age"] == 5
    assert child["character_id"] == "maisy"


def test_list_children_order(store):
    a = store.create_child(name="老大", age=6, character_id="maisy")
    b = store.create_child(name="老二", age=4, character_id="peppa")
    assert [c["id"] for c in store.list_children()] == [a, b]


def test_get_character_child_missing(store):
    assert store.get_child("nope") is None


def test_seed_words_idempotent(store):
    from kids_english.content import seed_words

    store.seed_words(seed_words())
    words = store.list_words()
    assert len(words) == len({w["text"] for w in seed_words()})
    by_text = {w["text"]: w for w in words}
    apple = by_text["apple"]
    assert apple["meaning_cn"]
    assert apple["theme"] == "food"


def test_word_lookup_case_insensitive(store):
    w = store.find_word("APPLE")
    assert w is not None and w["text"] == "apple"
    assert store.find_word("存在感") is None


def test_messages_roundtrip(store, child_id):
    sid = store.create_session(child_id=child_id, character_id="maisy")
    store.append_message(session_id=sid, child_id=child_id, role="user", content="hello")
    store.append_message(session_id=sid, child_id=child_id, role="assistant", content="Hi")
    msgs = store.get_messages(session_id=sid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert [m["content"] for m in msgs] == ["hello", "Hi"]


def test_session_lifecycle(store, child_id):
    from datetime import date

    sid = store.create_session(child_id=child_id, character_id="maisy")
    assert store.get_session(sid)["ended_at"] is None
    store.end_session(session_id=sid, summary='{"notes":"ok"}', end_date=date(2026, 10, 4))
    sess = store.get_session(sid)
    assert sess["ended_at"] is not None
    assert sess["end_date"] == "2026-10-04"
    assert sess["summary"] == '{"notes":"ok"}'


def test_message_history_cap(store, child_id):
    sid = store.create_session(child_id=child_id, character_id="maisy")
    for i in range(30):
        store.append_message(session_id=sid, child_id=child_id, role="user", content=f"m{i}")
    recent = store.get_messages(session_id=sid, limit=10)
    assert len(recent) == 10
    assert recent[0]["content"] == "m20"


def test_foreign_key_blocks_orphan_message(store, child_id):
    with pytest.raises(Exception):
        store.append_message(session_id="ghost", child_id=child_id, role="user", content="x")
