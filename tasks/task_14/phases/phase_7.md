# Phase 7: Documentation & Skill References

## Prerequisite

All previous phases complete. Arc system is functional and tested.

## Files to modify

| File | Change |
|------|--------|
| `skills/story-loader/references/index-format.md` | Document arc entity schema and index structure |
| `skills/story-editor/references/continuity-checks.md` | Add arc edit patterns |
| `skills/story-theory/SKILL.md` | Link to values.md reference |

## Step-by-step

### Step 7.1 — Update `skills/story-loader/references/index-format.md`

Add to top-level structure section:

```yaml
arc_count: 2
```

Add after `act_count` in the `project` block.

Add new section after the `characters` section in the file:

```markdown
## Arcs

```yaml
arcs:
  - id: "1"
    character: character-slug
    scene: scene-slug
    label: "First Doubt"
    action: "What the character does"
    gap: "Expectation vs reality"
    choice: "The choice made"
    shift: "positive → mixed"
    y: 0.5
    order: 1
    is_crisis: false
    is_climax: false
    sections: [Action, Gap, Choice, Shift, Development Log]
```

**Notes:**
- Arc beats are stored in `arcs/{character}/{beat_id}.md` (nested by character)
- Beat files use numeric IDs (`1.md`, `2.md`) for ordering
- The `character` field is inferred from the folder if not in frontmatter
- The `y` field is the value charge at that beat (-1.0 to +1.0)

### Enriched Fields on Characters

```yaml
characters:
  - id: character-slug
    arc_type: positive | negative | flat | ironic | absent
    arc_value: Value at stake
    arc_value_at_open: positive | negative | mixed | ironic
    arc_value_at_close: positive | negative | mixed | ironic
    arc_complete: true | false
    arc_beat_count: 3
    arc_beats_list:
      - id: "1"
        label: "First Doubt"
        scene: scene-slug
        y: 0.5
        order: 1
        is_crisis: false
        is_climax: false
```

**Source:** `arc_beats_list` and `arc_beat_count` are derived by the index generator. `arc_type`, `arc_value`, `arc_value_at_open`, `arc_value_at_close`, `arc_complete` are frontmatter (LLM domain).

### Enriched Fields on Scenes

```yaml
scenes:
  - id: scene-slug
    arc_beats:
      - character: character-slug
        beat_id: "1"
        label: "First Doubt"
        y: 0.5
        is_crisis: false
        is_climax: false
```

**Source:** `arc_beats` is derived by reverse lookup from arc beat files.
```

### Step 7.2 — Update `skills/story-editor/references/continuity-checks.md`

Add new section:

```markdown
## Arc Beat Patterns

### Creating a new arc beat

Use `story_create` with `entity_type: "arc"`:
- `character` field is required (must match existing character slug)
- `scene` field is required (must match existing scene slug)
- `order` is explicit (1, 2, 3...) — determines beat sequence
- `y` is the value charge (-1.0 to +1.0)
- Path is auto-generated: `arcs/{character}/{beat_id}.md`

### Editing beat frontmatter

Use `story_edit` with `entity_type: "arc"`:
- Can update any field: `label`, `action`, `gap`, `choice`, `shift`, `y`, `order`
- Can mark `is_crisis: true` or `is_climax: true`

### Retrieving beat content

Use `story_retrieve` with `entity_type: "arc"`:
- Retrieve full beat: `sections: ["all"]`
- Retrieve specific section: `sections: ["Development Log"]`

### Adding to development log

Use `story_edit` with `entity_type: "arc"`:
- Key `"Development Log"` appends to the section body
- Log entries should include timestamps and reasoning

### Arc design principles

1. Each beat corresponds to a scene (beat.scene → scene.id)
2. Beats are ordered per character by `order` field
3. Y value tracks the character's value charge at that point
4. Crisis beats mark major reversals; climax beats mark arc completion
5. The arc_type on character summarizes the overall trajectory
```

### Step 7.3 — Enrich `skills/story-theory/references/values.md`

The current values.md covers McKee theory and numeric encoding well but misses the bridge between theory and the actual beat file format. Add a new section **before** the "Numeric Value Encoding" section (Section 11) that maps theory to the file schema.

Add this content after Section 10 ("Encoding the Dialectical Turn"):

