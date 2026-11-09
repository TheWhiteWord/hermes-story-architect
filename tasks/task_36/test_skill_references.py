"""The agent skill must not drift from the code it describes.

A skill is written once and goes stale the moment a tool, view or status is
renamed — and a stale skill is worse than a thin one, because it sends the
agent to things that no longer exist. So every identifier the skill puts in
backticks has to resolve against the live code, and a rename fails here, in the
change that made it, instead of in a session.

The skill also costs context in every session (Hermes tells the agent to load
any skill that is even partly relevant), so its size is pinned: growing it
should be a decision, not drift.
"""

import importlib
import pkgutil
import re
from pathlib import Path

import story_architect
from story_architect import tools as tools_pkg
from story_architect.app.mcp_server import build_registry
from story_architect.core.constants import SCENE_STATUSES

PKG = Path(story_architect.__file__).parent
SKILL = PKG / "adapters" / "hermes" / "assets" / "skills" / "story-architect" / "SKILL.md"

# Response keys the skill tells the agent to look for. They are not schema
# parameters, so they are checked against the source that emits them.
RESPONSE_KEYS = {"truncated", "detail", "not_found", "validation", "preview_md"}

MAX_WORDS = 850             # the whole file; ~1.2k tokens
MAX_DESCRIPTION_CHARS = 300  # shown in every system prompt's skill index


def _tool_schemas() -> dict:
    out = {}
    for mod in pkgutil.iter_modules(tools_pkg.__path__):
        if mod.name.startswith("story_"):
            schema = getattr(importlib.import_module(f"story_architect.tools.{mod.name}"),
                             "SCHEMA", None)
            if isinstance(schema, dict):
                out[mod.name] = schema
    return out


def _enums(node, found=None):
    """Every enum value anywhere inside a schema (views, actions, ops, categories)."""
    found = set() if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "enum" and isinstance(value, list):
                found.update(v for v in value if isinstance(v, str))
            else:
                _enums(value, found)
    elif isinstance(node, list):
        for item in node:
            _enums(item, found)
    return found


def _param_names(node, found=None):
    found = set() if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                found.update(value)
            _param_names(value, found)
    elif isinstance(node, list):
        for item in node:
            _param_names(item, found)
    return found


def _source_text() -> str:
    return "\n".join(p.read_text() for sub in ("tools", "core")
                     for p in (PKG / sub).glob("*.py"))


def _split(text):
    assert text.startswith("---\n"), "SKILL.md must start with frontmatter"
    front, _, body = text[4:].partition("\n---\n")
    return front, body


def _vocabulary() -> dict:
    schemas = _tool_schemas()
    # Tool names as the agent sees them come from the registry the server
    # actually serves, not from module filenames.
    vocab = {"tool": {name for name, _, _ in build_registry()},
             "enum": set(), "param": set(), "status": set(SCENE_STATUSES)}
    for schema in schemas.values():
        vocab["enum"] |= _enums(schema)
        vocab["param"] |= _param_names(schema)
    return vocab


class TestSkillStaysTrue:
    def test_every_backticked_name_exists_in_the_code(self):
        _, body = _split(SKILL.read_text())
        vocab = _vocabulary()
        known = set().union(*vocab.values())
        source = _source_text()
        unknown = []
        for token in sorted(set(re.findall(r"`([^`]+)`", body))):
            if token in known:
                continue
            if token in RESPONSE_KEYS and f'"{token}"' in source:
                continue
            unknown.append(token)
        assert not unknown, (
            f"SKILL.md names {unknown}, which are no longer a tool, parameter, view, "
            f"action, status or response key. Update the skill (or this test's "
            f"vocabulary if the name is deliberately new).")

    def test_every_response_key_the_skill_relies_on_is_still_emitted(self):
        source = _source_text()
        gone = [k for k in RESPONSE_KEYS if f'"{k}"' not in source]
        assert not gone, f"no longer emitted anywhere: {gone}"

    def test_the_vocabulary_check_would_catch_a_rename(self):
        """Guard the guard: a made-up name must NOT resolve."""
        vocab = _vocabulary()
        known = set().union(*vocab.values())
        assert "load" in known and "track" in known and "locked" in known
        assert "story_overview" not in known and "timeline" not in known


class TestSkillStaysSmall:
    def test_frontmatter_is_valid_and_the_description_is_short(self):
        front, _ = _split(SKILL.read_text())
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        desc = re.search(r"^description:\s*(.+)$", front, re.M)
        assert name and name.group(1).strip() == "story-architect"
        assert desc and 20 < len(desc.group(1)) <= MAX_DESCRIPTION_CHARS, \
            "the description sits in every system prompt; keep it short"

    def test_the_body_stays_within_its_context_budget(self):
        words = len(SKILL.read_text().split())
        assert words <= MAX_WORDS, (
            f"SKILL.md is {words} words (limit {MAX_WORDS}). It is loaded in "
            f"every session: shorten it, or raise the limit on purpose.")
