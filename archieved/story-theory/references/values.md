# Values — Theory Reference

Grounds the LLM in McKee's theory of values so it can reason about value choices in features (character arcs, structure, scene design).

---

## 1. What Values Are

> **Story Values:** Universal qualities of human experience that can shift between positive and negative states from moment to moment. — *Good_Writing.md:100-101*

Values are not moral judgments. They are **chargeable conditions** — a character can move from love to hate, freedom to slavery, hope to despair within a single scene. The shift IS the event.

Key properties:
- **Universal** — recognized across cultures (alive/dead, love/hate, truth/lie)
- **Binary** — each value has a clear opposite (positive/negative charge)
- **Dynamic** — they change through conflict, not explanation
- **Hierarchical** — can be personal (love/hate), social (justice/injustice), or existential (meaning/meaninglessness)

---

## 2. McKee's Canonical Value List

> *Good_Writing.md:102-113*

Binary opposites (positive/negative):
- alive/dead
- love/hate
- freedom/slavery
- truth/lie
- courage/cowardice
- loyalty/betrayal
- wisdom/stupidity
- strength/weakness
- excitement/boredom
- hope/despair

Value-charged concepts (not moral/ethical but emotionally weighted):
- justice/injustice
- success/failure
- consciousness/unconsciousness
- wealth/poverty
- communication/silence
- maturity/immaturity
- honesty/deception
- liberty/oppression
- sanctioned sex/transgression

**Genre conventions** favor certain values: courtroom dramas live on justice/injustice; war films on courage/cowardice; romance on love/hate. The genre doesn't dictate the value but creates audience expectation.

---

## 3. Values Across the Structural Hierarchy

> *Good_Writing.md:136-153, 312-314*

McKee defines the structural hierarchy by **scale of value change**, not by different values:

| Level | Change Type | Value Scope |
|-------|-------------|-------------|
| Beat | Exchange of behavior | Micro-shift within a scene |
| Scene | Turns value-charged condition | One value, positive→negative or vice versa |
| Sequence | Cumulative impact | Moderate reversal across multiple scenes |
| Act | Major reversal | Major value swing, more powerful than any sequence |
| Story | Absolute and irreversible | The final value statement |

**Critical insight:** The hierarchy is about the *magnitude* of value change, not a taxonomy of values. A scene might turn on "Trust vs. Betrayal" while the act reverses "Innocence vs. Experience" and the story proves "Justice triumphs over Loyalty." These aren't the same value word, but they **rhyme** thematically.

### What this means for our system

McKeean theory does NOT require:
- Each level to use the same value word
- Act values to be "children" of story values
- Scene values to map 1:1 to act values

McKeean theory DOES require:
- Each level creates **progressively larger** value reversals
- The story climax delivers the **largest, irreversible** value change
- Values are **thematically related** across levels (not random)

**Conclusion:** the hierarchy is about the *size* of the reversal, and that is
what our charge fields record — the story's value word is stated once and every
level charges it with a progressively larger swing. The thematic "rhyme" between
a scene's turn and a larger reversal is real, and it is where a second value
word legitimately appears: on a **character**, as their own track (see §8). It is
not recorded as a second value on a story container, and it is not derived by a
rule — it is a judgement made while writing.

---

## 4. The Antagonism Schema — Value Escalation

> *Good_Writing.md:666-682*

McKee's schema for how values escalate through conflict:

| Label | Meaning | Relationship |
|-------|---------|--------------|
| **[P]** Positive | Ideal state | — |
| **[C]** Contrary | Opposite, tension | [P] ↔ [C] |
| **[CD]** Contradictory | Direct negation | [C] → [CD] |
| **[NN]** Negation of Negation | Perversion/false positive | [P] → [NN], [NN] → [P] |

Example (Truth):
- [P] Truth
- [C] Lie (but with hints of truth)
- [CD] Barefaced lie
- [NN] Self-deception (false truth that looks like [P])

**Arc implication:** A character doesn't just flip from positive to negative. They move through the schema: Truth → Lie → Barefaced Lie → Self-deception → Truth (earned). This is why flat arcs exist — a character may hold [P] while the world moves to [NN] around them.

