"""Response budget: keep a tool's answer small enough that the host never has
to cut it for us.

Why this exists. Hermes caps every MCP result (`tool_budget.mcp_result_size_chars`,
50k chars by default and scaled DOWN for small context windows: ~19k at a 32k
window, ~39k at 65k). Past the cap the host swaps the result for a ~1.5k-char
preview plus a file path, and this plugin's agents have no file tools to read
that path with. The agent then proceeds on a preview of a map that was meant to
be whole. A story tool's answer has to be complete or say, in its own words,
what it left out and how to ask for it.

So the rule here is: *the tool* decides what to compact, at a structural
boundary (a whole sequence, a whole entity), and says so. The host's cut never
fires. Nothing is silently dropped — a compacted unit stays visible as a
compact row, and the response carries the exact call that expands it.

The budget is in characters of the JSON text, which is what the host counts.
Set it a little under the host's threshold:

    STORY_ARCHITECT_MAX_RESPONSE_CHARS   (default 35000)

For a 32k-token model use ~15000; for 65k use ~30000; for 128k+ the default
is already safely under the host's 50k.
"""

from __future__ import annotations

import json
import os
from typing import Callable

DEFAULT_MAX_RESPONSE_CHARS = 35_000
_ENV = "STORY_ARCHITECT_MAX_RESPONSE_CHARS"
# Below this the budget cannot hold even a bare map; treat it as a typo.
_MIN_SANE = 2_000


def max_response_chars() -> int:
    """The configured budget, falling back to the default on a bad value."""
    raw = os.environ.get(_ENV, "").strip()
    if not raw:
        return DEFAULT_MAX_RESPONSE_CHARS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_RESPONSE_CHARS
    return value if value >= _MIN_SANE else DEFAULT_MAX_RESPONSE_CHARS


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
