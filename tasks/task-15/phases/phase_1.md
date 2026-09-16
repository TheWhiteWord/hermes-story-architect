# Phase 1: Coherence Check Engine

## Files to modify

None.

## Files to create

| File | Purpose |
|------|---------|
| `core/coherence.py` | New module — compute 5 coherence checks from index data |
| `tests/test_coherence.py` | Tests for all 5 checks + thresholds + edge cases |

## Step-by-step

### Step 1.1 — Create `core/coherence.py`

New module with a single public function `compute_coherence(index: dict) -> dict` that returns flag list.

**Threshold constants** (module-level):
```python
# Thresholds — generous defaults, tighten based on user feedback
DIRECTIONAL_ALIGNMENT_MIN_DELTA = 0.3   # net Δy below this is noise, not misalignment
ESCALATION_IMBALANCE_RATIO = 1.5        # Act N peak > 1.5× Act N+2 peak = flag
CONTROLLING_IDEA_TOLERANCE = 0.0        # zero tolerance — sign mismatch is always a flag
```

**Charge-to-numeric mapping** (for sign checks):
```python
CHARGE_SIGN = {
    "positive": 1,
    "mixed": 0,       # neutral — no direction
    "negative": -1,
    "ironic": 0,      # true charge stored separately; treat as neutral for net
}
```

**Helper functions** (private, same module):

```python
def _beats_for_character(index, character_slug) -> list[dict]:
    """Filter index['arcs'] by character, sorted by order."""

def _beats_in_act(index, act_id) -> list[dict]:
    """Filter beats by scene.act_id membership.
    A beat is in an act if beat['scene'] matches a scene with scene['act_id'] == act_id."""

def _act_direction(act: dict) -> int:
    """Map act's value_open/value_close to +1, -1, or 0.
    +1: positive→positive (or mixed→positive, etc.) — net positive shift
    -1: negative shift
    0: no change or ambiguous"""

def _protagonist_id(index) -> str:
    """Find protagonist: character with story_role == 'Protagonist'.
    Returns empty string if not found."""

def _antagonist_id(index) -> str:
    """Find antagonist: character with story_role == 'Antagonist'.
    Returns empty string if not found."""

def _y_sign(y_value) -> int:
    """Map a y numeric value to +1, -1, or 0."""

def _charge_to_sign(charge_str: str) -> int:
    """Map charge string to sign using CHARGE_SIGN."""
```

**The five checks** — each returns a flag dict or None:

```python
def _check_directional_alignment(index, protagonist_id) -> dict | None:
    """Check 1: Protagonist net Δy per act vs. act structural direction.
    Returns flag if sign opposes AND |net Δy| > threshold."""

def _check_escalation(index, protagonist_id) -> dict | None:
    """Check 2: Peak |Δy| per act should trend upward.
    Returns flag if any earlier act's peak > ratio × later act's peak."""

def _check_crisis_placement(index, protagonist_id) -> dict | None:
    """Check 3: is_crisis beat not in final act.
    is_climax beat must be in final act."""

def _check_controlling_idea(index, protagonist_id) -> dict | None:
    """Check 4: Protagonist y_final sign vs. project value_at_close sign.
    Returns flag if opposite."""

def _check_antagonist_divergence(index, protagonist_id, antagonist_id) -> dict | None:
    """Check 5: At structural climax, P and A should move in opposite directions.
    Returns flag if same direction."""
```

**Flag format** (consistent across all checks):
```python
{
    "check": "directional_alignment",    # check name
    "severity": "warning",               # all warnings for now (one tier)
    "act": "act-1",                      # relevant act (or "project" for global)
    "message": "Act 1 net movement is +0.6 but structural value goes positive→negative — intentional?",
    "data": {"net_dy": 0.6, "structural_direction": -1}  # debug data
}
```

**Public function:**
```python
def compute_coherence(index: dict) -> list[dict]:
    """Run all 5 coherence checks. Returns list of flag dicts (empty = all clear)."""
```

**Graceful degradation:**
- No protagonist → return `[]`
- No acts → skip act-level checks, run project-level checks only
- No antagonist → skip antagonist divergence check
- Single act → skip escalation check (need ≥2 acts)

### Step 1.2 — Create `tests/test_coherence.py`

