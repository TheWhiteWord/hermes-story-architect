# Task 15: Arc Coherence Analysis — Implementation Plan

> **Scope**: Validate that character arcs and structural arcs are coherent with each other using existing `y` beat data. Five numerical checks, visualization overlay, and sidebar alerts. No schema changes — pure aggregation over existing data.
> **Theory ground**: `skills/story-theory/references/values.md`, `tasks/OOS/arc_coherence_analysis.md` (specialist brief + responses)

---

## Architecture Decisions (Decided)

| Decision | Choice |
|----------|--------|
| Data source | Existing `y` values on arc beats — no schema changes |
| Check results | Computed at render time, not stored (recompute on dashboard open) |
| Character selection | Protagonist (full), Antagonist (inverted divergence), Supporting (light touch only) |
| Defer to v2 | Antagonist pressure gradient, midpoint check, positional weighting |
| Thresholds | Generous at first, tighten based on user feedback |
| Output framing | Questions, not verdicts ("appears to go against structural pressure — intentional?") |
| Graph decoupling | Render acts from `act_count` in `project.md`, not scene positions |
| Act skeleton | `act_count` declared in `project.md` — defaults to 3, auto-adjusts upward if more act files exist. Supports any positive integer (1-act short stories, 5-act epics, etc.) |

---

## Phase 1: Coherence Check Engine

### What changes

**`core/coherence.py`** — New module containing the five checks:

1. **Directional alignment per act**
   - Group protagonist beats by scene → act
   - Sum Δy within each act → net movement sign
   - Compare against act's `value_open → value_close` direction
   - Flag if net Δy sign opposes structural direction AND |net Δy| > 0.3

2. **Escalation check**
   - Compute peak |Δy| per act (largest single beat-to-beat jump)
   - Flag if Act 1 peak swing > 1.5× Act 3 peak swing

3. **Crisis/climax placement**
   - Find protagonist beat with `is_crisis: true` — verify it's not in Act 3's structural climax
   - Find protagonist beat with `is_climax: true` — verify it IS in Act 3
   - Binary flag, most reliable check

4. **Controlling idea sanity**
   - Protagonist `y_final` sign vs. `project.value_at_close` sign
   - Flag if opposite (logical contradiction)

5. **Antagonist divergence**
   - At structural climax scenes, compare protagonist and antagonist Δy
   - Flag if they move in same direction at climax (should diverge)

### Data access patterns

All checks read from the existing index:
- `index["arcs"]` → list of all beat files (parse frontmatter for `y`, `order`, `character`, `scene`)
- `index["characters"]` → character list with `arc_type`, `story_role`
- `index["scenes"]` → scene list with `act_id` field
- `index["acts"]` → act list from `acts/` folder with `value`, `value_open`, `value_close`
- `project.md` → `value_at_open`, `value_at_close`

### Helper functions

```python
def _beats_for_character(index, character_slug) -> list[dict]:
    """Filter arcs by character, sorted by order."""

def _beats_in_act(index, act_id) -> list[dict]:
    """Filter beats by scene.act_id membership."""

def _act_direction(act: dict) -> int:
    """Return +1, -1, or 0 for structural value direction."""

def _protagonist_id(index) -> str:
    """Find protagonist from character list (story_role == 'Protagonist')."""
```

### Tests to add

- `test_coherence.py` — Each check returns correct pass/false for known fixture
- `test_coherence.py` — Thresholds work (borderline cases)
- `test_coherence.py` — Empty/no-data case returns empty flag list
- `test_coherence.py` — Character filtering (P vs A vs supporting)

---

## Phase 2: Graph Decoupling

### Current problem

Act lines and scene positions are derived from scene positions on disk. Story is built over time — act files may exist but have no scenes/beats yet. The graph currently draws act boundaries at the first scene of each act, so acts without scenes are invisible.

### Target

Render the structural skeleton from `project.md`'s `act_count` declaration, regardless of whether act/scene/beat files exist. Beats populate inside that skeleton as they're created.

### Act skeleton declaration

Add `act_count` to `project.md` frontmatter:
- **Default:** 3 (imposed at project creation)
- **Auto-adjust:** If more act files exist than `act_count`, `act_count` auto-adjusts upward
- **Manual override:** Writer can change `act_count` anytime

### What changes

