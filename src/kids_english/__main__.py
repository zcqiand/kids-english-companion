"""python -m kids_english 启动（读 .env 的 APP_PORT）。"""
from __future__ import annotations

import uvicorn

from kids_english.main import create_app

app = create_app()
uvicorn.run(app, host="127.0.0.1", port=app.state.settings.app_port)
