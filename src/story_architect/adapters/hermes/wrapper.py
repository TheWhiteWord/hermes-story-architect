"""Wrapper around the hermes CLI and profile paths."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def find_hermes() -> str | None:
    return shutil.which("hermes")


def run_hermes(*args, env=None) -> tuple[int, str, str]:
    exe = find_hermes()
    if exe is None:
        raise FileNotFoundError("hermes executable not found on PATH")
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([exe, *args], capture_output=True, text=True, env=e)
    return p.returncode, p.stdout, p.stderr


def profile_dir(name: str) -> Path:
    return hermes_home() / "profiles" / name


def version() -> str | None:
    try:
        rc, out, err = run_hermes("--version")
    except FileNotFoundError:
        return None
    if rc != 0:
        return None
    return (out or err).strip()