**`tools/story_dashboard.py`** — Refactor graph data pipeline:

1. **Act positions from `act_count`**
   - Read `project.md` frontmatter for `act_count`
   - Divide x-axis equally by `act_count` (0.0–0.33 Act 1, 0.33–0.66 Act 2, etc.)
   - Render act bands as background shading even when empty

2. **Scene positions within acts**
   - Scenes belong to acts via `act_id` frontmatter field
   - Position scenes proportionally within their act band

3. **Beat positions layered on top**
   - Beats use scene→act→position when scenes exist
   - Beats without scenes placed proportionally within their act

### Edge cases

- `act_count: 3`, no act files → 3 empty bands, "No act file yet" label per band
- `act_count: 3`, `acts/act-1.md` exists → Act 1 populated, Act 2-3 empty
- `act_count: 3`, 4 act files exist → `act_count` auto-adjusts to 4, 4 bands rendered

### Tests to add

- `test_coherence.py` — Graph renders all declared acts even with no scene files
- `test_coherence.py` — Graph renders beats only in populated acts when others empty
- `test_coherence.py` — Mixed state (Act 1 full, Act 2 declared but empty, Act 3 undeclared)

---

## Phase 3: Coherence Visualization

### What changes

**`tools/story_dashboard.py`** — Add coherence overlay to existing arc graph:

1. **Act band backgrounds** (from Phase 2)
   - Alternating light/dark shading per act
   - Act label at top of band

2. **Multi-character arc lines**
   - Protagonist: bold solid line (existing behavior)
   - Antagonist: dashed line in contrasting color
   - Supporting: thin low-opacity lines

3. **Crisis/climax markers on curve**
   - `is_crisis` beats: yellow diamond
   - `is_climax` beats: white circle with border

4. **Per-act delta bar** (new small chart below main graph)
   - One bar per act showing net Δy for protagonist
   - Height = magnitude, color = direction (green up, red down)
   - Makes escalation visible at a glance

5. **Sidebar alert list** (not inline on graph)
   - Short plain-language flags
   - Clicking an alert highlights the relevant act band/curve section
   - Example: "Act 1 net movement is larger than Act 3 — arc may peak too early"

### Reference files

| File | Why |
|------|-----|
| `tasks/task_14/arc-panel-demo.html` | Existing arc graph CSS/JS to extend |
| `tasks/task_14/arc-visualization-brief.md` | Original specialist brief for arc visualization |
| `src/dashboard/story-dashboard.html` | Existing dashboard tokens, sidebar structure |

### Tests to add

- `test_coherence.py` — Dashboard renders act bands
- `test_coherence.py` — Dashboard renders multi-character lines
- `test_coherence.py` — Crisis/climax markers appear at correct positions
- `test_coherence.py` — Delta bar renders correct magnitudes
- `test_coherence.py` — Sidebar alert list populated with flagged issues
- `test_coherence.py` — Clicking alert highlights relevant graph region

---

## Phase 4: Fixtures & Integration

### What changes

**`tests/fixtures/save-the-children/`** — Expand arc fixture:

1. Add antagonist arc beats (3-4 beats with divergent `y` values)
2. Add one supporting character arc (2 beats)
3. Ensure at least one deliberate coherence "problem" for test validation (e.g., escalation that peaks too early)
4. Update `project.md` with `value_at_open` and `value_at_close`

### New files

- `tests/fixtures/save-the-children/arcs/{antagonist-slug}/1.md` through `3.md`
- `tests/fixtures/save-the-children/arcs/{supporting-slug}/1.md` through `2.md`

### Tests to add

- `test_coherence.py` — Full integration: all 5 checks run on save-the-children fixture
- `test_coherence.py` — Deliberate problem in fixture is correctly flagged

---

## Phase 5: Documentation

### What changes

**`skills/story-loader/references/index-format.md`** — Document:
- Coherence check results format (what the dashboard reads)
- How to retrieve coherence report via `story_retrieve`

**`skills/story-editor/references/continuity-checks.md`** — Add:
- How coherence alerts work
- What to do when a flag fires (intentional vs. genuine problem)
- How to address common flags (escalation, placement, etc.)

**`skills/story-theory/SKILL.md`** — Link to values.md §5 and §8 for arc-structure relationship

---

## File Inventory

### Files to modify

