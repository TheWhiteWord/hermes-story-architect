"""Response budget: keep a tool's answer small enough that the host never has
to cut it for us.

Why this exists. A host agent caps every tool result. Past its cap it swaps the
result for a short preview plus a file path, and this plugin's agents have no
file tools to read that path with. The agent then proceeds on a preview of a
map that was meant to be whole. A story tool's answer has to be complete or
say, in its own words, what it left out and how to ask for it.

So the rule here is: *the tool* decides what to compact, at a structural
boundary (a whole sequence, a whole entity), and says so. The host's cut never
fires. Nothing is silently dropped — a compacted unit stays visible as a
compact row, and the response carries the exact call that expands it.

The budget is in characters of the JSON text, which is what a host counts. It
must sit a little UNDER the host's cap, and that cap is not a fixed number: it
usually scales with the model's context window, which this plugin cannot see.
So the budget is a setting you state once, resolved in this order:

    1. env var   STORY_ARCHITECT_MAX_RESPONSE_CHARS
    2. config    max_response_chars   in the [story_architect] table of
                 ~/.config/story-architect/config.toml (the file that already
                 holds port and root)
    3. default   35000   (safe from ~65k-token windows up)

A value that is not a whole number >= 2000 is ignored and the next source is
tried. A host adapter (see adapters/) can provide a helper that works the
number out for its host's model.
"""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Callable

DEFAULT_MAX_RESPONSE_CHARS = 35_000
_ENV = "STORY_ARCHITECT_MAX_RESPONSE_CHARS"
# Below this the budget cannot hold even a bare map; treat it as a typo.
_MIN_SANE = 2_000


def _valid(value) -> int | None:
    """`value` as a usable budget, or None. Bools and floats are not budgets."""
    if isinstance(value, bool):
        return None
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number >= _MIN_SANE else None


def _config_file() -> Path:
    # Same location as app/config.py (core may not import from app).
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "story-architect" / "config.toml"


def _from_config_file() -> int | None:
    try:
        with _config_file().open("rb") as f:
            table = tomllib.load(f).get("story_architect", {})
        return _valid(table.get("max_response_chars"))
    except Exception:   # a missing or malformed file just means "not set"
        return None


def max_response_chars() -> int:
    """The response budget: env var, then config.toml, then the default."""
    from_env = _valid(os.environ.get(_ENV, ""))
    if from_env is not None:
        return from_env
    from_file = _from_config_file()
    if from_file is not None:
        return from_file
    return DEFAULT_MAX_RESPONSE_CHARS


def json_size(obj) -> int:
    """Length of `obj` as the tool will emit it (json.dumps defaults)."""
    return len(json.dumps(obj))


def largest_fitting(build: Callable[[int], object], n_units: int,
                    budget: int) -> tuple[int, object]:
    """Largest k in [0, n_units] for which `build(k)` fits `budget`.

    `build(k)` returns the response with the FIRST k units at full detail and
    the rest compacted. Size must not shrink as k grows (full rows are a
    superset of compact rows), which makes a binary search exact: the answer is
    measured on the real output, not estimated.

    Returns (k, response). When even k=0 is over budget, k=0 is returned
    anyway — the compact form is the floor, and the caller's hint tells the
    agent how to scope down.
    """
    full = build(n_units)
    if json_size(full) <= budget:
        return n_units, full
    lo, hi = 0, n_units - 1   # n_units is known not to fit
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if json_size(build(mid)) <= budget:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return best, build(best)


def compacted_note(unit_name: str, ids: list[str], expand_hint: str) -> dict:
    """The `detail` block that tells the agent what was compacted and how to
    get it back. Present only when something was compacted."""
    return {
        "compacted": ids,
        "reason": (f"The full response would exceed the size budget, so these "
                   f"{unit_name}s are listed compactly. Nothing was removed."),
        "expand": expand_hint,
    }
