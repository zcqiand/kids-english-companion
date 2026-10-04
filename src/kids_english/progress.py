"""进度记忆引擎（M01）——本仓突出点。

盒子模型：box 0-5，间隔表 [0,1,2,4,7] 天。
- 答对：box+1（封顶 5），due = 今天 + 间隔[min(box,4)]
- 答错：box-1（保底 0），due = 今天（当天再练）
状态：learning(0-1) / growing(2-3) / mastered(≥4)；薄弱 = 错≥2 或 错>对。
所有模块（对话/跟读/发音/看板）都经由本引擎读写同一份掌握度模型。
"""
from __future__ import annotations

from datetime import date, timedelta

from kids_english.store import Store

BOX_INTERVALS = (0, 1, 2, 4, 7)

KIND_ENCOUNTER = "encounter"                    # 角色对话里带出了这个词
KIND_ECHO = "echo_attempt"                      # 跟读
KIND_PRONUNCIATION = "pronunciation_attempt"    # 单词发音练习
KIND_FREE_USE = "free_use"                      # 孩子在对话里主动用了这个词

STATUS_CN = {"learning": "学习中", "growing": "巩固中", "mastered": "已掌握"}


def status_of(box: int) -> str:
    if box >= 4:
        return "mastered"
    if box >= 2:
        return "growing"
    return "learning"


