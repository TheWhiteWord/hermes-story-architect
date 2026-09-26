"""Test fixture round-trip: import → export → compare."""
import pytest
import json
import tempfile
import shutil
from pathlib import Path

from tools.story_import import handler as import_handler
from tools.story_export import handler as export_handler


def test_import_creates_schema_and_entities(fixture_path):
    """Import creates schema and populates all tables."""
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        result = import_handler({"project": str(project_path), "root_path": Path(tmp)})
        data = json.loads(result)
        assert data["success"] is True

        from core.db import get_db
        conn = get_db(project_path)

        entities = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
        assert entities > 0

        relations = conn.execute("SELECT count(*) FROM relations").fetchone()[0]
        assert relations > 0

        sections = conn.execute("SELECT count(*) FROM sections").fetchone()[0]
        assert sections > 0

        conn.close()


def test_round_trip_preserves_entities(fixture_path):
    """Import → export → all entities present and correct."""
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        export_dir = Path(tmp) / "exported"
        export_dir.mkdir()
        shutil.copytree(str(project_path), str(export_dir / "proj"))
        export_path = export_dir / "proj"

        # Remove all .md files to test pure DB→file export
        for f in export_path.rglob("*.md"):
            f.unlink()

        result = export_handler({"project": str(export_path), "root_path": str(export_dir)})
        data = json.loads(result)
        assert data["success"] is True

        # Verify key files exist
        assert (export_path / "project.md").exists()
        assert (export_path / "characters" / "kael.md").exists()
        assert (export_path / "arcs" / "kael" / "1.md").exists()
        assert (export_path / "scenes" / "central-room-day.md").exists()
        # No recycle bin with hard delete — soren.md is simply absent
        assert not (export_path / "_recycle-bin" / "character" / "soren.md").exists()


def test_round_trip_preserves_data(fixture_path):
    """Import → re-import exported data → same entity types, sections, relations."""
    import frontmatter

    with tempfile.TemporaryDirectory() as tmp:
        # First import
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))
        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        # Export
        export_dir = Path(tmp) / "exported"
        export_dir.mkdir()
        shutil.copytree(str(project_path), str(export_dir / "proj"))
        export_path = export_dir / "proj"
        for f in export_path.rglob("*.md"):
            f.unlink()
        export_handler({"project": str(export_path), "root_path": str(export_dir)})

        # Re-import from the exported files
        reimport_path = Path(tmp) / "reimported"
        reimport_path.mkdir()
        shutil.copytree(str(export_path), str(reimport_path / "save-the-children"))
        reimport_proj = reimport_path / "save-the-children"

        # Delete the story.db so we start fresh
        db_path = reimport_proj / ".story" / "story.db"
        if db_path.exists():
            db_path.unlink()

        import_handler({"project": str(reimport_proj), "root_path": str(reimport_path)})

        # Compare DB state (project id will differ since it's the folder name)
        from core.db import get_db
        conn1 = get_db(project_path)
        conn2 = get_db(reimport_proj)

        entities1 = set(conn1.execute("SELECT type FROM entities").fetchall())
        entities2 = set(conn2.execute("SELECT type FROM entities").fetchall())
        assert entities1 == entities2

        sections1 = set(conn1.execute("SELECT heading FROM sections").fetchall())
        sections2 = set(conn2.execute("SELECT heading FROM sections").fetchall())
        assert sections1 == sections2

        relations1 = set(conn1.execute("SELECT kind FROM relations").fetchall())
        relations2 = set(conn2.execute("SELECT kind FROM relations").fetchall())
        assert relations1 == relations2

        # Verify key entities exist
        kael = conn2.execute("SELECT id, type FROM entities WHERE id='kael'").fetchone()
        assert kael is not None

        conn1.close()
        conn2.close()


def test_round_trip_kael_note(fixture_path):
    """Kael's note: compare parsed frontmatter + body sections."""
    import frontmatter

    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        # Import
        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        # Export
        export_dir = Path(tmp) / "exported"
        export_dir.mkdir()
        shutil.copytree(str(project_path), str(export_dir / "proj"))
        export_path = export_dir / "proj"
        for f in export_path.rglob("*.md"):
            f.unlink()
        export_handler({"project": str(export_path), "root_path": str(export_dir)})

        orig = frontmatter.load(project_path / "characters" / "kael.md")
        exported = frontmatter.load(export_path / "characters" / "kael.md")

        # Compare frontmatter keys
        assert set(orig.metadata.keys()) == set(exported.metadata.keys())

        # Compare frontmatter values (as strings for simplicity)
        for key in orig.metadata:
            assert str(orig.metadata[key]) == str(exported.metadata[key]), f"Mismatch on {key}"

        # Compare body sections — all original sections must survive round trip
        # (export may add canonical sections that were missing from the fixture)
        from core.section_parser import list_sections
        orig_headings = set(list_sections(orig.content))
        exp_headings = set(list_sections(exported.content))
        assert orig_headings.issubset(exp_headings), (
            f"Sections lost in round trip: {orig_headings - exp_headings}"
        )


