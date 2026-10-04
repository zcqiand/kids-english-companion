"""跟读与发音评价（M03.F01 故事选择 / M03.F02.I02 评价 / M04.F01.I02 评价）。

评价两路：live 模式 LLM 判 JSON（解析失败自动落到启发式）；mock 模式直接启发式。
启发式=词元比对（精确 / 前缀 ≥3 字符 / 相似度 ≥0.8），只做转写文本判断，不做声学打分。
llm 传 None（mock 模式 / 评价器不可用）一律走启发式——MockLLM 是对话扮演件，
不该被拉来当裁判。
"""
from __future__ import annotations

import json
import re
from datetime import date
from difflib import SequenceMatcher

from kids_english.llm import LLMClient
from kids_english.progress import (
    KIND_ECHO,
    KIND_PRONUNCIATION,
    MasteryEngine,
    status_of,
)
from kids_english.store import Store

_JUDGE_SYSTEM = (
    "你是幼儿英语跟读评测器。只输出一个 JSON 对象，不要输出任何其他文字。格式："
    '{"words":[{"word":"…","ok":true,"heard":"转写里听到的最接近的词"}],'
    '"encouragement_en":"一句夸张的英文表扬","encouragement_cn":"对应的中文",'
    '"tip_cn":"一个具体的发音小提示（如果全对就给拓展建议）"}'
)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _word_ok(word: str, transcript_tokens: list[str]) -> bool:
    parts = word.split()
    for part in parts:
        if not any(
            tok == part
            or (len(part) >= 3 and (tok.startswith(part) or part.startswith(tok)))
            or (len(part) >= 4 and SequenceMatcher(None, tok, part).ratio() >= 0.8)
            for tok in transcript_tokens
        ):
            return False
    return True


def _heuristic_judge(target_words: list[str], transcript: str) -> dict:
    tokens = _tokens(transcript)
    words = [{"word": w, "ok": _word_ok(w, tokens), "heard": ""} for w in target_words]
    return {
        "words": words,
        "encouragement_en": "Good job trying!",
        "encouragement_cn": "勇敢开口就是最棒的！",
        "tip_cn": "慢一点，一个词一个词说清楚。",
    }


