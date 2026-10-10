# Value Tracking and Character Arcs

Derived from discussion of `docs/research/McKee_Story/Good_Writing.md`.
Answers: how do plot values, value shifts, and character arcs relate in data?

---

## 1. There is one value pool, not two

Line 100 gives the **rule**:

> STORY VALUES are universal qualities of human experience that can shift
> between positive and negative states from moment to moment.

The lists in the source are illustrations of that rule, not an enumeration —
line 102 introduces its list as "**Examples** of Story Values", and line 682
gives a **different** set of 14 (`Truth, Love, Might Makes Right, Consciousness,
Wealth, Communication, Success, Intelligence, Courage, Liberty, Sanctioned Sex,
Loyalty, Maturity, Honesty`). Two lists, partial overlap: the pool is open.

```
alive/dead, love/hate, freedom/slavery, truth/lie, courage/cowardice,
loyalty/betrayal, wisdom/stupidity, strength/weakness, excitement/boredom,
hope/despair
```

**Admission test:** does it have two poles with a meaningful charge flip?
`wealth/poverty` qualifies. `coffee/temperature` does not.

There is no separate "story values" set and no separate "arc values" set.
`courage` and `love` sit on the same shelf. **What differs is `locus`** — set
per scene, from one question:

> Did this shift change what happened to the character, or who they are?

```yaml
- id: s19
  values:
    - {value: honesty, charge: [negative → positive], locus: external}
    - {value: wisdom,  charge: [negative → positive], locus: internal}
    - {value: loyalty, charge: [negative → negative], locus: external}
```

`locus` is a property of the **shift**, not of the value. No formula produces
it. The same value can be tagged either way depending on the scene — `honesty`
in Dana's story is external at s8 (what it buys her changed) and would be
internal in a story about a character who has stopped being able to lie at all.

| locus | moves | drawn from the pool, tends to |
| --- | --- | --- |
| `plot` | the character's circumstance | love, freedom, truth, loyalty, alive/dead |
| `character` | the character's nature | courage, wisdom, strength |

**These are the only two values.** There is no third state and no "neither" —
`locus` is binary.

But the assignment is **per shift, not per value**, and that is the part worth
stating: `truth/lie`, `loyalty/betrayal` and `hope/despair` land either way
depending on the scene, with no default. `honesty` in Dana's story is external
at s8 (what it buys her changed) and would be internal in a story about someone
who has stopped being able to lie at all.

A value that doesn't turn in a scene is not a third kind — it is a **held**
value, recorded by its unchanged charge:

```yaml
- {value: excitement, charge: [mixed → mixed], locus: external}  # context, not a turn
```

---

## 2. What is declared, what is derived

Three different answers, because the three are knowable at different times.

|  | when | how |
| --- | --- | --- |
| `story_values` | before writing | **declared** — line 153 requires it |
| `character_values` | before writing | **declared** — you already know your protagonist |
| `arc_values` | per scene | **determined by the scene** — not declared |
| `schema` (C/CD/NN) | before writing | **declared** — it is a general structure, not a prediction |

### 2.1 `story values` — declared

Line 153: "Compare the value charge at the beginning and end of the story."
That comparison is impossible without knowing which value to compare — so the
story-level values are declared up front, and scenes are tested against them.

```yaml
project:
  story values:               # plural — line 654, "a revolution IN VALUES"
    - value: loyalty
      story_value_at_open: positive
    - value: justice
      story_value_at_close: negative
```

**Why plural.** Line 654 is the definition of the climax — the one place the
source uses the plural, and the place that matters most: "A revolution **in
values** from positive to negative or negative to positive." Line 153's singular
is an instruction to *measure*, singular because you compare them one at a time.
A definition should outweigh a measurement instruction.

**The gate is one, not all.** Line 151/155 require that the situation change
absolutely and irreversibly. That is satisfied when **at least one** declared
value swings. There is no requirement that every declared value swings — and
that distinction is what stops a second declaration from becoming padding.

| | status |
|---|---|
| declared, and swings irreversibly | the story's spine |
| declared, and ends flat | permitted — but a signal about the writing, not a schema error |
| more values swinging | **better writing, not a schema constraint** |

That last row is the honest reading. A climax that reverses several values is
stronger than one that reverses a single value — but the theory asks for the
revolution, not for a count.

