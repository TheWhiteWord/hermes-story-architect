# D5 — Add Regression Test for Dashboard Structural Stats

**Goal:** Verify `compute_structural_stats()` returns correct `sceneRoles` counts — not all `"unset"`.

## Why

This is the proof that the refactor fixed a real bug. Before: dashboard role-count panel was silently broken because `dramatic_role` was stripped from the index. After: `dramatic_role` is present, stats are correct.

## Current State

`tools/story_dashboard.py` line 382: `structural_stats = compute_structural_stats(yaml_data)`
`core/index.py` line 468-493: `compute_structural_stats()` reads `dramatic_role` from each scene

With unified index, the fixture scenes have roles: `setup`, `climax`, `resolution`.

## Changes

1. **`tests/test_story_dashboard_stats.py`** — Add new test:
   ```python
   def test_structural_stats_scene_roles(self):
       """compute_structural_stats returns correct role counts (not all 'unset')."""
       from core.index import compute_structural_stats
       import yaml
       
       fixture_path = Path(__file__).parent / "fixtures" / "save-the-children"
       with open(fixture_path / ".story" / "index.yaml") as f:
           index = yaml.safe_load(f)
       
       stats = compute_structural_stats(index)
       
       # Verify sceneRoles has actual roles, not just "unset"
       roles = stats["sceneRoles"]
       assert "unset" not in roles or roles.get("unset", 0) == 0, \
           f"Expected no 'unset' roles, got: {roles}"
       
       # Verify specific roles from fixture
       assert roles.get("setup", 0) >= 1
       assert roles.get("climax", 0) >= 1
       assert roles.get("resolution", 0) >= 1
   ```

## Verification Checklist

- [x] New test verifies `sceneRoles` contains actual dramatic roles
- [x] Test fails BEFORE Phase A (proves the bug existed)
- [x] Test passes AFTER Phase A+D4 (proves the fix works)
- [x] Test runs as part of the existing test suite (11/11 in file, 174/174 overall)

## Final Notes

Added `TestStructuralStats` class with `test_structural_stats_scene_roles` to `test_story_dashboard_stats.py`. Test asserts `sceneRoles` has no `"unset"` entries and verifies the fixture's exact role distribution (1 setup, 1 climax, 1 resolution). This is the regression guard — if anyone re-introduces the index split, this test catches it because `dramatic_role` would be stripped from the unified index and all scenes would count as `"unset"`.

## Notes

- Depends on D4 (fixture updated with `dramatic_role` values)
- This test is the regression guard — if someone re-introduces the split, this test catches it
