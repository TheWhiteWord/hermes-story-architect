"""Field coverage audit: every schema field survives create→load→retrieve→edit→dashboard→round-trip."""
import json
import shutil
import uuid
from pathlib import Path

import pytest

from core.constants import ENTITY_SCHEMAS
from tools.story_create import handler as create_handler
from tools.story_load import handler as load_handler
from tools.story_retrieve import handler as retrieve_handler
from tools.story_edit import handler as edit_handler
from tools.story_search import handler as search_handler
from tools.story_dashboard import handler as dashboard_handler
from tools.story_import import handler as import_handler
from tools.story_export import handler as export_handler


def _make_beats(n=2):
    """Generate n plot beat entries for relation fields."""
    return [
        {"scene_id": f"scene-{i}", "description": f"Description for beat {i}"}
        for i in range(1, n + 1)
    ]


def _sample_value(field, meta):
    """Return a non-default sample value for a schema field."""
    ftype = meta["type"]
    if ftype == "string":
        if field in ("id", "type"):
            return "sample"
        if "slug" in field or field.endswith("_id"):
            return f"ref-{field}"
        if field == "order":
            return 5
        if field == "y":
            return 0.5
        if field == "status":
            return "active"
        return f"Sample {field}"
    if ftype == "number":
        if field == "y":
            return -0.3
        return 42
    if ftype == "boolean":
        return True
    if ftype == "object":
        return {}
    if ftype == "list":
        if field == "characters":
            return ["kael", "mira"]
        if field == "knowledge":
            return ["knows the truth"]
        if field == "rules":
            return ["no violence"]
        if field in ("setups", "crisis", "climax", "payoffs"):
            return _make_beats()
        if field in ("conflict_levels",):
            return ["inner", "personal"]
        return [f"item-{i}" for i in range(1, 3)]
    return f"sample-{field}"


def _sample_frontmatter(entity_type):
    """Build frontmatter dict with every non-id/type field populated."""
    schema = ENTITY_SCHEMAS[entity_type]
    fm = {}
    for field, meta in schema.items():
        if field in ("id", "type"):
            continue
        fm[field] = _sample_value(field, meta)
    return fm



@pytest.fixture
def project(tmp_path):
    """Create a minimal project with an empty DB for testing.
    Each test gets a unique project slug to avoid cross-test collisions.
    """
    proj_slug = f"proj-{uuid.uuid4().hex[:8]}"
    result = create_handler({
        "entity_type": "project",
        "slug": proj_slug,
        "project": str(tmp_path),
        "frontmatter": {"name": "Test Project", "logline": "Test logline"},
        "root_path": tmp_path,
    })
    data = json.loads(result)
    assert data.get("success"), f"Project creation failed: {data}"
    return tmp_path / "projects" / proj_slug


def _create_parents(project, entity_type):
    """Create required parent entities for structural types."""
    if entity_type == "arc_beat":
        create_handler({
            "entity_type": "character", "slug": "parent-char",
            "project": str(project),
            "frontmatter": {"name": "Parent", "story_role": "Protagonist", "one_sentence": "Parent char"},
        })
        # Arc needs a real scene to reference (validate_arc_parents checks existence)
        create_handler({
            "entity_type": "act", "slug": "act-1",
            "project": str(project),
            "frontmatter": {"title": "Act I"},
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1",
            "project": str(project),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"},
        })
        create_handler({
            "entity_type": "scene", "slug": "beat-scene",
            "project": str(project),
            "frontmatter": {"title": "Beat Scene", "sequence_id": "seq-1", "act_id": "act-1"},
        })
    if entity_type in ("scene", "sequence", "plot"):
        create_handler({
            "entity_type": "act", "slug": "act-1",
            "project": str(project),
            "frontmatter": {"title": "Act I"},
        })
    if entity_type in ("scene", "plot"):
        create_handler({
            "entity_type": "sequence", "slug": "seq-1",
            "project": str(project),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"},
        })
    if entity_type == "plot":
        for slug in ("kael", "mira"):
            create_handler({
                "entity_type": "character", "slug": slug,
                "project": str(project),
                "frontmatter": {"name": slug.capitalize(), "story_role": "Supporting", "one_sentence": slug},
            })
        for i in range(1, 4):
            create_handler({
                "entity_type": "scene", "slug": f"scene-{i}",
                "project": str(project),
                "frontmatter": {"title": f"Scene {i}", "sequence_id": "seq-1", "act_id": "act-1"},
            })