def _llm_judge(
    llm: LLMClient, sentence: str, target_words: list[str], transcript: str
) -> dict | None:
    """live 模式裁判。任何失败返回 None，由调用方落启发式。"""
    prompt = (
        f"目标句: {sentence}\n目标词: {', '.join(target_words) or '（无）'}\n"
        f"孩子跟读转写: {transcript}\n"
        "请判断每个目标词是否说出来了（允许拼写小误差），输出 JSON。"
    )
    try:
        msg = llm.chat(
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        content = msg.get("content") or ""
        start = content.find("{")
        if start < 0:
            return None
        parsed = json.JSONDecoder().raw_decode(content[start:])[0]
        if isinstance(parsed, dict) and isinstance(parsed.get("words"), list):
            return parsed
    except Exception:
        return None
    return None


def _judge(
    llm: LLMClient | None, sentence: str, target_words: list[str], transcript: str
) -> dict:
    if llm is not None and target_words:
        verdict = _llm_judge(llm, sentence, target_words, transcript)
        if verdict is not None:
            return verdict
    return _heuristic_judge(target_words, transcript)


# ---- 故事与页（M03.F01 / M03.F02.I01）----


def next_readalong(
    store: Store,
    engine: MasteryEngine,
    child_id: str,
    story_id: str | None = None,
    today: date | None = None,
) -> dict:
    """选故事：到期词覆盖最多者优先；返回第 0 页与本文到期词。"""
    from kids_english.content import seed_stories

    today = today or date.today()
    due_texts = {m["text"] for m in engine.due_words(child_id, today)}
    stories = seed_stories()
    if story_id:
        chosen = next((s for s in stories if s["id"] == story_id), None)
        if chosen is None:
            return {"ok": False, "error": f"story 不存在: {story_id}"}
    else:
        chosen = max(
            stories,
            key=lambda s: len({w for p in s["pages"] for w in p["words"]} & due_texts),
        )
    all_texts = {w for p in chosen["pages"] for w in p["words"]}
    page = chosen["pages"][0]
    return {
        "ok": True,
        "story": {
            "id": chosen["id"],
            "title_en": chosen["title_en"],
            "title_cn": chosen["title_cn"],
            "character_id": chosen["character_id"],
            "theme": chosen["theme"],
            "total_pages": len(chosen["pages"]),
        },
        "page_index": 0,
        "page": page,
        "due_words": sorted(all_texts & due_texts),
    }


def get_page(store: Store, story_id: str, page_index: int) -> dict | None:
    """翻页：返回故事与该页；故事或页码非法返回 None。"""
    from kids_english.content import seed_stories

    story = next((s for s in seed_stories() if s["id"] == story_id), None)
    if story is None or not (0 <= page_index < len(story["pages"])):
        return None
    return {"story": story, "page": story["pages"][page_index]}


# ---- 评价（M03.F02.I02 / M04.F01.I02）----


def evaluate_readalong(
    llm: LLMClient | None,
    store: Store,
    engine: MasteryEngine,
    child_id: str,
    story_id: str,
    page_index: int,
    transcript: str,
    today: date | None = None,
) -> dict:
    got = get_page(store, story_id, page_index)
    if got is None:
        return {"ok": False, "error": "story 或页码不存在"}
    page = got["page"]
    verdict = _judge(llm, page["en"], page["words"], transcript)

    llm_words = {w.get("word"): w for w in verdict.get("words", []) if isinstance(w, dict)}
    results = []
    for word in page["words"]:
        judged = llm_words.get(word) or {}
        ok = bool(judged.get("ok", _word_ok(word, _tokens(transcript))))
        heard = str(judged.get("heard", ""))
        word_id = f"w_{word.replace(' ', '_')}"
        snap = engine.record_event(child_id, word_id, KIND_ECHO, ok, heard or transcript[:80], today=today)
        results.append({"word": word, "ok": ok, "heard": heard, "status": snap["status"]})
    return {
        "ok": True,
        "sentence_en": page["en"],
        "sentence_cn": page["cn"],
        "results": results,
        "encouragement_en": str(verdict.get("encouragement_en", "Good job!")),
        "encouragement_cn": str(verdict.get("encouragement_cn", "勇敢开口就是最棒的！")),
        "tip_cn": str(verdict.get("tip_cn", "")),
    }


def pronunciation_words(
    store: Store,
    engine: MasteryEngine,
    child_id: str,
    k: int = 5,
    today: date | None = None,
) -> list[dict]:
    """发音练习词卡：到期 > 薄弱 > 学习中（M01.F02.I02 的调度结果）。

    全部为空（全新孩子）时兜底到未学新词——练习页不能开天窗。
    """
    today = today or date.today()
    picked = engine.pick_practice_words(child_id, k=k, today=today)
    cards: list[dict] = []
    if picked:
        for m in picked:
            row = store.find_word(m["text"])
            cards.append(
                {
                    "word_id": m["word_id"],
                    "text": m["text"],
                    "phonetic": row["phonetic"] if row else "",
                    "meaning_cn": m["meaning_cn"],
                    "status": status_of(m["box"]),
                }
            )
        return cards
    for w in engine.new_word_candidates(child_id, k=k):
        cards.append(
            {
                "word_id": w["id"],
                "text": w["text"],
                "phonetic": w["phonetic"],
                "meaning_cn": w["meaning_cn"],
                "status": "learning",
            }
        )
    return cards


def evaluate_pronunciation(
    llm: LLMClient | None,
    store: Store,
    engine: MasteryEngine,
    child_id: str,
    word: str,
    transcript: str,
    today: date | None = None,
) -> dict:
    row = store.find_word(word)
    if row is None:
        return {"ok": False, "error": f"word 不在词库: {word}"}
    verdict = _judge(llm, row["text"], [row["text"]], transcript)
    judged = next((w for w in verdict.get("words", []) if w.get("word") == row["text"]), {})
    ok = bool(judged.get("ok", _word_ok(row["text"], _tokens(transcript))))
    snap = engine.record_event(child_id, row["id"], KIND_PRONUNCIATION, ok, transcript[:80], today=today)
    return {
        "ok": True,
        "word": row["text"],
        "phonetic": row["phonetic"],
        "meaning_cn": row["meaning_cn"],
        "correct": ok,
        "heard": str(judged.get("heard", "")),
        "encouragement_en": str(verdict.get("encouragement_en", "")),
        "encouragement_cn": str(verdict.get("encouragement_cn", "")),
        "tip_cn": str(verdict.get("tip_cn", "")),
        "status": snap["status"],
    }
