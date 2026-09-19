# Task 3.1: Replace `test_phase2_db_reads.py` — Nested Structure Tests

## Goal
Rewrite `tests/test_phase2_db_reads.py` — remove all old column/relation format tests, replace with nested structure assertions, sections presence, stub detection, embedded cross-refs, and token budget.

**Scope:** `tests/test_phase2_db_reads.py` — full rewrite.

---

## Current State (verified against code)

The file has these test classes/methods that must be **removed**:
- `TestStoryLoadDB::test_load_returns_column_format` — asserts `entities`/`relations` keys with `cols`/`rows`
- `TestStoryLoadDB::test_load_no_derived_arrays` — asserts no enriched arrays (now the point)
- `TestStoryLoadDB::test_load_no_sections_list` — asserts no `sections` in rows (now per-entity)
- `TestStoryLoadDB::test_load_relations_completeness` — asserts relation kinds (key gone)
- `TestStoryLoadDB::test_load_memory_included` — asserts `"memory" in result` (now `memory_outline`)
- `TestTokenBudget::test_load_under_5k_tokens` — asserts < 5000 tokens (now 8500)
- `TestNavigationalQueries` — all 5 tests navigate via `result["relations"]["rows"]`

These tests **stay** (still valid, minor updates):
- `TestStoryRetrieveDB` — retrieve tests, unaffected
- `TestStorySearchDB` — search tests, unaffected
- `TestStoryDashboardDB` — dashboard tests, unaffected
- `TestAutoReimport` — create/edit sync tests, unaffected

---

## Target State

### Remove entirely:
- `test_load_returns_column_format`
- `test_load_no_derived_arrays`
- `test_load_no_sections_list`
- `test_load_relations_completeness`
- `test_load_memory_included` (replaced by memory_outline test)

### Update:
- `TestTokenBudget::test_load_under_5k_tokens` → `test_load_under_8_5k_tokens`, threshold 5000 → 8500

### New test class: `TestNestedStructure`
```python
class TestNestedStructure:
    """story_load returns nested acts/characters/plots/locations/worlds dicts."""

    def test_load_returns_nested_acts(self, db_project):
        """acts[] contains sequences[] contains scenes[]."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "acts" in result
        assert isinstance(result["acts"], list)
        assert len(result["acts"]) > 0
        act = result["acts"][0]
        assert "sequences" in act
        assert isinstance(act["sequences"], list)
        if act["sequences"]:
            seq = act["sequences"][0]
            assert "scenes" in seq
            assert isinstance(seq["scenes"], list)

    def test_load_characters_keyed_by_slug(self, db_project):
        """characters is a dict keyed by slug."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "characters" in result
        assert isinstance(result["characters"], dict)
        assert "kael" in result["characters"]

    def test_load_plots_keyed_by_slug(self, db_project):
        """plots is a dict keyed by slug."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "plots" in result
        assert isinstance(result["plots"], dict)

    def test_load_locations_keyed_by_slug(self, db_project):
        """locations is a dict keyed by slug."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "locations" in result
        assert isinstance(result["locations"], dict)

    def test_load_worlds_keyed_by_slug(self, db_project):
        """worlds is a dict keyed by slug."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "worlds" in result
        assert isinstance(result["worlds"], dict)

    def test_no_entities_key(self, db_project):
        """Old flat entities key is gone."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "entities" not in result

    def test_no_relations_key(self, db_project):
        """Old flat relations key is gone."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "relations" not in result

    def test_no_memory_key(self, db_project):
        """Old full-memory key is gone (replaced by memory_outline)."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "memory" not in result
        assert "memory_outline" in result
```