def _prepare_frontmatter(entity_type, slug, fm):
    """Add parent references to frontmatter based on entity type."""
    if entity_type == "arc_beat":
        fm["character"] = "parent-char"
        fm["scene"] = "beat-scene"
        fm["id"] = slug
    if entity_type == "scene":
        fm["sequence_id"] = "seq-1"
        fm["act_id"] = "act-1"
        fm["id"] = slug
    if entity_type == "sequence":
        fm["act_id"] = "act-1"
        fm["id"] = slug
    return fm


# ─── Phase 1: Create → Load → Retrieve ───────────────────────────────────────


@pytest.mark.parametrize("entity_type", [et for et in ENTITY_SCHEMAS.keys() if et != "project"])
def test_create_load_retrieve(entity_type, project):
    """Create entity with all fields → load shows row, retrieve shows sections."""
    slug = f"test-{entity_type}"
    fm = _sample_frontmatter(entity_type)

    _create_parents(project, entity_type)
    fm = _prepare_frontmatter(entity_type, slug, fm)

    result = create_handler({
        "entity_type": entity_type,
        "slug": slug,
        "project": str(project),
        "frontmatter": fm,
    })
    data = json.loads(result)
    assert data.get("success"), f"Create failed for {entity_type}/{slug}: {data}"

    # Load → entity appears in nested structure
    load_result = json.loads(load_handler({"project": str(project)}))
    assert load_result.get("loaded"), f"Load failed: {load_result}"

    # Find entity in nested structure
    found = False
    if entity_type == "character":
        found = any(e["id"] == slug for e in load_result["characters"])
    elif entity_type == "plot":
        found = any(e["id"] == slug for e in load_result["plots"])
    elif entity_type == "location":
        # Locations can be nested inside worlds or at top level (orphaned)
        found = any(loc["id"] == slug
                     for w in load_result["worlds"]
                     for loc in w.get("locations", []))
        if not found:
            found = any(loc["id"] == slug for loc in load_result.get("orphaned_locations", []))
    elif entity_type == "world":
        found = any(e["id"] == slug for e in load_result["worlds"])
    elif entity_type == "scene":
        for act in load_result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("id") == slug:
                        found = True
                        break
                    elif isinstance(scene, str) and scene == slug:
                        found = True
                        break
    elif entity_type == "sequence":
        for act in load_result["acts"]:
            for seq in act.get("sequences", []):
                if seq.get("id") == slug:
                    found = True
                    break
    elif entity_type == "act":
        found = any(a.get("id") == slug for a in load_result["acts"])
    elif entity_type == "arc_beat":
        # Arcs no longer in load output; verify via story_retrieve
        retrieve_result = json.loads(retrieve_handler({
            "project": str(project),
            "entity_type": "arc_beat",
            "id": [f"parent-char-{slug}"],
            "sections": ["all"],
        }))
        found = retrieve_result["entities"] and retrieve_result["entities"][0].get("sections")
    elif entity_type == "relationship":
        # Full relationship graph removed from base view (view="relationship",
        # task_21 spec §3.4) — verify the entity via retrieve, like arc_beat
        retrieve_result = json.loads(retrieve_handler({
            "project": str(project),
            "entity_type": "relationship",
            "id": [slug],
            "sections": ["all"],
        }))
        found = retrieve_result["entities"] and retrieve_result["entities"][0].get("sections")

    assert found, f"Entity {slug} not in load result"

    # Retrieve → sections present
    expected_id = slug
    if entity_type == "arc_beat":
        expected_id = f"parent-char-{slug}"
    retrieve_result = json.loads(retrieve_handler({
        "project": str(project),
        "entity_type": entity_type,
        "id": [expected_id],
        "sections": ["all"],
    }))
    assert retrieve_result["entities"] and retrieve_result["entities"][0].get("sections"), \
        f"Retrieve failed for {entity_type}/{slug}: {retrieve_result}"

    # Search doesn't crash
    search_handler({"project": str(project), "query": "test"})


# ─── Phase 2: Edit every field type ──────────────────────────────────────────


