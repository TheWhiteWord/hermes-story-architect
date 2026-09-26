# Story value vs character value

Two tracks. The field name says which one you are writing.

| scope | value word | charge | reading | curve |
|---|---|---|---|---|
| `project` | `story_value` | `story_value_at_open` / `_close` | — | — |
| `act` / `sequence` | *inherited* | `value_at_open` / `_close` | — | — |
| `scene` | *inherited* | `value_at_open` / `_close` | `shift` | `y` |
| `character` | `character_value` | `character_value_at_open` / `_close` | — | — |
| `arc_beat` | *inherited* | `character_value_at_open` / `_close` | `shift` | `y` |

**Story value** is the thematic exploration the whole work is about. **Character
value** is what one person's arc explores. A protagonist's arc may run on a
different value from the story's — that is the second track, not an error, and
nothing in either field name implies one is derived from the other.

## The two rules

1. **The value word is stated once per track and inherited downward.** No value
   word field on act, sequence, scene or arc beat. Every one of them charges the
   word its track already declared.
2. **The charge is per-entity, everywhere.** `value_at_open` / `_close`, `shift`
   and `y` are never inherited — a charge belongs to *this* scene, *this* beat,
   because that is where the story turns.

## A scene cannot introduce a second theme

If a scene seems to turn on a value word that is not the story's, that word
belongs on a **character** (with their beats), or it is a **`plot`** concern. A
subplot with its own theme is not a value field. Opening a new value in a scene
puts a character's value in the wrong place.

## Reading a `y`

`y` is the **ending** charge after the turn, −1.0 to +1.0, signed like the charge
word: `positive` above zero, `negative` below, `mixed` and `ironic` in between.
The same rule holds on a scene and on a beat — one rule, not two.

A missing `y` is not `0.0`. `0.0` is a charge a writer can choose; a scene or
beat with no recorded turn has no `y`, and the graph draws no point for it.

## Reading a container

A container states an **expectation**; a scene records what **happened**. An act
or sequence with charges but empty scenes is not drift — the design is ahead of
the draft. What `view="unfilled"` reports as `value_drift` is the real problem: a
container with no charge at all whose children are charged.

**No continuity check.** Do not require a scene's `value_at_open` to equal the
previous scene's `value_at_close`, or a character's `character_value_at_open` to
equal their first beat. A value can move *consequentially*, with nothing on
screen to turn it — a scene a character is absent from can shift what they
believe. Stories are written incrementally, so there is no fixed start or end to
check against. Where the beats and the promise disagree, that is a judgement to
make while writing, not a mismatch for a tool to report.

Full theory, including the P/C/CD/NN escalation schema and arc types, is in
`story-theory/references/values.md`.
