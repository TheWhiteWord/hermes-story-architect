# Phase 5: Documentation

## Files to modify

| File | Change |
|------|--------|
| `skills/story-loader/references/index-format.md` | Document coherence report format |
| `skills/story-editor/references/continuity-checks.md` | Add coherence alert patterns |
| `skills/story-theory/SKILL.md` | Link to values.md §5 and §8 |

## Step-by-step

### Step 5.1 — Update `story-loader/references/index-format.md`

Add new section at the end:

```markdown
## Coherence Report

The index includes a computed coherence report at `window.__COHERENCE_FLAGS__` (injected by `story_dashboard.py`).

Each flag is a dict with fields:

| Field | Type | Description |
|-------|------|-------------|
| `check` | string | Check name (`directional_alignment`, `escalation`, `crisis_placement`, `controlling_idea`, `antagonist_divergence`) |
| `severity` | string | All flags are `"warning"` (questions, not verdicts) |
| `act` | string | Relevant act slug (or `"project"` for global checks) |
| `message` | string | Human-readable description of the finding |
| `data` | dict | Debug data (net Δy, structural direction, etc.) |

An empty list means no coherence issues detected.
```

### Step 5.2 — Update `story-editor/references/continuity-checks.md`

Add new section:

```markdown
### coherence_flags

Does this contradict the coherence report from the dashboard?

**Example**:
- Coherence flag: "Protagonist ends at +0.5 but project closes negative — intentional?"
- Edit: Protagonist's final beat deepens their hope despite the tragic ending
- **Finding**: Either intentional (flag acknowledges ambiguity) or a genuine problem — verify with the writer

**Severity**: `warning` — all flags are questions, not verdicts. Never auto-fix.

**Common flags**:
- `directional_alignment`: Protagonist's value movement goes opposite to the structural pressure in an act
- `escalation`: An earlier act has more dramatic reversal than a later act (arc peaks too early)
- `crisis_placement`: `is_crisis` beat is in the final act, or `is_climax` beat is not in the final act
- `controlling_idea`: Protagonist's final charge contradicts the story's stated ending charge
- `antagonist_divergence`: Protagonist and antagonist move in the same direction at a structural climax (they should oppose)
```

### Step 5.3 — Update `story-theory/SKILL.md`

Update the references section to include §5 and §8 links:

```markdown
## References

- `references/plot.md` — Plot theory: definitions, characteristics, schema mapping
- `references/values.md` — Value theory: arc types, value charges, value hierarchy, beat file schema, character arc theory (§5), structural value hierarchy (§8)
```

## Legacy cleanup

None — additive documentation only.

## Naming convention check

- `coherence_flags` — lowercase with underscore, matches `character_knowledge`, `chronology` pattern in continuity-checks
- `__COHERENCE_FLAGS__` — uppercase dunder, matches existing `__STORY_DATA__` pattern

## Verification checklist

- [ ] `story-loader/references/index-format.md` updated with coherence report section
- [ ] `story-editor/references/continuity-checks.md` updated with coherence_flags category
- [ ] `story-theory/SKILL.md` references section updated with §5 and §8 links
- [ ] All 5 phases of `tasks/task-15/phases/` created
