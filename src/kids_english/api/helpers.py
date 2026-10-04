"""路由共用件：app.state 访问、LLM 工厂、SSE 编码。"""
from __future__ import annotations

import json

from fastapi import HTTPException, Request

from kids_english.agent.mock_llm import MockLLM
from kids_english.llm import LLMClient
from kids_english.progress import MasteryEngine
from kids_english.store import Store


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_engine(request: Request) -> MasteryEngine:
    return request.app.state.engine


def child_or_404(request: Request, child_id: str) -> dict:
    child = request.app.state.store.get_child(child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="孩子档案不存在")
    return child


def chat_llm(request: Request, child_id: str) -> LLMClient:
    """对话用 LLM：mock 模式每请求建 MockLLM（绑定孩子）；live 模式共享单例。"""
    s = request.app.state
    if s.settings.llm_mode == "mock":
        return MockLLM(s.store, s.engine, child_id)
    assert s.live_llm is not None  # live 模式启动时已装配
    return s.live_llm


def judge_llm(request: Request) -> LLMClient | None:
    """评价用 LLM：live 才用（LLM 裁判）；mock 模式 None → 启发式。"""
    return request.app.state.live_llm


def sse_line(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
