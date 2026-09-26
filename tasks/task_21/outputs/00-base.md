# 00 — base view (no `view` arg) — FINAL

Project: `browser-verification-test` (title: **Save the Children**)
Raw: `00-base.json` · **7,159 bytes** (started at 7,570)

## Shape

```
loaded: true
confirmation: str
project:   {16 fields, incl. value / value_at_open / value_at_close}
acts:      [ act → sequences → scenes ]              # NO value fields
characters: [{id, name, one_sentence, story_role, arc_*, relationships[]}]
plots:      [{id, name, one_sentence, status, plot_*, value_arc, characters[]}]
worlds:     [{id, name, one_sentence, locations[{id,name,one_sentence}]?, period}]
memory:     {status, usage, counts, categories}
```

Verified in this run:

| check | result |
|---|---|
| acts carry value fields | none |
| sequences carry value fields | none |
| project carries value fields | `value`, `value_at_open`, `value_at_close` |
| `the-real-world` has `locations: []` | key absent, other two worlds keep theirs |
| plots carry setups/crisis/climax/payoffs | none — see change 6 |

## What changed, and what each one uncovered

**1. Value moved to `view='story_value'`.** Acts and sequences no longer emit
`value` / `value_at_open` / `value_at_close`. The project's own value stays —
it is the frame of reference for the whole story. Each container develops the
value independently, so a sequence's shift is not derivable from its act's and
belongs in the view built to answer that question.

**2. That exposed a pre-existing bug: `story_value` was already broken.** Acts
and sequences stored their charges under `value_open` / `value_close`
(`core/constants.py:135`) while the project — and the value view — used
`value_at_open` / `value_at_close` (`:114`). The old base view was the *only*
reader of the correct key, so the damage stayed hidden: `story_value` returned
four empty strings per container, indistinguishable from a story with no value
work done.

Renamed to the `_at_` family, matching `project` and `arc_value_at_*`:

- `core/constants.py` — 3 schema blocks; `core/entity.py` — 6 validators
- Data migrated once, no migration code shipped: 8 rows in the live DB, 5 in the
  test fixture, 15 markdown/index files across both. The markdown is what
  `story_import` rebuilds the DB from, so migrating only the DB would have
  reverted on the next import.
- Backup: `projects/browser-verification-test/.story/story.db.pre-valuekey-migration`

`tests/test_value_ownership.py` pins it, including a test asserting the view is
**not silently empty** — keys present but always `""` is a different lie from
no keys at all, and that is what hid this.

**3. `the-real-world` printing `locations: []` — fixed.** `_build_world` was the
only builder in `core/db.py` that skipped `_omit`, so it emitted an empty
collection where every other builder drops the key.
`tests/test_phase2_db_reads.py` had pinned the inconsistency
(`assert "locations" in w`) and was rewritten.

**4. Castless scenes — fixed at the authoring layer.** The detection half
already worked: `view='unfilled'` was reporting exactly
`characters: [garden-day, garden-dream]`, two scenes whose cast the LLM had
simply never attached. What was missing was the other half — recording that a
scene *deliberately* has no cast. Added scene field **`no_cast`** (boolean),
honoured by `get_unfilled_map`. Settable through the normal path:
`story_edit(action='edit_note', target={...slug: 'garden-dream'}, data={'no_cast': True})`.

Set on `garden-dream` to verify: `total_gaps` 69 → 68, and that scene stopped
being flagged. `garden-day` remains flagged — a real, outstanding omission.

**5. And that surfaced a third bug, in `unfilled` itself.** With `garden-dream`
cleared, the `characters` gap **vanished from the view entirely** — including
`garden-day`, still castless. `UNFILLED_LIMIT = 15` and the list is sorted by
count descending: `characters` was already past the cap at count 2, and fixing
one scene dropped it to 1, pushing it further off. The view reported a gap as
resolved *because* the author fixed something. The tool got quieter as the work
got done.

The cap is right — a 90-scene project would otherwise emit hundreds of entries.
The lie was that an omitted field looked identical to a clean one. Added
`other_fields`, naming what is still a gap:

```json
"truncated": true, "shown_types": 15,
"other_fields": ["value_at_open", "characters", "dramatic_function", "mood", ...]
```

`tests/test_unfilled_truncation.py` asserts every field the DB knows about is
either shown or named — the invariant that was missing.

**6. Plot beats removed — `setups` / `crisis` / `climax` / `payoffs`.** The base
map named the plots; it did not need to enumerate their beats. Verified
redundant before cutting: `view='dramatic_elements'` with `add_plot=True`
returns all four roles (`setup`, `crisis`, `climax`, `payoff`) per scene, each
with the beat's own prose attached, and `story_retrieve(entity_type='plot')`
returns the whole plot. The map was carrying bare scene ids that said less than
either of those.

Also deleted the `plot_scenes` accumulation that fed it — a dict per plot built
on every load for a value nothing read. Writes are untouched: beats still go
through `RELATION_FIELDS` in `core/entity.py`, so only the read surface moved.

Three tests were reading the base map for beats and were repointed at the
surfaces that still carry them (`test_field_coverage.py`,
`test_phase2_db_reads.py` ×2). `TestPlotBeatsLiveInTheirOwnView` now pins all
three: absent from the map, present in `dramatic_elements`, present in
`story_retrieve` — so "readable nowhere" fails the build.

## Read

**Good:**

- `confirmation` is a ready-made sentence — relay it without re-deriving counts.
- Scenes carry `chars` + `loc` + `dramatic_role` + `milestone`: navigable without a `story_retrieve` each.
- `relationships` inline on every character, so the social map is free.
- `memory.usage: 662/3000` — a self-limiting budget signal.
- Stable slug ids throughout, usable verbatim in the next call.
- Every empty collection is now omitted uniformly, so a missing key means one thing only.

**Not bugs, confirmed with the author:**

- `act_count: 3` with 2 acts — acts are pre-created for the arc graph.
- Project `value_at_close: "ironic"` vs act-1 closing `negative` — the project closes where the whole story closes, not where act-1 does.

**Still open:**

- No size signal on any entity, though `unfilled` is meant to answer "what next?".

**Verdict:** 7,159 bytes, down from 7,570 — a 5.4% reduction with nothing lost.
Shape sound. Three real bugs fixed — one pre-existing (`story_value` reading a
key that did not exist), one an inconsistency, one a view that hid gaps as they
were being fixed — one authoring gap made recordable, and two redundant
duplications removed. 621 tests pass.
