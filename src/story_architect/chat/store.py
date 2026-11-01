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
    tools TEXT,
    drafts TEXT,
    attachments TEXT,
    hidden INTEGER NOT NULL DEFAULT 0,
    error TEXT,
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
    # migrate older DBs: add new columns if missing
    cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
    for col, ddl in (
        ("tools", "TEXT"),
        ("drafts", "TEXT"),
        ("attachments", "TEXT"),
        ("hidden", "INTEGER NOT NULL DEFAULT 0"),
        ("error", "TEXT"),
    ):
        if col not in cols:
            conn.execute(f"ALTER TABLE messages ADD COLUMN {col} {ddl}")
    conn.commit()
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


def get_conversation(project_path, cid, include_hidden=False) -> dict | None:
    conn = connect(project_path)
    try:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at, backend_state FROM conversations WHERE id=?",
            (cid,),
        ).fetchone()
        if not row:
            return None
        msgs = conn.execute(
            "SELECT id, role, text, timestamp, metadata, status, tools, drafts, attachments, hidden, error FROM messages WHERE conversation_id=? ORDER BY id",
            (cid,),
        ).fetchall()
        messages = []
        for m in msgs:
            if (m[9] or 0) and not include_hidden:
                continue
            tools = _loads(m[6])
            if isinstance(tools, list):
                conv_tools = []
                for t in tools:
                    if isinstance(t, str):
                        conv_tools.append({"id": t, "name": t, "status": "finished"})
                    else:
                        conv_tools.append(t)
                tools = conv_tools
            messages.append({
                "id": m[0], "role": m[1], "text": m[2], "timestamp": m[3],
                "metadata": _loads(m[4]), "status": m[5],
                "tools": tools, "drafts": _loads(m[7]),
                "attachments": _loads(m[8]), "hidden": bool(m[9]),
                "error": m[10],
            })
        return {
            "id": row[0], "title": row[1], "created_at": row[2],
            "updated_at": row[3], "backend_state": _loads(row[4]),
            "messages": messages,
        }
    finally:
        conn.close()


def prepare_retry(project_path, cid) -> str | None:
    """Delete the last assistant message and hidden notes after the last user
    message; return that user message's text, or None if there is none."""
    conn = connect(project_path)
    try:
        rows = conn.execute(
            "SELECT id, role FROM messages WHERE conversation_id=? ORDER BY id", (cid,)
        ).fetchall()
        last_user_id = None
        for r in rows:
            if r[1] == "user":
                last_user_id = r[0]
        if last_user_id is None:
            return None
        for r in rows:
            if r[0] > last_user_id:
                conn.execute("DELETE FROM messages WHERE id=?", (r[0],))
        conn.commit()
        row = conn.execute("SELECT text FROM messages WHERE id=?", (last_user_id,)).fetchone()
        return row[0] if row else None
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


def add_message(project_path, cid, role, text, metadata=None, status="complete",
                tools=None, drafts=None, attachments=None, hidden=False, error=None) -> int:  # type: ignore[return-value]
    now = _now()
    conn = connect(project_path)
    try:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, text, timestamp, metadata, status, tools, drafts, attachments, hidden, error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cid, role, text, now, _dumps(metadata), status, _dumps(tools),
             _dumps(drafts), _dumps(attachments), 1 if hidden else 0, error),
        )
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))
        conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid
    finally:
        conn.close()


def update_message(project_path, msg_id, text, status="complete", metadata=None,
                   tools=None, drafts=None, attachments=None, hidden=None, error=None,
                   update_tools=False, update_drafts=False, update_attachments=False,
                   update_hidden=False, update_error=False) -> None:
    conn = connect(project_path)
    try:
        sets = ["text=?", "status=?"]
        vals = [text, status]
        if metadata is not None:
            sets.append("metadata=?"); vals.append(_dumps(metadata))
        if update_tools:
            sets.append("tools=?"); vals.append(_dumps(tools))
        if update_drafts:
            sets.append("drafts=?"); vals.append(_dumps(drafts))
        if update_attachments:
            sets.append("attachments=?"); vals.append(_dumps(attachments))
        if update_hidden:
            sets.append("hidden=?"); vals.append(1 if hidden else 0)
        if update_error:
            sets.append("error=?"); vals.append(error)
        vals.append(msg_id)
        conn.execute(f"UPDATE messages SET {', '.join(sets)} WHERE id=?", tuple(vals))
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