```markdown
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
| `y` | Numeric value of the shift | -1.0 to +1.0, derived from Shift |
| `order` | Position in arc sequence | 1, 2, 3... (explicit, not derived) |
| `is_crisis` | Major reversal marker | `true` only for sequence/act climax beats |
| `is_climax` | Arc completion marker | `true` only for the final beat of the arc |

### Character Arc Fields

On the character file, these fields describe the overall arc:

| Field | Theory Source | What to Write |
|-------|---------------|---------------|
| `arc_type` | Arc trajectory type | `positive`, `negative`, `flat`, `ironic`, or `absent` |
| `arc_value` | The value that changes for this character | Same value word as the story's value, or a thematic variant |
| `arc_value_at_open` | Starting charge | `positive`, `negative`, `mixed`, `ironic` |
| `arc_value_at_close` | Ending charge | `positive`, `negative`, `mixed`, `ironic` |
| `arc_complete` | Whether arc is finished | `true` when all beats are designed |

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
y: 0.8
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
| `positive → negative` | +1.0 | -1.0 | Full reversal — only for crisis/climax |
| `negative → ironic` | -0.5 | *true* -0.5, surface +0.5 | Ironic: store true charge, mark shift as ironic |
| `flat arc` | +0.8 | +0.7 | Small movement, character holds [P] |

**Practical rule:** The `y` value is the ENDING charge after this beat's shift. If the shift is "positive → mixed" and the character started at +1.0, the `y` is where they land (e.g., +0.3).

### Arc Design Checklist

Before writing beat files, the LLM should:

1. **Choose which characters get arcs** — protagonist always, antagonist usually, supporting if they change, minor/cameo = `absent`
2. **Determine arc_type** — look at the character's journey across all scenes
3. **Identify arc_value** — what value is at stake for THIS character (may differ from story value)
4. **Map beats to scenes** — which scenes show this character changing?
5. **Check P/C/CD/NN escalation** — beats should escalate through the schema, not jump
6. **Verify crisis/climax placement** — crisis should be a major reversal, climax should resolve the arc

After writing beats, verify:
- [ ] Beat count matches `arc_beat_count` on character
- [ ] `arc_value_at_open` matches first beat's starting charge
- [ ] `arc_value_at_close` matches last beat's ending charge
- [ ] Crisis beats have `is_crisis: true`
- [ ] Climax beat has `is_climax: true`
- [ ] Y values follow a gradual trend (not too jagged, not too flat)
```

### Step 7.4 — Update `skills/story-theory/SKILL.md`

Add to the References section:

```markdown
- `references/values.md` — Value theory: arc types, value charges, value hierarchy, beat file schema
```

Add after existing references.

## Legacy cleanup

None — additive only.

## Naming convention check

- All field names match code exactly (`arc_beats_list`, `arc_beat_count`, `arc_type`, etc.)
- All entity types match (`arc`)
- All section names match (`Action`, `Gap`, `Choice`, `Shift`, `Development Log`)

## Final checklist

- [x] `index-format.md` documents arc entity schema
- [x] `index-format.md` documents character arc fields (`arc_beats_list`, `arc_type`, etc.)
- [x] `index-format.md` documents scene `arc_beats` reverse lookup
- [x] `index-format.md` documents `arc_count` on project
- [x] `continuity-checks.md` has arc beat creation pattern
- [x] `continuity-checks.md` has arc beat edit pattern
- [x] `continuity-checks.md` has arc beat retrieval pattern
- [x] `continuity-checks.md` has development log pattern
- [x] `continuity-checks.md` has arc design principles
- [x] `values.md` enriched with "Theory → File Schema Bridge" section
- [x] `values.md` has frontmatter field mapping table
- [x] `values.md` has character arc field mapping table
- [x] `values.md` has arc type decision logic
- [x] `values.md` has beat-to-scene relationship diagram
- [x] `values.md` has complete beat file example
- [x] `values.md` has Y-from-shift derivation table
- [x] `values.md` has arc design checklist
- [x] `story-theory/SKILL.md` links to `values.md`

---

## Phase 7 — Final Brief

**Completed:** All steps (7.1–7.4) implemented and verified.

**Files modified:**
- `skills/story-loader/references/index-format.md` — Added `arc_count` to project block, new Arcs section with beat schema, enriched character fields (including `shift` in `arc_beats_list`), scene `arc_beats` reverse lookup
- `skills/story-editor/references/continuity-checks.md` — Added Arc Beat Patterns section (create/edit/retrieve/log/principles)
- `skills/story-theory/references/values.md` — Added Section 11 "Theory → File Schema Bridge" with frontmatter table, character arc fields, arc type decision logic, beat-to-scene diagram, complete file example, Y-from-shift derivation, arc design checklist. Renumbered old Section 11 → 12.
- `skills/story-theory/SKILL.md` — Added `references/values.md` link

**Key fix:** `arc_beats_list` docs now correctly list `shift` as one of the 8 lightweight fields (matching `core/index.py` and `test_arcs.py`). Dashboard tooltips depend on it (`story-dashboard.html:2565, 3821, 3919`).
