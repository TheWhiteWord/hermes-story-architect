"""A scene's script as an editable list of blocks — pure functions, no DB.

The scene's `Content` section (Fountain text) stays the single source of truth,
so the agent and a human edit the same artifact. This module is the bridge the
script editor needs: Fountain text <-> typed blocks, plus the facts the editor
shows beside the page (cast, heading parts, findings, stats).

Why not just reuse `fountain_lexer.parse`? The lexer is a *reader* built for
rendering: it throws away blank-line structure and the original text of lines
it does not model. An editor has to write the text back, so this module works
paragraph by paragraph (the unit Fountain is actually defined in) and keeps
anything it does not model as a `raw` block, verbatim. It still leans on the
lexer's own regexes so the two can never disagree about what a heading, a cue
or a transition is. `tests/test_scene_script.py` pins that parity against the
lexer on real scene content.

Block types: action, character, parenthetical, dialogue, transition, note, raw.
The scene heading is NOT a block: it is generated from INT/EXT + location +
time of day (see `compose_heading`) and written as the first line of Content.

What this module deliberately does not do: touch the database, decide who may
write, or validate that a location exists. Those are `core/manual_edits.py`.
"""
from __future__ import annotations

import re

from .constants import SCENE_TIMES_OF_DAY
from .fountain_lexer import (
    CHARACTER_RE,
    PARENTHETICAL_RE,
    SCENE_HEADING_RE,
    TRANSITION_RE,
    trim_character_extension,
    trim_character_force_symbol,
)

BLOCK_TYPES = ("action", "character", "parenthetical", "dialogue",
               "transition", "note", "raw")

# Canonical INT/EXT prefixes the heading controls offer.
INT_EXT_CHOICES = ("INT.", "EXT.", "INT./EXT.", "EST.")

_PLACEHOLDER_RE = re.compile(r"^\s*\[placeholder", re.IGNORECASE)
_NOTE_RE = re.compile(r"^\[\[(.*)\]\]$", re.DOTALL)
_SCENE_NUMBER_RE = re.compile(r"#[-.0-9a-z]+#\s*$", re.IGNORECASE)
_HEADING_PARTS_RE = re.compile(
    r"^\s*(?P<ie>INT\./EXT\.|INT/EXT\.?|I/E\.?|INT\.?|EXT\.?|EST\.?)\s+(?P<rest>\S.*?)\s*$",
    re.IGNORECASE)
_TIME_SEP_RE = re.compile(r"\s+[-–—]\s+")
# A line that is exactly two spaces is Fountain's in-dialogue line break, not a
# paragraph separator.
_LINE_BREAK = "  "


# ─── Content in/out ──────────────────────────────────────────────────────────

def is_placeholder(content: str) -> bool:
    """A template's `[placeholder — scene/Content]` marker is not content."""
    return bool(_PLACEHOLDER_RE.match(content or ""))


def _split_paragraphs(lines: list[str]) -> list[list[str]]:
    paras, cur = [], []
    for ln in lines:
        if ln.strip() == "" and ln != _LINE_BREAK:
            if cur:
                paras.append(cur)
                cur = []
        else:
            cur.append(ln.rstrip() if ln != _LINE_BREAK else ln)
    if cur:
        paras.append(cur)
    return paras


