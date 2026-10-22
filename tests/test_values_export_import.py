"""Export and import of the single `values.md`.

Values serialize as one file at the project root, one frontmatter block per
value — not the per-note folder model every other type uses. The database holds
one entity per value. These tests pin the round trip and the edges the bespoke
block format introduces: order, the optional `note`, the empty file, and a
hand-edited block that duplicates a ladder word.
"""
import json
import shutil
import sqlite3

import pytest

from core.writes import create_entity, create_project
from tools.story_export import handler as export_handler
from tools.story_import import handler as import_handler
from tools.story_retrieve import handler as retrieve_handler


@pytest.fixture
def vault(tmp_path):
    """An empty project root; import/export resolve `p` against it."""
    root = tmp_path / "vault"
    (root / "projects" / "p").mkdir(parents=True)
    create_project("p", {"name": "P"}, root)
    return root


@pytest.fixture
def proj(vault):
    return vault / "projects" / "p"


def _values(proj):
    conn = sqlite3.connect(str(proj / ".story" / "story.db"))
    try:
        rows = conn.execute(
            "SELECT id, name, extra FROM entities WHERE type='value' ORDER BY id"
        ).fetchall()
        out = []
        for entity_id, name, extra in rows:
            fields = json.loads(extra or "{}")
            out.append((entity_id, name, fields))
        return out
    finally:
        conn.close()


def _sections(proj, entity_id):
    conn = sqlite3.connect(str(proj / ".story" / "story.db"))
    try:
        return conn.execute(
            "SELECT heading, body FROM sections WHERE entity_id=? ORDER BY rowid",
            (entity_id,),
        ).fetchall()
    finally:
        conn.close()


def _export(project, vault):
    return json.loads(export_handler({"project": "p"}, root_path=str(vault)))


def _reimport(project, vault):
    (project / ".story" / "story.db").unlink()
    return json.loads(import_handler({"project": "p", "confirm": True},
                                     root_path=str(vault)))


def _seed(proj):
    create_entity(proj, "value", "trust",
                  {"name": "trust", "p": "open", "c": "wary", "cd": "deceived",
                   "nn": "exploited", "note": "Whether the system tells the truth."},
                  sections={"Definition": "Trust is the throughline.",
                            "Notes": "Held by Kael."})
    create_entity(proj, "value", "loyalty",
                  {"name": "loyalty", "p": "devoted", "c": "bound",
                   "cd": "false", "nn": "betrayed"})
    create_entity(proj, "value", "betrayal",
                  {"name": "betrayal", "p": "open", "c": "wary",
                   "cd": "cruel", "nn": "used"})


