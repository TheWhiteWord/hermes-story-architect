# Structural Arc Visualization — Design Plan

> **Scope**: Replace the existing Phase 3 structural avenue (standalone charge-based band) with a derived structural arc computed from character beat data. The arc shows the *actual* thematic state of the story as expressed by character arcs, not the *intended* trajectory from act charge values.
>
> **Theory ground**: McKee's value theory — the structural value is the thematic investigation of the story. Character arcs are sub-thematic investigations that aggregate to express the structural value. The audience experiences the structure through the characters, not through an independent charge line.
>
> **Reference mockups**: `tasks/task-15/structural-avenue-band.html`, `tasks/task-15/structural-avenue-with-antagonist.html`

---

## Design Intentions

### The Problem with the Old Design

The existing Phase 3 renders the structural arc as a standalone band derived from `act.value_open` → `act.value_close`. This has two issues:

1. **It's a straight line (or flat band)** — two points define a line, not a journey. Real stories have ups and downs.
2. **It competes with character arcs** — the structural arc should *emerge from* character arcs, not exist alongside them as an independent element.

### The New Design

The structural arc is **derived from character beats** — a weighted average of all character `y` values at each scene position. This produces a curve that:

- Follows the same visual grammar as character arcs (polyline, not flat band)
- Has natural amplitude (most stories hover in ±0.3–0.5, not ±1.0)
- Shows the *actual* thematic state of the story (reality), not the *intended* trajectory (expectation)
- Gets smoother and narrower as more characters contribute (more averaging = less variance)

### Key Distinctions

| Concept | Old Design | New Design |
|---------|-----------|------------|
| **Structural arc source** | `act.value_open` → `act.value_close` | Weighted average of character beat `y` values |
| **Visual treatment** | Flat band (rect) | Curved polyline (like character arcs) |
| **Amplitude** | Full ±1.0 (charge mapping) | Natural ±0.3–0.5 (from actual beat data) |
| **Relationship to characters** | Independent | Derived from characters |
| **Intention vs. reality** | Only intention shown | Both: dashed line = intention, solid band = reality |
| **Coherence warnings** | Compare character to charge line | Compare character to derived arc band |

### The Avenue (Acceptable Range)

The structural arc is rendered as a **soft band** (the "avenue"), not a thin line:

- **Band height = acceptable drift margin** (e.g., ±0.12 around the derived arc)
- **Characters inside the band = within acceptable range** (no warning)
- **Characters outside the band = potential coherence issue** (warning fires)
- **The band is not a visual effect** — it *is* the range of acceptable values

This reflects the reality of storytelling: there's no single "correct" value at any point, but rather a range of values that still serve the thematic intention.

### Intention vs. Reality

The dashboard shows both:

- **Dashed faint line** = intended trajectory (from `act.value_open` → `act.value_close`)
- **Solid soft band** = derived structural arc (reality from character beats)

The gap between them is the **storytelling problem** — the writer can see exactly where the story drifts from the intention and adjust character arcs accordingly.

---

## Architecture

### Data Flow

```
Character beats (y values, scene, order)
    ↓
Weighted average per scene position
    ↓
Derived structural arc (polyline points)
    ↓
Avenue band = arc ± drift_margin
    ↓
Render in dashboard (soft band + dashed intention line)
```

### Weighting by Role

| Role | Weight | Rationale |
|------|--------|-----------|
| Protagonist | 1.0 | Drives the thematic core; closest to structural value |
| Antagonist | 0.7 | Mirrors/inverts the theme; significant structural weight |
| Supporting | 0.4 | Sub-thematic; contributes but doesn't drive |
| Minor/Cameo | 0.1 | Texture only; negligible structural impact |

### Computation

```python
def compute_structural_arc(index) -> list[dict]:
    """
    Compute the derived structural arc from character beats.
    Returns list of {scene_id, x_position, y_value, y_upper, y_lower}.
    """
    # 1. Group beats by scene
    # 2. For each scene, compute weighted average of character y values
    # 3. Apply drift margin (±0.12) for avenue band
    # 4. Return polyline points + band bounds
```

### Rendering

```javascript
// In buildArcGraph():
// 1. Draw intended trajectory (dashed line from act value_open → value_close)
// 2. Draw derived structural avenue (soft band from compute_structural_arc)
// 3. Draw character arcs (existing behavior)
// 4. Coherence warnings fire when characters drift outside the avenue
```

---

## Implementation Plan

### Phase A: Backend — Compute Derived Structural Arc

**File: `core/structural_arc.py`** (new)

