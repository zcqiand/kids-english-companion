# 英语启蒙伙伴（kids-english-companion）

**记得住孩子学习进度**的动画 IP 角色英语启蒙 Agent。孩子跟小鼠波波（Maisy）等角色聊天、跟读小故事、练单词发音；角色记得孩子学过什么、哪里薄弱、今天该复习什么，并把复习自然织进对话里。

突出点只有一个：**学习进度记忆闭环**——

```
对话/跟读/发音 ──记录──▶ 掌握度引擎（盒子 0-5 · 间隔 0/1/2/4/7 天）
     ▲                        │
     └────进度卡织入系统提示词──┤ 到期复习 → 优先开口
                              ├ 薄弱词 → 多鼓励慢示范
                              ├ 连击天数 → 表扬坚持
                              └ 建议新词（每天 ≤2）
```

所有模块（对话、跟读、发音、家长看板）读写同一份掌握度模型，而不是各记各的。

## 快速开始

```bash
# 1) 后端 + 依赖 + 测试（无 Key、无网全绿）
pip install -e ".[dev]"
pytest -q

# 2) 配置环境：复制 .env.example 为 .env
#    mock  = 离线演示（不需要任何 Key/网络）
#    live  = 真实调用 OpenAI 兼容接口（MiniMax-M3）
#    live 模式下 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 缺一启动即报错（fail-fast）
copy .env.example .env

# 3) 起后端（默认 8801；读 .env 的 LLM_MODE 决定离线/真实）
python -m kids_english

# 4) 起前端（5801；vite proxy /api → 8801，无需 CORS 配置）
cd frontend
npm install        # 走 registry.npmmirror.com
npm run dev
```

打开 `http://localhost:5801`：选一个角色伙伴 → 聊天 / 跟读 / 发音 / 家长看板。

也可以 `uvicorn kids_english.main:create_app --factory --port 8801` 直接起工厂。

## 双模式说明

| 模式 | 行为 | 用途 |
| --- | --- | --- |
| `LLM_MODE=mock` | 假 LLM（脚本化回复，复习词必织入）+ 启发式发音评价 | 离线演示、开发、CI——零外部依赖 |
| `LLM_MODE=live` | OpenAI 兼容直调（stream + function calling），评价走 LLM JSON judge，失败自动落启发式 | 真实使用 |

live 模式已对 MiniMax-M3 验证：其思维链以 `<think>…</think>` 内联在 content 中，客户端流式状态机负责剥离，孩子只会看到干净正文。

## 功能页

- **聊天**：SSE 流式逐字回复；孩子说出的词实时记录（record_word_event 工具）；每次 ≤3 个重点词做成贴纸；英文句自动朗读（TTS）+ 一键重听；麦克风输入（STT）。
- **跟读**：按「到期词覆盖」挑故事；句子卡听示范 → 孩子跟读 → 逐词 ✓/✗ 反馈 + 中英鼓励。
- **发音**：到期 > 薄弱 > 学习中挑词卡；听示范 → 录音评价 → 状态章即时更新，评后词卡自动重排。
- **家长看板**：连击/今日复习/薄弱/已掌握四格统计、近 14 天活动条、词汇全景分色格、最近学习事件流。

## 技术栈

- 后端：Python 3.10+ / FastAPI / **LangGraph**（对话流程图，书 ch9 单框架）/ openai SDK（OpenAI 兼容直调；禁 langchain 顶层与 langchain-openai）/ SQLite（thin DAO）
- 前端：React 18 + TypeScript 5.6 + Vite 5，零额外运行时依赖
- 语音：浏览器 Web Speech API（TTS 朗读 + STT 转写），无需额外 Key
- 版本钉死于 [version-lock.json](version-lock.json)；npm 依赖以 package-lock.json 实际解析版本为准

## 语音的浏览器要求

TTS/STT 用 Web Speech API：

- **语音输入（跟读/发音/麦克风）**：Chrome / Edge 桌面版可用（`webkitSpeechRecognition`，en-US）；Firefox/Safari 不支持，界面会提示换浏览器，键盘输入对话不受影响。
- **朗读（TTS）**：依赖系统已装的英文语音包；Windows 推荐 Chrome 内置的 Google US English。识别质量直接影响发音判定——安静环境、对着麦克风说效果最好。

## 已知边界（如实说明）

- 发音评价基于浏览器 STT 的**转写文本**做词级比对（LLM judge + 兜底启发式），不是声学打分——它判「听清了没」，不判「音素准不准」。
- IP 角色只借名字做扮演，人设/故事全部原创文案，不复刻原作台词与情节。
- 词库与故事是种子内容（`content.py`），扩词库只加数据行，不动引擎。

## 开发约定

见 [CLAUDE.md](CLAUDE.md)：TDD、mock-friendly（无 Key 无网 `pytest -q` 全绿）、版本钉死、env 无默认兜底、密钥只放 `.env` 不入库、功能树锚点 `docs/functions/function-tree.md`。
