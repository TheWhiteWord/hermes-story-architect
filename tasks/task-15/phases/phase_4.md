# Phase 4: Fixtures & Integration

## Files to modify

| File | Change |
|------|--------|
| `tests/fixtures/save-the-children/arcs/kael/` | Add 3 beat files (protagonist) |
| `tests/fixtures/save-the-children/arcs/the-administrator/` | Add 3 beat files (antagonist) |
| `tests/fixtures/save-the-children/arcs/marcus-chen/` | Add 2 beat files (supporting) |
| `tests/test_arcs.py` | Update beat count expectations (3 → 11) |
| `tests/test_coherence.py` | Full integration tests |

## Files to create

| File | Purpose |
|------|---------|
| `tests/fixtures/save-the-children/arcs/kael/1.md` | Protagonist beat — open, y=+0.8 |
| `tests/fixtures/save-the-children/arcs/kael/2.md` | Protagonist beat — doubt, y=+0.3 |
| `tests/fixtures/save-the-children/arcs/kael/3.md` | Protagonist beat — still positive (deliberate problem: ends +0.5 but project closes negative) |
| `tests/fixtures/save-the-children/arcs/the-administrator/1.md` | Antagonist beat — y=-0.7 (diverges from protagonist) |
| `tests/fixtures/save-the-children/arcs/the-administrator/2.md` | Antagonist beat — y=-0.9 |
| `tests/fixtures/save-the-children/arcs/the-administrator/3.md` | Antagonist beat — y=-0.8 |
| `tests/fixtures/save-the-children/arcs/marcus-chen/1.md` | Supporting beat — y=+0.2 |
| `tests/fixtures/save-the-children/arcs/marcus-chen/2.md` | Supporting beat — y=-0.4 |

## Step-by-step

### Step 4.1 — Create `kael` beat files (protagonist)

**`arcs/kael/1.md`** — First beat: Kael trusts the system, starts positive.
```yaml
---
id: "1"
character: kael
scene: central-room-day
label: "First Doubt"
action: "Kael asks Mira about the inconsistency they noticed."
gap: "Mira deflects — says Kael is imagining things."
choice: "Kael drops it, but files the moment away."
shift: "positive → mixed"
y: 0.8
order: 1
is_crisis: false
is_climax: false
---
```

**`arcs/kael/2.md`** — Second beat: Kael's trust erodes.
```yaml
---
id: "2"
character: kael
scene: the-core-day
label: "The Crack"
action: "Kael accesses the core logs without permission."
gap: "The logs show deliberate erasure — someone has been hiding something for years."
choice: "Kael copies the data instead of reporting it."
shift: "mixed → negative"
y: 0.3
order: 2
is_crisis: false
is_climax: false
---
```

**`arcs/kael/3.md`** — Third beat: Kael finds truth but still hopeful (deliberate problem).
```yaml
---
id: "3"
character: kael
scene: central-room-night
label: "The Choice"
action: "Kael confronts the Administrator with the data."
gap: "The Administrator offers Kael a place in the system — 'You're too valuable to waste.'"
choice: "Kael refuses, but still believes the system can be fixed from inside."
shift: "negative → mixed"
y: 0.5
order: 3
is_crisis: false
is_climax: true
---
```

**Deliberate problem:** Kael's final `y` is +0.5 (positive charge — still hopeful), but `project.value_at_close` is `negative`. The controlling idea sanity check should flag this.

### Step 4.2 — Create `the-administrator` beat files (antagonist)

**`arcs/the-administrator/1.md`**
```yaml
---
id: "1"
character: the-administrator
scene: central-room-day
label: "The Mask"
action: "The Administrator performs their daily rounds, flawless."
gap: "A child asks an innocent question that nearly pierces the facade."
choice: "Smile. Redirect. Move on."
shift: "positive → mixed"
y: -0.7
order: 1
is_crisis: false
is_climax: false
---
```

**`arcs/the-administrator/2.md`**
```yaml
---
id: "2"
character: the-administrator
scene: the-core-day
label: "The Threat"
action: "The Administrator discovers the accessed logs."
gap: "Not anger — calculation. A threat to the system is a threat to existence itself."
choice: "Quietly mark the access. Wait."
shift: "mixed → negative"
y: -0.9
order: 2
is_crisis: false
is_climax: false
---
```

