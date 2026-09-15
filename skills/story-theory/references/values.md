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

Mckean theory does NOT require:
- Each level to use the same value word
- Act values to be "children" of story values
- Scene values to map 1:1 to act values

Mckean theory DOES require:
- Each level creates **progressively larger** value reversals
- The story climax delivers the **largest, irreversible** value change
- Values are **thematically related** across levels (not random)

**Conclusion for Q4 (hierarchy):** Values should be **independent at each level** but **thematically coherent** across levels. The LLM should be able to see the thematic link without enforcing a rigid parent-child relationship.

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

The character arc is NOT a separate thing from structural values — it's **how the character's internal value changes as external structure turns the screws**.

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

The controlling idea is the **story-level value statement**. It's built from the value charge at open and close:

- **Idealistic (up-ending):** "Value moves from negative to positive" → hope, optimism
- **Pessimistic (down-ending):** "Value moves from positive to negative" → loss, cynicism
- **Ironic (up/down):** "Value appears to move one way but actually moves the other" → complexity

The controlling idea emerges FROM the arc — it's not imposed before writing. The LLM can propose one after analyzing the climaxes, but it should be treated as a hypothesis, not a constraint.

---

## 7. Practical Rules for the LLM

When reasoning about values in features:

1. **Values must be chargeable.** If you can't imagine it flipping positive↔negative within a scene, it's not a value — it's a trait.

2. **Genre suggests, doesn't dictate.** A thriller might favor justice/injustice, but the specific value should emerge from the story's world and characters.

3. **Values escalate through the P/C/CD/NN schema.** Don't jump from [P] to [CD] — move through [C] first. Save [NN] for crisis/climax.

4. **Character arc = structural value turned inward.** When designing an arc beat, ask: what value is at stake for THIS character, how is it charged, and how does this beat change that charge?

5. **Independence with thematic coherence.** Act values don't need to match project values word-for-word, but they must rhyme. "Trust → Betrayal" at project level can play out as "Certainty → Doubt" in Act 1, "Loyalty → Treason" in Act 2, "Justice → Corruption" in Act 3.

6. **The controlling idea is the arc's thesis.** After arc beats are designed, the controlling idea should be derivable from the value journey — not the other way around.

---

## 8. Value Fields in Our System

Current state across entity types:

| Entity | Fields | Status |
|--------|--------|--------|
| Project | `value`, `value_at_open`, `value_at_close`, `structure_type`, `spine`, `controlling_idea` | ✅ Present |
| Act | `value`, `value_open`, `value_close` | ✅ Present |
| Sequence | `value`, `value_open`, `value_close` | ✅ Present |
| Scene | `value`, `value_open`, `value_close`, `conflict_levels`, `dramatic_role` | ✅ Present |
| Character | None | ❌ Missing |

What character arc needs (derived from theory):
- `arc_value` — the value that changes for this character
- `arc_value_at_open` / `arc_value_at_close` — starting/ending charge
- `arc_type` — positive/negative/flat/ironic
- Arc beats that encode: action → gap → choice → value shift

These are **not structural values** — they're the character's personal value journey that plays out within the structural pressure.

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

| Element | What it captures | Example (Trust → Betrayal) |
|---------|------------------|----------------------------|
| **Action** | What the character tries (their move in the argument) | "Mara asks Oak directly about the discrepancy" |
| **Gap** | Unexpected reaction that disconfirms their expectation | "He lies smoothly — and she realizes he's been lying for months" |
| **Choice** | What they do next (reveals true character under pressure) | "She nods, says nothing, files the report herself" |
| **Value shift** | How the value charge changes as a result | Trust → Doubt (positive → contrary) |

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
  Shift: Trust → Doubt (positive → contrary)
```

Not:
```markdown
- In this scene, Mara decides that she needs to confront Oak about the files she found. She goes to his office and asks him directly. He reacts by lying smoothly. She realizes he's been lying. She chooses not to confront him further and instead files the report herself. This shifts her trust to doubt.
```

**The principle:** Facts only, no narration. The LLM reasons from the four facts; it doesn't need them explained.

---

## 11. Numeric Value Encoding (for graphs and analysis)

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

For irony: store the **true** charge numerically, mark `ironic: true`. The dashboard can render irony as a dashed line or different color. This keeps the graph honest to the character's real journey.

### Why This Works

Each beat becomes a point `(x, y)` where:
- `x` = narrative position (0.0 to 1.0, by scene order)
- `y` = that beat's value charge (-1.0 to +1.0)

Connecting the points gives you the **arc wave**.

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
  Shift: Trust → Doubt (positive → contrary)
  Y: +0.3
```

The LLM populates `Y` at authoring time, derived from the Shift line. The dashboard reads `Y` directly to plot the curve. No separate derivation pipeline — the LLM does the translation once, the number is stored alongside the language.

### The Verification Loop

1. LLM designs the beat linguistically (Action/Gap/Choice/Shift)
2. LLM derives `Y` from the Shift (positive→contrary leaning negative = +0.3)
3. Dashboard plots the curve from all beats' `Y` values
4. Human/LLM checks the curve shape: too jagged? too flat? adjust beats
5. The curve doesn't replace judgment — it **surfaces** problems the language hides

This is the encoding as **lens**, not replacement.