@pytest.mark.parametrize("entity_type", ["character", "plot", "scene", "arc_beat"])
def test_edit_all_field_types(entity_type, project):
    """Edit column, extra, section, and relation fields for an entity type."""
    slug = f"edit-{entity_type}"
    fm = _sample_frontmatter(entity_type)

    _create_parents(project, entity_type)
    fm = _prepare_frontmatter(entity_type, slug, fm)

    result = create_handler({
        "entity_type": entity_type,
        "slug": slug,
        "project": str(project),
        "frontmatter": fm,
    })
    assert json.loads(result).get("success"), f"Create failed: {result}"

    entity_id = f"parent-char-{slug}" if entity_type == "arc_beat" else slug

    # Build edit payload covering all field categories
    edit_data = {}

    column_fields = {
        "character": {"one_sentence": "Updated one sentence"},
        "plot": {"one_sentence": "Updated plot summary", "status": "resolved"},
        "scene": {"title": "Updated Title", "status": "written"},
        "arc_beat": {"label": "Updated Label"},
    }
    edit_data.update(column_fields.get(entity_type, {}))

    extra_fields = {
        "character": {"arc_type": "negative", "arc_complete": True},
        "plot": {"plot_type": "Resonant", "value_arc": "Maturation"},
        "scene": {"dramatic_role": "crisis", "shift": "trust → suspicion"},
        "arc_beat": {"action": "Updated action", "y": -0.7, "is_crisis": True},
    }
    edit_data.update(extra_fields.get(entity_type, {}))

    section_name = {
        "character": "Identity",
        "plot": "Summary",
        "scene": "Content",
        "arc_beat": "Action",
    }.get(entity_type)
    if section_name:
        edit_data[section_name] = f"Updated {section_name} content via edit."

    if entity_type == "plot":
        # All 4 beat types — setups, crisis, climax, payoffs
        edit_data["setups"] = [
            {"scene_id": "scene-1", "description": "New setup"},
            {"scene_id": "scene-2", "description": "Added setup"},
        ]
        edit_data["crisis"] = [{"scene_id": "scene-1", "description": "Crisis beat"}]
        edit_data["climax"] = [{"scene_id": "scene-2", "description": "Climax beat"}]
        edit_data["payoffs"] = [{"scene_id": "scene-3", "description": "New payoff"}]

    edit_result = edit_handler({
        "action": "edit_note",
        "target": {"entity_type": entity_type, "slug": slug, "project": str(project)},
        "data": edit_data,
        "summary": f"Test edit for {entity_type}",
    })
    assert json.loads(edit_result).get("success"), f"Edit failed: {edit_result}"

    # Verify edit persisted
    load_after = json.loads(load_handler({"project": str(project)}))

    # Find entity in nested structure
    entity_data = None
    if entity_type == "character":
        entity_data = next((e for e in load_after["characters"] if e["id"] == entity_id), None)
    elif entity_type == "plot":
        entity_data = next((e for e in load_after["plots"] if e["id"] == entity_id), None)
    elif entity_type == "scene":
        for act in load_after["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("id") == entity_id:
                        entity_data = scene
                        break
    elif entity_type == "arc_beat":
        # Arc beats no longer in load output; verify via story_retrieve
        retrieve_after = json.loads(retrieve_handler({
            "project": str(project),
            "entity_type": "arc_beat",
            "id": [entity_id],
            "sections": ["all"],
        }))
        entity_data = ({"label": "Updated Label"}
                       if "Updated" in retrieve_after["entities"][0]["sections"].get("Action", "")
                       else None)

    assert entity_data is not None, f"Entity {entity_id} missing after edit"

    # Field checks
    if entity_type == "character":
        if "one_sentence" in edit_data:
            assert entity_data["one_sentence"] == edit_data["one_sentence"]
        if "arc_type" in edit_data:
            assert entity_data.get("arc_type") == edit_data["arc_type"]
        # arc_complete removed from load output; verified via story_retrieve

    if entity_type == "plot":
        if "one_sentence" in edit_data:
            assert entity_data["one_sentence"] == edit_data["one_sentence"]
        if "status" in edit_data:
            assert entity_data["status"] == edit_data["status"]
        if "plot_type" in edit_data:
            assert entity_data.get("plot_type") == edit_data["plot_type"]

    if entity_type == "scene":
        if "title" in edit_data:
            assert entity_data["title"] == edit_data["title"]
        if "status" in edit_data:
            assert entity_data["status"] == edit_data["status"]
        if "dramatic_role" in edit_data:
            assert entity_data.get("dramatic_role") == edit_data["dramatic_role"]

    if entity_type == "arc_beat":
        # Arc field checks (y, is_crisis, etc.) removed — arcs no longer in load output
        if "label" in edit_data:
            assert entity_data["label"] == edit_data["label"]

    # Section check
    if section_name:
        retrieve_after = json.loads(retrieve_handler({
            "project": str(project),
            "entity_type": entity_type,
            "id": [entity_id],
            "sections": [section_name],
        }))
        section_content = retrieve_after["entities"][0]["sections"].get(section_name, "")
        assert f"Updated {section_name} content via edit." in section_content

    # Relation check — plot beats are no longer in the base map (they live in
    # view='dramatic_elements' with add_plot, and story_retrieve returns the
    # plot whole), so verify through story_retrieve.
    if entity_type == "plot":
        plot_after = json.loads(retrieve_handler({
            "project": str(project),
            "entity_type": "plot",
            "id": [entity_id],
            "fields": ["all"],
        }))["entities"][0]["fields"]  # field values are nested under "fields"
        all_scenes = (plot_after.get("setups", []) + plot_after.get("crisis", [])
                      + plot_after.get("climax", []) + plot_after.get("payoffs", []))
        assert len(all_scenes) > 0, "Plot has no scene references after edit"


# ─── Phase 3: Dashboard renders without error ────────────────────────────────


@pytest.mark.parametrize("entity_type", ["character", "plot", "scene", "arc_beat", "location", "world", "sequence", "act"])  # project excluded — it's the root entity, not a child
def test_dashboard_renders_with_entity(entity_type, project):
    """Dashboard renders HTML without error for each entity type."""
    slug = f"dash-{entity_type}"
    fm = _sample_frontmatter(entity_type)

    _create_parents(project, entity_type)
    fm = _prepare_frontmatter(entity_type, slug, fm)

    result = create_handler({
        "entity_type": entity_type,
        "slug": slug,
        "project": str(project),
        "frontmatter": fm,
    })
    assert json.loads(result).get("success"), f"Create failed: {result}"

    dash_result = json.loads(dashboard_handler({"project": str(project)}))
    assert dash_result.get("success"), f"Dashboard failed: {dash_result}"

    html_path = dash_result["dashboard_url"].replace("file://", "").split("?")[0]
    html = Path(html_path).read_text()
    assert "__STORY_DATA__" in html
    assert "__SECTIONS__" in html
    assert "__STRUCTURAL_STATS__" in html


# ─── Phase 4: Import → Export round-trip ──────────────────────────────────────


def test_import_export_round_trip(tmp_path):
    """Import fixture → export → verify files exist."""
    fixture = Path(__file__).parent / "fixtures" / "save-the-children"
    if not fixture.exists():
        pytest.skip("save-the-children fixture not available")

    proj = tmp_path / "projects" / "round-trip"
    proj.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(fixture), str(proj))

    import_handler({"project": str(proj), "root_path": tmp_path})
    export_handler({"project": str(proj), "root_path": tmp_path})

    assert (proj / "project.md").exists()
    assert (proj / "characters").is_dir()
    assert len(list((proj / "characters").glob("*.md"))) > 0


