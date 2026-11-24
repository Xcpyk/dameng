"""本地存储：所有回答只写进 data/dream.db（SQLite），不联网。"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_DB = DATA_DIR / "dream.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS answers (
    qid        TEXT PRIMARY KEY,
    text       TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_answer(qid: str, db_path: str | Path | None = None) -> dict | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM answers WHERE qid = ?", (qid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_answer(qid: str, text: str, db_path: str | Path | None = None) -> None:
    conn = connect(db_path)
    try:
        if text.strip():
            conn.execute(
                "INSERT INTO answers(qid, text, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(qid) DO UPDATE SET text=excluded.text, updated_at=excluded.updated_at",
                (qid, text, now()),
            )
        else:
            conn.execute("DELETE FROM answers WHERE qid = ?", (qid,))
        conn.commit()
    finally:
        conn.close()


def upsert_many(items: dict[str, str], db_path: str | Path | None = None) -> int:
    """items: {qid: text}。空文本视为清空。返回写入条数。"""
    conn = connect(db_path)
    try:
        stamp = now()
        n = 0
        for qid, text in items.items():
            if text and text.strip():
                conn.execute(
                    "INSERT INTO answers(qid, text, updated_at) VALUES(?,?,?) "
                    "ON CONFLICT(qid) DO UPDATE SET text=excluded.text, updated_at=excluded.updated_at",
                    (qid, text, stamp),
                )
                n += 1
            else:
                conn.execute("DELETE FROM answers WHERE qid = ?", (qid,))
        conn.commit()
        return n
    finally:
        conn.close()


def all_answers(db_path: str | Path | None = None) -> dict[str, dict]:
    conn = connect(db_path)
    try:
        rows = conn.execute("SELECT qid, text, updated_at FROM answers ORDER BY qid").fetchall()
        return {r["qid"]: {"text": r["text"], "updated_at": r["updated_at"]} for r in rows}
    finally:
        conn.close()


def clear_all(db_path: str | Path | None = None) -> None:
    conn = connect(db_path)
    try:
        conn.execute("DELETE FROM answers")
        conn.commit()
    finally:
        conn.close()


def set_meta(key: str, value: str, db_path: str | Path | None = None) -> None:
    conn = connect(db_path)
    try:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()