- `compute_structural_arc(index)` → returns polyline points + band bounds
- `compute_intended_trajectory(index)` → returns start/end points from act charge values
- Helper: `_beats_by_scene(index)` → groups beats by scene
- Helper: `_weighted_average(weights_values)` → computes weighted avg

**Tests: `tests/test_structural_arc.py`**

- Test weighted average computation
- Test arc computation with known fixture data
- Test band bounds (±drift margin)
- Test empty data (no beats → no arc)
- Test single character (arc = character arc)
- Test multiple characters (arc = weighted blend)

### Phase B: Dashboard — Render Avenue + Intention Line

**File: `src/dashboard/story-dashboard.html`**

- Add CSS for `.structural-avenue` (soft band) and `.intended-trajectory` (dashed line)
- Inject `window.__STRUCTURAL_ARC__` from backend
- Render avenue band before character arcs
- Render intention line (dashed) behind avenue

**File: `tools/story_dashboard.py`**

- Inject `window.__STRUCTURAL_ARC__` (derived arc + band bounds)
- Inject `window.__INTENDED_TRAJECTORY__` (act charge line)

### Phase C: Coherence Integration

**File: `core/coherence.py`** (extend existing)

- Update coherence checks to compare characters against the **derived arc** (not the charge line)
- Warnings fire when a character's `y` value is outside the avenue band at that scene position
- Keep existing checks (directional alignment, escalation, crisis placement, controlling idea, antagonist divergence) but update the comparison baseline

### Phase D: Fixture Updates

**File: `tests/fixtures/save-the-children/`**

- Update `kael` beat `y` values to match the new theoretical model (smaller, more nuanced)
- Add `the-administrator` beats (antagonist, divergent arc)
- Add `mira` beats (supporting, sub-thematic)
- Update `project.md` with `value_at_open: positive`, `value_at_close: ironic`

**File: `tests/test_arcs.py`**

- Update beat count expectations
- Update index `arc_count` assertion

### Phase E: Documentation

**File: `skills/story-loader/references/index-format.md`**

- Document the derived structural arc format
- Explain the difference between intended trajectory and derived arc
- Document the avenue band (acceptable range)

**File: `skills/story-editor/references/continuity-checks.md`**

- Explain how coherence warnings work with the new derived arc
- What to do when a flag fires (adjust character arcs vs. adjust intention)

**File: `skills/story-theory/SKILL.md`**

- Link to the new structural arc design
- Explain the theory: structure emerges from character arcs

---

## File Inventory

### Files to create

| File | Phase | What |
|------|-------|------|
| `core/structural_arc.py` | A | Derived arc computation |
| `tests/test_structural_arc.py` | A | Arc computation tests |
| `tests/fixtures/save-the-children/arcs/the-administrator/1.md` | D | Antagonist beat |
| `tests/fixtures/save-the-children/arcs/the-administrator/2.md` | D | Antagonist beat |
| `tests/fixtures/save-the-children/arcs/the-administrator/3.md` | D | Antagonist beat |
| `tests/fixtures/save-the-children/arcs/mira/1.md` | D | Supporting beat |
| `tests/fixtures/save-the-children/arcs/mira/2.md` | D | Supporting beat |

### Files to modify

| File | Phase | What |
|------|-------|------|
| `src/dashboard/story-dashboard.html` | B | Add avenue + intention line rendering |
| `tools/story_dashboard.py` | B | Inject structural arc data |
| `core/coherence.py` | C | Update comparison baseline to derived arc |
| `tests/fixtures/save-the-children/arcs/kael/*.md` | D | Update y values |
| `tests/fixtures/save-the-children/project.md` | D | Update value_at_open/close |
| `tests/test_arcs.py` | D | Update beat count expectations |
| `skills/story-loader/references/index-format.md` | E | Document new format |
| `skills/story-editor/references/continuity-checks.md` | E | Update coherence patterns |
| `skills/story-theory/SKILL.md` | E | Link to new design |

### Files to remove/modify (old Phase 3)

| File | Action |
|------|--------|
| `src/dashboard/story-dashboard.html` (old `.arc-structural-avenue` CSS) | Remove — replaced by new avenue band |
| `tools/story_dashboard.py` (old `window.__COHERENCE_FLAGS__` injection) | Keep — still needed, but update comparison logic |

---

## Test Coverage Requirements