**Direction of travel:**

|  | wrong | correct |
| --- | --- | --- |
| story values | derived from scenes | declared first |
| scenes | produce the value | service / test against them |

This is what makes the theory's own scene check work (line 129, "no scene that
doesn't turn"): a scene that leaves every dominant value flat is a broken scene.

### 2.2 `character_values` — declared

You know who your protagonist is before you write a word, so the internal
values are a decision, not a discovery.

```yaml
project:
  character_values: [courage, wisdom, strength]   # the protagonist's nature
```

### 2.3 `external_values` — determined by the scene

**Not declared, and not derivable in advance.** A scene's external values come
from what the scene is about; they are decided when the scene is written.

```yaml
- id: s8
  values:
    - {value: honesty, charge: [positive → negative], locus: external}
```

There is no project-level list of external values to keep in sync, because
there is nothing to sync — they belong to the scene, not to the project.

### 2.4 The value schema — the opposition, not the external values

The **value schema** (lines 666-682) is a separate thing and is often confused
with the above. It describes **the forces of antagonism in general** (line 662),
in the P / C / CD / NN form:

```yaml
schema:
  loyalty:
    C:  complicity                  # contrary — opposite, not absolute
    CD: betrayal                    # contradictory — direct negation
    NN: fanatic loyalty             # negation of negation — the perversion
```

Two things it is **not**:

- It does not enumerate a scene's external values. A schema names the
  opposition to one value; a scene may carry external values the schema never
  mentioned.
- It does not describe a character. It describes the forces. Line 664 gives it
  an ordering: "moving through Contrary, Contradictory, and Negation of
  Negation in antagonism."

So the schema constrains *the opposition's escalation*, and nothing else.

## 3. How many values does a plot have?

**Multiple.** Line 119: a scene turns the condition "on **at least one value**
with perceptible significance." One is legal, many is legal.

`mixed` as a charge state (lines 124-125) only exists if more than one value is
in play at once — a single value cannot be mixed.

**Discipline:** multiple values in, at least one flipped out. The unchanged
ones are context.

---

## 4. Storage — one table, tagged

Not a plot value store plus an arc value store. One record set:

```yaml
value_charge:
  value: courage
  charge: [positive, negative]
  character: protagonist
  locus: internal
  scene_id: s12
```

The arc is a **query** over these records. Two stores would make the invariant
"arc and plot can never disagree" unenforceable.

---

## 5. Is the arc tracked separately per value?

**No — per-value slices are diagnostics, not the arc.**

```yaml
honesty:   positive → negative → positive   # returns to start
loyalty:   positive → negative → negative   # degrades
courage:   negative → mixed → positive      # grows
```

Read alone, only `loyalty` looks like an arc — but it is a *dominant* value,
and reading it alone tells you nothing about who Dana became.

The arc is the row *above* them — what all values add up to:

```yaml
character_arc:
  character: Dana
  meaning: integrity held, but its price rose from a lost partner,
    to a lost unit, to a lost life
```

In practice: **filter by `locus: internal` and read across the story.** That
slice is the arc. Per-value slices remain useful — they check coherence, and
catch a character who moved on one axis while static on all others (a twitch,
not an arc).

**Exception:** when the whole story turns on one axis and the others are
stable, that value's trajectory *is* the arc. Not the default — do not build
for it up front.

---

## 6. Worked example — three scenes

Project declaration:

```yaml
project:
  story values:                # one swings irreversibly; the other may not
    - {value: loyalty, opening_charge: positive}
    - {value: honesty, opening_charge: positive}

  character_values: [courage, wisdom, strength]      # declared
```

Character: **Dana**, a police officer. Starting state: principled, refuses to
bend the rules.

### Scene 1 — the bribe

Partner offers a shortcut. She refuses; a colleague takes it.

```yaml
- id: s1
  values:
    - {value: honesty, charge: [positive → positive], locus: external}  # held
    - {value: loyalty, charge: [positive → negative], locus: external}  # turn
  reveals: she will not compromise for the job
```

### Scene 8 — the evidence

The shortcut gets a child killed. Dana holds the proof exposing her own unit.

