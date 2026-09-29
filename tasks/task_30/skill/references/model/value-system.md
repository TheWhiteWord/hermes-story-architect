# Value system

*Schematic draft — headings and notes only.*

How this system records a story's value and a character's value, and which of
those rules the code enforces and which are ours to keep.

The field *table* is here, because the shape of the two tracks is the thing
being explained and a table says it in one line. Everything else about the
fields — types, defaults, which are required — is in `story_describe`, and is
not repeated.

The theory — what a value is, what it does, why a scene turns — is not here.

---

## What is checked and what is not

*Read this before assuming a mistake will be caught.*

- **Checked on write, every time:** the charge word on every value field must be
  one of `positive`, `negative`, `mixed`, `ironic`. All six pairs are validated —
  the project's, the character's, and the unprefixed pair on act, sequence and
  scene. A wrong word is reported, not stored quietly.
- **Checked on write:** `y` must be a number in −1.0 … +1.0, on scene and arc
  beat. Nothing else about it.
- **Checked on write:** a relationship has exactly two characters.
- **Not checked at all:**
  - *Which word a container inherits.* There is no field for it, so there is
    nothing to validate. Inheritance is a convention this file states.
  - *That `shift` and `y` are never inherited.* They are per-entity and nothing
    checks that you did not copy one down.
  - *That a scene cannot open a second theme.* Nothing looks.
  - *How `y` relates to `shift`.* No code derives one from the other.
- **So:** a wrong charge word is caught; everything structural about the value
  system is on the author. This file is the only enforcement those rules have.

## The two tracks

*The first thing to get right, and the easiest to get wrong.*

- There are **two** value words in a story and they are independent.
  - The **story's** value lives on the `project` and is inherited downward.
  - **A character's** value lives on that `character` and is inherited by their
    arc beats.
- A protagonist whose arc runs on a different value from the story's is **not a
  contradiction and not a subplot.** It is the second track, recorded on purpose.
- Nothing derives one from the other, and no field expresses the relationship
  between them. How the two relate is a judgement made while writing — which is
  the right place for it.
- *Note:* only `project` and `character` carry a value word. Every other type
  inherits. That is the whole of the two-track rule in field terms.

## The field table

*Which type owns what. Verified against the schema.*

| Type | Value word | Charge | Shift | `y` |
|---|---|---|---|---|
| project | its own | `story_value_at_open` / `_close` | — | — |
| act | inherited | `value_at_open` / `_close` | — | — |
| sequence | inherited | `value_at_open` / `_close` | — | — |
| scene | inherited | `value_at_open` / `_close` | yes | yes |
| character | its own | `character_value_at_open` / `_close` | — | — |
| arc beat | inherited | `character_value_at_open` / `_close` | yes | yes |

- **The word is stated once per track and never repeated.** No act, sequence,
  scene or beat has a field for one.
- **The charge is per-entity, everywhere, on both tracks.** Never inherited. A
  charge belongs to *this* scene, *this* beat — that is where the turn happens,
  so that is where it is written.
- **`shift` and `y` are unprefixed on purpose.** The prefix is only needed where
  the ambiguity lives, which is the *identity* of the value. Each entity carries
  exactly one track, so its shift has one possible owner.
- **A character carries no `shift` and no `y`.** It is the promise — where the
  arc starts and ends — not a sampled point. The beats are the path.

## `shift` and `y` — three different things

*Why there are two fields for one turn.*

- The **charge pair** is a measurement: `positive → negative`.
- **`y`** is the ending charge as a point on a line, −1.0 … +1.0, which is what
  the graph interpolates. It is the only one of the three that can.
- **`shift`** is the reading in the story's own language: "trust → suspicion".
- *The charge pair is instrumentation; `shift` is the finding, and the one a
  writer actually uses.* `y` exists so the shape can be drawn.
- **No code derives `y` from `shift`, or `shift` from the pair.** All three are
  set by hand. Filling one does not fill another, and there is no check that
  they agree.
- *Open question:* should the file say more about keeping them consistent, or
  is that the sort of guidance that goes stale? Nothing enforces it, so a
  sentence is the only place it can live.

## A scene cannot open a second theme

*The rule with no code behind it, and the one most often broken.*

- If a scene seems to turn on a word that is not the story's, that word belongs
  somewhere else:
  - it is **a character's value** — recorded on them and their beats, while the
    scene charges the story's;
  - or it is **a plot's concern** — a genuine subplot with its own theme belongs
  to the `plot`, not to a value field.
- Do not invent a value word on a scene. There is no field for one, by design:
  a second theme in a story-container field is almost always a character's value
  written in the wrong place.
- *Nothing checks this.* It is the convention most worth stating carefully.

## Reading it back

- `story_load(view="story_value")` returns the story's word once at the top and
  the charges down through act → sequence → scene. It does **not** return a word
  per container — there is none to return.
- The character track is a different view: `view="arc"` with a `character`.
- `story_load(view="unfilled")` with `field` answers "who else is missing this?"
  across both tracks — the field name is given, so both prefixes are worth
  knowing.
- *Not in this file:* the view parameters, which the tool schema carries.

---

## Open questions

- [ ] `shift`, the charge pair and `y` can disagree silently. Worth a sentence
      here, or is that guidance nobody can check?
- [ ] The file states conventions with no code behind them. Should it say so
      once, as it does above, or per rule? Once is shorter; per rule is harder
      to misread.
