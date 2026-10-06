"""角色对话 Agent（M02.F01）：LangGraph 编排 + SSE 队列旁路。

v2 编排内核（书 ch9 流程视角）：工具轮状态机由 agent/graph.py 的 StateGraph 承载，
本模块只做接线——graph.invoke 跑在 worker 线程，SSE 事件经队列旁路实时透出；
事件形状与 v1 一致：session / delta / reasoning / tool / word_focus / done / error。
"""
from __future__ import annotations

import queue
import threading
from collections.abc import Iterator
from datetime import date

from kids_english.agent.graph import TutorState, build_graph
from kids_english.llm import LLMClient
from kids_english.progress import MasteryEngine
from kids_english.store import Store

__all__ = ["ChatTutor"]


class ChatTutor:
    """每请求构造：持 LLM/Store/进度引擎，绑定 child_id。"""

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
        self._graph = build_graph(llm, store, engine, child_id, today=self.today)

    # ---- 对话回合（M02.F01）：worker 线程 + 队列旁路 ----

    def reply(self, session_id: str | None, text: str) -> Iterator[dict]:
        events: queue.SimpleQueue = queue.SimpleQueue()
        config = {"configurable": {"events": events}}
        state: TutorState = {"session_id": session_id, "text": text}

        def run() -> None:
            try:
                self._graph.invoke(state, config)
            except Exception as exc:  # 图内异常兜底：对孩子说人话（v1:85-87 语义）
                events.put({"type": "error", "message": f"AI 走神了：{exc}"})
                events.put({"type": "done"})
            finally:
                events.put(None)  # 结束标记：消费端据此终止

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        for event in iter(events.get, None):
            yield event
        worker.join()

    # ---- 会话收束（M02.F03）：无循环，不入图 ----

    def end_session(self, session_id: str, notes: str = "家长手动结束") -> dict:
        session = self.store.get_session(session_id)
        if session is None or session["child_id"] != self.child_id:
            return {"ok": False, "error": "session 不存在"}
        if session["ended_at"] is not None:
            return {"ok": True, "streak_days": self.engine.streak(self.child_id, self.today), "already_ended": True}
        self.store.end_session(session_id, notes, self.today)
        return {"ok": True, "streak_days": self.engine.streak(self.child_id, self.today)}
