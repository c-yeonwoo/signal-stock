"""SQLite 통합 저장소 (data/cache/app.db).

1단계 스캐폴딩 범위: 인증·온보딩·워치리스트·범용 캐시만.
시세/시그널 전용 테이블은 2단계 시그널 엔진 도입 시 이 파일에 추가한다(kv로 임시 대체 가능).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB = Path("data/cache/app.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE, pwhash TEXT, created INTEGER);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, uid INTEGER, ts INTEGER);
CREATE TABLE IF NOT EXISTS profile(uid INTEGER PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS favorites(uid INTEGER, kind TEXT, key TEXT, label TEXT, ts INTEGER,
    PRIMARY KEY(uid, kind, key));
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT, ts INTEGER);
"""


def conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript(_SCHEMA)
    return c


# ---------- users / sessions ----------
def user_create(email: str, pwhash: str) -> int | None:
    c = conn()
    try:
        cur = c.execute("INSERT INTO users(email,pwhash,created) VALUES(?,?,?)",
                        (email.lower().strip(), pwhash, int(time.time())))
        c.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None  # 이미 가입된 이메일
    finally:
        c.close()


def user_by_email(email: str):
    c = conn()
    row = c.execute("SELECT id,email,pwhash FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
    c.close()
    return {"id": row[0], "email": row[1], "pwhash": row[2]} if row else None


def session_create(token: str, uid: int) -> None:
    c = conn()
    c.execute("INSERT OR REPLACE INTO sessions(token,uid,ts) VALUES(?,?,?)", (token, uid, int(time.time())))
    c.commit()
    c.close()


def session_user(token: str):
    if not token:
        return None
    c = conn()
    row = c.execute("SELECT u.id,u.email FROM sessions s JOIN users u ON u.id=s.uid WHERE s.token=?",
                    (token,)).fetchone()
    c.close()
    return {"id": row[0], "email": row[1]} if row else None


def session_delete(token: str) -> None:
    c = conn()
    c.execute("DELETE FROM sessions WHERE token=?", (token,))
    c.commit()
    c.close()


# ---------- profile (uid → JSON, 온보딩 데이터) ----------
def profile_get(uid: int) -> dict:
    c = conn()
    row = c.execute("SELECT data FROM profile WHERE uid=?", (uid,)).fetchone()
    c.close()
    return json.loads(row[0]) if row and row[0] else {}


def profile_set(uid: int, data: dict) -> None:
    c = conn()
    c.execute("INSERT OR REPLACE INTO profile(uid,data) VALUES(?,?)",
              (uid, json.dumps(data, ensure_ascii=False)))
    c.commit()
    c.close()


# ---------- favorites (워치리스트 — kind='ticker') ----------
def fav_list(uid: int) -> list[dict]:
    c = conn()
    rows = c.execute("SELECT kind,key,label FROM favorites WHERE uid=? ORDER BY ts DESC", (uid,)).fetchall()
    c.close()
    return [{"kind": k, "key": key, "label": lb} for k, key, lb in rows]


def fav_add(uid: int, kind: str, key: str, label: str) -> None:
    c = conn()
    c.execute("INSERT OR REPLACE INTO favorites(uid,kind,key,label,ts) VALUES(?,?,?,?,?)",
              (uid, kind, key, label, int(time.time())))
    c.commit()
    c.close()


def fav_remove(uid: int, kind: str, key: str) -> None:
    c = conn()
    c.execute("DELETE FROM favorites WHERE uid=? AND kind=? AND key=?", (uid, kind, key))
    c.commit()
    c.close()


# ---------- kv (범용 JSON 캐시) ----------
def kv_get(k: str, max_age: int | None = None):
    """캐시 값(JSON 역직렬화). 없거나 max_age(초) 초과 시 None."""
    c = conn()
    row = c.execute("SELECT v, ts FROM kv WHERE k=?", (k,)).fetchone()
    c.close()
    if not row:
        return None
    if max_age is not None and (time.time() - row[1]) > max_age:
        return None
    return json.loads(row[0])


def kv_set(k: str, v) -> None:
    c = conn()
    c.execute("INSERT OR REPLACE INTO kv(k,v,ts) VALUES(?,?,?)",
              (k, json.dumps(v, ensure_ascii=False), int(time.time())))
    c.commit()
    c.close()