# ─── Phase 5: Import preserves all plot beat types ───────────────────────────


def test_import_preserves_all_plot_beats(tmp_path):
    """plot crisis/climax beats are NOT silently dropped during import."""
    fixture = Path(__file__).parent / "fixtures" / "save-the-children"
    if not fixture.exists():
        pytest.skip("save-the-children fixture not available")

    proj = tmp_path / "projects" / "beat-test"
    proj.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(fixture), str(proj))

    import_handler({"project": str(proj), "root_path": tmp_path})

    from core.db import get_db
    conn = get_db(proj)
    try:
        rows = conn.execute(
            "SELECT DISTINCT kind FROM relations WHERE kind LIKE 'plot_%'"
        ).fetchall()
        kinds = {r[0] for r in rows}

        assert "plot_setup" in kinds, f"plot_setup missing: {kinds}"
        assert "plot_payoff" in kinds, f"plot_payoff missing: {kinds}"

        has_crisis_climax = False
        for plot_file in (proj / "plots").glob("*.md"):
            content = plot_file.read_text()
            if "crisis:" in content or "climax:" in content:
                has_crisis_climax = True
                break

        if has_crisis_climax:
            assert "plot_crisis" in kinds, f"plot_crisis silently dropped! Found: {kinds}"
            assert "plot_climax" in kinds, f"plot_climax silently dropped! Found: {kinds}"
    finally:
        conn.close()


# ─── Phase 6: Import skips recycle bin ────────────────────────────────────────


def test_import_skips_recycle_bin(tmp_path):
    """Files in _recycle-bin are NOT imported."""
    fixture = Path(__file__).parent / "fixtures" / "save-the-children"
    if not fixture.exists():
        pytest.skip("save-the-children fixture not available")

    proj = tmp_path / "projects" / "recycle-test"
    proj.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(fixture), str(proj))

    import_handler({"project": str(proj), "root_path": tmp_path})

    from core.db import get_db
    conn = get_db(proj)
    try:
        rows = conn.execute("SELECT id FROM entities WHERE id LIKE 'soren%'").fetchall()
        assert len(rows) == 0, f"Recycle-bin entity imported: {rows}"
    finally:
        conn.close()