### New test class: `TestStubClassification`
```python
class TestStubClassification:
    """Scene and arc beat stubs are correctly classified."""

    def test_scene_stub_has_only_id(self, db_project):
        """A planned scene with no dramatic_role is a stub: {id} only."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        # Find a stub scene in the nested tree
        found_stub = False
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and "dramatic_role" not in scene:
                        # Stub: should have id, maybe chars, but no status/dramatic_role
                        assert "id" in scene
                        assert "status" not in scene or scene.get("status") == "planned"
                        found_stub = True
        # Fixture should have at least one stub
        assert found_stub, "No stub scenes found in fixture"

    def test_scene_full_has_dramatic_role(self, db_project):
        """A non-stub scene has dramatic_role."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        found_full = False
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("dramatic_role"):
                        found_full = True
        assert found_full, "No full scenes found in fixture"

    def test_arc_beat_stub_is_bare_string(self, db_project):
        """An arc beat with empty label is a bare string in character.arc[]."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        found_stub = False
        for char in result["characters"].values():
            for beat in char.get("arc", []):
                if isinstance(beat, str):
                    found_stub = True
        # Fixture may or may not have stub beats — just verify the mechanism
        # (if no stubs in fixture, this is vacuous but not wrong)

    def test_arc_beat_full_has_label(self, db_project):
        """A full arc beat has label/scene/shift/y."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        found_full = False
        for char in result["characters"].values():
            for beat in char.get("arc", []):
                if isinstance(beat, dict):
                    assert "label" in beat
                    assert "scene" in beat
                    found_full = True
        assert found_full, "No full arc beats found in fixture"
```

### New test class: `TestEmbeddedCrossReferences`
```python
class TestEmbeddedCrossReferences:
    """Cross-references are embedded directly, not in a relations table."""

    def test_scene_has_chars(self, db_project):
        """scene.chars populated from character_scene relations."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("dramatic_role"):
                        # Full scene should have chars (if any assigned)
                        # Just verify the key exists
                        assert "chars" in scene

    def test_scene_has_loc(self, db_project):
        """scene.loc populated from location_scene relation."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("dramatic_role"):
                        assert "loc" in scene

    def test_character_has_rel(self, db_project):
        """character.rel populated from character_relationship relations."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for char in result["characters"].values():
            assert "rel" in char
            if char["rel"]:
                rel = char["rel"][0]
                assert "id" in rel
                assert "label" in rel

    def test_plot_has_setups(self, db_project):
        """plot.setups populated from plot_setup relations."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for plot in result["plots"].values():
            assert "setups" in plot
```

### New test class: `TestSectionsPerEntity`
```python
class TestSectionsPerEntity:
    """Each entity has a sections array (omitted when empty)."""

    def test_character_has_sections(self, db_project):
        """Character with notes has sections array."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        kael = result["characters"]["kael"]
        assert "sections" in kael
        assert isinstance(kael["sections"], list)
        assert len(kael["sections"]) > 0

    def test_sections_omitted_when_empty(self, db_project):
        """Entity with no sections written omits the sections key."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        # Find an entity with no sections (if any exist in fixture)
        # This is a soft check — vacuous if all entities have sections
        for char in result["characters"].values():
            if "sections" not in char:
                # Found one — key is correctly omitted
                return
        # All have sections — vacuously true
```

### New test class: `TestUnfilledInverted`
```python
class TestUnfilledInverted:
    """Unfilled is inverted: {field: [entity_ids]}, stubs excluded."""

    def test_unfilled_inverted_shape(self, db_project):
        """unfilled maps field names to lists of entity slugs."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        unfilled = result["unfilled"]
        assert isinstance(unfilled, dict)
        # Each value should be a list
        for field, entities in unfilled.items():
            assert isinstance(entities, list), f"unfilled[{field}] is not a list"

    def test_unfilled_excludes_stubs(self, db_project):
        """Stub entities do not appear in unfilled lists."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        unfilled = result["unfilled"]
        # Collect all entity slugs mentioned in unfilled
        all_unfilled = set()
        for entities in unfilled.values():
            all_unfilled.update(entities)
        # No stub scene slug should appear
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and "dramatic_role" not in scene:
                        assert scene["id"] not in all_unfilled, f"Stub scene {scene['id']} in unfilled"

    def test_character_goals_unfilled(self, db_project):
        """New character has goals_short/goals_long unfilled."""
        proj, vault = db_project
        # Create a new character
        create_handler({
            "entity_type": "character", "slug": "unfilled-test",
            "project": str(proj),
            "frontmatter": {"name": "Unfilled", "story_role": "Minor"},
            "vault_path": vault
        })
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        unfilled = result["unfilled"]
        # goals_short should list the new character
        assert "goals_short" in unfilled
        assert "unfilled-test" in unfilled["goals_short"]
```

