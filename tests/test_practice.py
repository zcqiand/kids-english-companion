"""跟读/发音评价（M03/M04）：故事选择、启发式判定、LLM 裁判与兜底。"""
from __future__ import annotations

from datetime import date

from kids_english.agent.practice import (
    evaluate_pronunciation,
    evaluate_readalong,
    get_page,
    next_readalong,
    pronunciation_words,
)
from kids_english.llm import FakeLLM, assistant_msg

TODAY = date(2026, 10, 4)


# ---- 故事选择 ----

def test_next_readalong_prefers_due_word_coverage(store, engine, child_id):
    engine.record_event(child_id, "w_banana", "echo_attempt", True, "", today=TODAY)  # due 明天？
    # 造一个已到期的词：picnic 故事(food)里有 banana？改用直接造到期事件
    engine.record_event(child_id, "w_banana", "echo_attempt", False, "", today=TODAY)  # 答错 due=今天
    result = next_readalong(store, engine, child_id, today=TODAY)
    assert result["ok"] is True
    assert result["page_index"] == 0
    assert result["story"]["total_pages"] >= 1
    assert "banana" in result["due_words"]


def test_next_readalong_explicit_story_and_missing(store, engine, child_id):
    got = next_readalong(store, engine, child_id, story_id="st_red_balloon", today=TODAY)
    assert got["ok"] and got["story"]["id"] == "st_red_balloon"
    missing = next_readalong(store, engine, child_id, story_id="st_nope", today=TODAY)
    assert missing["ok"] is False


def test_get_page_bounds(store):
    assert get_page(store, "st_red_balloon", 0) is not None
    assert get_page(store, "st_red_balloon", 99) is None
    assert get_page(store, "st_nope", 0) is None


# ---- 跟读评价 ----

def test_readalong_heuristic_all_correct(store, engine, child_id):
    page = get_page(store, "st_red_balloon", 0)["page"]
    transcript = page["en"]  # 完美跟读
    result = evaluate_readalong(None, store, engine, child_id, "st_red_balloon", 0, transcript, today=TODAY)
    assert result["ok"] is True
    assert all(r["ok"] for r in result["results"])
    # 每个目标词都真实记了 echo 事件
    for r in result["results"]:
        m = store.get_mastery(child_id, f"w_{r['word'].replace(' ', '_')}")
        assert m is not None and m["correct"] == 1


def test_readalong_heuristic_missing_word_fails(store, engine, child_id):
    page = get_page(store, "st_red_balloon", 0)["page"]
    target = page["words"][0]
    result = evaluate_readalong(None, store, engine, child_id, "st_red_balloon", 0, "nonsense gibberish", today=TODAY)
    flagged = next(r for r in result["results"] if r["word"] == target)
    assert flagged["ok"] is False
    m = store.get_mastery(child_id, f"w_{target.replace(' ', '_')}")
    assert m["wrong"] == 1 and m["due_date"] == TODAY.isoformat()  # 答错当天再练


def test_readalong_missing_page(store, engine, child_id):
    result = evaluate_readalong(None, store, engine, child_id, "st_nope", 0, "hi", today=TODAY)
    assert result["ok"] is False


def test_readalong_llm_judge_used_and_fallback(store, engine, child_id):
    judge = FakeLLM(turns=[assistant_msg(
        '{"words":[{"word":"red","ok":false,"heard":"bed"}],'
        '"encouragement_en":"Almost!","encouragement_cn":"就差一点！","tip_cn":"注意 r 的口型"}'
    )])
    result = evaluate_readalong(judge, store, engine, child_id, "st_red_balloon", 0, "bed balloon up", today=TODAY)
    red = next(r for r in result["results"] if r["word"] == "red")
    assert red["ok"] is False and red["heard"] == "bed"
    assert result["tip_cn"] == "注意 r 的口型"

    # LLM 返回垃圾 → 启发式兜底不炸
    bad = FakeLLM(turns=[assistant_msg("哈哈我可不是 JSON")])
    result2 = evaluate_readalong(bad, store, engine, child_id, "st_red_balloon", 0, "red balloon up", today=TODAY)
    assert result2["ok"] is True and all(r["ok"] for r in result2["results"])


# ---- 发音练习 ----

def test_pronunciation_words_due_first(store, engine, child_id):
    engine.record_event(child_id, "w_dog", "echo_attempt", False, "", today=TODAY)   # due 今天
    engine.record_event(child_id, "w_cat", "echo_attempt", True, "", today=TODAY)    # due 明天
    words = pronunciation_words(store, engine, child_id, k=2, today=TODAY)
    assert words[0]["text"] == "dog"
    assert words[0]["phonetic"].startswith("/")
    assert len(words) == 2


def test_pronunciation_evaluate_correct_and_wrong(store, engine, child_id):
    good = evaluate_pronunciation(None, store, engine, child_id, "apple", "apple", today=TODAY)
    assert good["correct"] is True and good["word"] == "apple"

    bad = evaluate_pronunciation(None, store, engine, child_id, "apple", "applesauce", today=TODAY)
    # "applesauce" 以 "apple" 开头 → 前缀 ≥3 命中，宽容判定为对（启发式特性）
    assert bad["correct"] is True

    miss = evaluate_pronunciation(None, store, engine, child_id, "banana", "zebra zebra", today=TODAY)
    assert miss["correct"] is False
    m = store.get_mastery(child_id, "w_banana")
    assert m["wrong"] == 1 and m["due_date"] == TODAY.isoformat()


def test_pronunciation_unknown_word(store, engine, child_id):
    result = evaluate_pronunciation(None, store, engine, child_id, "flibbertigibbet", "anything", today=TODAY)
    assert result["ok"] is False
