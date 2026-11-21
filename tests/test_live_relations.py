"""Deleting flags; reading hides. Relations are never removed by a delete.

Until now `delete_entity` removed the relation rows that pointed AT a deleted
entity and a plot's role rows, and kept the rows the entity owned. Readers did
not filter, so the kept rows showed a deleted character in a live scene's cast
(retrieve, the form, the script editor), while the removed rows were gone for
good: delete + restore lost a scene's cast, its location link and its plot
role.

Now every row stays, and every READ of relations goes through the
`live_relations` view, which drops a row whose either end is flagged deleted.
"""
import json
import re
import shutil
import sqlite3
from pathlib import Path

import pytest

from story_architect.core import db as core_db
from story_architect.core.db import SCHEMA_MIGRATIONS, apply_migrations, create_schema, get_db
from story_architect.core.writes import create_project, delete_entity
from story_architect.tools.story_admin import handler as admin
from story_architect.tools.story_import import handler as import_handler
import twin_helpers as twin

SLUG = "save-the-children"
SRC = Path(core_db.__file__).resolve().parents[1]


@pytest.fixture
def proj(fixture_path, tmp_path):
    vault = tmp_path / "v"
    p = vault / "projects" / SLUG
    p.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(p))
    import_handler({"project": SLUG, "confirm": True}, root_path=str(vault))
    return p, vault


def _sql(p, sql, *args):
    conn = sqlite3.connect(str(p / ".story" / "story.db"))
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _raw(p):
    return sorted(_sql(p, "SELECT from_id, to_id, kind, note, \"order\" FROM relations"))


def _visible(p):
    return sorted(_sql(p, "SELECT from_id, to_id, kind, note, \"order\" FROM live_relations"))


def _restore(proj, etype, eid):
    p, vault = proj
    return json.loads(admin({"action": "restore", "project": SLUG,
                             "target": {"entity_type": etype, "id": eid},
                             "summary": "t"}, root_path=str(vault)))


# ─── the view ───

class TestTheView:
    def test_a_new_project_has_it(self, tmp_path):
        root = tmp_path / "v"
        (root / "projects").mkdir(parents=True)
        create_project("stc", {"name": "STC", "logline": "L"}, root)
        conn = get_db(root / "projects" / "stc")
        try:
            assert conn.execute("SELECT 1 FROM sqlite_master WHERE type='view' "
                                "AND name='live_relations'").fetchone()
        finally:
            conn.close()

    def test_an_old_database_gets_it_on_open_and_keeps_its_rows(self, proj):
        p, _ = proj
        before = _raw(p)
        c = sqlite3.connect(str(p / ".story" / "story.db"))
        c.execute("DROP VIEW live_relations")
        c.execute("PRAGMA user_version = 3")
        c.close()
        get_db(p).close()
        assert _raw(p) == before
        assert _visible(p) == before  # nothing deleted yet: all visible

    def test_a_row_with_either_end_deleted_is_hidden(self, proj):
        p, _ = proj
        c = sqlite3.connect(str(p / ".story" / "story.db"))
        c.execute("UPDATE entities SET is_deleted=1 WHERE id='kael'")        # a from_id
        c.execute("UPDATE entities SET is_deleted=1 WHERE id='the-core-day'")  # a to_id
        c.commit()
        c.close()
        hidden = set(_raw(p)) - set(_visible(p))
        assert hidden
        assert all("kael" in r[:2] or "the-core-day" in r[:2] for r in hidden)
        assert not any("kael" in r[:2] or "the-core-day" in r[:2] for r in _visible(p))

    def test_it_is_skipped_where_there_is_no_relations_table(self, tmp_path):
        """A view over a missing table breaks every later ALTER TABLE RENAME."""
        c = sqlite3.connect(str(tmp_path / "x.db"), isolation_level=None)
        c.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT)")
        apply_migrations(c, SCHEMA_MIGRATIONS)
        assert c.execute("SELECT 1 FROM sqlite_master WHERE type='view'").fetchone() is None
        c.execute("ALTER TABLE entities RENAME TO entities_old")  # would raise with a dangling view
        c.close()

    def test_create_schema_makes_it_once_the_tables_exist(self, tmp_path):
        c = sqlite3.connect(str(tmp_path / "x.db"), isolation_level=None)
        c.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT)")
        apply_migrations(c, SCHEMA_MIGRATIONS)  # stamped current, no view
        create_schema(c)
        assert c.execute("SELECT 1 FROM sqlite_master WHERE type='view' "
                         "AND name='live_relations'").fetchone()
        c.close()


# ─── delete keeps every row ───

