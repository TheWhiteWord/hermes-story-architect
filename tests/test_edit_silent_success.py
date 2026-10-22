"""An edit must never report success for an edit it did not make.

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
from pathlib import Path

import pytest


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
    _import(v)
    return v


def _import(root):
    from tools.story_import import handler
    handler({"project": "save-the-children", "confirm": True}, root_path=str(root))


def _project(vault):
    return vault / "projects" / "save-the-children"


def _edit(vault, data, entity_type="character", slug="kael"):
    from core.writes import edit_entity
    return edit_entity(_project(vault), entity_type, slug, data, "t")


def _probe_value(meta: dict):
    """A well-typed value for a field's declared type, for the acceptance sweep.

    The sweep asserts a valid KEY is accepted; a wrong-typed value is correctly
    refused, so the probe must satisfy the field's shape. Scalar fields take a
    plain string (empty for enums, which the write path accepts); a structured
    field takes one entry whose sub-fields carry type-correct values.

    Optional sub-fields are filled too, not only the required ones: a list of
    objects whose optional members are all absent is an empty entry, and a
    field with a content rule (scene_beats.beats) refuses that. Filling them is
    also what makes the probe exercise the nested shape.
    """
    if not meta:
        return "PROBE"
    kind = meta.get("type")
    if kind == "number":
        return 0
    if kind == "boolean":
        return False
    if kind == "list":
        entry = {k: _probe_value(m) for k, m in (meta.get("sub_fields") or {}).items()}
        return [entry] if entry else []
    if kind == "object":
        if meta.get("keyed"):
            return {}
        return {k: _probe_value(m) for k, m in (meta.get("sub_fields") or {}).items()}
    if meta.get("enum"):
        return ""
    return "PROBE"


def _has_ref(meta: dict) -> bool:
    """True if the field, or any nested sub-field, declares a `ref`."""
    if meta.get("ref"):
        return True
    return any(_has_ref(m) for m in (meta.get("sub_fields") or {}).values())


def _has_reference_site(meta: dict) -> bool:
    """True if any sub-field is a reference site, declared or by name.

    `_has_ref` covers a declared `ref`. A `scene_beats` beat's `by` and
    `changes[].entity` are reference sites the schema cannot declare (three and
    four target types), so they are resolved by name instead — see
    `core.entity.validate_beat_references`. A probe of "PROBE" cannot resolve
    either way, so the sweep skips a field carrying one.
    """
    if meta.get("ref"):
        return True
    for name, sub in (meta.get("sub_fields") or {}).items():
        if name in ("by", "entity") or _has_ref(sub):
            return True
        if _has_reference_site(sub):
            return True
    return False


def _field(vault, name, entity_type="character", entity_id="kael"):
    from tools.story_retrieve import handler
    r = json.loads(handler({
        "project": "save-the-children", "entity_type": entity_type,
        "id": [entity_id], "fields": [name]}, root_path=str(vault)))
    return r["entities"][0]["fields"][name]


class TestUnrecognisedKeysAreRejected:
    """The original defect: a nested call reported success and changed nothing."""

    def test_nested_frontmatter_is_rejected(self, vault):
        with pytest.raises(ValueError, match="frontmatter"):
            _edit(vault, {"frontmatter": {"goals_short": "NESTED"}})

    def test_nested_sections_is_rejected(self, vault):
        with pytest.raises(ValueError):
            _edit(vault, {"sections": {"Background": "x"}})

    def test_rejected_edit_changes_nothing(self, vault):
        before = _field(vault, "goals_short")
        with pytest.raises(ValueError):
            _edit(vault, {"frontmatter": {"goals_short": "NESTED"}})
        assert _field(vault, "goals_short") == before

    def test_error_explains_the_flat_shape(self, vault):
        """The caller must be able to correct itself without guessing — so the
        shape rule travels with the failure, not just the key that broke."""
        with pytest.raises(ValueError) as exc:
            _edit(vault, {"frontmatter": {}})
        assert "flat" in str(exc.value)

    def test_error_offers_the_valid_names(self, vault):
        """Same reason: an error naming nothing actionable just gets retried
        the same wrong way."""
        from core.constants import ENTITY_SCHEMAS
        with pytest.raises(ValueError) as exc:
            _edit(vault, {"nonsense_key": 1})
        message = str(exc.value)
        # A real field name and a real section name, so the caller can copy one.
        fields = [f for f, m in ENTITY_SCHEMAS["character"].items()
                  if not m.get("computed")]
        assert fields[0] in message
        assert "Background" in message

    def test_one_bad_key_rejects_the_whole_call(self, vault):
        """Partial application is worse than none: the agent would think the
        valid half landed and not retry."""
        before = _field(vault, "goals_short")
        with pytest.raises(ValueError):
            _edit(vault, {"goals_short": "SHOULD NOT APPLY", "sectons": {"x": 1}})
        assert _field(vault, "goals_short") == before

    def test_nothing_is_leaked_into_extra(self, vault):
        with pytest.raises(ValueError):
            _edit(vault, {"frontmatter": {"goals_short": "NESTED"}})
        conn = sqlite3.connect(str(_project(vault) / ".story" / "story.db"))
        try:
            extra = conn.execute(
                "SELECT extra FROM entities WHERE id='kael'").fetchone()[0]
        finally:
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
        from core.entity import (ENTITY_COLUMN_MAP, relation_fields,
                                 standard_sections)
        from core.writes import _FIELDS_TO_SKIP

        conn = sqlite3.connect(str(_project(vault) / ".story" / "story.db"))
        try:
            samples = {}
            for etype, eid in conn.execute("SELECT type, id FROM entities"):
                samples.setdefault(etype, eid)
        finally:
            conn.close()

        rejected = []
        for etype, sample in samples.items():
            schema = ENTITY_SCHEMAS.get(etype, {})
            keys = ([k for k in schema if not schema[k].get("computed")]
                    + list(standard_sections(etype))
                    + list(relation_fields(etype))
                    + list(ENTITY_COLUMN_MAP.get(etype, {})))
            for key in keys:
                if key in _FIELDS_TO_SKIP:
                    continue
                # A field is accepted only when its VALUE is well-typed, the
                # same rule every write path enforces. A bare "PROBE" is the
                # right probe for a scalar but is refused for a structured
                # field — which is correct, not a rejection. Build the probe
                # from the field's declared type so the sweep tests acceptance
                # of a valid value rather than tolerance of a wrong one.
                probe = _probe_value(schema.get(key, {}))
                # A value's id is fixed at create and must stay the slug of
                # its name (validate_value), so renaming a value is only
                # accepted for a name that slugs back to the same id. The
                # sweep's sample id IS that slug, so the probe renames to it.
                if etype == "value" and key == "name":
                    probe = sample
                # A field whose entries carry a `ref` needs a real entity of that
                # type; the sweep cannot synthesise one, so those fields are out
                # of scope for the acceptance check (their ref is validated
                # elsewhere, at write time, against real records).
                if _has_reference_site(schema.get(key, {})):
                    continue
                try:
                    # Rebuild per probe: one field's probe can invalidate
                    # another's (a plot schema probe orphans the scenes' turns),
                    # so each edit runs against a fresh copy of the project.
                    shutil.rmtree(_project(vault) / ".story", ignore_errors=True)
                    _import(vault)
                    _edit(vault, {key: probe}, etype, sample)
                except ValueError:
                    rejected.append(f"{etype}.{key}")
        assert not rejected, f"valid keys wrongly rejected: {rejected}"