```yaml
- id: s8
  values:
    - {value: honesty,    charge: [positive → negative], locus: external}  # turn
    - {value: complicity, charge: [negative → positive], locus: external}  # turn, C
    - {value: loyalty,    charge: [negative → negative], locus: external}  # held
    - {value: courage,    charge: [negative → mixed],    locus: internal}  # turn
  reveals: still honest — but the cost is now destroying her
```

Note `honesty` dips **negative** here. Her integrity never changed; what changed
is what integrity buys her. This is how a "good" arc moves without the person
becoming someone else.

`complicity` arrives at s8 as the schema's `C` — the partner took the shortcut,
and the unit's willingness to look the other way is what put the child at risk.
Nobody chose it in advance; it is the opposition `loyalty` generates.

### Scene 19 — the confession

She testifies. Loses the unit, the badge, her partner.

```yaml
- id: s19
  values:
    - {value: honesty,    charge: [negative → positive], locus: external}  # turn
    - {value: loyalty,    charge: [negative → negative], locus: external}  # held
    - {value: betrayal,   charge: [positive → negative], locus: external}  # turn, CD
    - {value: wisdom,     charge: [negative → positive], locus: internal}  # turn
    - {value: strength,   charge: [mixed → positive],    locus: internal}  # turn
  reveals: integrity was never conditional — it cost her everything
```

`betrayal` is also scene-local. Whatever opposition s19 needed, it was chosen
at s19 — which is what makes it a climax rather than another turn.

### The arc

Read the `locus: internal` rows — s8 `courage`, s19 `wisdom`, s19 `strength`:

```yaml
character_arc:
  character: Dana
  direction: for better (integrity confirmed, at full cost)
  depth_reached: maximum pressure

  evidence:   # structured, queryable — the internal slice
    - {scene: s8,  value: courage,  change: negative → mixed}
    - {scene: s19, value: wisdom,   change: negative → positive}
    - {scene: s19, value: strength, change: mixed → positive}

  meaning:    # prose, not graphable
    integrity confirmed at full cost
```

**Two lessons visible in the data:**

1. `honesty` ends where it began (positive → positive), yet Dana changed
   completely. **Circumstance-level charge and nature-level charge are
   different measurements** — do not read the arc off the dominant value.
2. `loyalty` is a dominant value and does the irreversible swing — but on its
   own it describes *what happened to her*, not *who she became*.

---

## 7. Graph representation

**An arc is not a node and not an edge.** It has no position — "changes in
inner nature" is a reading across many shifts.

But it *is* representable in a graph, as a derived path over stored edges:

```yaml
nodes: [s1, s8, s19, Dana]
edges:
  - {from: s1, to: s8,  value: honesty, charge: positive → negative, locus: external}
  - {from: s8, to: s19, value: wisdom,  charge: negative → positive, locus: internal}
```

The arc is the path over Dana's `locus: internal` edges. Nothing extra is
stored.

### What does not graph

| | graphable |
|---|---|
| value shifts | yes — edges, first class |
| the arc | yes — derived path over those edges |
| "integrity confirmed at full cost" | **no** — prose |

The *measurement* graphifies. The *meaning* does not. Hence a `character_arc`
entity carrying `evidence` (structured) plus `meaning` (free text) — two
fields, one entity.

**Avoid:** making `character_arc` a node with edges to scenes. It duplicates
the value edges, and the two copies will drift apart.

---

## 8. Multiple characters

`value_charge` already carries `character`, so tracking is one record set with a
filter. What moves is **where `character_values` is declared** — per character, not
per project. `story values` stay project-level.

```yaml
characters:
  Dana:
    character_values: [courage, wisdom, strength]
  partner:
    character_values: [loyalty, complicity]
```

### 8.1 Who gets an arc

**The test: does the character hold a dominant value?**

The protagonist arcs because they carry one — line 153 requires
their charge to swing, irreversibly. Anyone else arcs **iff** they hold that
same value in opposition.

```yaml
arc_roster:
  Dana:    full   # holds loyalty: positive → negative, irreversible
  partner: full   # holds loyalty: negative → positive (NN — fanatic loyalty)
  the_unit: flat  # holds loyalty as an institution, never shifts
```

Two lines decide the roster:

