"""SQLite 存储（M00 数据层 + 会话/消息）。

薄 DAO：单连接 + 锁，够用就好，不引 ORM。
时间戳存 UTC ISO 串；日期字段（due_date / end_date）存本地 YYYY-MM-DD。
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS children(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  age INTEGER NOT NULL,
  character_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS words(
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL UNIQUE,
  phonetic TEXT NOT NULL DEFAULT '',
  meaning_cn TEXT NOT NULL,
  example_en TEXT NOT NULL DEFAULT '',
  example_cn TEXT NOT NULL DEFAULT '',
  theme TEXT NOT NULL,
  level INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS mastery(
  child_id TEXT NOT NULL REFERENCES children(id),
  word_id TEXT NOT NULL REFERENCES words(id),
  box INTEGER NOT NULL DEFAULT 0,
  encounters INTEGER NOT NULL DEFAULT 0,
  correct INTEGER NOT NULL DEFAULT 0,
  wrong INTEGER NOT NULL DEFAULT 0,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  due_date TEXT NOT NULL,
  PRIMARY KEY(child_id, word_id)
);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id TEXT NOT NULL REFERENCES children(id),
  word_id TEXT REFERENCES words(id),
  kind TEXT NOT NULL,
  success INTEGER NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY,
  child_id TEXT NOT NULL REFERENCES children(id),
  character_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  end_date TEXT,
  summary TEXT
);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  child_id TEXT NOT NULL REFERENCES children(id),
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    """所有持久化读写的唯一入口。"""

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ---- children ----

    def create_child(self, name: str, age: int, character_id: str) -> str:
        cid = f"c_{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._conn.execute(
                "INSERT INTO children(id, name, age, character_id, created_at) VALUES(?,?,?,?,?)",
                (cid, name, age, character_id, now_iso()),
            )
            self._conn.commit()
        return cid

    def get_child(self, child_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM children WHERE id=?", (child_id,)).fetchone()
        return dict(row) if row else None

    def list_children(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM children ORDER BY rowid").fetchall()
        return [dict(r) for r in rows]

    # ---- words ----

    def seed_words(self, words: list[dict]) -> None:
        with self._lock:
            for w in words:
                self._conn.execute(
                    """INSERT INTO words(id, text, phonetic, meaning_cn, example_en, example_cn, theme, level)
                       VALUES(:id, :text, :phonetic, :meaning_cn, :example_en, :example_cn, :theme, :level)
                       ON CONFLICT(id) DO NOTHING""",
                    w,
                )
            self._conn.commit()

    def list_words(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM words ORDER BY level, theme, text").fetchall()
        return [dict(r) for r in rows]

    def find_word(self, text: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM words WHERE text = ? COLLATE NOCASE", (text.strip(),)
        ).fetchone()
        return dict(row) if row else None

    # ---- mastery / events ----

    def get_mastery(self, child_id: str, word_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM mastery WHERE child_id=? AND word_id=?", (child_id, word_id)
        ).fetchone()
        return dict(row) if row else None

    def list_mastery(self, child_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT m.*, w.text, w.meaning_cn, w.theme, w.level FROM mastery m "
            "JOIN words w ON w.id = m.word_id WHERE m.child_id=? ORDER BY m.due_date, m.box",
            (child_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_mastery(self, child_id: str, word_id: str, fields: dict) -> dict:
        """全量字段更新（progress 引擎算好再写入）。"""
        cols = ",".join(fields)
        sets = ",".join(f"{c}=?" for c in fields)
        with self._lock:
            self._conn.execute(
                f"UPDATE mastery SET {sets} WHERE child_id=? AND word_id=?",
                (*fields.values(), child_id, word_id),
            )
            self._conn.commit()
        return self.get_mastery(child_id, word_id)  # type: ignore[return-value]

    def insert_mastery(self, child_id: str, word_id: str, fields: dict) -> None:
        base = {"child_id": child_id, "word_id": word_id, **fields}
        cols = ",".join(base)
        marks = ",".join("?" for _ in base)
        with self._lock:
            self._conn.execute(f"INSERT INTO mastery({cols}) VALUES({marks})", tuple(base.values()))
            self._conn.commit()

    def insert_event(self, child_id: str, word_id: str | None, kind: str, success: bool, detail: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO events(child_id, word_id, kind, success, detail, created_at) VALUES(?,?,?,?,?,?)",
                (child_id, word_id, kind, int(success), detail, now_iso()),
            )
            self._conn.commit()

    def recent_events(self, child_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT e.*, w.text AS word_text FROM events e LEFT JOIN words w ON w.id=e.word_id "
            "WHERE e.child_id=? ORDER BY e.id DESC LIMIT ?",
            (child_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- sessions / messages ----

    def create_session(self, child_id: str, character_id: str) -> str:
        sid = f"s_{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._conn.execute(
                "INSERT INTO sessions(id, child_id, character_id, started_at) VALUES(?,?,?,?)",
                (sid, child_id, character_id, now_iso()),
            )
            self._conn.commit()
        return sid

    def get_session(self, session_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None

    def end_session(self, session_id: str, summary: str | None, end_date: date) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET ended_at=?, end_date=?, summary=? WHERE id=?",
                (now_iso(), end_date.isoformat(), summary, session_id),
            )
            self._conn.commit()

    def list_session_dates(self, child_id: str) -> list[str]:
        """已结束会话的本地日期（去重升序）——连击计算的数据源。"""
        rows = self._conn.execute(
            "SELECT DISTINCT end_date FROM sessions WHERE child_id=? AND end_date IS NOT NULL ORDER BY end_date",
            (child_id,),
        ).fetchall()
        return [r["end_date"] for r in rows]

    def append_message(self, session_id: str, child_id: str, role: str, content: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages(session_id, child_id, role, content, created_at) VALUES(?,?,?,?,?)",
                (session_id, child_id, role, content, now_iso()),
            )
            self._conn.commit()

    def get_messages(self, session_id: str, limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            "SELECT role, content, created_at FROM ("
            "  SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?"
            ") ORDER BY id",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
