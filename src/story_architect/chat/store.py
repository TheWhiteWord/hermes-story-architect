"""SQLite conversation store (chat.db per project)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    backend_state TEXT,
    last_opened INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL,
    metadata TEXT,
    status TEXT NOT NULL DEFAULT 'complete',
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path(project_path: Path) -> Path:
    return Path(project_path) / ".story" / "chat.db"


def connect(project_path: Path) -> sqlite3.Connection:
    p = _db_path(project_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def create_conversation(project_path, title="") -> str:
    cid = str(uuid.uuid4())
    now = _now()
    conn = connect(project_path)
    try:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (cid, title, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return cid


def list_conversations(project_path) -> list[dict]:
    conn = connect(project_path)
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at, last_opened FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [{"id": r[0], "title": r[1], "created_at": r[2],
                 "updated_at": r[3], "last_opened": bool(r[4])} for r in rows]
    finally:
        conn.close()


def get_conversation(project_path, cid) -> dict | None:
    conn = connect(project_path)
    try:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at, backend_state FROM conversations WHERE id=?",
            (cid,),
        ).fetchone()
        if not row:
            return None
        msgs = conn.execute(
            "SELECT role, text, timestamp, metadata, status FROM messages WHERE conversation_id=? ORDER BY id",
            (cid,),
        ).fetchall()
        return {
            "id": row[0], "title": row[1], "created_at": row[2],
            "updated_at": row[3], "backend_state": _loads(row[4]),
            "messages": [
                {"role": m[0], "text": m[1], "timestamp": m[2],
                 "metadata": _loads(m[3]), "status": m[4]} for m in msgs
            ],
        }
    finally:
        conn.close()


def delete_conversation(project_path, cid) -> bool:
    conn = connect(project_path)
    try:
        cur = conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def add_message(project_path, cid, role, text, metadata=None, status="complete") -> int:  # type: ignore[return-value]
    now = _now()
    conn = connect(project_path)
    try:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, text, timestamp, metadata, status) VALUES (?,?,?,?,?,?)",
            (cid, role, text, now, _dumps(metadata), status),
        )
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))
        conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid
    finally:
        conn.close()


def update_message(project_path, msg_id, text, status="complete", metadata=None) -> None:
    conn = connect(project_path)
    try:
        if metadata is None:
            conn.execute("UPDATE messages SET text=?, status=? WHERE id=?", (text, status, msg_id))
        else:
            conn.execute("UPDATE messages SET text=?, status=?, metadata=? WHERE id=?",
                         (text, status, _dumps(metadata), msg_id))
        conn.commit()
    finally:
        conn.close()


def set_backend_state(project_path, cid, state) -> None:
    conn = connect(project_path)
    try:
        conn.execute("UPDATE conversations SET backend_state=? WHERE id=?", (_dumps(state), cid))
        conn.commit()
    finally:
        conn.close()


def set_title(project_path, cid, title) -> None:
    conn = connect(project_path)
    try:
        conn.execute("UPDATE conversations SET title=? WHERE id=?", (title, cid))
        conn.commit()
    finally:
        conn.close()


def mark_last_opened(project_path, cid) -> None:
    conn = connect(project_path)
    try:
        conn.execute("UPDATE conversations SET last_opened=0")
        conn.execute("UPDATE conversations SET last_opened=1 WHERE id=?", (cid,))
        conn.commit()
    finally:
        conn.close()


def _loads(v):
    if v is None:
        return None
    try:
        return json.loads(v)
    except Exception:
        return None


def _dumps(v):
    if v is None:
        return None
    return json.dumps(v)
