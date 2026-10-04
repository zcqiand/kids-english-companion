# kids-english-companion — 仓库工作约定（供 Claude Code）

英语启蒙伙伴：**记得住孩子学习进度**的动画 IP 角色英语启蒙 Agent。
孩子跟小鼠波波（Maisy）等角色对话、跟读、练发音；角色记得孩子学过什么、哪里薄弱、今天该复习什么，并把复习自然织进对话。突出点只有一个：**学习进度记忆闭环**。

## 铁律

- **TDD**：核心逻辑（进度引擎/工具/Agent 循环）先写失败测试 → 实现 → 绿 → commit。
- **mock-friendly**：`pip install -e ".[dev]" && pytest -q` 必须在无 Key、无网下全绿（FakeLLM 注入，禁止测试里真调 API）。
- **版本钉死**：依赖与 `version-lock.json` 一致，不引 lock 外的库（不引 LangGraph/CrewAI/LangChain）。
- **禁止 env 默认值兜底**：`LLM_MODE` 必填（mock|live）；live 模式下 base_url/api_key/model 缺一即启动报错。
- **密钥不入库**：key 只在 `.env`（已 gitignore），`.env.example` 放占位符。
- **只增不改**：扩功能不动现有模块签名/行为。

## 技术栈（钉死于 version-lock.json）

- 后端：Python 3.10+ / FastAPI / openai SDK（OpenAI 兼容直调：MiniMax-M3，base_url 可配）
- 前端：React 18 + TypeScript + Vite 5（npm 走 registry.npmmirror.com）
- 存储：SQLite（`data/app.db`，thin DAO，不引 ORM）
- 语音：浏览器 Web Speech API（STT 转写 + TTS 朗读），无需额外 Key

## 验收

```bash
pip install -e ".[dev]"
pytest -q                        # 全绿，无 Key/无网
uvicorn kids_english.main:app --port 8801   # LLM_MODE=mock 时离线可演示
cd frontend && npm install && npm run build  # 前端构建通过
```

## 结构

```text
src/kids_english/
├── config.py        # env 装配，fail-fast
├── llm.py           # LLMClient 协议 + LiveLLM(OpenAI兼容) + MockLLM
├── store.py         # SQLite DAO（children/words/mastery/events/sessions/messages）
├── progress.py      # ★ 进度引擎：事件→掌握度盒子、到期、薄弱、连击、进度卡
├── characters.py    # IP 角色档案（Maisy 小鼠波波等，原创人设文案）
├── content.py       # 原创小故事 + 主题词库（种子内容）
├── agent/
│   ├── prompts.py   # 人设 + 策略 + 进度卡 组装系统提示词
│   ├── tools.py     # function calling 工具表与执行
│   ├── tutor.py     # 对话 Agent 循环（SSE）
│   └── practice.py  # 跟读/发音评价
└── api/             # 路由：children / chat / practice / meta
```

## 领域规则

- 掌握度盒子 0-5，间隔 [0,1,2,4,7] 天；正确升盒、错误降盒；box≥4 = mastered。
- 每次会话新词 ≤2；开场必织入 1-2 个到期复习词；孩子自发用词必须记录并表扬。
- IP 人设/故事全部原创文案，只借角色名做扮演，不复刻原作台词与情节。
- 发音评价基于浏览器 STT 转写文本做词级比对（LLM 判断 + 兜底启发式），不做声学打分——如实告知用户这个边界。