def split_heading(content: str) -> tuple[str | None, str]:
    """(heading line or None, the rest of the content).

    The heading is the first non-blank line when it is a scene heading — the
    one rule `scene_content_lint` enforces. Without one, everything is body and
    `findings` reports it.
    """
    if is_placeholder(content):
        return None, ""
    lines = (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for i, ln in enumerate(lines):
        if ln.strip():
            if SCENE_HEADING_RE.match(ln):
                return ln.strip(), "\n".join(lines[i + 1:])
            return None, "\n".join(lines[i:])
    return None, ""


def parse_blocks(body: str) -> list[dict]:
    """Fountain body text (no heading) -> blocks. Never raises, never drops text."""
    lines = (body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[dict] = []
    for para in _split_paragraphs(lines):
        blocks.extend(_parse_paragraph(para))
    return blocks


def _raw(para):
    return [{"type": "raw", "text": "\n".join(para)}]


def _parse_paragraph(para: list[str]) -> list[dict]:
    first = para[0].strip()

    if first.startswith("!"):                       # forced action
        text = "\n".join([para[0].lstrip()[1:]] + para[1:])
        return [{"type": "action", "text": text}]

    if first.startswith("@"):                       # forced character
        if len(para) >= 2 and not first.endswith("^"):
            return _dialogue_group(para)
        return _raw(para)

    # Everything the editor does not model stays verbatim.
    if (SCENE_HEADING_RE.match(first)               # a heading mid-script
            or first[:1] in ("#", "=", "~", ">")    # section/synopsis/page break/lyric/centered
            or first.endswith("^")):                # dual dialogue
        return _raw(para)

    if len(para) == 1 and TRANSITION_RE.match(first):
        return [{"type": "transition", "text": first}]

    joined = "\n".join(para)
    m = _NOTE_RE.match(joined.strip())
    if m and "]]" not in m.group(1):
        return [{"type": "note", "text": m.group(1).strip()}]

    # A cue needs something after it: the lexer only treats an all-caps line as
    # a character when dialogue follows, and a lone all-caps line is action.
    if len(para) >= 2 and CHARACTER_RE.match(first):
        return _dialogue_group(para)

    return [{"type": "action", "text": joined}]


def _dialogue_group(para: list[str]) -> list[dict]:
    cue = para[0].strip()
    if cue.startswith("@"):
        cue = cue[1:].strip()
    out = [{"type": "character", "text": cue}]
    speech: list[str] = []

    def flush():
        if speech:
            out.append({"type": "dialogue",
                        "text": "\n".join("" if s == _LINE_BREAK else s
                                          for s in speech)})
            speech.clear()

    for ln in para[1:]:
        if PARENTHETICAL_RE.match(ln.strip()):
            flush()
            out.append({"type": "parenthetical", "text": ln.strip()})
        else:
            speech.append(ln.strip() if ln != _LINE_BREAK else ln)
    flush()
    return out


def serialize_blocks(blocks: list[dict]) -> str:
    """Blocks -> Fountain body text (no heading, no trailing newline).

    A force marker is added only where the plain text would be read as
    something else, so the stored Fountain stays clean for the agent: `!` for
    an action line that would parse as a heading/cue/etc., `@` for a cue that
    is not all-caps. Empty blocks are dropped.
    """
    paras: list[list[str]] = []
    in_speech = False  # inside a character's group: parentheticals/dialogue attach
    for b in blocks:
        t = b.get("type")
        text = (b.get("text") or "")
        if t == "raw":
            paras.append(text.split("\n"))
            in_speech = False
            continue
        if not text.strip():
            continue
        if t == "character":
            cue = text.strip()
            paras.append([cue if CHARACTER_RE.match(cue) else "@" + cue])
            in_speech = True
        elif t == "parenthetical":
            p = text.strip()
            if not (p.startswith("(") and p.endswith(")")):
                p = "(" + p.strip("()") + ")"
            (paras[-1].append(p) if in_speech else paras.append([p]))
        elif t == "dialogue":
            lines = [ln.strip() if ln.strip() else _LINE_BREAK
                     for ln in text.strip("\n").split("\n")]
            (paras[-1].extend(lines) if in_speech else paras.append(lines))
        elif t == "transition":
            paras.append([text.strip()])
            in_speech = False
        elif t == "note":
            paras.append(["[[" + text.strip() + "]]"])
            in_speech = False
        else:  # action (and any unknown type: never lose the text)
            lines = text.strip("\n").split("\n")
            if _would_misparse(lines):
                lines[0] = "!" + lines[0].lstrip()
            paras.append(lines)
            in_speech = False
    return "\n\n".join("\n".join(p) for p in paras)


def _would_misparse(lines: list[str]) -> bool:
    got = _parse_paragraph([ln.rstrip() for ln in lines if ln.strip()] or [""])
    return not (len(got) == 1 and got[0]["type"] == "action")


def compose_content(heading: str | None, blocks: list[dict]) -> str:
    body = serialize_blocks(blocks)
    parts = [p for p in (heading, body) if p]
    return "\n\n".join(parts) + ("\n" if parts else "")


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text or "", re.UNICODE)


def is_lossless(content: str, heading: str | None, blocks: list[dict]) -> bool:
    """True when opening this content in the editor and saving it back keeps
    every word. A False here means the editor must open read-only rather than
    silently rewrite a script it does not fully understand."""
    again = compose_content(heading, blocks)
    if _words(again) != _words(content):
        return False
    h2, body2 = split_heading(again)
    return parse_blocks(body2) == blocks


# ─── Heading ─────────────────────────────────────────────────────────────────

def _canon_int_ext(raw: str) -> str:
    r = raw.upper().replace(" ", "")
    if r.startswith(("INT./EXT", "INT/EXT", "I/E")):
        return "INT./EXT."
    if r.startswith("INT"):
        return "INT."
    if r.startswith("EXT"):
        return "EXT."
    return "EST."


def parse_heading(heading: str | None) -> dict:
    """Split a heading line into the three controls the editor shows.

    `mode` is "structured" when the heading round-trips through
    `compose_heading`, and "custom" when it does not (a forced `.SNIPER POV`
    heading, a scene number, a time of day outside the six the schema allows).
    A custom heading is kept verbatim and its controls are disabled.
    """
    text = (heading or "").strip()
    empty = {"mode": "structured", "int_ext": "INT.", "location_text": "",
             "time_text": "", "time_of_day": "", "text": text}
    if not text:
        return empty
    custom = {**empty, "mode": "custom"}
    if text.startswith(".") or _SCENE_NUMBER_RE.search(text):
        return custom
    m = _HEADING_PARTS_RE.match(text)
    if not m:
        return custom
    rest = m.group("rest")
    parts = _TIME_SEP_RE.split(rest)
    time_text = ""
    if len(parts) >= 2 and parts[-1].strip().upper() in SCENE_TIMES_OF_DAY:
        time_text = parts[-1].strip().upper()
        rest = " - ".join(parts[:-1])
    return {"mode": "structured", "int_ext": _canon_int_ext(m.group("ie")),
            "location_text": rest.strip(), "time_text": time_text,
            "time_of_day": time_text, "text": text}


def compose_heading(int_ext: str, location_name: str, time_of_day: str = "") -> str:
    """`INT. KITCHEN - NIGHT`. The location name is upper-cased, as in a script."""
    if int_ext not in INT_EXT_CHOICES:
        raise ValueError(f"int_ext must be one of {', '.join(INT_EXT_CHOICES)}")
    if time_of_day and time_of_day not in SCENE_TIMES_OF_DAY:
        raise ValueError(f"time_of_day must be one of {', '.join(SCENE_TIMES_OF_DAY)}")
    name = " ".join((location_name or "").split()).upper()
    if not name:
        raise ValueError("a heading needs a location")
    return f"{int_ext} {name}" + (f" - {time_of_day}" if time_of_day else "")


def suggest_location(location_text: str, locations: list[dict]) -> str | None:
    """A registered location whose name or slug equals the heading's text.

    Exact (case/whitespace/leading "the" aside) on purpose: the heading says
    KITCHEN, and silently linking it to "Kitchen Annex" because the words
    overlap is a wrong link the author never sees. The editor offers the
    suggestion; it does not apply it.
    """
    def norm(s):
        s = " ".join((s or "").lower().replace("-", " ").split())
        return s[4:] if s.startswith("the ") else s
    want = norm(location_text)
    if not want:
        return None
    hits = [l["id"] for l in locations
            if want in (norm(l.get("name")), norm(l.get("id")))]
    return hits[0] if len(hits) == 1 else None


# ─── Cast ────────────────────────────────────────────────────────────────────

def cue_key(cue: str) -> str:
    """A cue as a stable key: no `@`, `(V.O.)`, `^`; one space; upper-case."""
    c = trim_character_extension(trim_character_force_symbol(cue or ""))
    return " ".join(c.replace("^", "").split()).upper()


def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[^\w']+", s.upper()) if t}


def resolve_cue(key: str, characters: list[dict]) -> dict:
    """Resolve one cue key to a registered character.

    -> {"id": slug|None, "candidates": [slugs]}. Strictly: the full name, the
    slug, or a set of whole words of exactly one character's name (OAK ->
    Detective Oak). No substring and no fuzzy matching: DET would match
    "Detective Oak" and so would MA match "Mara", and a link made on a prefix
    is a wrong link the author never sees. Ambiguity resolves to nothing.
    """
    for c in characters:
        if key in (c["name"].upper(), c["id"].replace("-", " ").upper(), c["id"].upper()):
            return {"id": c["id"], "candidates": []}
    want = _tokens(key)
    if not want or len(key) < 2:
        return {"id": None, "candidates": []}
    hits = [c["id"] for c in characters if want <= _tokens(c["name"])]
    if len(hits) == 1:
        return {"id": hits[0], "candidates": []}
    return {"id": None, "candidates": hits}


def script_cast(blocks: list[dict], characters: list[dict]) -> list[dict]:
    """Who speaks in this script, in order of first appearance.

    Registered speakers carry their slug and role; the rest are ad-hoc, known
    only from the script — nothing is stored for them, which is the point.
    """
    order: list[str] = []
    counts: dict[str, int] = {}
    first_block: dict[str, int] = {}
    for i, b in enumerate(blocks):
        if b.get("type") == "character" and b.get("text", "").strip():
            k = cue_key(b["text"])
            if not k:
                continue
            if k not in counts:
                order.append(k)
                first_block[k] = i
            counts[k] = counts.get(k, 0) + 1
    by_id = {c["id"]: c for c in characters}
    cast, seen_ids = [], set()
    for k in order:
        r = resolve_cue(k, characters)
        cid = r["id"]
        if cid and cid in seen_ids:           # OAK and DETECTIVE OAK: one person
            for e in cast:
                if e["id"] == cid:
                    e["cues"] += counts[k]
            continue
        if cid:
            seen_ids.add(cid)
        cast.append({
            "cue": k, "id": cid, "registered": bool(cid),
            "name": by_id[cid]["name"] if cid else k.title(),
            "story_role": by_id[cid].get("story_role", "") if cid else "",
            "cues": counts[k], "first_block": first_block[k],
            "candidates": r["candidates"],
        })
    return cast


# ─── Stats ───────────────────────────────────────────────────────────────────

def script_stats(content: str, cast: list[dict]) -> dict:
    """`lines` are text lines (non-blank), per the existing dashboard figure;
    `speaking_parts` are distinct speakers."""
    lines = [ln for ln in (content or "").splitlines() if ln.strip()]
    return {"lines": len(lines), "words": len(_words(content)),
            "speaking_parts": len(cast)}


# ─── Findings ────────────────────────────────────────────────────────────────

CRITICAL, OTHER = "critical", "other"

# Optional fields the editor reports as gaps in the "Others" group. The ones
# below are CRITICAL for a scene and are reported there, so they are skipped in
# the generic unfilled list rather than reported twice.
_REPORTED_AS_CRITICAL = {"heading", "location", "time_of_day", "plot_roles",
                         "characters"}


def _finding(level, code, message, **anchor):
    return {"level": level, "code": code, "message": message, **anchor}


def findings(*, scene: dict, heading: dict, heading_line: str | None,
             blocks: list[dict], cast: list[dict], location: dict | None,
             has_plot_roles: bool, unfilled: list[str],
             lossless: bool = True) -> list[dict]:
    """Everything worth telling the author about this scene's script.

    Critical = what breaks the script or the scene's place in the story:
    entities the script uses that do not exist, and the optional fields a
    scene cannot function without. Required fields are not reported (the write
    path already refuses a record without them). Other = remaining optional
    gaps, from the shared `unfilled_fields`.

    Each finding may carry an anchor — {"block": i} or {"field": name} — so the
    editor can jump to the thing.
    """
    out: list[dict] = []

    if not lossless:
        out.append(_finding(CRITICAL, "not_editable",
                            "This script uses Fountain the editor cannot round-trip "
                            "without losing text, so it opens read-only. Edit it with Hermes."))
    if not heading_line:
        out.append(_finding(CRITICAL, "heading_missing",
                            "The script has no scene heading. A scene without one is "
                            "absent from the script view.", field="heading"))
    if not scene.get("order"):
        out.append(_finding(CRITICAL, "order_unset",
                            "Scene order is 0 — it has not been placed in its sequence yet.",
                            field="order"))
    if not scene.get("time_of_day"):
        out.append(_finding(CRITICAL, "time_of_day_missing",
                            "Time of day is not set.", field="time_of_day"))

    if location is None:
        text = heading.get("location_text")
        out.append(_finding(
            CRITICAL, "location_unregistered",
            (f"Location '{text}' is not a registered location." if text
             else "No location is set."), field="location"))
    elif not location.get("world"):
        out.append(_finding(CRITICAL, "location_no_world",
                            f"Location '{location['name']}' belongs to no world.",
                            field="location"))

    for c in cast:
        if not c["registered"]:
            hint = (f" Could be: {', '.join(c['candidates'])}." if c["candidates"] else "")
            out.append(_finding(CRITICAL, "character_unregistered",
                                f"Character '{c['name']}' is not a registered character.{hint}",
                                block=c["first_block"]))

    in_speech = False
    for i, b in enumerate(blocks):
        t = b.get("type")
        if t == "character":
            in_speech = bool((b.get("text") or "").strip())
        elif t in ("parenthetical", "dialogue"):
            if not in_speech and (b.get("text") or "").strip():
                out.append(_finding(CRITICAL, "orphan_dialogue",
                                    f"This {t} has no character before it, so it will "
                                    f"read as action.", block=i))
        else:
            in_speech = False
        if t == "transition" and not TRANSITION_RE.match((b.get("text") or "").strip()):
            out.append(_finding(CRITICAL, "transition_unrecognised",
                                "This will not read as a transition. Use 'CUT TO:' or "
                                "'FADE OUT.' style.", block=i))

    if not has_plot_roles and scene.get("dramatic_role") not in ("transition", "non-event"):
        out.append(_finding(CRITICAL, "plot_roles_missing",
                            "The scene serves no plot, and is not marked transition or "
                            "non-event.", field="plot_roles"))

    for f in unfilled:
        if f in _REPORTED_AS_CRITICAL and f != "characters":
            continue
        if f == "characters" and (scene.get("no_cast") or cast):
            continue
        out.append(_finding(OTHER, "unfilled",
                            f"Missing: field '{f}' not found in scene "
                            f"'{scene.get('title') or scene.get('id')}'.", field=f))
    return out