def test_fts5_populated_after_import(fixture_path):
    """FTS5 virtual table is populated and searchable."""
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        from core.db import get_db
        conn = get_db(project_path)

        # Search via FTS — join back to sections to get entity_id
        cursor = conn.execute(
            """SELECT s.entity_id FROM sections_fts f
               JOIN sections s ON f.rowid = s.rowid
               WHERE f.body MATCH ?""",
            ("Marcus",)
        )
        results = cursor.fetchall()
        assert len(results) > 0

        conn.close()


def test_recycle_bin_not_imported(fixture_path):
    """Recycle bin entities are NOT imported (hard delete means they're gone)."""
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        from core.db import get_db
        conn = get_db(project_path)

        soren = conn.execute("SELECT id FROM entities WHERE id=?", ("soren",)).fetchone()
        assert soren is None

        conn.close()


def test_world_fields_round_trip(fixture_path):
    """World with new fields (period, values, power, rules) survives import→export."""
    import frontmatter

    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        export_dir = Path(tmp) / "exported"
        export_dir.mkdir()
        shutil.copytree(str(project_path), str(export_dir / "proj"))
        export_path = export_dir / "proj"
        for f in export_path.rglob("*.md"):
            f.unlink()
        export_handler({"project": str(export_path), "root_path": str(export_dir)})

        orig = frontmatter.load(project_path / "worlds" / "the-i.md")
        exported = frontmatter.load(export_path / "worlds" / "the-i.md")

        # FM keys match
        assert set(orig.metadata.keys()) == set(exported.metadata.keys())
        # Specific new fields preserved
        assert exported.metadata["period"] == "+400y after the collapse"
        assert isinstance(exported.metadata["values"], list)
        assert len(exported.metadata["values"]) == 2
        assert isinstance(exported.metadata["power"], list)
        assert len(exported.metadata["power"]) == 2


def test_location_world_and_variant_fields_round_trip(fixture_path):
    """Location with world, mood, dramatic_function, variant_of survives import→export."""
    import frontmatter

    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        export_dir = Path(tmp) / "exported"
        export_dir.mkdir()
        shutil.copytree(str(project_path), str(export_dir / "proj"))
        export_path = export_dir / "proj"
        for f in export_path.rglob("*.md"):
            f.unlink()
        export_handler({"project": str(export_path), "root_path": str(export_dir)})

        orig = frontmatter.load(project_path / "locations" / "the-central-room.md")
        exported = frontmatter.load(export_path / "locations" / "the-central-room.md")

        # FM keys match
        assert set(orig.metadata.keys()) == set(exported.metadata.keys())
        # World field preserved
        assert exported.metadata["world"] == "the-i"
        # New fields preserved
        assert exported.metadata["mood"] == "oppressive stillness"
        assert exported.metadata["dramatic_function"] == "where the children's hope is tested"


def test_relationship_round_trip(fixture_path):
    """Relationship entities survive import → export → re-import."""
    import frontmatter

    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        # Export
        export_dir = Path(tmp) / "exported"
        export_dir.mkdir()
        shutil.copytree(str(project_path), str(export_dir / "proj"))
        export_path = export_dir / "proj"
        for f in export_path.rglob("*.md"):
            f.unlink()
        export_handler({"project": str(export_path), "root_path": str(export_dir)})

        # Verify relationships/ folder has files
        rel_dir = export_path / "relationships"
        assert rel_dir.is_dir()
        rel_files = list(rel_dir.glob("*.md"))
        assert len(rel_files) >= 3

        # Re-import from exported files
        reimport_path = Path(tmp) / "reimported"
        reimport_path.mkdir()
        shutil.copytree(str(export_path), str(reimport_path / "save-the-children"))
        reimport_proj = reimport_path / "save-the-children"

        # Delete the story.db so we start fresh
        db_path = reimport_proj / ".story" / "story.db"
        if db_path.exists():
            db_path.unlink()

        import_handler({"project": str(reimport_proj), "root_path": str(reimport_path)})

        # Verify relationship entities in DB
        from core.db import get_db
        conn = get_db(reimport_proj)
        rel_count = conn.execute(
            "SELECT count(*) FROM entities WHERE type='relationship'"
        ).fetchone()[0]
        assert rel_count >= 3
        conn.close()


def test_world_variant_of_round_trip(fixture_path):
    """World with variant_of creates a relation row that exports back to FM."""
    import frontmatter

    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        # Verify relation row was created
        from core.db import get_db
        conn = get_db(project_path)
        rel = conn.execute(
            "SELECT to_id FROM relations WHERE from_id='the-real-world' AND kind='world_variant'"
        ).fetchone()
        assert rel is not None
        assert rel[0] == "the-i"
        conn.close()

        # Export and verify variant_of appears in FM
        export_dir = Path(tmp) / "exported"
        export_dir.mkdir()
        shutil.copytree(str(project_path), str(export_dir / "proj"))
        export_path = export_dir / "proj"
        for f in export_path.rglob("*.md"):
            f.unlink()
        export_handler({"project": str(export_path), "root_path": str(export_dir)})

        exported = frontmatter.load(export_path / "worlds" / "the-real-world.md")
        assert exported.metadata["variant_of"] == "the-i"