@pytest.mark.parametrize("etype,eid", [
    ("character", "kael"), ("scene", "central-room-day"), ("plot", "the-resistance"),
    ("location", "the-central-room"), ("world", "the-i"),
])
class TestDeleteKeepsRowsAndRestoreIsExact:
    def test_no_relation_row_is_removed_by_a_delete(self, proj, etype, eid):
        p, _ = proj
        before = _raw(p)
        assert delete_entity(p, etype, eid, "t", True)["success"]
        assert _raw(p) == before

    def test_no_reader_sees_a_relation_to_it(self, proj, etype, eid):
        p, _ = proj
        delete_entity(p, etype, eid, "t", True)
        dead = {r[0] for r in _sql(p, "SELECT id FROM entities WHERE is_deleted=1")}
        assert [r for r in _visible(p) if r[0] in dead or r[1] in dead] == []

    def test_delete_then_restore_gives_back_every_relation(self, proj, etype, eid):
        p, _ = proj
        raw, visible = _raw(p), _visible(p)
        delete_entity(p, etype, eid, "t", True)
        assert _restore(proj, etype, eid)["success"]
        assert _raw(p) == raw
        assert _visible(p) == visible


class TestNoGhostsInReaders:
    """After deleting a character, a live scene no longer lists them.

    Each reader below used to show kael in the cast of a live scene, through
    the relation row he owned.
    """
    SCENE = "central-room-day"

    @pytest.fixture
    def gone(self, proj):
        p, vault = proj
        assert "kael" in {r[0] for r in _sql(
            p, "SELECT from_id FROM relations WHERE to_id=? AND kind='character_scene'", self.SCENE)}
        delete_entity(p, "character", "kael", "t", True)
        return p, vault

    def test_story_retrieve(self, gone):
        from story_architect.tools.story_retrieve import handler
        p, vault = gone
        out = json.loads(handler({"project": SLUG, "entity_type": "scene", "id": self.SCENE,
                                  "fields": ["characters"]}, root_path=str(vault)))
        assert out["entities"][0]["fields"]["characters"] == ["mira"]

    def test_the_entity_form(self, gone):
        from story_architect.core.manual_entities import load_entity
        p, _ = gone
        form = load_entity(p, "scene", self.SCENE)
        assert form["values"]["characters"] == ["mira"]
        assert [c["display"] for c in form["computed"]["characters"]] == ["Mira"]

    def test_the_script_editor_cast(self, gone):
        from story_architect.core.manual_edits import load_scene_script
        p, _ = gone
        assert [c["id"] for c in load_scene_script(p, self.SCENE)["cast"]] == ["mira"]

    def test_the_markdown_export(self, gone):
        from story_architect.tools.story_export import handler
        p, vault = gone
        assert json.loads(handler({"project": SLUG}, root_path=str(vault)))["success"]
        text = next(f.read_text() for f in (p / "scenes").rglob("*.md")
                    if f"id: {self.SCENE}\n" in f.read_text())
        front = text.split("---")[1]
        cast = re.search(r"^characters:\n((?:- .*\n)+)", front, re.M)
        assert cast and "kael" not in cast.group(1) and "mira" in cast.group(1)

    def test_a_dead_plots_role_is_not_a_plot_of_the_scene(self, proj):
        """story_load's values view and the retrieve plot_roles field."""
        from story_architect.tools.story_retrieve import handler
        p, vault = proj
        delete_entity(p, "plot", "the-resistance", "t", True)
        out = json.loads(handler({"project": SLUG, "entity_type": "scene", "id": self.SCENE,
                                  "fields": ["plot_roles"]}, root_path=str(vault)))
        assert "the-resistance" not in [r["plot"] for r in out["entities"][0]["fields"]["plot_roles"]]


class TestPreviewAndPurge:
    def test_the_preview_counts_what_will_go_out_of_view(self, proj):
        p, _ = proj
        n = len(_sql(p, "SELECT 1 FROM relations WHERE from_id='kael' OR to_id='kael'"))
        assert n > 0
        assert delete_entity(p, "character", "kael", "t")["relations_deleted"] == n

    def test_purge_still_removes_the_rows_for_good(self, proj):
        p, vault = proj
        delete_entity(p, "character", "kael", "t", True)
        from story_architect.core.trash import purge_deleted
        res = purge_deleted(p, {"entity_type": "character", "id": "kael"})
        assert res.get("success"), res
        assert [r for r in _raw(p) if "kael" in r[:2]] == []


# ─── story_load on an old database ───

