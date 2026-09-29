# Value system

*Schematic draft — headings and notes only.*

How this system records a story's value and a character's value, and how a turn
in one becomes a number in the other.

Each rule below is tagged. **[checked]** means the write path rejects a
violation. **[convention]** means nothing does — the rule is ours, and this file
is the only place it is written down.

The field *table* is here, because the shape of the two tracks is the thing
being explained and a table says it in one line. Everything else about the
fields — types, defaults, which are required — is in `story_describe`.

The theory — what a value is, why a scene turns — is not here.

---

## The two tracks

- There are **two** value words in a story, and they are independent.
  - The **story's** lives on the `project` and is inherited downward.
  - **A character's** lives on that `character` and is inherited by their beats.
- A protagonist whose arc runs on a different value from the story's is **not a
  contradiction and not a subplot.** It is the second track, recorded on purpose.
- Nothing derives one from the other, and no field holds the relationship
  between them. How the two relate is a judgement made while writing.
  **[convention]**
- Only `project` and `character` carry a value word; every other type inherits.
  That is the whole of the two-track rule in field terms. **[convention]**
- The charge word on every value field must be one of `positive`, `negative`,
  `mixed`, `ironic` — all six pairs, on both tracks. **[checked]**
- `y` must be a number in −1.0 … +1.0, on scene and arc beat. **[checked]**

## The field table

| Type | Value word | Charge | Shift | `y` |
|---|---|---|---|---|
| project | its own | `story_value_at_open` / `_close` | — | — |
| act | inherited | `value_at_open` / `_close` | — | — |
| sequence | inherited | `value_at_open` / `_close` | — | — |
| scene | inherited | `value_at_open` / `_close` | yes | yes |
| character | its own | `character_value_at_open` / `_close` | — | — |
| arc beat | inherited | `character_value_at_open` / `_close` | yes | yes |

- **The word is stated once per track and never repeated** — no act, sequence,
  scene or beat has a field for one. **[convention]**
- **The charge is per-entity, everywhere, on both tracks.** Never inherited: a
  charge belongs to *this* scene, *this* beat, because that is where the turn
  happens. **[convention]**
- **`shift` and `y` are unprefixed on purpose.** The prefix is only needed where
  the ambiguity lives, which is the *identity* of the value; each entity carries
  exactly one track, so its shift has one possible owner. **[convention]**
- **A character carries no `shift` and no `y`.** It is the promise — where the arc
  starts and ends — not a sampled point. The beats are the path.
  **[convention]**

## `shift` is the choice; `y` is the reading of it

*The centre of this file. The turn is decided in language, then placed on a line.*

- **`shift` is where the decision happens.** It is written in the story's own
  language: `trust → suspicion`. That is the real choice, and it is made first.
- **`y` is a representation of that shift, not a second opinion.** It is the
  same turn expressed as a point, so a curve can be drawn through it.
- **Nothing derives one from the other in code.** The translation is made once,
  by whoever is writing, and the number is stored beside the language.
  **[convention]**
- So the question is never "do they agree" — it is **"where does this shift
  land on the scale."**

### What −1 to +1 means

- The scale is the **charge**, signed the way the charge word reads: `positive`
  above zero, `negative` below, `mixed` and `ironic` in between.
- The extremes are the poles of the value, not "good" and "bad". A story about
  Loyalty swings between `+1.0` and `−1.0` as readily as one about Freedom.
- **Reserve the bottom for the crisis.** A full reversal should not spend `−1.0`
  in an early scene, or there is nowhere left to fall.

| Charge word | Number |
|---|---|
| `positive` | `+1.0` |
| `mixed`, leaning positive | `+0.5` |
| `mixed`, neutral | `0.0` |
| `mixed`, leaning negative | `−0.5` |
| `negative` | `−1.0` |

### Deriving `y` from a `shift`

- **`y` is the ENDING charge, not the starting one.** If a beat moves from
  `+1.0` to `mixed` leaning positive, the `y` is where it lands, not where it
  began. This is the easiest thing to get backwards.
- **The sign must follow the ending charge.** A `shift` of `positive → negative`
  with `y: +0.3` is a contradiction.

| Shift | Lands at |
|---|---|
| `positive → mixed` | `+0.3` … `0.0` |
| `mixed → negative` | `−0.5` … `−0.8` |
| `positive → negative` | `−0.8`, or `−1.0` at a crisis or climax |
| `negative → ironic` | the **true** charge, unchanged |
| flat arc — the character holds | a small move, e.g. `+0.8 → +0.7` |

- The same reading applies on a scene and on a beat. A scene's `y` is where its
  own turn lands, and it is the point the story-value curve passes through.
- **The two tracks are read separately.** A character turning on `Freedom` is
  not the story turning on `Trust`; they are two lines on one scale and do not
  have to move together.

### Irony

- **Store the true charge, and let the `shift` line carry the irony.** There is
  no `ironic: true` flag — irony lives in the charge word and the shift line,
  and `y` holds what is actually true underneath.
- A character who appears to be at `+0.5` and is really at `−0.5` records
  `y: -0.5`. The graph stays honest to the journey rather than to the
  appearance.

### A missing `y` is not `0.0`

- `0.0` is a real charge a writer can choose — a genuinely neutral landing.
- A scene or beat with **no recorded turn** has no `y` at all, and the graph
  draws no point for it.
- **Never write `y: 0.0` to fill the gap.** It draws a point saying "something
  happened here and it landed in the middle", which is a claim, not an absence.

### Keeping the curve honest

- Most beats should be **small** movements. A sawtooth curve is melodrama; a
  flat one is nothing happening.
- The shape is the check the language cannot give: a sudden drop is a revelation
  or a cheat, and only reading the beats tells you which.
- *Note:* judgement about the story, not a rule. **[convention]**

## A scene cannot open a second theme

- If a scene turns on a word that is not the story's, that word belongs
  elsewhere:
  - it is **a character's value** — recorded on them and their beats, while the
    scene charges the story's;
  - or it is **a plot's concern** — a genuine subplot with its own theme belongs
    to the `plot`, not to a value field.
- Do not invent a value word on a scene. There is no field for one, by design: a
  second theme in a story-container field is almost always a character's value
  written in the wrong place. **[convention]**

## Reading it back

- `story_load(view="story_value")` returns the story's word **once, at the top**,
  and the charges down through act → sequence → scene. It does not return a word
  per container — there is none to return, and its absence is not a gap.
- The character track is a different view: `view="arc"` with a `character`.
- `story_load(view="unfilled")` with a `field` answers "who else is missing
  this?" across both tracks, so both prefixes are worth knowing.
- *Not in this file:* the view parameters, which the tool schema carries.