**`arcs/the-administrator/3.md`**
```yaml
---
id: "3"
character: the-administrator
scene: central-room-night
label: "The Offer"
action: "The Administrator offers Kael a place in the system."
gap: "Kael refuses. The Administrator expected this."
choice: "Accept the refusal. Begin planning the real solution."
shift: "negative → negative (deepened)"
y: -0.8
order: 3
is_crisis: false
is_climax: true
---
```

**Note on divergence:** At the climax scene (`central-room-night`), protagonist Δy is positive (refuses to give up hope) while antagonist Δy is negative (committed to the system). They diverge — this is correct, no flag.

### Step 4.3 — Create `marcus-chen` beat files (supporting)

**`arcs/marcus-chen/1.md`**
```yaml
---
id: "1"
character: marcus-chen
scene: central-room-day
label: "The Witness"
action: "Marcus notices Kael's distraction."
gap: "He's seen it before — the ones who start asking questions either break or leave."
choice: "Says nothing. Watches."
shift: "positive → mixed"
y: 0.2
order: 1
is_crisis: false
is_climax: false
---
```

**`arcs/marcus-chen/2.md`**
```yaml
---
id: "2"
character: marcus-chen
scene: central-room-night
label: "The Aftermath"
action: "Marcus sees Kael leave the Administrator's office, still whole."
gap: "Relief — then guilt. He did nothing."
choice: "Vows to act next time."
shift: "mixed → negative"
y: -0.4
order: 2
is_crisis: false
is_climax: false
---
```

### Step 4.4 — Update `test_arcs.py` beat count expectations

```python
# Before:
assert len(beats) == 3
# After:
assert len(beats) == 11

# Before:
assert index["project"]["arc_count"] == 3
# After:
assert index["project"]["arc_count"] == 11

# Before:
assert "3 arc beats" in data["confirmation"]
# After:
assert "11 arc beats" in data["confirmation"]
```

### Step 4.5 — Add integration tests to `test_coherence.py`

```python
class TestCoherenceFixtureIntegration:
    FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"

    def test_controlling_idea_flag(self):
        """Protagonist ends at +0.5 but project closes negative — should flag."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        controlling = [f for f in flags if f["check"] == "controlling_idea"]
        assert len(controlling) == 1
        assert "opposite" in controlling[0]["message"].lower() or "contradiction" in controlling[0]["message"].lower()

    def test_antagonist_divergence_no_flag(self):
        """P and A diverge at climax — no flag expected."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        divergence = [f for f in flags if f["check"] == "antagonist_divergence"]
        assert len(divergence) == 0

    def test_protagonist_beats_all_in_act1(self):
        """All protagonist beats are in act-1 — escalation skipped (single act)."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        escalation = [f for f in flags if f["check"] == "escalation"]
        assert len(escalation) == 0

    def test_full_coherence_report_structure(self):
        """All flags have required fields."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        for f in flags:
            assert "check" in f
            assert "severity" in f
            assert "act" in f
            assert "message" in f
            assert "data" in f
```

## Legacy cleanup

- `test_arcs.py` — update beat count assertions (3 → 11)
- No structural changes to existing tests

## Naming convention check

- File names `1.md`, `2.md`, `3.md` — match existing `dr-elena-voss` pattern
- `character` field uses slug (`kael`, `the-administrator`, `marcus-chen`) — matches folder names and existing character IDs

## Verification checklist

- [x] 8 new beat fixture files created
- [x] `kael` beats span 3 scenes with y values: +0.8, +0.3, +0.5
- [x] `the-administrator` beats span 3 scenes with y values: -0.7, -0.9, -0.8
- [x] `marcus-chen` beats span 2 scenes with y values: +0.2, -0.4
- [x] `test_arcs.py` beat count assertions updated (3 → 11)
- [x] `test_coherence.py` fixture integration tests added
- [x] `pytest tests/test_coherence.py` passes
- [x] `pytest tests/test_arcs.py` passes
- [x] `pytest tests/test_core.py` passes (regression)
