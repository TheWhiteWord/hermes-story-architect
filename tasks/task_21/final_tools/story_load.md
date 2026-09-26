# story_load

**Role:** the structural map. Call once per session, before the other story tools.
**Not** the tool for reading an entity's content — that is `story_retrieve`.

---

## The rule this tool exists to enforce

The base view is the once-per-session load, so it must stay cheap enough to
always load. Measured on the fixture, and after growing it to 90 scenes:

```
 3 scenes →  5,034 chars (~1,258 tokens)
90 scenes →  6,427 chars (~1,606 tokens)   ← 16 chars per scene
```

**16 characters per scene.** That is the design working: a feature-length project
costs a few hundred tokens more than an empty one. Anything that would break
that belongs in a view, not the default.

Because the base view is deliberately incomplete, **depth is opt-in via `view`.**
A view is a *budget*, not a feature — the default stays small so that any one
view can afford to be large.

---

## Base view (default — no `view`)

Slim structural overview. Deliberately **excludes** the domains the views own:
relationships, arc beats, unfilled fields, per-character perspectives.

Kept per scene: `id`, `title`, `status`, `dramatic_role`, `chars`, `loc`,
`milestone` — one short string each, which is why they stay in the map.

Pinned by `TestBaseViewIsUnchanged`, which also asserts the growth rate stays
under 40 chars per scene. If the base view ever needs to grow, that test is the
thing to argue with first.

---

## Extended views

| `view` | Answers the question | Extra params | Cost (fixture) |
|---|---|---|---|
| `arc` | "are we working on this character's arc?" | `character` | 126–525 tok |
| `story_value` | "how does value move through the structure?" | `act` | 52 tok |
| `dramatic_elements` | "which scene is the crisis / climax?" | `act`, `add_plot` | 122–127 tok |
| `relationship` | "how do these people see each other?" | — | 314 tok |
| `unfilled` | **"what shall we work on next?"** | — | 479 tok |

### `view="arc"` — Character Arc Shape

The beat chain with the value shift at each step (`shift`, `y`, `is_crisis`,
`is_climax`). Omit `character` for every arc, summarised by `beat_count` — the
map of arcs. Pass `character` for one arc in full.

### `view="story_value"` — Value Across the Structure

The project's controlling value, its opening and closing value, and the same per
act. Pass `act` to narrow.

### `view="dramatic_elements"` — Structural Markers

Per-scene `dramatic_role`, the boolean markers (`is_setup`, `is_crisis`,
`is_climax`, …) and `milestone`, nested act → sequence → scene.

**`add_plot: true`** adds, per scene, which plots reference it and in which role.
The role is **derived from the relation kind** (`plot_setup` → `setup`) rather
than read from a hardcoded list — so adding a new plot role cannot silently go
missing from this view. Off by default; it roughly doubles the payload.

### `view="relationship"` — The Full Relationship Graph

The only view that exposes complete perspective data. Perspectives are returned
as a **flat list naming the character**, not a dict keyed by character id —
storage-friendly, but awkward to read at a glance:

```json
"perspectives": [{"character": "kael", "type": "…", "label": "…",
                  "feeling": "…", "strength": 0.7, "secret": false}]
```

### `view="unfilled"` — What To Work On Next

The inverted map: which optional fields are still at default, per entity. This is
the one view that answers a *meta* question — "what could we work on next".

**Ranked and capped at 15 field types.** A 90-scene project produces hundreds of
unfilled entries, and an unbounded list is a wall the LLM cannot act on. So it
reports `total_gaps` and `gap_types` alongside the top 15, and says plainly that
it truncated:

```json
{"view": "unfilled", "total_gaps": 63, "gap_types": 19,
 "unfilled": [{"field": "goals_long", "count": 6, "entities": [...]}],
 "truncated": true, "shown_types": 15,
 "hint": "19 field types are incomplete; the 15 most common are shown."}
```

Ranking is **structural** (count descending, then field name) — deliberately, per
decision. A severity model would need a priority order per entity type, and the
structural signal was judged sufficient.

**Note the gap this view does not cover:** `unfilled_fields` skips *required*
fields by design, so a required field emptied by a `story_edit` cascade is
invisible here. `story_edit` reports those in its own `detached` list instead.
Together the two cover everything.

---

## Verification

`tests/test_story_load_views.py` — 24 tests: the base view's shape and growth
rate, each view's contract, `add_plot` role derivation, the `unfilled` ranking
and cap, and the unknown-view error listing every valid name.
