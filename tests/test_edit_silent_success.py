"""story_edit must never report success for an edit it did not make.

`data` is flat: {"<field>": value} or {"<Section name>": body}. Before this was
pinned, any unrecognised key — including a nested call like
`{"frontmatter": {...}}`, which the schema description invites — was dumped
verbatim into `entities.extra`. The write "succeeded", the response said
`success: true`, and the edit was silently lost. The agent had no way to notice.

Two guarantees:
  1. An unrecognised key is a hard error, before anything is written.
  2. A success names what actually landed, so "nothing applied" is visible.
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "v"
    dest = v / "projects" / "save-the-children"
    dest.parent.mkdir(parents=True)
    shutil.copytree(str(FIXTURE), str(dest))
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config",
                        lambda: {"root_path": str(v)})
    from tools.story_import import handler
    handler({"project": "save-the-children", "confirm": True}, root_path=str(v))
    return v


def _edit(vault, data, entity_type="character", slug="kael"):
    from tools.story_edit import handler
    return json.loads(handler({
        "action": "edit_note",
        "target": {"entity_type": entity_type, "slug": slug,
                   "project": "save-the-children"},
        "data": data, "summary": "t"}, root_path=str(vault)))


def _field(vault, name, entity_type="character", entity_id="kael"):
    from tools.story_retrieve import handler
    r = json.loads(handler({
        "project": "save-the-children", "entity_type": entity_type,
        "id": [entity_id], "fields": [name]}, root_path=str(vault)))
    return r["entities"][0]["fields"][name]


class TestUnrecognisedKeysAreRejected:
    """The original defect: a nested call reported success and changed nothing."""

    def test_nested_frontmatter_is_rejected(self, vault):
        r = _edit(vault, {"frontmatter": {"goals_short": "NESTED"}})
        assert "error" in r
        assert "frontmatter" in r["error"]

    def test_nested_sections_is_rejected(self, vault):
        assert "error" in _edit(vault, {"sections": {"Background": "x"}})

    def test_rejected_edit_changes_nothing(self, vault):
        before = _field(vault, "goals_short")
        _edit(vault, {"frontmatter": {"goals_short": "NESTED"}})
        assert _field(vault, "goals_short") == before

    def test_error_explains_the_flat_shape(self, vault):
        """The caller must be able to correct itself without guessing."""
        r = _edit(vault, {"frontmatter": {}})
        assert "flat" in r["error"]
        assert "unrecognised_keys" in r

    def test_error_offers_the_valid_names(self, vault):
        r = _edit(vault, {"nonsense_key": 1})
        assert r["valid_field_examples"]
        assert "story_describe" in r["hint"]

    def test_one_bad_key_rejects_the_whole_call(self, vault):
        """Partial application is worse than none: the agent would think the
        valid half landed and not retry."""
        before = _field(vault, "goals_short")
        r = _edit(vault, {"goals_short": "SHOULD NOT APPLY", "sectons": {"x": 1}})
        assert "error" in r
        assert _field(vault, "goals_short") == before

    def test_nothing_is_leaked_into_extra(self, vault):
        _edit(vault, {"frontmatter": {"goals_short": "NESTED"}})
        db = vault / "projects" / "save-the-children" / ".story" / "story.db"
        conn = sqlite3.connect(str(db))
        extra = conn.execute(
            "SELECT extra FROM entities WHERE id='kael'").fetchone()[0]
        conn.close()
        assert "frontmatter" not in extra
        assert "NESTED" not in extra


class TestSuccessNamesWhatLanded:
    def test_field_edit_reports_the_field(self, vault):
        r = _edit(vault, {"goals_short": "ESCAPE OR DIE"})
        assert r["success"] is True
        assert r["applied"]["fields"] == ["goals_short"]
        assert r["applied"]["sections"] == []

    def test_section_edit_reports_the_section(self, vault):
        r = _edit(vault, {"Background": "Prose."})
        assert r["applied"]["sections"] == ["Background"]
        assert r["applied"]["fields"] == []

    def test_relation_edit_is_reported(self, vault):
        r = _edit(vault, {"characters": ["kael", "mira"]},
                  entity_type="scene", slug="central-room-day")
        assert r["applied"]["relations"] == ["characters"]

    def test_computed_only_edit_warns_that_nothing_landed(self, vault):
        """A read-only field must not look like a successful write."""
        from core.constants import ENTITY_SCHEMAS
        computed = [f for f, m in ENTITY_SCHEMAS["character"].items()
                    if m.get("computed")]
        if not computed:
            pytest.skip("character has no computed fields")
        r = _edit(vault, {computed[0]: "anything"})
        assert "warning" in r
        assert r["skipped_read_only"] == [computed[0]]
        assert not any(r["applied"].values())


class TestValidKeysStillWork:
    """A guard that rejects real keys is worse than no guard."""

    def test_flat_field_edit_applies(self, vault):
        _edit(vault, {"goals_short": "ESCAPE OR DIE"})
        assert _field(vault, "goals_short") == "ESCAPE OR DIE"

    def test_section_prose_applies(self, vault):
        from tools.story_retrieve import handler
        _edit(vault, {"Background": "PROSE MARKER."})
        r = json.loads(handler({
            "project": "save-the-children", "entity_type": "character",
            "id": ["kael"], "sections": ["all"]}, root_path=str(vault)))
        assert r["entities"][0]["sections"]["Background"] == "PROSE MARKER."

    def test_every_valid_key_of_every_entity_type_is_accepted(self, vault):
        """Sweeps the whole surface, so a schema addition cannot be locked out."""
        from core.constants import ENTITY_SCHEMAS
        from core.entity import (_RELATION_FIELDS, ENTITY_COLUMN_MAP,
                                 standard_sections)
        from tools.story_edit import _FIELDS_TO_SKIP

        db = vault / "projects" / "save-the-children" / ".story" / "story.db"
        conn = sqlite3.connect(str(db))
        samples = {}
        for etype, eid in conn.execute("SELECT type, id FROM entities"):
            samples.setdefault(etype, eid)
        conn.close()

        rejected = []
        for etype, sample in samples.items():
            schema = ENTITY_SCHEMAS.get(etype, {})
            keys = ([k for k in schema if not schema[k].get("computed")]
                    + list(standard_sections(etype))
                    + list(_RELATION_FIELDS.get(etype, {}))
                    + list(ENTITY_COLUMN_MAP.get(etype, {})))
            for key in keys:
                if key in _FIELDS_TO_SKIP:
                    continue
                if "error" in _edit(vault, {key: "PROBE"}, etype, sample):
                    rejected.append(f"{etype}.{key}")
        assert not rejected, f"valid keys wrongly rejected: {rejected}"
