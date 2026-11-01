"""Bearer token management for the MCP endpoint."""
from __future__ import annotations

import os
import secrets
from pathlib import Path


def config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / "story-architect"
    d.mkdir(parents=True, exist_ok=True)
    return d


def token_path() -> Path:
    return config_dir() / "token"


def load_token() -> str | None:
    p = token_path()
    if not p.exists():
        return None
    return p.read_text().strip() or None


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_token() -> str:
    existing = load_token()
    if existing:
        return existing
    tok = generate_token()
    p = token_path()
    p.write_text(tok)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return tok


def api_key_path() -> Path:
    return config_dir() / "api_key"


def load_api_key() -> str | None:
    p = api_key_path()
    if not p.exists():
        return None
    return p.read_text().strip() or None


def ensure_api_key() -> str:
    existing = load_api_key()
    if existing:
        return existing
    tok = generate_token()
    p = api_key_path()
    p.write_text(tok)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return tok