class MasteryEngine:
    def __init__(self, store: Store):
        self.store = store

    # ---- 事件 → 掌握度（M01.F01.I01/I02）----

    def record_event(
        self,
        child_id: str,
        word_id: str,
        kind: str,
        success: bool,
        detail: str = "",
        today: date | None = None,
    ) -> dict:
        today = today or date.today()
        m = self.store.get_mastery(child_id, word_id)
        if m is None:
            box, correct, wrong = 0, 0, 0
            first_seen = today.isoformat()
            encounters = 0
        else:
            box, correct, wrong = m["box"], m["correct"], m["wrong"]
            first_seen = m["first_seen"]
            encounters = m["encounters"]
        if success:
            box = min(box + 1, 5)
            correct += 1
            interval = BOX_INTERVALS[min(box, len(BOX_INTERVALS) - 1)]
            due = today + timedelta(days=interval)
        else:
            box = max(box - 1, 0)
            wrong += 1
            due = today  # 答错当天再练
        row = {
            "box": box,
            "encounters": encounters + 1,
            "correct": correct,
            "wrong": wrong,
            "first_seen": first_seen,
            "last_seen": today.isoformat(),
            "due_date": due.isoformat(),
        }
        if m is None:
            self.store.insert_mastery(child_id, word_id, row)
        else:
            m = self.store.upsert_mastery(child_id, word_id, row)
        self.store.insert_event(child_id, word_id, kind, success, detail)
        return self.snapshot(child_id, word_id)

    def snapshot(self, child_id: str, word_id: str) -> dict:
        m = dict(self.store.get_mastery(child_id, word_id))  # type: ignore[arg-type]
        m["status"] = status_of(m["box"])
        return m

    # ---- 薄弱 / 复习调度（M01.F01.I02, M01.F02）----

    def is_weak(self, child_id: str, word_id: str) -> bool:
        m = self.store.get_mastery(child_id, word_id)
        if m is None:
            return False
        return m["wrong"] >= 2 or m["wrong"] > m["correct"]

    def due_words(self, child_id: str, today: date | None = None) -> list[dict]:
        today = today or date.today()
        due = [
            m
            for m in self.store.list_mastery(child_id)
            if m["due_date"] <= today.isoformat()
        ]
        due.sort(key=lambda m: (m["box"], m["due_date"]))
        return due

    def weak_words(self, child_id: str) -> list[dict]:
        return [m for m in self.store.list_mastery(child_id) if self._row_weak(m)]

    def _row_weak(self, m: dict) -> bool:
        return m["wrong"] >= 2 or m["wrong"] > m["correct"]

    def pick_practice_words(self, child_id: str, k: int = 3, today: date | None = None) -> list[dict]:
        """到期 > 薄弱 > 学习中，去重取前 k。"""
        today = today or date.today()
        picked: list[dict] = []
        seen: set[str] = set()
        for bucket in (self.due_words(child_id, today), self.weak_words(child_id)):
            for m in bucket:
                if m["word_id"] not in seen:
                    picked.append(m)
                    seen.add(m["word_id"])
        if len(picked) < k:
            for m in self.store.list_mastery(child_id):
                if m["word_id"] not in seen and status_of(m["box"]) != "mastered":
                    picked.append(m)
                    seen.add(m["word_id"])
                if len(picked) >= k:
                    break
        return picked[:k]

    def new_word_candidates(self, child_id: str, k: int = 2) -> list[dict]:
        known = {m["word_id"] for m in self.store.list_mastery(child_id)}
        fresh = [w for w in self.store.list_words() if w["id"] not in known]
        return fresh[:k]

    # ---- 连击（M01.F03.I03）----

    def streak(self, child_id: str, today: date | None = None, count_today: bool = True) -> int:
        """截至今天（或昨天）的连续学习天数。

        今天还没学不打断显示：锚点取「今天若学过则今天，否则昨天」。
        count_today=False 时锚点强制昨天（看板展示「截至昨天」口径用）。
        """
        today = today or date.today()
        dates = set(self.store.list_session_dates(child_id))
        anchor = today
        if not count_today or today.isoformat() not in dates:
            anchor = today - timedelta(days=1)
        n = 0
        d = anchor
        while d.isoformat() in dates:
            n += 1
            d -= timedelta(days=1)
        return n

    # ---- 进度卡（M01.F03.I01）与看板数据（M01.F03.I02）----

    def progress_card(self, child_id: str, name: str, today: date | None = None) -> str:
        today = today or date.today()
        due = self.due_words(child_id, today)
        weak = [m for m in self.weak_words(child_id) if m not in due]
        all_m = self.store.list_mastery(child_id)
        mastered = [m for m in all_m if status_of(m["box"]) == "mastered" and m not in due]
        learning = [m for m in all_m if status_of(m["box"]) != "mastered" and m not in due]
        fresh = self.new_word_candidates(child_id, k=2)
        streak_n = self.streak(child_id, today)

        lines = [f"【{name}的学习进度卡】（今天是 {today.isoformat()}）"]
        lines.append(f"- 连续学习：{streak_n} 天")
        lines.append(
            f"- 待复习（{len(due)}）: {self._fmt(due)} —— 开场自然带进对话，让孩子再说一遍，及时表扬"
        )
        lines.append(
            f"- 薄弱词（{len(weak)}）: {self._fmt(weak)} —— 多给鼓励，放慢示范，别纠正过头"
        )
        lines.append(f"- 已掌握（{len(mastered)}）: {self._fmt(mastered)}")
        lines.append(f"- 学习中（{len(learning)}）: {self._fmt(learning)}")
        if fresh:
            lines.append(
                "- 今日建议新词（≤2）: "
                + "、".join(f"{w['text']}（{w['meaning_cn']}）" for w in fresh)
                + " —— 一句对话只教一个，配上动作或表情"
            )
        return "\n".join(lines)

    @staticmethod
    def _fmt(rows: list[dict], cap: int = 8) -> str:
        texts = [m["text"] for m in rows[:cap]]
        more = f" 等{len(rows)}个" if len(rows) > cap else ""
        return ("、".join(texts) + more) if texts else "暂无"

    def dashboard(self, child_id: str, today: date | None = None) -> dict:
        today = today or date.today()
        all_m = []
        for m in self.store.list_mastery(child_id):
            row = dict(m)
            row["status"] = STATUS_CN[status_of(m["box"])]
            row["weak"] = self._row_weak(m)
            all_m.append(row)
        stats = {cn: 0 for cn in STATUS_CN.values()}
        for row in all_m:
            stats[row["status"]] += 1
        dates = self.store.list_session_dates(child_id)
        activity: dict[str, int] = {}
        for i in range(13, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            activity[d] = sum(1 for x in dates if x == d)
        return {
            "words": all_m,
            "due_today": [m["text"] for m in self.due_words(child_id, today)],
            "weak": [m["text"] for m in self.weak_words(child_id)],
            "streak": self.streak(child_id, today),
            "stats": {**stats, "total_known": len(all_m)},
            "recent_events": [
                {**e, "word": e.get("word_text") or ""} for e in self.store.recent_events(child_id, limit=20)
            ],
            "activity": activity,
        }