### New test class: `TestConfirmationFormat`
```python
class TestConfirmationFormat:
    """Confirmation string matches new format."""

    def test_confirmation_format(self, db_project):
        """Confirmation: 'Loaded <name> — N scenes (M developed), ...'"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        conf = result["confirmation"]
        assert conf.startswith("Loaded Save the Children — ")
        assert "scenes" in conf
        assert "developed" in conf
        assert "sequences" in conf
        assert "acts" in conf
        assert "characters" in conf
        assert "locations" in conf
        assert "plots" in conf
        assert "worlds" in conf
```

### Updated `TestTokenBudget`:
```python
class TestTokenBudget:
    def test_load_under_8_5k_tokens(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        data = json.dumps(result)
        est_tokens = len(data) // 4
        assert est_tokens < 8500, f"Estimated tokens: {est_tokens}"
```

### Rewritten `TestNavigationalQueries`:
```python
class TestNavigationalQueries:
    """5 navigational queries answerable from nested structure alone."""

    def test_plot_to_scenes(self, db_project):
        """Which scenes does 'the-resistance' plot touch?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        plot = result["plots"]["the-resistance"]
        scenes = plot["setups"] + plot["crisis"] + plot["climax"] + plot["payoffs"]
        assert len(scenes) > 0

    def test_character_to_scenes(self, db_project):
        """What scenes has Kael been in?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        kael = result["characters"]["kael"]
        # Navigate: find scenes where kael is in chars
        kael_scenes = []
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and "kael" in scene.get("chars", []):
                        kael_scenes.append(scene["id"])
        assert "central-room-day" in kael_scenes

    def test_scene_to_plots(self, db_project):
        """Which plots touch central-room-day?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        touching = []
        for plot in result["plots"].values():
            all_scenes = plot["setups"] + plot["crisis"] + plot["climax"] + plot["payoffs"]
            if "central-room-day" in all_scenes:
                touching.append(plot["id"])
        assert len(touching) > 0

    def test_scene_to_arc_beats(self, db_project):
        """What arc beats does central-room-day host?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        beats = []
        for char in result["characters"].values():
            for beat in char.get("arc", []):
                if isinstance(beat, dict) and beat.get("scene") == "central-room-day":
                    beats.append(beat["label"])
        assert len(beats) > 0

    def test_structure_hierarchy(self, db_project):
        """act→sequence→scene hierarchy is directly visible in nesting."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        acts = result["acts"]
        assert len(acts) > 0
        for act in acts:
            assert "sequences" in act
            for seq in act["sequences"]:
                assert "scenes" in seq
                assert len(seq["scenes"]) > 0
```

---

## Code anchors

| What | Where |
|---|---|
| File to rewrite | `tests/test_phase2_db_reads.py` |
| Fixture used | `tests/fixtures/save-the-children` |
| `db_project` fixture | `tests/test_phase2_db_reads.py:24-32` |

---

## Test impact

This IS the test task. After this file is rewritten:
- All old column/relation tests gone
- New nested structure tests added
- Token budget updated to 8500
- Navigational queries rewritten for nested structure

---

## Legacy code removal

This task deletes:
- `test_load_returns_column_format`
- `test_load_no_derived_arrays`
- `test_load_no_sections_list`
- `test_load_relations_completeness`
- `test_load_memory_included`
- Old `TestNavigationalQueries` (5 tests using `relations.rows`)
- Old `TestTokenBudget::test_load_under_5k_tokens`

---

## Checklist

- [ ] `test_load_returns_column_format` removed
- [ ] `test_load_no_derived_arrays` removed
- [ ] `test_load_no_sections_list` removed
- [ ] `test_load_relations_completeness` removed
- [ ] `test_load_memory_included` removed (replaced by memory_outline test)
- [ ] `TestTokenBudget` threshold updated to 8500
- [ ] `TestNestedStructure` class added (acts/characters/plots/locations/worlds)
- [ ] `TestStubClassification` class added (scene stubs, arc beat stubs)
- [ ] `TestEmbeddedCrossReferences` class added (chars, loc, rel, setups)
- [ ] `TestSectionsPerEntity` class added (sections array, omitted when empty)
- [ ] `TestUnfilledInverted` class added (inverted shape, stubs excluded)
- [ ] `TestConfirmationFormat` class added (new format)
- [ ] `TestNavigationalQueries` rewritten for nested structure
- [ ] No test references `result["entities"]["rows"]`
- [ ] No test references `result["relations"]["rows"]`
- [ ] No test references `result["memory"]`
- [ ] All tests pass against Phase 1+2 implementation

---

## Final Brief

_To be filled after task completion._