def test_story_load_upgrades_an_old_database_instead_of_failing(proj):
    """It used to open the file with a bare connect, which skips the upgrade."""
    from story_architect.tools.story_load import handler
    p, vault = proj
    c = sqlite3.connect(str(p / ".story" / "story.db"))
    c.execute("DROP VIEW live_relations")
    c.execute("PRAGMA user_version = 3")
    c.close()
    for view in (None, "dramatic_elements", "values"):
        args = {"project": SLUG, **({"view": view} if view else {})}
        out = json.loads(handler(args, root_path=str(vault)))
        assert "no such table" not in json.dumps(out), (view, out)


# ─── the rule, enforced ───

def test_every_read_of_relations_goes_through_the_view():
    """A raw `FROM relations` read would show a deleted entity again.

    Writers (INSERT / DELETE / UPDATE) use the table and are not matched. The
    allowed reads are the view's own definition (SCHEMA_SQL and migration 4)
    and the integrity oracle: it must see rows the view hides, because a
    dangling reference whose other end is in the trash is still an orphan.
    """
    pattern = re.compile(r"(?<!DELETE )\b(?:FROM|JOIN)\s+relations\b")
    found = {}
    for f in SRC.rglob("*.py"):
        n = len(pattern.findall(f.read_text(encoding="utf-8")))
        if n:
            found[str(f.relative_to(SRC))] = n
    assert found == {"core/db.py": 2, "core/integrity.py": 2}, (
        f"raw reads of the relations table: {found}. Read `live_relations` instead.")


# ─── hiding is the same as removing, for every reader ───

@pytest.mark.parametrize("etype,eid", [
    ("character", "kael"), ("character", "mira"), ("scene", "central-room-day"),
    ("scene", "the-core-day"), ("plot", "the-resistance"), ("location", "the-central-room"),
    ("location", "the-garden"), ("world", "the-i"), ("relationship", "kael-mira"),
])
def test_hiding_a_deleted_entitys_relations_reads_the_same_as_removing_them(
        fixture_path, tmp_path, etype, eid):
    """The invariant behind the whole change, checked against every reader.

    Twin projects, one entity deleted in both. In one the relation rows stay
    (hidden by the view); in the other every row touching a deleted entity is
    physically removed, which is what the delete used to do. No reader may be
    able to tell them apart. A reader that goes back to the raw table shows the
    kept rows and breaks the equality.
    """
    hidden, vh = twin.build(fixture_path, tmp_path, "hidden")
    removed, vr = twin.build(fixture_path, tmp_path, "removed")
    has_rows = bool(_sql(hidden, "SELECT 1 FROM relations WHERE from_id=? OR to_id=?", eid, eid))
    for p in (hidden, removed):
        assert delete_entity(p, etype, eid, "t", True)["success"]
    twin.remove_relation_rows(removed)
    if has_rows:  # (a relationship entity keeps its characters in extra, not in the table)
        assert len(_raw(hidden)) > len(_raw(removed)), "the twins must differ in the table"

    a = twin.everything_a_reader_can_say(hidden, vh)
    b = twin.everything_a_reader_can_say(removed, vr)
    differing = twin.differing(a, b)
    assert differing == [], f"readers that can tell hidden from removed: {differing}"


# ─── the two writers that read relations ───

class TestWritersSeeOnlyLiveRelations:
    def test_a_dead_plots_role_does_not_block_marking_the_scene_a_transition(self, proj):
        """`transition` requires no plot roles. The only role here belongs to a
        plot that is in the trash, so the scene has none that count."""
        from story_architect.core.writes import edit_entity
        p, _ = proj
        scene = "the-core-day"
        roles = [r for r in _sql(p, "SELECT from_id FROM relations WHERE to_id=? "
                                    "AND kind LIKE 'plot\\_%' ESCAPE '\\'", scene)]
        assert roles, "fixture changed: this scene needs a plot role"
        for (plot_id,) in set(roles):
            delete_entity(p, "plot", plot_id, "t", True)
        res = edit_entity(p, "scene", scene, {"dramatic_role": "transition"}, "t")
        assert res.get("success"), res

    def test_the_preview_does_not_count_relations_already_hidden(self, proj):
        p, _ = proj
        delete_entity(p, "scene", "central-room-day", "t", True)
        visible = len(_sql(p, "SELECT 1 FROM live_relations WHERE from_id='kael' OR to_id='kael'"))
        raw = len(_sql(p, "SELECT 1 FROM relations WHERE from_id='kael' OR to_id='kael'"))
        assert visible < raw
        assert delete_entity(p, "character", "kael", "t")["relations_deleted"] == visible