```python
"""Tests for arc coherence checks (Phase 1)."""
import pytest
from core.coherence import compute_coherence, _act_direction, _y_sign, CHARGE_SIGN


class TestHelperFunctions:
    def test_act_direction_positive_to_negative(self): ...
    def test_act_direction_negative_to_positive(self): ...
    def test_act_direction_no_change(self): ...
    def test_act_direction_mixed_charges(self): ...
    def test_y_sign_positive(self): ...
    def test_y_sign_negative(self): ...
    def test_y_sign_zero(self): ...
    def test_charge_sign_mapping(self): ...


class TestDirectionalAlignment:
    def test_aligned_no_flag(self):
        """Protagonist net Δy matches structural direction — no flag."""
    def test_misaligned_flags(self):
        """Protagonist net Δy opposes structural direction — flag."""
    def test_small_movement_no_flag(self):
        """Net Δy below threshold — no flag even if opposing."""
    def test_multiple_acts_independent(self):
        """Each act checked independently — one misalignment doesn't flag others."""


class TestEscalation:
    def test_escalates_no_flag(self):
        """Peak |Δy| increases act over act — no flag."""
    def test_peaks_early_flags(self):
        """Act 1 peak > 1.5× Act 3 peak — flag."""
    def test_single_act_skipped(self):
        """Only 1 act — escalation check skipped."""


class TestCrisisPlacement:
    def test_climax_in_final_act_no_flag(self):
        """is_climax beat in final act — no flag."""
    def test_climax_not_in_final_act_flags(self):
        """is_climax beat in Act 1 — flag."""
    def test_crisis_in_final_act_flags(self):
        """is_crisis beat in final act — flag."""


class TestControllingIdea:
    def test_aligned_no_flag(self):
        """Protagonist y_final matches project value_at_close — no flag."""
    def test_contradicts_flags(self):
        """Protagonist y_final opposite to value_at_close — flag."""


class TestAntagonistDivergence:
    def test_diverge_at_climax_no_flag(self):
        """P and A move opposite at climax — no flag."""
    def test_converge_at_climax_flags(self):
        """P and A move same direction at climax — flag."""
    def test_no_antagonist_skipped(self):
        """No antagonist — check skipped."""


class TestComputeCoherence:
    def test_empty_index_no_flags(self):
        """Empty/minimal index — no flags."""
    def test_no_protagonist_no_flags(self):
        """No protagonist — no flags."""
    def test_full_fixture_all_checks_run(self):
        """Full index — all applicable checks run."""
```

### Step 1.3 — Verify

```bash
pytest tests/test_coherence.py -v
```

Expected: all tests pass.

## Legacy cleanup

None — this is additive. No existing coherence code to remove.

## Naming convention check

- `compute_coherence` — verb-first, matches `generate_index`, `compute_stats` pattern
- `_check_*` — private helpers, leading underscore matches `_parse_*`, `_enrich_*` pattern
- `DIRECTIONAL_ALIGNMENT_MIN_DELTA` — uppercase constants, matches existing threshold style
- `severity: "warning"` — lowercase string, matches `severity` field convention

## Verification checklist

- [x] `core/coherence.py` created with `compute_coherence()` and 5 check functions
- [x] Module-level threshold constants defined
- [x] Helper functions `_beats_for_character`, `_act_direction`, `_protagonist_id`, `_antagonist_id`, `_y_sign`, `_charge_to_sign`
- [x] Graceful degradation (no protagonist, no acts, no antagonist, single act)
- [x] Flag dict format consistent across all checks
- [x] `tests/test_coherence.py` created with all test classes
- [x] `pytest tests/test_coherence.py` passes (35/35)
- [x] Existing tests still pass (`pytest tests/test_arcs.py` — 49/49)
- [x] No schema changes (`project.md`, frontmatter, constants unchanged)

## Final notes

**Fixture update:** Kael (Protagonist) had no arc beats — now has 3 beats (1/crisis/climax) across act-1. This was required for coherence checks to have data to validate against. The Elena Voss arc beats were unchanged (3 beats, also Supporting role — used for antagonist divergence checks via separate character).

**Test count:** `test_coherence.py` has 35 tests covering all 5 check functions, helpers, thresholds, and edge cases.

**Regression:** Updated `test_arcs.py` arc count assertions (3→6) to match the new Kael beats in the fixture.

**NITE:** None — module is self-contained, no cross-module coupling. The escalation check uses act-based grouping which requires scenes; if beats lack scene→act mapping they silently skip (graceful).

## Divergences from spec

| # | Spec | Code | Reason |
|---|------|------|--------|
| 1 | Each `_check_*` returns `dict \| None` | Each returns `list[dict]` | Multiple flags per check type (e.g., 2 misaligned acts). Caller `extend()` instead of wrapping. |
| 2 | `_beats_in_act(index, act_id)` helper | Deleted | Spec-defined but dead code — semantics didn't match any use case, zero callers. |
| 3 | `_scenes_in_act` not in spec | Added (private helper) | Required by crisis placement check ("is_crisis NOT in final act"). |
| 4 | `compute_coherence` returns `dict` (intro) | Returns `list[dict]` | Spec intro contradicts its own "Graceful degradation" section (which says `return []`). List is correct shape. |

## Final notes

**Fixture update:** Kael (Protagonist) had no arc beats — now has 3 beats (1/crisis/climax) across act-1. This was required for coherence checks to have data to validate against. The Elena Voss arc beats were unchanged (3 beats, also Supporting role — used for antagonist divergence checks via separate character).

**Test count:** `test_coherence.py` has 35 tests covering all 5 check functions, helpers, thresholds, and edge cases.

**Regression:** Updated `test_arcs.py` arc count assertions (3→6) to match the new Kael beats in the fixture.

**NITE:** None — module is self-contained, no cross-module coupling. The escalation check uses act-based grouping which requires scenes; if beats lack scene→act mapping they silently skip (graceful).

## Divergences from spec

| # | Spec | Code | Reason |
|---|------|------|--------|
| 1 | Each `_check_*` returns `dict \| None` | Each returns `list[dict]` | Multiple flags per check type (e.g., 2 misaligned acts). Caller `extend()` instead of wrapping. |
| 2 | `_beats_in_act(index, act_id)` helper | Deleted | Spec-defined but dead code — semantics didn't match any use case, zero callers. |
| 3 | `_scenes_in_act` not in spec | Added (private helper) | Required by crisis placement check ("is_crisis NOT in final act"). |
| 4 | `compute_coherence` returns `dict` (intro) | Returns `list[dict]` | Spec intro contradicts its own "Graceful degradation" section (which says `return []`). List is correct shape. |
