"""Small UI-writable settings store (state.json next to config.toml)."""
from __future__ import annotations
import json
import os
from pathlib import Path

def state_file() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "story-architect" / "state.json"

def load_state() -> dict:
    p = state_file()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}

def save_state(patch: dict) -> dict:
    p = state_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    cur = load_state()
    cur.update(patch)
    p.write_text(json.dumps(cur))
    return cur