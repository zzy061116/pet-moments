"""SQLite 存储层：只有 pet / post 两张表，够用就好。"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from .config import DB_PATH, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS pet (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    name        TEXT NOT NULL,
    species     TEXT NOT NULL,
    age         TEXT DEFAULT '',
    persona     TEXT NOT NULL,
    exp         INTEGER DEFAULT 0,
    streak      INTEGER DEFAULT 0,
    last_post   TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    is_demo     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS post (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    caption     TEXT NOT NULL,
    mood        TEXT DEFAULT '',
    event       TEXT DEFAULT '',
    photo       TEXT DEFAULT '',
    comments    TEXT NOT NULL,
    likes       TEXT NOT NULL,
    exp_gain    INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL
);
"""

# 等级阶梯：exp 门槛 -> 称号
LEVELS: list[tuple[int, str]] = [
    (0, "沙发土豆"),
    (60, "拆家学徒"),
    (150, "干饭专家"),
    (280, "撒娇大师"),
    (450, "一家之主"),
]


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        # 老库升级：早期版本没有 is_demo 列，这里补上
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(pet)")}
        if "is_demo" not in cols:
            conn.execute("ALTER TABLE pet ADD COLUMN is_demo INTEGER DEFAULT 0")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- 宠物

def get_pet() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM pet WHERE id = 1").fetchone()
    if not row:
        return None
    pet = dict(row)
    pet["persona"] = json.loads(pet["persona"])
    pet["level"] = level_of(pet["exp"])
    return pet


def save_pet(
    name: str,
    species: str,
    age: str,
    persona: dict[str, Any],
    is_demo: int = 0,
) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """INSERT INTO pet (id, name, species, age, persona, exp, streak, last_post, created_at, is_demo)
               VALUES (1, ?, ?, ?, ?, 0, 0, '', ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, species=excluded.species, age=excluded.age,
                 persona=excluded.persona, is_demo=excluded.is_demo""",
            (
                name,
                species,
                age,
                json.dumps(persona, ensure_ascii=False),
                now_iso(),
                is_demo,
            ),
        )
    return get_pet()  # type: ignore[return-value]


def reset_all() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM post")
        conn.execute("DELETE FROM pet")


# ---------------------------------------------------------------- 动态

def list_posts(limit: int = 60) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM post ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    posts = []
    for row in rows:
        item = dict(row)
        item["comments"] = json.loads(item["comments"])
        item["likes"] = json.loads(item["likes"])
        posts.append(item)
    return posts


def add_post(
    caption: str,
    mood: str,
    event: str,
    photo: str,
    comments: list[dict[str, str]],
    likes: list[str],
    exp_gain: int,
    created_at: str | None = None,
) -> dict[str, Any]:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO post (caption, mood, event, photo, comments, likes, exp_gain, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                caption,
                mood,
                event,
                photo,
                json.dumps(comments, ensure_ascii=False),
                json.dumps(likes, ensure_ascii=False),
                exp_gain,
                created_at or now_iso(),
            ),
        )
        post_id = cur.lastrowid
        conn.execute("UPDATE pet SET exp = exp + ? WHERE id = 1", (exp_gain,))
    return get_post(post_id)  # type: ignore[return-value]


def get_post(post_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM post WHERE id = ?", (post_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["comments"] = json.loads(item["comments"])
    item["likes"] = json.loads(item["likes"])
    return item


# ---------------------------------------------------------------- 成长

def level_of(exp: int) -> dict[str, Any]:
    idx = 0
    for i, (threshold, _title) in enumerate(LEVELS):
        if exp >= threshold:
            idx = i
    title = LEVELS[idx][1]
    current = LEVELS[idx][0]
    if idx + 1 < len(LEVELS):
        nxt, next_title = LEVELS[idx + 1]
        span = nxt - current
        percent = int((exp - current) / span * 100)
    else:
        nxt, next_title = current, ""
        percent = 100
    return {
        "index": idx,
        "title": title,
        "next_title": next_title,
        "percent": max(0, min(100, percent)),
        "exp": exp,
        "to_next": max(0, nxt - exp),
    }


def touch_streak() -> tuple[int, int]:
    """根据上次发帖日期更新连续天数，返回 (streak, exp_bonus)。"""
    today = date.today()
    with connect() as conn:
        row = conn.execute("SELECT streak, last_post FROM pet WHERE id = 1").fetchone()
        if not row:
            return 0, 0
        streak = row["streak"] or 0
        last = row["last_post"] or ""
        if last:
            try:
                last_day = date.fromisoformat(last[:10])
            except ValueError:
                last_day = None
            if last_day == today:
                # 同一天再发，不涨连续天数
                pass
            elif last_day == today - timedelta(days=1):
                streak += 1
            elif last_day and last_day < today - timedelta(days=1):
                streak = 1
            else:
                streak = max(streak, 1)
        else:
            streak = 1
        conn.execute(
            "UPDATE pet SET streak = ?, last_post = ? WHERE id = 1",
            (streak, today.isoformat()),
        )
    bonus = min(20, 5 * max(0, streak - 1))
    return streak, bonus


def stats() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(exp_gain), 0) AS exp FROM post"
        ).fetchone()
        liked = conn.execute("SELECT likes FROM post").fetchall()
    total_likes = 0
    for item in liked:
        total_likes += len(json.loads(item["likes"]))
    return {
        "total_posts": row["total"],
        "total_likes": total_likes,
        "total_exp": row["exp"],
    }
