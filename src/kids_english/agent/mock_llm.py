"""MockLLM（M06.F01.I03）：LLM_MODE=mock 的运行时离线件。

规则式扮演：识别孩子文本里的词库词 → 记录事件（工具调用形态）→
用角色口吻回一句带复习词的英文+中文。无需 Key、无需网，让全链路可演示。
这是演示兜底，不是教学质量基线——live 模式才是真实体验。
"""
from __future__ import annotations

import random
import re
from typing import Iterator

from kids_english.llm import ToolCall, assistant_msg
from kids_english.progress import MasteryEngine
from kids_english.store import Store

_REPLIES = [
    ("Wow! You said \"{text}\"! I love {word}!", "哇！你说了“{text}”！我好喜欢{word}！"),
    ("Yummy! {text} is fun! Say {word} with me!", "好吃！{text} 真有趣！跟我一起说“{word}”！"),
    ("Let's try one more: can you say \"{word}\"?", "我们再试一个：你能说“{word}”吗？"),
    ("Great job! Now look — {word}! {word}!", "真棒！你看——{word}！{word}！"),
]


class MockLLM:
    """无 Key 演示件。实现与 LiveLLM 相同的 chat / chat_stream 形状。"""

    def __init__(self, store: Store, engine: MasteryEngine, child_id: str):
        self.store = store
        self.engine = engine
        self.child_id = child_id
        self._recorded_for: str | None = None
        self._rng = random.Random(42)

    # ---- 行为 ----

    def _last_user_text(self, messages: list[dict]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content") or ""
        return ""

    def _words_in(self, text: str) -> list[str]:
        # 标点归一成空格，"apple!" 也能命中 " apple "
        pattern = re.compile(r"[^a-z']+")
        normalized = " " + pattern.sub(" ", text.lower()) + " "
        found = []
        for word in self.store.list_words():
            if f" {word['text'].lower()} " in normalized:
                known = self.store.get_mastery(self.child_id, word["id"])
                if known is not None:
                    found.append(word["text"])
        return found

    def _respond(self, messages: list[dict], tools: list[dict] | None) -> dict:
        text = self._last_user_text(messages)
        if tools and text and text != self._recorded_for:
            hits = self._words_in(text)
            if hits:
                self._recorded_for = text
                return assistant_msg(
                    tool_calls=[ToolCall(id="call_mock_1", name="record_word_event",
                                         arguments={"word": hits[0], "kind": "free_use", "success": True})]
                )
        due = self.engine.due_words(self.child_id)
        due_word = due[0]["text"] if due else "apple"
        tpl_en, tpl_cn = self._rng.choice(_REPLIES)
        child = self.store.get_child(self.child_id)
        name = child["name"] if child else "小朋友"
        content = f"Hello {name}! " + tpl_en.format(text=text.strip() or due_word, word=due_word) + "\n" + tpl_cn.format(
            text=text.strip() or due_word, word=due_word
        )
        return assistant_msg(content)

    # ---- LLMClient ----

    def chat(self, *, messages, tools=None, temperature: float = 0.8) -> dict:
        return self._respond(messages, tools)

    def chat_stream(self, *, messages, tools=None, temperature: float = 0.8) -> Iterator[dict]:
        msg = self._respond(messages, tools)
        if msg.get("content"):
            for chunk in msg["content"].split("\n"):
                yield {"type": "delta", "text": chunk + "\n"}
        yield {"type": "final", "message": msg}
