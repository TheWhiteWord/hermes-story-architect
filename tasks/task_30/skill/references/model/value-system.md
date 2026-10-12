# Value system — the character track

*How a character's value and their arc's turns are recorded. The story's and a
plot's values are a different mechanism — that is `../craft/value-pass.md`, and
nothing here applies to it.*

The field *table* is here, because the shape of the track is the thing being
explained and a table says it in one line. Types, defaults and which are
required are in `story_describe`.

Each rule below is tagged. **[checked]** means the write path rejects a
violation. **[convention]** means nothing does — the rule is ours, and this file
is the only place it is written down.

The theory — what a value is — is not here. → `theory/values.md`

---

## The character track

- **A character carries their own value** (`character_value`) — which value their
  arc explores — and the charge it holds where the arc begins
  (`character_value_at_open`) and ends (`character_value_at_close`).
- **The beats are the path.** Each `arc_beat` carries the charge entering and
  leaving that beat, the `shift` in the story's own words, and `y`, the shift
  measured.
- **The charges are `positive`, `negative`, `mixed`, `ironic`**, on the character
  and on every beat. **[checked]**
- **`y` is a number in −1.0 … +1.0**, on an arc beat. **[checked]**

## The field table

|| Type | Field | Meaning |
|---|---|---|
|| character | `character_value` | the value this arc explores |
|| character | `character_value_at_open` / `_close` | the charge where the arc begins / ends |
|| arc beat | `character_value_at_open` / `_close` | the charge entering / leaving this beat |
|| arc beat | `shift` | how the value turns here, in dramatic language |
|| arc beat | `y` | that shift as a number, for the curve |

- **The value word is stated once, on the character, and never repeated on the
  beats.** The beats inherit it. **[convention]**
- **A character carries no `shift` and no `y`.** It is the promise — where the arc
  starts and ends — not a sampled point. The beats are the path. **[convention]**

## `shift` is the choice; `y` is the reading of it

*The centre of this file. The turn is decided in language, then placed on a line.*

- **`shift` is where the decision happens.** It is written in the story's own
  language: `trust → suspicion`.
- **`y` is a representation of that shift, not a second opinion** — the same turn
  expressed as a point, so a curve can be drawn through it.
- **Nothing derives one from the other in code.** The translation is made once,
  by whoever is writing. **[convention]**
- So the question is never "do they agree" — it is **"where does this shift land
  on the scale."**

### What −1 to +1 means

- The scale is the **charge**, signed the way the charge word reads: `positive`
  above zero, `negative` below, `mixed` and `ironic` in between.
- **Reserve the bottom for the crisis.** A full reversal should not spend `−1.0`
  in an early beat, or there is nowhere left to fall.

|| Charge word | Number |
|---|---|
|| `positive` | `+1.0` |
|| `mixed`, leaning positive | `+0.5` |
|| `mixed`, neutral | `0.0` |
|| `mixed`, leaning negative | `−0.5` |
|| `negative` | `−1.0` |

### Deriving `y` from a `shift`

- **`y` is the ENDING charge, not the starting one.** A beat moving from `+1.0` to
  `mixed` leaning positive has the `y` where it lands. This is the easiest thing
  to get backwards.
- **The sign must follow the ending charge.** A `shift` of `positive → negative`
  with `y: +0.3` is a contradiction.

|| Shift | Lands at |
|---|---|
|| `positive → mixed` | `+0.3` … `0.0` |
|| `mixed → negative` | `−0.5` … `−0.8` |
|| `positive → negative` | `−0.8`, or `−1.0` at a crisis or climax |
|| `negative → ironic` | the **true** charge, unchanged |
|| flat arc — the character holds | a small move, e.g. `+0.8 → +0.7` |

### Irony

- **Store the true charge, and let the `shift` line carry the irony.** There is no
  `ironic: true` flag — irony lives in the charge word and the shift line, and `y`
  holds what is actually true underneath.
- A character who appears to be at `+0.5` and is really at `−0.5` records
  `y: -0.5`. The graph stays honest to the journey rather than to the appearance.

### A missing `y` is not `0.0`

- `0.0` is a real charge a writer can choose — a genuinely neutral landing.
- A beat with **no recorded turn** has no `y` at all, and the graph draws no point
  for it.
- **Never write `y: 0.0` to fill the gap.** It draws a point saying "something
  happened here and it landed in the middle", which is a claim, not an absence.

### Keeping the curve honest

- Most beats should be **small** movements. A sawtooth curve is melodrama; a flat
  one is nothing happening. The shape is the check the language cannot give: a
  sudden drop is a revelation or a cheat, and only reading the beats tells you
  which. *Judgement, not a rule.* **[convention]**

## Reading it back

- **`story_load(view="arc")` with a character id** returns that character's beats,
  in order, with the shift at each step. Pass the character: without one it
  returns every character's arc. → `reading-the-project.md`
- **`story_load(view="unfilled")` with a `field`** answers "who else is missing
  this?" — `character_value_at_close` finds the arc's end.
- *Not in this file:* the view parameters, which the tool schema carries.