| Test Area | Count | Key Cases |
|-----------|-------|-----------|
| Structural arc computation | 5 | Weighted avg, empty data, single char, multiple chars, band bounds |
| Dashboard rendering | 3 | Avenue renders, intention line renders, character arcs on top |
| Coherence integration | 3 | Character inside band (no warning), outside band (warning), boundary case |
| Fixture updates | 2 | All beats parse, arc_count correct |
| **Total** | **13** | |

---

## Risk & Verification Checklist

Before calling Phase N complete:

- [ ] Phase A: `pytest tests/test_structural_arc.py` passes
- [ ] Phase B: Dashboard renders avenue + intention line (visual verification)
- [ ] Phase C: Coherence warnings fire correctly with derived arc baseline
- [ ] Phase D: Fixture updates pass all existing tests
- [ ] Phase E: Skill docs updated, references cross-linked

---

## Open Questions

| Question | Status |
|----------|--------|
| Drift margin value | ±0.12 (configurable constant in `core/structural_arc.py`) |
| How to handle scenes with no beats | Skip — arc only renders where data exists |
| How to handle characters with no beats in a scene | Character doesn't contribute to that scene's average |
| Should the avenue be configurable? | Yes — `STRUCTURAL_DRIFT_MARGIN` constant, user-tunable later |
| What if act has no `value_at_open`/`value_at_close`? | No intention line rendered (only derived arc shows) |
| What does "drift from range" actually mean in storytelling? | **Open — see investigation below** |
| How should warnings interact with structural elements (climax, escalation)? | **Open — see investigation below** |
| Are there sub-ranges within the avenue for different phases (opening tension → climax)? | **Open — see investigation below** |

---

## Open Investigation (Tomorrow)

These need deeper thinking grounded in narrative theory before we finalize Phase C:

### 1. What drift really means

Drift is expected. Stories have ups and downs. The question is: **what kind of drift matters?**

- Temporary drift mid-act (within the band by end) = probably fine
- Drift at the **act endpoints** = may signal the story misses its intended landing
- Drift at **structural moments** (climax, crisis) = higher stakes, may need attention
- Drift in **trajectory shape** (keeps going up when should come down) = may signal pacing problem

**The real signal is not "are you inside the band right now?" but "are you heading where you said you'd go?"**

### 2. Warnings are thinking aids, not verdicts

Current coherence flags are binary (in range / out of range). They should be:

- **Contextual**: "Mira at scene 3 is 0.2 below the avenue band — but this is her crisis moment, where the value is tested. Intentional?"
- **Graduated**: slight drift = gentle nudge; large drift = stronger question
- **Suggestive**: "The derived arc ends +0.3 but the act targets ironic. Consider: is this where you want to land, or does the protagonist's final beat need adjustment?"

### 3. Structural moments and their warning thresholds

Different story moments may have different sensitivity to drift:

| Moment | Drift sensitivity | Why |
|--------|-------------------|-----|
| Opening beats | Low | Still establishing; natural variation |
| Mid-act | Low-Medium | Exploration; drift is the journey |
| Crisis point | **High** | Structural pivot; drift undermines the turn |
| Climax | **High** | Payoff; drift means the setup didn't land |
| Closing beats | **High** | Final statement; drift means the story didn't say what it meant to say |

This suggests the avenue band might not be uniform — it could **narrow at structural moments** (crisis, climax, close) and widen in between.

### 4. Trajectory vs. position

Two characters can be at the same y-value but moving in opposite directions. One is climbing out of a hole; the other is falling into one. Same position, very different meanings.

The warning logic should consider:
- **Current position** relative to the band
- **Direction of movement** (Δy from previous beat)
- **Distance from intended endpoint** (are we drifting toward or away from the target?)

### 5. The shape question

Does the **shape** of the derived arc matter, or only its endpoints?

- If the shape matters: a story that goes +0.3 → +0.5 → -0.4 → -0.1 has a different arc than one that goes +0.3 → -0.4 → +0.5 → -0.1, even though endpoints match
- If only endpoints matter: we only care that we land where we intended, and the journey is the writer's craft

This may be the key question for warning logic.

---

## Estimated Task Breakdown

| Phase | Tasks | Est. Lines |
|-------|-------|------------|
| A. Structural Arc Computation | 3 tasks | ~80 |
| B. Dashboard Rendering | 3 tasks | ~90 |
| C. Coherence Integration | 2 tasks | ~40 |
| D. Fixture Updates | 2 tasks | ~50 |
| E. Documentation | 2 tasks | ~30 |
| **Total** | **12 tasks** | **~290 lines** |

---

## Next Steps

1. Review this plan with user for any gaps or changes
2. Break each phase into individual implementation tasks with full specs
3. Begin Phase A implementation