**Progressive antagonism:** Scenes should escalate through the schema. Early scenes = Contrary [C] opposition. Crisis scenes = Contradictory [CD] or Negation of Negation [NN].

---

## 5. Values and Character Arc

> *Good_Writing.md:282-293, 332-346*

> **Character Arc:** The finest writing reveals true character and depicts arcs — changes in inner nature — over the course of the story, for better or worse.

Two forces in tension:
- **Structure's job:** Create progressively increasing pressures (value turns)
- **Character's job:** Make credible choices under that pressure

The character arc is how a character's *own* value changes as the external structure turns the screws. The two tracks are recorded separately — the story's charges on story containers, the character's on the character and their beats — and neither is computed from the other. The pressure is real even when the value word is not shared.

### McKee's arc types (implied, not named)
- **Positive arc:** Character moves from negative to positive value (disillusionment → hope)
- **Negative arc:** Character moves from positive to negative (trust → betrayal)
- **Flat arc:** Character holds [P] value while world changes around them (flat protagonist is still an arc — it's the world that arcs)
- **Ironic arc:** Character achieves the goal but loses the value (wins freedom but loses meaning)

### Arc and the Gap
> *Good_Writing.md:400-416*

Each arc beat should open a **gap** between what the character expects and what the world delivers. The beat is NOT just "what happens" — it's "the character acts, meets unexpected reaction, and must choose under pressure."

This means arc beats encode:
1. **The action** (what the character tries)
2. **The gap** (unexpected reaction from world/self/relationships)
3. **The choice** (what they do next — reveals true character)
4. **The value shift** (how the value charge changes as a result)

---

## 6. Values and the Controlling Idea

> *Good_Writing.md:302-308, 310-314*

> **Controlling Idea:** Expressed in a single sentence describing *how and why life changes* from beginning to end.

The controlling idea is the **story-level value statement** — the story track, read from `story_value_at_open` and `story_value_at_close`:

- **Idealistic (up-ending):** "Value moves from negative to positive" → hope, optimism
- **Pessimistic (down-ending):** "Value moves from positive to negative" → loss, cynicism
- **Ironic (up/down):** "Value appears to move one way but actually moves the other" → complexity

It is a statement about the *story's* value. A character's arc is a separate track and does not have to agree with it.

The controlling idea emerges FROM the arc — it's not imposed before writing. The LLM can propose one after analyzing the climaxes, but it should be treated as a hypothesis, not a constraint.

---

## 7. Practical Rules for the LLM

When reasoning about values in features:

1. **Values must be chargeable.** If you can't imagine it flipping positive↔negative within a scene, it's not a value — it's a trait.

2. **Genre suggests, doesn't dictate.** A thriller might favor justice/injustice, but the specific value should emerge from the story's world and characters.

3. **Values escalate through the P/C/CD/NN schema.** Don't jump from [P] to [CD] — move through [C] first. Save [NN] for crisis/climax.

4. **Character arc = structural value turned inward.** When designing an arc beat, ask: what value is at stake for THIS character, how is it charged, and how does this beat change that charge? Answer the last two on the character's own value, which need not be the story's.

5. **Progressive size, one word per track.** The story's value word is stated once on the project and inherited downward — a scene does not get to name a different one. What grows down the hierarchy is the *size* of the reversal. A character, by contrast, states their own value word once, and it may differ from the story's: that is the second track, recorded independently, not a mismatch.

6. **The controlling idea is the arc's thesis.** After arc beats are designed, the controlling idea should be derivable from the value journey — not the other way around.

---

## 8. Two Tracks — Story Value and Character Value

There are **two** value tracks, and they are not the same thing.

| Track | Whose value it is | Stated once, on | Inherited by |
|-------|-------------------|-----------------|-------------|
| **Story value** | the thematic exploration the whole work is about | `project` | act, sequence, scene |
| **Character value** | what one person's arc explores | `character` | their arc beats |

Kael's `Freedom` inside a story about `Trust` is not a contradiction and not a
sub-theme. It is the second track: a protagonist's arc may run on a different
value from the story's, and that is often the point. The two are recorded
independently, and how they relate is a judgement made while writing, not a
fact stored in the data.

**The vocabulary is shared.** Same value words, same charge words
(`positive`, `negative`, `mixed`, `ironic`) on both tracks. The field name says
whose arc it is. There is no separate naming scheme for character values, and
nothing in either name implies one track is derived from the other.

### The field table

| scope | value word | charge | reading | curve |
|---|---|---|---|---|
| `project` | `story_value` | `story_value_at_open` / `_close` | — | — |
| `act` / `sequence` | *inherited* | `value_at_open` / `_close` | — | — |
| `scene` | *inherited* | `value_at_open` / `_close` | `shift` | `y` |
| `character` | `character_value` | `character_value_at_open` / `_close` | — | — |
| `arc_beat` | *inherited* | `character_value_at_open` / `_close` | `shift` | `y` |

Two rules hold this together:

1. **The value word is stated once per track and inherited downward.** There is
   no value word field on act, sequence, scene or arc beat. Every one of them
   charges the word its track already declared.
2. **The charge is per-entity, everywhere, on both tracks.** `value_at_open` /
   `_close`, `shift` and `y` are never inherited. A charge is a property of
   *this* scene, *this* beat — that is where the story turns, so it is recorded
   where the turn happens.

`shift` and `y` are unprefixed on both tracks on purpose: the prefix is only
needed where the ambiguity lives, which is the *identity* of the value. Each
entity carries exactly one track, so its shift and charge have one possible
owner.

The character carries no `shift` / `y` — it is the promise (where the arc must
start and end), not a sampled point. The beats are the path.

### A scene cannot introduce a second theme

If a scene seems to turn on a value word that is not the story's, that word
belongs somewhere else:

- it is a **character value** — record it on that character and their beats, and
  charge the story value in the scene
- it is a **plot concern** — a genuine subplot with its own theme belongs to
  `plot`, not to a value field

Do not open a new value in a scene. There is no field for it, by design: a
second theme in a story-container field is almost always a character's value
recorded in the wrong place.

### What `shift` and `y` add on top of the charge pair

Three different kinds of data, all kept:

| | what it is | example |
|---|---|---|
| `value_at_open` / `_close` | a measurement on the charge scale | `positive → negative` |
| `y` | the ending charge — the point a curve passes through | `-0.3` |
| `shift` | the dramaturgical reading, in the story's language | `suspicious doubt → active defiance` |

The charge pair is instrumentation; `shift` is the finding, and the one a
writer actually uses. `y` is the only one of the three that can be interpolated,
which is why the graph plots it.

---

## 9. The Dialectical Progression

> *Good_Writing.md:310-314*

Story as argument between positive Idea and negative Counter-Idea. Each scene/sequence/act is a "vote" for one side. The climax resolves the debate.

For character arcs, this means:
- **Protagonist** embodies one side of the value debate
- **Antagonist** embodies the other
- **Arc beats** are the "turns" in the argument — each beat is a scene where the character's value position is tested
- **Crisis** = the strongest counter-argument (when the opposite value seems most true)
- **Climax** = the final choice that resolves the debate

This is why arc beats can't just be "events" — they're **dialectical turns** in the character's internal argument about what's true, what matters, what they believe.

---

## 10. Encoding the Dialectical Turn (for implementation)

Each arc beat should encode **four elements** without becoming verbose:

### The Four Elements

| Element | What it captures | Example (this character's own value: Trust → Betrayal) |
|---------|------------------|----------------------------|
| **Action** | What the character tries (their move in the argument) | "Mara asks Oak directly about the discrepancy" |
| **Gap** | Unexpected reaction that disconfirms their expectation | "He lies smoothly — and she realizes he's been lying for months" |
| **Choice** | What they do next (reveals true character under pressure) | "She nods, says nothing, files the report herself" |
| **Value shift** | How *this character's* value charge changes as a result | Trust → Doubt (positive → mixed) |

### The Gap is the Core

> *Good_Writing.md:400-416*

The gap between expectation and result IS the story substance. Without it, the beat is just activity. With it, the beat is **true action** — a collision between subjective belief and objective reality.

**Practical rule:** If you can't state the gap in one sentence, the beat isn't designed yet.

### Nuanced Value Escalation

Values don't just flip positive↔negative. They progress through McKee's schema:

```
[P]ositive → [C]ontrary → [CD]ontradictory → [NN]egation-of-negation → [P]ositive (earned)
```

A **subtle scene** might shift value one step: [P] → [C] (trust → doubt)
A **dramatic scene** might shift two steps: [C] → [CD] (doubt → betrayal confirmed)
A **crisis/climax** might hit [NN]: the character gets what they wanted but it's a hollow perversion of the value (false trust restored)

**Arc design rule:** Don't force every beat to be a dramatic reversal. Most beats should be [C] shifts (nuance). Reserve [CD] and [NN] for sequence/act climaxes. The **overall arc** is the sum of all beats, not each individually.

### Keeping it Non-Verbose

The four elements should fit in **3-5 short lines**:

```markdown
- Action: Mara asks Oak directly about the discrepancy.
  Gap: He lies smoothly — she realizes he's been lying for months.
  Choice: She nods, says nothing, files the report herself.
  Shift: Trust → Doubt (positive → mixed)
```

Not:
```markdown
- In this scene, Mara decides that she needs to confront Oak about the files she found. She goes to his office and asks him directly. He reacts by lying smoothly. She realizes he's been lying. She chooses not to confront him further and instead files the report herself. This shifts her trust to doubt.
```

**The principle:** Facts only, no narration. The LLM reasons from the four facts; it doesn't need them explained.

---

## 11. Theory → File Schema Bridge

> This section maps McKee's theory to the actual frontmatter fields the LLM fills in when creating arc beats.

### Frontmatter Fields

Each beat file (`arcs/{character}/{beat_id}.md`) uses these fields:

| Field | Theory Source | What to Write |
|-------|---------------|---------------|
| `id` | Beat identifier | Numeric (`"1"`, `"2"`) — order within character |
| `character` | Character whose arc this belongs to | Character slug (must exist) |
| `scene` | The scene where this beat occurs | Scene slug (must exist) |
| `label` | Beat name | Short human description (`"First Doubt"`) |
| `action` | What the character tries | One sentence, present tense |
| `gap` | Expectation vs reality | One sentence, the surprise |
| `choice` | True character revealed | One sentence, what they do next |
| `shift` | Value charge change | Format: `"positive → mixed"` or `"negative → ironic"` |
| `character_value_at_open` | Charge entering this beat | `positive`, `negative`, `mixed`, `ironic` |
| `character_value_at_close` | Charge leaving this beat | `positive`, `negative`, `mixed`, `ironic` |
| `y` | **Ending** charge after the shift, −1.0 to +1.0 | Derived from `shift`; see below |
| `order` | Position in arc sequence | 1, 2, 3... (explicit, not derived) |
| `is_crisis` | Major reversal marker | `true` only for sequence/act climax beats |
| `is_climax` | Arc completion marker | `true` only for the final beat of the arc |

### Character Arc Fields

On the character file, these fields describe the overall arc:

| Field | Theory Source | What to Write |
|-------|---------------|---------------|
| `arc_type` | Arc trajectory type | `positive`, `negative`, `flat`, `ironic`, or `absent` |
| `character_value` | The value this character's arc explores | Same vocabulary as the story's value, or a different one. **May differ from the story's** — that is the second track, not an error |
| `character_value_at_open` | Starting charge — the promise | `positive`, `negative`, `mixed`, `ironic` |
| `character_value_at_close` | Ending charge — the promise | `positive`, `negative`, `mixed`, `ironic` |
| `arc_complete` | Whether arc is finished | `true` when all beats are designed |

The character's open/close are the **promise** — where this journey must start
and end. The beats are the **path**, and the path is allowed to wobble, because
the wobble is the drama.

### Arc Type Decision Logic

How to choose `arc_type`:

| Type | Pattern | Example |
|------|---------|---------|
| `positive` | Y ends higher than it starts | Trust → Betrayal → Earned Trust (earned positive) |
| `negative` | Y ends lower than it starts | Trust → Doubt → Betrayal confirmed |
| `flat` | Y stays roughly the same | World changes around them, they hold [P] |
| `ironic` | Y appears to go one way but the true charge goes the other | Gains freedom but loses meaning (surface +1.0, true -0.5) |
| `absent` | Character has no arc | Minor characters, cameos — they exist but don't change |

**Rule:** Not every character needs an arc. Use `absent` for characters who don't change. The index will still track scenes they appear in.

### Beat-to-Scene Relationship

A beat happens WITHIN a scene. The `scene` field links to the scene where this beat occurs. A scene can have multiple beats (different characters, different arcs crossing). A character's beats span multiple scenes across the story.

```
Scene: central-room-day
├── Beat 1 (Elena) — "The Choice"
└── Beat 2 (Marcus) — "The Witness"

Scene: central-room-night
├── Beat 2 (Elena) — "The Haunting"
└── Beat 3 (Kael) — "The Discovery"
```

### Complete Beat File Example

```markdown
---
id: "1"
character: dr-elena-voss
scene: central-room-day
label: "The Choice"
action: "Elena makes the call — save the minds, abandon the bodies."
gap: "She expects relief. She gets silence."
choice: "She does not explain herself. She signs the order."
shift: "positive → negative"
character_value_at_open: positive
character_value_at_close: negative
y: -0.8
order: 1
is_crisis: false
is_climax: false
---

## Action

Elena stands before the console. She has minutes. She chooses the safe path: save the four hundred inside, let the four hundred outside die.

## Gap

She expected salvation to feel like strength. It feels like murder. The math was simple; the aftermath is not.

## Choice

She does not call Marcus. She signs alone. She watches the vitals flatline. She does not look away.

## Shift

From "I saved them" to "I chose who dies." Certainty becomes a wall.

## Development Log

Beat designed during arc planning. Elena's arc is negative. First beat sets up the value journey.
```

### Deriving Y from the Shift Line

The `shift` line is linguistic. The `y` field is numeric. The LLM derives `y` from the shift using this logic:

| Shift Pattern | Starting Y | Ending Y | How to derive |
|---------------|------------|----------|---------------|
| `positive → mixed` | +1.0 | +0.3 to 0.0 | Start high, move slightly negative |
| `mixed → negative` | +0.3 | -0.5 to -0.8 | Cross zero into negative |
| `positive → negative` | +1.0 | -0.8, or -1.0 at crisis/climax | Full reversal — reserve the bottom of the scale for the crisis |
| `negative → ironic` | -0.5 | *true* -0.5, surface +0.5 | Ironic: store true charge, mark shift as ironic |
| `flat arc` | +0.8 | +0.7 | Small movement, character holds [P] |

**The `y` value is the ENDING charge after this shift.** If the shift is
`positive → mixed` and the character started at +1.0, the `y` is where they land
(e.g. `+0.3`) — not the start.

**Sign convention:** `y` is signed like the charge word. `positive` is above
zero, `negative` below, `mixed` and `ironic` in between. A `shift` of
`positive → negative` with `y: +0.3` is a contradiction, not a nuance.

**The same rule holds on a scene.** A scene's `y` is its ending charge after the
scene's own turn, signed the same way, and it is the point the story-value curve
passes through. The story side of a scene and the character side of a beat are
read the same way.

**A missing `y` is not `0.0`.** `0.0` is a charge a writer can choose; a scene
or beat with no recorded turn has no `y`, and the graph draws no point for it.
Never write `y: 0.0` to fill the gap.

### Arc Design Checklist

Before writing beat files, the LLM should:

1. **Choose which characters get arcs** — protagonist always, antagonist usually, supporting if they change, minor/cameo = `absent`
2. **Determine arc_type** — look at the character's journey across all scenes
3. **Identify `character_value`** — what value is at stake for THIS character. It may be a different word from the story's; that is the second track, not a problem to solve
4. **Map beats to scenes** — which scenes show this character changing?
5. **Check P/C/CD/NN escalation** — beats should escalate through the schema, not jump
6. **Verify crisis/climax placement** — crisis should be a major reversal, climax should resolve the arc

After writing beats, verify:
- [ ] Beat count matches `arc_beat_count` on character
- [ ] Every beat records its own `character_value_at_open` / `_close` — the charge pair is per-beat, never inherited
- [ ] Every beat's `y` is the **ending** charge, and its sign matches its `shift`
- [ ] Crisis beats have `is_crisis: true`
- [ ] Climax beat has `is_climax: true`
- [ ] Y values follow a gradual trend (not too jagged, not too flat)

**Do not add a continuity check the beats did not earn.** Do not require
`character_value_at_open` to equal the first beat's opening charge, or
`character_value_at_close` to equal the last beat's ending `y`. A value can move
*consequentially*, with no turn on screen — a scene the character is absent from
can shift what they believe. When the beats and the promise disagree, that is
information: it means the design needs adjusting, sometimes by rewriting scenes,
sometimes by reshaping the arc itself. It is a judgement made while writing, not
a mismatch a tool reports.

---

## 12. Numeric Value Encoding (for graphs and analysis)

### The Axes

- **X-axis** = narrative progression. Use normalized `0.0 → 1.0` (story start → story end) so arcs are comparable across different-length stories.
- **Y-axis** = value charge, mapped to a `-1.0 → +1.0` scale.

### The Mapping

| Charge String | Numeric | McKee Schema |
|---------------|---------|--------------|
| `positive` | `+1.0` | [P] |
| `mixed` (leaning positive) | `+0.5` | [C] positive side |
| `mixed` (neutral) | `0.0` | [C] midpoint |
| `mixed` (leaning negative) | `-0.5` | [C] negative side |
| `negative` | `-1.0` | [CD] |
| `ironic` (surface) | *opposite of true* | [NN] — use true charge + irony flag |

For irony: store the **true** charge numerically, and say so in the `shift` line
(`"negative → ironic"`). There is no `ironic: true` field — irony is carried by
the charge word and the shift line, and `y` holds the true charge. This keeps the
graph honest to the character's real journey.

### Why This Works

Each beat becomes a point `(x, y)` where:
- `x` = narrative position (0.0 to 1.0, by scene order)
- `y` = that beat's **ending** value charge (-1.0 to +1.0)

Connecting the points gives you the **arc wave**. Scenes plot the same way on the
same scale, in story order — one engine, two sources.

### Decoding Math Back to Language

| Math Property | Story Meaning |
|---------------|---------------|
| **Slope** (Δy/Δx) | Pacing of change. Steep = sudden revelation. Flat = stasis. |
| **Inflection point** (curvature sign change) | Turning point. Direction of change reverses. |
| **Local max/min** | False hope / darkest moment. Temporary peak or valley before reversal. |
| **Curvature magnitude** (second derivative) | Acceleration of conflict. High = pressure building fast. |
| **Area under curve** | Cumulative value experience. Total "charge" the character carries. |
| **Amplitude** (max - min) | Arc magnitude. How far the value swings. |

### Preventing Over-Drama

This actually **solves** your concern. On a numeric scale:
- A subtle beat shifts `+0.2` (trust → slight doubt)
- A moderate beat shifts `-0.5` (doubt → confirmed lie)
- A crisis beat shifts `-0.8` (confirmation → total betrayal)

Most beats SHOULD be small movements. The curve should look like a gradual trend with occasional steep drops — not a sawtooth. If the curve is too jagged, the arc is melodramatic. If it's too flat, nothing's happening.

**Dashboard check:** If no beat has |Δy| > 0.3, the arc lacks turning points. If all beats have |Δy| > 0.7, the arc is hysterical.

### Where the Numbers Live

The beat stores both the linguistic description **and** the numeric encoding:

```markdown
- Action: Mara asks Oak directly about the discrepancy.
  Gap: He lies smoothly — she realizes he's been lying for months.
  Choice: She nods, says nothing, files the report herself.
  Shift: Trust → Doubt (positive → mixed)
  Y: +0.3
```

The LLM populates `y` at authoring time, derived from the shift line. The dashboard reads `y` directly to plot the curve. No separate derivation pipeline — the LLM does the translation once, the number is stored alongside the language.

### The Verification Loop

1. LLM designs the beat linguistically (action/gap/choice/shift)
2. LLM derives `y` from the shift — the **ending** charge, signed like the charge word (`positive → mixed` leaning positive = `+0.3`)
3. Dashboard plots the curve from all beats' `y` values
4. Human/LLM checks the curve shape: too jagged? too flat? adjust beats
5. The curve doesn't replace judgment — it **surfaces** problems the language hides

This is the encoding as **lens**, not replacement.

The story track plots through the same loop, from scene `y` values in story
order. Two tracks, two lines, one engine — and they are read separately, because
a character turning on `Freedom` is not the story turning on `Trust`.
