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
| `unfilled` | "what is still at default — and where?" | `field`, `entity` | 583 tok unfiltered, ~50 filtered |

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

### `view="unfilled"` — What Is Still At Default

The inverted map: which optional fields are still at default, per entity.

**Two filters, and they are the point.** Unfiltered, this is a long list
grouped by field; the two questions worth asking are both lookups against it,
and each returns a complete answer that is never truncated:

| call | Answers | Size on the live project |
|---|---|---|
| `field="character_value_at_close"` | who else is missing this? | 200 chars |
| `entity="kael"` | what did I skip on this one? | 79 chars |
| both | both questions at once | 287 chars |
| unfiltered | the whole picture | 2,330 chars |

`entities` is *who has the gap*; `fields` is *what one entity lacks*. They point
opposite ways and are different lengths, so neither carries a count — the list
is the answer.

Unfiltered it reports `total_gaps` and `gap_types` alongside the top 15, and
says plainly that it truncated:

```json
{"view": "unfilled", "total_gaps": 74, "gap_types": 22,
 "unfilled": [{"field": "goals_long", "count": 6, "entities": [...]}],
 "truncated": true, "shown_types": 15, "other_fields": ["mood", "power", …],
 "hint": "22 field types are incomplete; the 15 most common are shown. … Pass field=<name> for one, or entity=<id> for one entity."}
```

A filter that matches nothing returns an **empty list plus a `message`**, not
silence — an empty list with no explanation reads as "complete" when it usually
means "you typed the field wrong".

**The ordering is not a priority ranking.** Rows are sorted by count descending
(structural, per decision), so `goals_long` outranks a real gap on a character
arc — it is high because nothing writes it, not because it matters more. There
is no score and no "top N to work on" for the same reason: a count of
fields-at-default is a fact about the schema, not about the story. To ask about
a specific field, filter for it.

**Fields empty by design are not gaps.** `variant_of` on a base location or
world is empty *because it is a base one* — filling it would mean inventing a
parent that does not exist. It is skipped in `unfilled_fields`, so it reaches
neither this view nor `story_retrieve`'s per-entity list. Same class as
`status` and the boolean/number fields.

**Note the gap this view does not cover:** `unfilled_fields` skips *required*
fields by design, so a required field emptied by a `story_edit` cascade is
invisible here. `story_edit` reports those in its own `detached` list instead.
Together the two cover everything.

---

## Verification

`tests/test_story_load_views.py` — the base view's shape and growth rate, each
view's contract, `add_plot` role derivation, and the unknown-view error listing
every valid name.

`tests/test_unfilled_truncation.py` — the unfilled view: a filtered answer is
never truncated, the two filters compose, an empty result says why, and
`variant_of` is not reported as a gap on either entity type.
