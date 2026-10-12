"""A hand-edited note must not import a value the schema forbids.

The gap this closes: `_extra_for` refused an unknown KEY but never checked the
value of a known one, so `dramatic_role: climax` imported clean after the enum
narrowed to plot_role/transition/non-event — stored, reported as success, and
read back as a value no reader expects. The importer is the one place a
value arrives that no agent typed through a validating tool, so it is the one
place this has to be checked.

The second half is the part that is easy to get wrong by accident. Only the
VALUE checks are fatal to an import; the structural ones are build-order
constraints (a required field not yet written, a relationship still missing
one of its two perspectives) and a note is allowed to be mid-shape. Filtering
too much turns the check into a no-op that still looks present.

"""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from core.entity import validate_entity, value_problems


def make_project(tmp_path):
    """Copy the fixture into tmp_path once. Returns the project dir.

    Separate from `import_project` because the rollback test imports TWICE —
    copytree refuses an existing destination, so a combined helper would fail
    on the second call and quietly never exercise the refusal.
    """
    root = tmp_path / "projects"
    root.mkdir(exist_ok=True)
    proj = root / "stc"
    shutil.copytree(
        str(Path(__file__).parent / "fixtures" / "save-the-children"), str(proj))
    return proj


def run_import(proj, root):
    """Import an already-copied project and return the parsed response, so a
    refusal is asserted on the response rather than on an exception raised
    somewhere below."""
    from tools.story_import import handler
    import core.config

    real = core.config.load_plugin_config
    core.config.load_plugin_config = lambda: {"root_path": str(root)}
    try:
        return json.loads(handler({"project": str(proj), "confirm": True,
                                   "root_path": str(root)}))
    finally:
        core.config.load_plugin_config = real


def import_project(tmp_path, mutate=None):
    """Copy the fixture, optionally mutate one note, import it once."""
    proj = make_project(tmp_path)
    if mutate:
        mutate(proj)
    return run_import(proj, tmp_path)


def _strip_yaml_block(text: str, key: str) -> str:
    """Drop a top-level YAML key and its whole block value.

    `plot_roles:` is a block sequence, whose items sit at the SAME indentation
    as every other top-level key — so "indented under the key" is not the
    boundary. An item is any line that is another mapping entry (`key:`), a
    sequence item (`- `), or a continuation (indented); the value ends at the
    first line that is none of those. Removing only the `key:` line leaves the
    items dangling, which is a YAML syntax error: it is what made the three
    `test_every_current_value_still_imports` cases fail on a document no
    parser could read, with the check itself never once running.
    """
    lines = text.splitlines()
    fm_end = lines.index("---", 1)
    start = lines.index(f"{key}:", 0, fm_end)
    end = start + 1
    while end < fm_end:
        line = lines[end]
        if line.startswith("- ") or line.startswith(" ") or not line.strip():
            end += 1
            continue
        break
    return "\n".join(lines[:start] + lines[end:fm_end] + lines[fm_end:])


def set_dramatic_role(value, clear_roles=False):
    def mutate(proj):
        note = proj / "scenes" / "Central Room - Day.md"
        text = note.read_text().replace(
            "dramatic_role: plot_role", f"dramatic_role: {value}")
        if clear_roles:
            # `transition` / `non-event` are mutually exclusive with carrying
            # plot roles, so a scene that keeps its roles and claims to be a
            # non-event is refused by the CROSS-FIELD rule — correctly, and
            # tested in test_scene_dramatic_role.py. These cases are about the
            # value vocabulary, so the roles go too.
            text = _strip_yaml_block(text, "plot_roles")
        note.write_text(text)
    return mutate


