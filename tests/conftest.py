"""共享 fixture：临时库 + 种子内容 + 测试用假 LLM。"""
from __future__ import annotations

import pytest

from kids_english.content import seed_words
from kids_english.store import Store


@pytest.fixture()
def store(tmp_path):
    s = Store(str(tmp_path / "test.db"))
    s.seed_words(seed_words())
    return s


@pytest.fixture()
def child_id(store):
    return store.create_child(name="乐乐", age=5, character_id="maisy")