| File | Phase | What |
|------|-------|------|
| `core/coherence.py` | 1 | New module with 5 checks |
| `tools/story_dashboard.py` | 2, 3 | Graph decoupling + coherence overlay + sidebar alerts |
| `src/dashboard/story-dashboard.html` | 3 | Extend arc graph CSS/JS |
| `tests/fixtures/save-the-children/...` | 4 | Add antagonist + supporting arcs + deliberate problem |
| `skills/story-loader/references/index-format.md` | 5 | Document coherence report format |
| `skills/story-editor/references/continuity-checks.md` | 5 | Add coherence check patterns |
| `skills/story-theory/SKILL.md` | 5 | Link to values.md |

### Files to create

| File | Phase | What |
|------|-------|------|
| `tests/test_coherence.py` | 1-4 | All coherence tests |
| `tests/fixtures/save-the-children/arcs/{antagonist}/1.md` | 4 | Antagonist beat fixture |
| `tests/fixtures/save-the-children/arcs/{antagonist}/2.md` | 4 | Antagonist beat fixture |
| `tests/fixtures/save-the-children/arcs/{antagonist}/3.md` | 4 | Antagonist beat fixture |
| `tests/fixtures/save-the-children/arcs/{supporting}/1.md` | 4 | Supporting beat fixture |
| `tests/fixtures/save-the-children/arcs/{supporting}/2.md` | 4 | Supporting beat fixture |

### Files already created (research phase)

| File | What |
|------|------|
| `skills/story-theory/references/values.md` | Theory reference for values |
| `docs/research/arc-visualization-example.html` | Graph mockup |
| `tasks/task_14/arc-panel-demo.html` | Working arc graph demo |
| `tasks/OOS/arc_coherence_analysis.md` | Specialist brief + responses |

---

## Test Coverage Requirements

| Test Area | Count | Key Cases |
|-----------|-------|-----------|
| Coherence engine (5 checks) | 5 | Each check pass/fail with known data |
| Thresholds | 4 | Borderline cases per check |
| Empty data | 1 | No beats → no flags |
| Character selection | 3 | P/A/Supporting filtering |
| Graph decoupling | 3 | Declared-only acts, mixed state |
| Visualization | 6 | Bands, lines, markers, delta bar, alerts, click |
| Integration | 2 | Full fixture, deliberate problem flagged |
| **Total** | **24** | |

---

## Risk & Verification Checklist

Before calling Phase N complete:

- [ ] Phase 1: `pytest tests/test_coherence.py -k "check"` passes
- [ ] Phase 2: `pytest tests/test_coherence.py -k "decoupling"` passes
- [ ] Phase 3: `pytest tests/test_coherence.py -k "dashboard"` passes
- [ ] Phase 4: Full integration tests pass with save-the-children fixture
- [ ] Phase 5: Skill docs updated, references cross-linked

---

## Open Questions for Task Creation

All resolved — see architecture decisions above.

| Question | Answer |
|----------|--------|
| Act declaration format | `act_count` in `project.md` frontmatter (default 3, auto-adjusts upward) |
| Scene→Act membership | `act_id` field on scene frontmatter |
| Protagonist identification | `story_role: "Protagonist"` on character frontmatter |
| Alert severity | One tier — all flags are questions, not verdicts |
| Threshold storage | Module-level constants in `coherence.py` |

---

## Estimated Task Breakdown

| Phase | Tasks | Est. Lines |
|-------|-------|------------|
| 1. Coherence Engine | 4 tasks | ~120 |
| 2. Graph Decoupling | 3 tasks | ~90 |
| 3. Visualization | 5 tasks | ~180 |
| 4. Fixtures & Integration | 2 tasks | ~50 |
| 5. Documentation | 2 tasks | ~30 |
| **Total** | **16 tasks** | **~470 lines** |

---

## Next Steps

1. ~~Review this plan with user for any gaps or changes~~
2. ~~Verify open questions against existing code~~ ✅
3. Break each phase into individual implementation tasks with full specs
4. Begin Phase 1 implementation
| **Total** | **16 tasks** | **~470 lines** |

---

## Next Steps

1. ~~Review this plan with user for any gaps or changes~~
2. ~~Verify open questions against existing code~~ ✅
3. Break each phase into individual implementation tasks with full specs
4. Begin Phase 1 implementation
