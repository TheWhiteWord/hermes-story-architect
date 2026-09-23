# Phase 9: Cleanup & Validation

## Goal

Final cleanup and validation. Run full test suite. Verify assembled HTML is structurally equivalent to the original monolith.

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — full baseline for comparison.

Use baseline to verify:
- All 103 static DOM IDs present in assembled HTML
- All 77 functions defined (as `DASH.foo = ...`)
- All 3 CDNs present
- Boot comment string intact
- All 21 CSS sections preserved
- All 13 `data-hermes-send` attributes preserved

## Verification Against Code

### Final Checklist

After all extractions are complete, verify:

### Placeholder Replacement
- [ ] No `<!-- CSS_PLACEHOLDER -->` survives assembly
- [ ] No `<!-- JS_PLACEHOLDER -->` survives assembly
- [ ] No `<!-- SCREENPLAY_CSS_PLACEHOLDER -->` survives assembly

### DOM Integrity
- [ ] All 112 DOM IDs present in assembled HTML
- [ ] All 12 `data-hermes-send` attributes present

### External Resources
- [ ] vis-network CDN present
- [ ] js-yaml CDN present
- [ ] D3 CDN present

### Script Integrity
- [ ] All 77 functions defined (converted to `DASH.foo = ...`)
- [ ] Boot comment (`// ─── Boot`) preserved for data injection
- [ ] `boot()` called at end of script

### CSS Integrity
- [ ] `.fountain-scene_heading` present (from screenplay.css)
- [ ] `.fountain-dialogue` present (from screenplay.css)
- [ ] All CSS variables (`:root`) preserved
- [ ] All 21 CSS sections preserved
- [ ] No standalone `.fountain-scene_heading` in dashboard CSS

### Behavioral Integrity
- [ ] `DASH.boot()` calls `initStory()` if `window.__STORY_DATA__` exists
- [ ] `DASH.switchView()` wrapper reassigns `DASH.switchView`
- [ ] `DASH.openStatsPanel()` calls `DASH.buildScriptView()` if `!DASH._scriptBuilt`
- [ ] `DASH.showScenePanel()` called on scene heading click in script view

### Dead Code Deleted
- [ ] `buildSequencesView` — DELETED
- [ ] `buildActsView` — DELETED

## Integration Tests

### Updated Tests

| Test | Source |
|------|--------|
| `test_script_view_exists` | `index.html` ✓ |
| `test_stats_panel_exists` | `index.html` ✓ |
| `test_stats_panel_width_defined` | assembled CSS ✓ |
| `test_script_nav_button_exists` | `index.html` ✓ |
| `test_stats_element_ids_present` | `index.html` ✓ |
| `test_build_script_view_function` | `js/script-view.js` |
| `test_open_stats_panel_function` | `js/statistics/statistics.js` |
| `test_d3_charts_functions` | `js/statistics/charts.js` |
| `test_sort_table_function` | `js/statistics/statistics.js` |
| `test_switch_view_wrapper` | `js/navigation.js` |
| `test_scene_click_matching` | `js/script-view.js` |
| `test_no_new_inline_fountain_css` | assembled CSS |
| `test_d3_cdn_loaded` | `index.html` ✓ |
| `test_fountain_parse_imported` | `tools/story_dashboard.py` (unchanged) |
| `test_screenplay_stats_computation` | `tools/story_dashboard.py` (unchanged) |
| `test_stats_injected_before_boot` | assembled HTML |
| `test_hsl_from_name_deterministic` | `tools/story_dashboard.py` (unchanged) |

### New Assembly Integrity Tests

```python
def test_assembled_dashboard_contains_no_placeholders(dashboard_html):
    assert "<!-- CSS_PLACEHOLDER -->" not in dashboard_html
    assert "<!-- JS_PLACEHOLDER -->" not in dashboard_html
    assert "<!-- SCREENPLAY_CSS_PLACEHOLDER -->" not in dashboard_html

def test_assembled_dashboard_contains_required_dom_ids(dashboard_html):
    required_ids = [...]
    for eid in required_ids:
        assert f'id="{eid}"' in dashboard_html

def test_assembled_dashboard_preserves_external_deps(dashboard_html):
    assert "vis-network.min.js" in dashboard_html
    assert "js-yaml.min.js" in dashboard_html
    assert "d3.min.js" in dashboard_html

def test_assembled_dashboard_preserves_data_injection_point(dashboard_html):
    assert "// ─── Boot" in dashboard_html

def test_assembled_dashboard_preserves_hermes_attributes(dashboard_html):
    assert "data-hermes-send" in dashboard_html

def test_assembled_dashboard_preserves_screenplay_css(dashboard_html):
    assert ".fountain-scene_heading" in dashboard_html
    assert ".fountain-dialogue" in dashboard_html
```

## Issues Found

None. All verifications are automated via tests.

## Dependencies

**Parallel:** None. Phase 9 depends on Phases 1-8 all being complete.

## Expected Output

After Phase 9:
- All tests pass
- Assembled HTML is structurally equivalent to original monolith
- Dashboard behaves identically
- All dead code removed

## Next Steps

After Phase 9: Refactor complete. Ready for user testing.
