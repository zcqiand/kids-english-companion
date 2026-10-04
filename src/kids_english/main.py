"""FastAPI 应用工厂（M06）：装配 Store / 进度引擎 / LLM，挂四组路由。

工厂模式：测试用 create_app(Settings(...)) 注入；运行用
`uvicorn kids_english.main:create_app --factory --port 8801`（读 cwd/.env，fail-fast）。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kids_english.api import chat, children, meta, practice
from kids_english.config import Settings, load_settings
from kids_english.content import seed_words as word_data
from kids_english.llm import LiveLLM
from kids_english.progress import MasteryEngine
from kids_english.store import Store

CORS_ORIGINS = [
    "http://localhost:5801",
    "http://127.0.0.1:5801",
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = Store(settings.db_path)
    store.seed_words(word_data())
    engine = MasteryEngine(store)

    app = FastAPI(title="Kids English Companion", version="0.1.0")
    app.state.settings = settings
    app.state.store = store
    app.state.engine = engine
    app.state.live_llm = (
        LiveLLM(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
        if settings.llm_mode == "live"
        else None
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(children.router)
    app.include_router(chat.router)
    app.include_router(practice.router)
    app.include_router(meta.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "mode": settings.llm_mode}

    return app