class TestTheValueCheck:
    def test_a_retired_role_is_refused(self, tmp_path):
        """`climax` was a valid value before the enum narrowed. It imports as
        a silent corruption today; this is the case that motivated the check."""
        result = import_project(tmp_path, set_dramatic_role("climax"))
        assert result.get("success") is not True, "a retired value imported clean"
        assert "Invalid scene frontmatter" in result.get("error", "")
        assert "climax" in result["error"]

    def test_the_refusal_names_the_valid_values(self, tmp_path):
        """The agent holding the note needs to know what to put instead."""
        result = import_project(tmp_path, set_dramatic_role("climax"))
        assert "story_describe" in result["error"]

    @pytest.mark.parametrize("value", ["plot_role", "transition", "non-event"])
    def test_every_current_value_still_imports(self, tmp_path, value):
        """The check must not have narrowed the vocabulary by accident."""
        result = import_project(tmp_path, set_dramatic_role(value, clear_roles=True))
        assert result.get("success") is True, result

    def test_a_refused_import_leaves_the_project_untouched(self, tmp_path):
        """The wipe-and-rebuild is inside a transaction, so a refusal must
        leave the PREVIOUS state standing — not an empty database.

        Asserting "no rows" would pass on a rollback and also pass on an
        import that simply never ran; what distinguishes a correct rollback
        from a silently skipped import is that the rows before are the rows
        after, still carrying their original values.
        """
        proj = make_project(tmp_path)
        assert run_import(proj, tmp_path).get("success") is True, \
            "the fixture must import clean first"

        db = proj / ".story" / "story.db"

        def snapshot():
            conn = sqlite3.connect(str(db))
            rows = conn.execute(
                "SELECT id, extra FROM entities ORDER BY id").fetchall()
            conn.close()
            return rows

        before = snapshot()

        note = proj / "scenes" / "Central Room - Day.md"
        note.write_text(note.read_text().replace(
            "dramatic_role: plot_role", "dramatic_role: climax"))
        result = run_import(proj, tmp_path)
        assert result.get("success") is not True
        assert snapshot() == before, "a refused import changed the project"

    def test_another_enum_field_is_caught_too(self, tmp_path):
        """It is not a dramatic_role special case — the check is per type, and
        `arc_type` is a character enum with its own vocabulary."""
        def mutate(proj):
            note = proj / "characters" / "Dr Elena Voss.md"
            text = note.read_text()
            assert "arc_type: negative" in text, "fixture changed; pick another"
            note.write_text(text.replace("arc_type: negative",
                                         "arc_type: sideways"))
        result = import_project(tmp_path, mutate)
        assert result.get("success") is not True
        assert "Invalid character frontmatter" in result.get("error", "")


class TestTheStructuralChecksAreNotFatal:
    """The half that must NOT be filtered in.

    These are build-order constraints. An import creates every entity in one
    pass over notes that may be mid-shape, so enforcing them refuses a whole
    project over a field the author has not got to yet. A test asserting only
    that a bad value is refused would still pass with the filter empty.
    """

    def test_a_missing_required_field_does_not_block_the_import(self, tmp_path):
        def mutate(proj):
            note = proj / "characters" / "Kael.md"
            text = note.read_text()
            note.write_text(text.replace("story_role: Protagonist\n", ""))
        result = import_project(tmp_path, mutate)
        assert result.get("success") is True, result

    def test_a_relationship_missing_a_perspective_does_not_block(self, tmp_path):
        """The case that caught this: enforcing the structural checks broke
        the fixture import outright, 306 errors, because perspectives arrive
        after the characters they reference."""
        assert validate_entity("relationship", {
            "characters": ["kael", "mira"], "perspectives": {"kael": {}}})
        assert not value_problems("relationship", {
            "characters": ["kael", "mira"], "perspectives": {"kael": {}}})

    def test_the_fixture_imports_clean(self, tmp_path):
        """The whole fixture, through the real check. Every structural warning
        it legitimately carries must be filtered, and every value valid."""
        result = import_project(tmp_path)
        assert result.get("success") is True, result

    def test_value_problems_is_a_real_subset_not_everything(self, tmp_path):
        """Guards the filter against silently excluding every check: a bad
        value must survive it, a missing field must not."""
        bad_value = value_problems("scene", {"dramatic_role": "climax"})
        assert bad_value, "the value check is being filtered out"
        missing = value_problems("scene", {})
        assert not missing, "a structural warning leaked into the fatal set"