class TestExport:
    def test_writes_one_root_values_file(self, proj, vault):
        _seed(proj)
        assert _export(proj, vault)["success"]
        path = proj / "values.md"
        assert path.exists()
        # One file, not a values/ folder of per-note files.
        assert not (proj / "values").exists()

    def test_one_block_per_value_in_id_order(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        text = (proj / "values.md").read_text()
        assert text.count("---\nid:") == 3
        # ORDER BY type, id in the export query keeps the file in id order.
        assert text.index("id: betrayal") < text.index("id: loyalty") \
            < text.index("id: trust")

    def test_field_order_is_schema_order_and_note_is_optional(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        text = (proj / "values.md").read_text()
        # `note` present only on the value that has one.
        assert "note: Whether the system tells the truth." in text
        loyalty = text.split("id: loyalty", 1)[1].split("---", 1)[0]
        assert "note" not in loyalty
        # The ladder reads p/c/cd/nn, not alphabetically.
        block = text.split("id: trust", 1)[1]
        assert block.index("\np:") < block.index("\nc:") < block.index("\ncd:") \
            < block.index("\nnn:") < block.index("\nnote:")

    def test_zero_values_writes_an_empty_present_file(self, proj, vault):
        _export(proj, vault)
        path = proj / "values.md"
        assert path.exists() and path.read_text() == ""

    def test_values_file_is_tracked_in_the_manifest(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        manifest = json.loads((proj / ".story" / "exported.json").read_text())
        assert "values.md" in manifest


class TestRoundTrip:
    def test_fields_survive_exactly_and_order_is_preserved(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        assert _reimport(proj, vault)["success"]
        rows = _values(proj)
        assert [r[0] for r in rows] == ["betrayal", "loyalty", "trust"]
        by_id = {r[0]: r for r in rows}
        assert by_id["trust"][2] == {
            "p": "open", "c": "wary", "cd": "deceived", "nn": "exploited",
            "note": "Whether the system tells the truth."}
        # A value with no note comes back with no note key.
        assert "note" not in by_id["loyalty"][2]
        assert by_id["loyalty"][2] == {
            "p": "devoted", "c": "bound", "cd": "false", "nn": "betrayed"}

    def test_sections_survive(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        _reimport(proj, vault)
        assert _sections(proj, "trust") == [
            ("Definition", "Trust is the throughline."), ("Notes", "Held by Kael.")]

    def test_values_import_before_scenes(self, fixture_path, tmp_path):
        """A scene's turn names a value, so the value must exist first.

        The fixture carries a value turn (`freedom`) and its value in
        `values.md`, so order is asserted directly by watching the import
        walk.
        """
        vault = tmp_path / "vault"
        p = vault / "projects" / "save-the-children"
        p.parent.mkdir(parents=True)
        shutil.copytree(str(fixture_path), str(p))
        _export(p, vault)

        import tools.story_import as si
        order = []
        orig_values, orig_folder = si._import_values, si._import_folder
        si._import_values = lambda conn, pp: (
            order.append("values"), orig_values(conn, pp))[1]

        def _folder(conn, pp, folder, entity_type):
            if entity_type == "scene":
                order.append("scenes")
            return orig_folder(conn, pp, folder, entity_type)

        si._import_folder = _folder
        try:
            (p / ".story" / "story.db").unlink()
            r = json.loads(import_handler(
                {"project": "save-the-children", "confirm": True}, root_path=str(vault)))
        finally:
            si._import_values, si._import_folder = orig_values, orig_folder
        assert r["success"]
        assert order.index("values") < order.index("scenes"), order

    def test_retrieve_reads_a_value_back(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        _reimport(proj, vault)
        out = json.loads(retrieve_handler(
            {"project": "p", "entity_type": "value", "id": ["trust"],
             "fields": ["all"]}, root_path=str(vault)))
        fields = out["entities"][0]["fields"]
        assert list(fields) == ["name", "p", "c", "cd", "nn", "note"]
        assert fields["p"] == "open"


class TestEmptyFile:
    def test_empty_values_md_imports_clean(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        (proj / "values.md").write_text("")
        assert _reimport(proj, vault)["success"]
        assert _values(proj) == []

    def test_absent_values_md_imports_clean(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        (proj / "values.md").unlink()
        assert _reimport(proj, vault)["success"]
        assert _values(proj) == []


class TestHandEditedValues:
    def test_duplicate_ladder_word_is_refused(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        (proj / "values.md").write_text(
            "---\nid: trust\nname: trust\np: open\nc: open\n"
            "cd: deceived\nnn: exploited\n---\n")
        out = _reimport(proj, vault)
        assert "error" in out
        assert "four distinct words" in out["error"]

    def test_id_not_the_slug_is_refused(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        (proj / "values.md").write_text(
            "---\nid: trust-2\nname: trust\np: open\nc: wary\n"
            "cd: deceived\nnn: exploited\n---\n")
        out = _reimport(proj, vault)
        assert "error" in out
        assert "slug of its name" in out["error"]

    def test_duplicate_name_across_blocks_is_refused(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        (proj / "values.md").write_text(
            "---\nid: trust\nname: trust\np: open\nc: wary\n"
            "cd: deceived\nnn: exploited\n---\n\n"
            "---\nid: loyalty\nname: trust\np: a\nc: b\ncd: c\nnn: d\n---\n")
        out = _reimport(proj, vault)
        # The second block's id is not the slug of `trust`, so it is refused —
        # and a real duplicate name is refused too.
        assert "error" in out


class TestIdempotence:
    def test_reexport_removes_nothing(self, proj, vault):
        _seed(proj)
        assert _export(proj, vault)["files_removed"] == []
        assert _export(proj, vault)["files_removed"] == []
        assert _export(proj, vault)["files_removed"] == []
        assert (proj / "values.md").exists()

    def test_a_deleted_value_disappears_from_the_file(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        conn = sqlite3.connect(str(proj / ".story" / "story.db"))
        conn.execute("DELETE FROM entities WHERE id='loyalty'")
        conn.execute("DELETE FROM sections WHERE entity_id='loyalty'")
        conn.commit()
        conn.close()
        _export(proj, vault)
        assert "id: loyalty" not in (proj / "values.md").read_text()
        _reimport(proj, vault)
        assert "loyalty" not in {r[0] for r in _values(proj)}


class TestDiffGuard:
    def test_exported_values_are_not_reported_at_risk(self, proj, vault):
        _seed(proj)
        _export(proj, vault)
        report = json.loads(import_handler({"project": "p", "dry_run": True},
                                           root_path=str(vault)))
        assert report["would_be_destroyed"] == []
