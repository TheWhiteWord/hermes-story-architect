# Value system — the character track

*How a character's value and the arc it moves on are recorded. The story's and a
plot's values are a different mechanism — that is `../craft/value-pass.md`, and
nothing here applies to it.*

The field *table* is here, because the shape of the track is the thing being
explained and a table says it in one line. Types, defaults and which are
required are in `story_describe`.

Each rule below is tagged. **[checked]** means the write path rejects a
violation. **[convention]** means nothing does — the rule is ours, and this file
is the only place it is written down.

The theory — what a value is — is not here. → `references/theory/values.md`

---

## The character track

- **A character carries their own value** (`character_value`) — which value their
  arc explores — and the charge it holds where the arc begins
  (`character_value_at_open`) and ends (`character_value_at_close`).
- **The arc is the sweep between those two charges.** It is not a sampled line:
  the ends are the promise, and the turns between them are recorded on the
  scenes, as `value_turns`.
- **The charges are `positive`, `negative`, `mixed`, `ironic`**, on the
  character. **[checked]**
- **A character carries no `shift` and no `y`.** It is the promise — where the arc
  starts and ends — not a sampled point. **[convention]**

## The field table

| Type | Field | Meaning |
|---|---|---|
| character | `character_value` | the value this arc explores |
| character | `character_value_at_open` / `_close` | the charge where the arc begins / ends |
| scene | `value_turns` | the turn each value takes in this scene, and its effects |

- **The value word is stated once, on the character, and never repeated on the
  scenes.** A turn names the value and the shift; it does not restate which value
  the character's arc is about. **[convention]**
- **The turn is recorded on the scene, not on the character.** A character's
  charge moves because a scene moved it, so the scene is the record and the
  character's two ends are its summary. → `../craft/value-pass.md`

## Reading the arc back

- **`story_load(view="values")`** returns, for each plot a value is used in,
  where it was last left and where it turns next — the line read in story order.
  That is how the arc is read: the turns, in order, with the charge each one
  lands on.
- **`story_load(view="unfilled")` with a `field`** answers "who else is missing
  this?" — `character_value_at_close` finds the arc's end.
- *Not in this file:* the view parameters, which the tool schema carries.

## What the store checks

- **`character_value` names an existing `value` entity**, else the write is
  refused and the message lists the defined values and their words. **[checked]**
- **`character_value_at_open` and `character_value_at_close` are charge words** —
  `positive`, `negative`, `mixed`, `ironic`. **[checked]**
- **`arc_type` is one of the five words**, or empty. **[checked]**

## What the store does not check

- **That the arc's ends are produced by the scenes.** `character_value_at_close`
  is a charge word, not a sum of the turns. A close that no scene produced is
  accepted, and the scenes are the only place to look. → `../craft/character-arc.md`
