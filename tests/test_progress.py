"""progress.py：掌握度盒子/到期/薄弱/连击/进度卡——本项目的突出点，测试从严。"""
from __future__ import annotations

from datetime import date

from kids_english.progress import (
    MasteryEngine,
    status_of,
)


def _word_id(store, text):
    return store.find_word(text)["id"]


def test_status_boundaries():
    assert status_of(0) == "learning"
    assert status_of(1) == "learning"
    assert status_of(2) == "growing"
    assert status_of(3) == "growing"
    assert status_of(4) == "mastered"
    assert status_of(5) == "mastered"


def test_first_correct_moves_box_and_sets_due(store, child_id):
    eng = MasteryEngine(store)
    wid = _word_id(store, "apple")
    m = eng.record_event(
        child_id, wid, kind="free_use", success=True, detail="孩子主动说 apple", today=date(2026, 10, 1)
    )
    assert m["box"] == 1
    assert m["status"] == "learning"
    assert m["due_date"] == "2026-10-02"  # 间隔表 [0,1,2,4,7]
    assert m["correct"] == 1


def test_four_streak_correct_reaches_mastered(store, child_id):
    eng = MasteryEngine(store)
    wid = _word_id(store, "apple")
    m = {}
    for day in (1, 2, 4, 8):
        m = eng.record_event(child_id, wid, kind="echo_attempt", success=True, detail="", today=date(2026, 10, day))
    assert m["box"] == 4
    assert m["status"] == "mastered"
    assert m["due_date"] == "2026-10-15"  # 10-08 + 7 天


def test_wrong_drops_box_and_due_today(store, child_id):
    eng = MasteryEngine(store)
    wid = _word_id(store, "ball")
    eng.record_event(child_id, wid, kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    eng.record_event(child_id, wid, kind="echo_attempt", success=True, detail="", today=date(2026, 10, 2))
    m = eng.record_event(child_id, wid, kind="echo_attempt", success=False, detail="读成 bell", today=date(2026, 10, 4))
    assert m["box"] == 1
    assert m["wrong"] == 1
    assert m["due_date"] == "2026-10-04"  # 当天再练


def test_weak_word_detection(store, child_id):
    eng = MasteryEngine(store)
    wid = _word_id(store, "three")
    for _ in range(3):
        eng.record_event(child_id, wid, kind="pronunciation_attempt", success=False, detail="th 音", today=date(2026, 10, 1))
    assert eng.is_weak(child_id, wid) is True
    wid2 = _word_id(store, "cat")
    eng.record_event(child_id, wid2, kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    assert eng.is_weak(child_id, wid2) is False


def test_due_words_order_and_filter(store, child_id):
    eng = MasteryEngine(store)
    eng.record_event(child_id, _word_id(store, "apple"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    eng.record_event(child_id, _word_id(store, "dog"), kind="echo_attempt", success=False, detail="", today=date(2026, 10, 1))
    # dog 答错 → 当天到期；apple 答对 → 10-02 到期
    assert {"dog", "apple"} == {w["text"] for w in eng.due_words(child_id, today=date(2026, 10, 2))}
    # 错词盒子更低 → 排前面（更紧急）
    assert eng.due_words(child_id, today=date(2026, 10, 2))[0]["text"] == "dog"
    # 都过了间隔仍未复习 → 持续到期
    assert {"dog", "apple"} == {w["text"] for w in eng.due_words(child_id, today=date(2026, 10, 3))}


def test_pick_practice_words_priority(store, child_id):
    eng = MasteryEngine(store)
    # dog: 错两次 → 弱 + 当天到期；apple: 学过未到期；fish: 没学过
    eng.record_event(child_id, _word_id(store, "dog"), kind="echo_attempt", success=False, detail="", today=date(2026, 10, 4))
    eng.record_event(child_id, _word_id(store, "apple"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    picked = eng.pick_practice_words(child_id, k=2, today=date(2026, 10, 4))
    assert [p["text"] for p in picked] == ["dog", "apple"]


def test_new_word_candidates_skip_known(store, child_id):
    eng = MasteryEngine(store)
    eng.record_event(child_id, _word_id(store, "apple"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    fresh = eng.new_word_candidates(child_id, k=3)
    texts = [w["text"] for w in fresh]
    assert "apple" not in texts
    assert len(texts) == 3


def test_streak_counts_consecutive_days(store, child_id):
    eng = MasteryEngine(store)
    for day in (1, 2, 3):
        sid = store.create_session(child_id=child_id, character_id="maisy")
        store.end_session(session_id=sid, summary=None, end_date=date(2026, 10, day))
    assert eng.streak(child_id, today=date(2026, 10, 3)) == 3
    # 今天还没学不打断显示：锚昨天仍是 3
    assert eng.streak(child_id, today=date(2026, 10, 4)) == 3
    assert eng.streak(child_id, today=date(2026, 10, 4), count_today=False) == 3
    # 断了两天 → 归零
    assert eng.streak(child_id, today=date(2026, 10, 6)) == 0


def test_streak_resets_after_gap(store, child_id):
    eng = MasteryEngine(store)
    for day in (1, 2, 5, 6):
        sid = store.create_session(child_id=child_id, character_id="maisy")
        store.end_session(session_id=sid, summary=None, end_date=date(2026, 10, day))
    assert eng.streak(child_id, today=date(2026, 10, 6)) == 2
    assert eng.streak(child_id, today=date(2026, 10, 7)) == 2
    assert eng.streak(child_id, today=date(2026, 10, 8)) == 0


def test_progress_card_contains_key_sections(store, child_id):
    eng = MasteryEngine(store)
    eng.record_event(child_id, _word_id(store, "dog"), kind="echo_attempt", success=False, detail="", today=date(2026, 10, 4))
    eng.record_event(child_id, _word_id(store, "apple"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    eng.record_event(child_id, _word_id(store, "cat"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    eng.record_event(child_id, _word_id(store, "cat"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 2))
    eng.record_event(child_id, _word_id(store, "cat"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 3))
    eng.record_event(child_id, _word_id(store, "cat"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 4))
    card = eng.progress_card(child_id, name="乐乐", today=date(2026, 10, 4))
    assert "乐乐" in card
    assert "待复习" in card and "dog" in card
    assert "薄弱" in card
    assert "mastered" not in card  # 卡面向 LLM，不暴露内部英文枚举
    assert "连续" in card


def test_dashboard_payload_shape(store, child_id):
    eng = MasteryEngine(store)
    eng.record_event(child_id, _word_id(store, "apple"), kind="echo_attempt", success=True, detail="", today=date(2026, 10, 1))
    payload = eng.dashboard(child_id, today=date(2026, 10, 2))
    assert set(payload) >= {"words", "due_today", "weak", "streak", "stats", "recent_events", "activity"}
    assert payload["stats"]["学习中"] >= 1
    assert "apple" in payload["due_today"]
    assert any(w["text"] == "apple" for w in payload["words"])