- **Line 740:** "The protagonist creates the rest of the cast... Other
  characters exist primarily in relation to the protagonist, highlighting
  dimensions of the protagonist's complex nature." A supporting character
  exists to *press* the protagonist. If pressing them changes nothing, the
  character is redundant (line 451: "avoid redundant characters").
- **Line 278:** "**Principals** must have hidden dimensions." Principals only —
  not everyone in the cast.

| role | arc? | why |
|---|---|---|
| protagonist | yes | holds a dominant value, must swing |
| principal mirroring it in opposition | yes | the dialectic (line 314) — the NN case |
| functional character | no | exists to press someone else |

**The partner is the case to note:** same value as Dana, opposite direction.
Two arcs on one value in opposing charge — that *is* the story's argument
expressed as data.

**The unit is the counter-case:** an institution holding loyalty as a property,
never shifting. `flat` is correct data. Do not fabricate an arc for it.

**Failure mode:** giving every named character an arc. Then you have N shallow
arcs, no dialectic (nothing opposes anything), and the protagonist's arc drowns
— because it was only ever meaningful as the thing being pushed against.

### 8.2 Multi-character scenes

A scene records one row per tracked character. The scene's turn requirement
(line 129) is satisfied if **any** tracked character turned:

```yaml
- id: s8
  values:
    - {character: Dana,    value: honesty, charge: [positive → negative], locus: external}
    - {character: Dana,    value: courage, charge: [negative → mixed],    locus: internal}
    - {character: partner, value: loyalty, charge: [negative → positive], locus: external}  # NN
```

**The trap:** giving each character their own value pool. Internal and external
values for one character come from the same pool (§1) — splitting them per
character duplicates the pool and breaks cross-character comparison, which is
the whole point of the NN case above.

---

## 9. Multiple protagonists

Multi-protagonist is the **miniplot** case (line 178: "Multi-Protagonists: focus
on multiple characters"), and it is the one place a second project-level field
appears.

### 9.1 Several spines, one dominant value set

The *spine* does not multiply into a hierarchy. Co-protagonists share the
dominant value set (§2.1) and oppose each other within it.

```yaml
project:
  story values:
    - {value: loyalty}            # both leads hold it, in opposite charge
  co_protagonists:
    - {name: Dana,    role: lead, character_values: [courage, wisdom]}
    - {name: partner, role: co,   character_values: [complicity, loyalty]}
```

What *does* multiply is the **spine** — line 468 defines it as "the energy of
the protagonist's desire," and that definition has **no variants**. Every spine
has the same shape; only the content differs. Whether two spines oppose, align,
or ignore each other is read off the desires themselves; it is not a field.

```yaml
protagonists:
  Dana:
    spine:
      conscious_desire: expose the unit
      unconscious_desire: keep her place in it   # optional (line 472)
  partner:
    spine:
      conscious_desire: protect the unit
      unconscious_desire: be seen as loyal
```

### 9.2 The test

**Both spines must be load-bearing at the climax.** If one could be deleted and
the climax still works, that character is not a co-protagonist — they are a
principal (§8.1) and belong in `arc_roster`, not in `co_protagonists`.

A common near-miss: a partner who confesses at the climax because the plot needs
a confession, but whose own spine is never resolved. They get a scene, not an
arc.

| symptom | real category |
|---|---|
| spine resolved at the climax, opposed | co-protagonist |
| spine partly resolved, presses the lead | principal (§8.1) |
| spine never resolved | functional (§8.1 `flat`) |

### 9.3 Cost

A second protagonist earns its keep only if its spine generates conflict the
first one's cannot. Miniplot pairs it with **internal conflict** (line 176) and
**open endings** (line 175) — multi-protagonist alone tends to sprawl, because
there are now two sets of scenes to fill and only one dominant value set to
justify them.

---

## 10. Peak terminology by level

The theory does not call every level's peak a "climax":

| rung | peak term | effect |
|---|---|---|
| scene | **turning point** | minor but significant change (value shift) |
| sequence | **climax** | moderate reversal |
| act | **climax** | major reversal |
| story | **story climax** | absolute, irreversible |

Sources: line 515 ("Ideal scene is a Turning Point"), line 543 ("Scene Impact:
minor but significant change. Sequence Climax = moderate reversal, Act Climax =
major reversal"), lines 151/155 (STORY CLIMAX).

There is no "world climax" and no world level — the ladder tops out at story.