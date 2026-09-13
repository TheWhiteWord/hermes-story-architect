Good, the brief is thorough. Now let me read the theory file to ground the proposal in McKee's framework.Excellent — both files are fully read. Now I have everything I need to write a comprehensive proposal. Let me put it together.

---

# Design Proposal: Story Structure & Character Arc System

This proposal answers all seven questions from the brief, grounded in McKee's theory from `Good_Writing.md`, and constrained by the existing Hermes plugin architecture.

---

## 1. Core Principle: One Design Decision That Answers Most Questions

Before touching schemas, I want to name the organizing principle that resolves most of the brief's ambiguities:

**Structure lives in the project. Arc lives in the character. The scene is where they meet.**

This means:
- Act/sequence metadata belongs in `project.md` (or a thin `structure.md` per project)
- Arc data belongs in each `character.md`
- The *link* between them — "in this scene, this character faced this choice which advanced this arc beat" — lives as a lightweight annotation on the scene entry in the index

This avoids new entity folders (`acts/`, `arcs/`) entirely, avoids duplicating data, and fits the three-layer retrieval model perfectly.

---

## 2. Data Model

### 2a. Structure Type (Q1)

The user picks a structure type **once, at project creation**, stored in `project.md` frontmatter. It's a foundational commitment, not a discovery. McKee is clear: Classical, Miniplot, and Antiplot have fundamentally different expectations for endings, causality, protagonist posture, and arc resolution. A system that doesn't know the type can't validate against the right expectations.

The type is a **soft constraint**, not a hard one — the LLM uses it to frame feedback and set expectations, not to block edits.

```yaml
# project.md frontmatter (additions)
structure_type: Classical | Miniplot | Antiplot
controlling_idea: "string — how and why life changes, beginning to end"
inciting_incident_scene: 3          # scene number, null if unwritten
climax_scene: 82                    # scene number, null if unwritten
spine: "string — protagonist's core desire driving the whole story"
value_positive: "Freedom"           # the positive pole of the story's central value
value_negative: "Slavery"           # the negative pole
value_at_open: positive | negative | mixed
value_at_close: positive | negative | mixed | ironic
```

Structure type implications (stored in constants, not in the vault):
- **Classical**: closed ending required, active protagonist, external conflict dominant, single protagonist
- **Miniplot**: open ending expected, internal conflict dominant, passive protagonist or multi-protagonist permitted
- **Antiplot**: nonlinear time permitted, coincidence as valid plot engine, inconsistent realities expected

### 2b. Act and Sequence Structure (Q2)

Acts and sequences are **not new entity folders**. They are structured data inside `project.md`'s body section `## Structure`, loaded on demand via `story_retrieve`.

```yaml
# project.md frontmatter (additions to index entry)
act_count: 3
sequence_count: 8
structure_complete: false           # has user defined all acts/sequences?
```

Body section `## Structure` in `project.md` (loaded on demand):

```markdown
## Structure

### Acts

- id: act-1
  label: "The Setup"
  sequence_ids: [seq-1, seq-2]
  opening_value: positive
  closing_value: negative
  climax_scene: 28
  climax_description: "Mara discovers the files — trust collapses"
  notes: ""

- id: act-2
  label: "Confrontation"
  sequence_ids: [seq-3, seq-4, seq-5, seq-6]
  opening_value: negative
  closing_value: negative          # deeper negative in act 2
  climax_scene: 68
  climax_description: "The arrest — all options close"
  notes: ""

- id: act-3
  label: "Resolution"
  sequence_ids: [seq-7, seq-8]
  opening_value: negative
  closing_value: ironic
  climax_scene: 94
  climax_description: "She wins but at the cost of everything she protected"
  notes: ""

### Sequences

- id: seq-1
  act_id: act-1
  label: "The World Before"
  scene_range: [1, 12]             # scene numbers (inclusive)
  closing_scene: 12
  moderate_reversal: "Mara's routine life is disrupted"
  notes: ""

- id: seq-2
  act_id: act-1
  label: "The Inciting Discovery"
  scene_range: [13, 28]
  closing_scene: 28
  moderate_reversal: "The files point to Oak — her partner"
  notes: ""
```

**Why this shape?**
- Acts and sequences are hierarchical by nature; this YAML-in-markdown is a tree that the index summarizes with edge labels
- `scene_range` is how planned structure links to actual screenplay scenes without requiring new derivation logic — it's a range, not a pointer to each individual scene
- The body section is never in context unless explicitly retrieved — perfectly fits the three-layer model

### 2c. Character Arc (Q2, Q4)

Arc data lives in a **new `## Arc` section** inside each `character.md`. This is already listed as a standard section (the brief mentions `Arc` exists); we're now giving it a defined schema.

```yaml
# character.md frontmatter (additions)
arc_type: positive | negative | flat | ironic | absent
arc_value: "Trust"                  # the value that changes for this character
arc_value_at_open: positive         # their starting charge
arc_value_at_close: negative        # their ending charge
arc_complete: false                 # has the arc been fully designed?
```

Body section `## Arc` in `character.md`:

```markdown
## Arc

### Arc Beats

- id: arc-beat-1
  label: "Naïve Trust"
  act_id: act-1
  scene: 4
  description: "Mara takes Oak's word without question — trust as reflex"
  conflict_level: personal          # inner | personal | extra-personal
  value_charge: positive

- id: arc-beat-2
  label: "First Doubt"
  act_id: act-1
  scene: 22
  conflict_level: inner
  description: "She notices the inconsistency but chooses not to see it"
  value_charge: mixed

- id: arc-beat-3
  label: "Betrayal Confirmed"
  act_id: act-2
  scene: 45
  conflict_level: inner|personal
  description: "Oak lies to her face. She knows. She still covers for him."
  value_charge: negative

- id: arc-beat-4
  label: "The Choice"
  act_id: act-3
  scene: 89
  conflict_level: inner|personal|extra-personal
  description: "True crisis: turn him in and destroy both their careers, or stay silent"
  value_charge: negative            # crisis = maximum pressure, not yet resolved
  is_crisis: true

- id: arc-beat-5
  label: "Climax"
  act_id: act-3
  scene: 94
  conflict_level: inner|personal|extra-personal
  description: "She turns him in. Trust is dead. Justice is cold. She's alone."
  value_charge: ironic
  is_climax: true

### Arc Notes

The conflict levels escalate through the story: personal (she trusts her partner) → 
inner (she doubts herself) → all three simultaneously at the crisis. This is McKee's 
complexity, not just complication.
```

**On multi-protagonist stories (Q4):** Each character has their own `## Arc` section. In Miniplot, there may be no single spine — the `spine` field in `project.md` can be left null and the system operates without it. The index tracks arc status per character; the LLM can load multiple character arcs in parallel when needed.

**On relationship arcs:** These are not a new entity. A relationship arc is represented as an arc beat on one or both characters, with `conflict_level: personal`. The existing relationship edges in the index handle the graph; arc beats handle the progression.

**On flat arcs:** `arc_type: flat` is valid. A flat protagonist who doesn't change is still a design choice — McKee allows it. The system tracks it without judgment.

### 2d. Scene Structure Annotation (Q2, Q3)

Scenes are currently derived from `screenplay.fountain`. We need to add structural awareness without breaking that derivation. The solution is a **thin annotation layer** in the index, not in scene notes.

In the index, each scene entry gains:

```yaml
scenes:
  - id: 22
    heading: "INT. PRECINCT BATHROOM - DAY"
    characters: [mara, detective-oak]
    location: precinct-bathroom
    plots: [main-plot]
    # NEW fields:
    act_id: act-1
    sequence_id: seq-2
    value_at_open: positive         # optional — filled by LLM or user
    value_at_close: mixed
    arc_beats: [{char: mara, beat_id: arc-beat-2}]  # cross-reference
    planned: false                  # true = planned but not yet written
```

The `planned` flag answers Q3: planned-but-unwritten scenes exist in the index with no corresponding content in `screenplay.fountain`. They have a heading and description but no prose. When the screenplay is written, `planned` flips to `false` and the derivation logic matches by scene number or heading (exact match first, fuzzy second — this is an implementation detail for the build list).

**Do scenes need to know their act/sequence?** Yes, but only in the index — one line per scene, not a new note. This keeps context cost minimal while enabling queries like "what scenes are in Act 2?"

---

## 3. Index Design (Q6)

The index stays small. Here is what it gains:

**Project-level additions** (always in context):

```yaml
projects:
  - slug: falling-woman
    name: "The Falling Woman"
    structure_type: Classical
    spine: "A detective discovers her partner's corruption and must choose justice over loyalty"
    controlling_idea: "Justice triumphs when we sacrifice what we love most for what we believe"
    value_positive: Trust
    value_negative: Betrayal
    value_at_open: positive
    value_at_close: ironic
    act_count: 3
    sequence_count: 8
    inciting_incident_scene: 8
    climax_scene: 94
    structure_complete: true
    arc_count: 2
    arcs_complete: 1               # how many characters have full arcs designed
    sections: [Structure, Synopsis, Treatment, ...]
```

**Character-level additions** (always in context, per character):

```yaml
characters:
  - slug: mara
    name: "Mara Voss"
    story_role: Protagonist
    one_sentence: "Idealistic detective who must choose between loyalty and truth"
    arc_type: negative
    arc_value: Trust
    arc_value_at_open: positive
    arc_value_at_close: ironic
    arc_complete: true
    arc_beat_count: 5
    sections: [Personality, Background, Voice, Arc, Goals, Relationships]
    ...
```

**Scene-level additions** (already in index, gains three fields):

```yaml
scenes:
  - id: 22
    heading: "INT. PRECINCT BATHROOM - DAY"
    characters: [mara, detective-oak]
    location: precinct-bathroom
    act_id: act-1
    sequence_id: seq-2
    arc_beats: [{char: mara, beat_id: arc-beat-2}]
    planned: false
```

**What the index does NOT contain:** Full arc beat descriptions, act/sequence notes, value turn prose, scene analysis. Those live in `## Arc` and `## Structure` sections, loaded on demand.

**Index size estimate:** At 40 characters and 94 scenes, the new fields add roughly 3–4 lines per character (arc summary) and 3 lines per scene (act/seq/arc_beats). That's ~160 + ~280 = ~440 additional lines — well within budget for a project this size.

---

## 4. Retrieval Examples (Q4, Q6)

**Query 1: "Is Mara's arc working?"**

Load order:
1. Index → read `mara.arc_type`, `arc_value`, `arc_complete`, `arc_beat_count`; also `project.structure_type`, `spine`
2. `story_retrieve mara ## Arc` → full arc beats with scene numbers, conflict levels, value charges
3. Optionally: `story_retrieve project ## Structure` to see which acts those scenes fall in
4. Optionally: `story_retrieve mara ## Personality` to check if arc beats are credible given who she is

The LLM checks: Does the arc escalate conflict levels (inner → personal → all three)? Is there a true dilemma at the crisis beat? Does the climax beat deliver absolute and irreversible change? Does the arc type match the structure type's expectations?

**Query 2: "What happens in Act 2?"**

Load order:
1. Index → read `project.act_count`, then filter `scenes[]` by `act_id: act-2` → get scene headings, characters, arc_beats
2. `story_retrieve project ## Structure` → act-2 entry with sequences, climax scene, reversal description
3. If the user wants detail on specific scenes: `story_retrieve screenplay` (specific page range) or `story_search` by scene number

The LLM can answer structure questions (what sequences, what moderate reversals, what climax) and character questions (which arc beats fire in act 2) from steps 1–2 alone.

**Query 3: "I just wrote scene 45 — does it fit the plan?"**

Load order:
1. Index → find scene 45 entry → read `act_id: act-2`, `sequence_id: seq-4`, `arc_beats: [{char: mara, beat_id: arc-beat-3}]`
2. `story_retrieve mara ## Arc` → arc-beat-3 description ("Betrayal Confirmed — she covers for him")
3. `story_retrieve project ## Structure` → seq-4 entry to see where this scene sits in the sequence arc
4. `story_retrieve screenplay` → the actual text of scene 45

The LLM compares planned arc beat against actual scene content. No automated detection — the LLM reads and reasons.

---

## 5. Interaction Map (Q4)

```
PROJECT
├── structure_type (Classical/Miniplot/Antiplot)
├── spine (protagonist's desire)
├── controlling_idea
├── value_positive / value_negative / value_at_open / value_at_close
│
├── ACT 1
│   ├── opening_value → closing_value
│   ├── climax_scene (→ SCENE)
│   └── SEQUENCE 1, SEQUENCE 2
│       └── scene_range (→ SCENES)
│
├── ACT 2
│   └── ...
│
└── ACT 3
    └── ...

CHARACTER (Protagonist)
├── arc_type / arc_value / arc_at_open / arc_at_close
└── ARC BEATS
    ├── arc-beat-1 → scene: 4 (→ SCENE 4 in ACT 1 / SEQ 1)
    ├── arc-beat-2 → scene: 22 (→ SCENE 22 in ACT 1 / SEQ 2)
    ├── arc-beat-3 → scene: 45 (→ SCENE 45 in ACT 2 / SEQ 4)
    ├── arc-beat-4 [crisis] → scene: 89 (→ SCENE 89 in ACT 3 / SEQ 7)
    └── arc-beat-5 [climax] → scene: 94 (→ SCENE 94 in ACT 3 / SEQ 8)

SCENE (index entry)
├── act_id (→ ACT)
├── sequence_id (→ SEQUENCE)
├── arc_beats[] (→ CHARACTER ARC BEATS)
└── plots[] (→ PLOT threads, existing)
```

The graph has three kinds of edges:
- **Containment**: Act → Sequence → Scene (by scene_range)
- **Arc firing**: Scene → Arc Beat → Character (bidirectional cross-reference)
- **Existing**: Character ↔ Scene, Scene ↔ Plot (unchanged)

Subplots (existing `plots/` entities) are **independent of act structure** — they have their own setups/payoffs that may or may not align with act boundaries. The LLM can correlate them, but we don't force a parent-child link. This preserves the existing graph model.

---

## 6. UI Design (Q5)

Two new dashboard views. Both follow the existing sidebar nav pattern.

### New View: Structure

A **timeline / hierarchy panel** showing the full act/sequence/scene breakdown.

**Layout:**
- Top bar: project spine + controlling idea (one line each, always visible)
- Three-column act view, each column = one act
  - Act header: label, opening→closing value charge shown as colored badge (green=positive, red=negative, amber=mixed, purple=ironic)
  - Below each act header: sequence cards in vertical stack
  - Each sequence card: label, scene range, moderate reversal summary (1 line)
  - Scene count indicator per sequence
- Click a sequence → expand to show individual scenes within it (heading, characters, arc_beats indicator dots)
- Click a scene → existing scene detail (scene text + "Ask Hermes" button)
- **"Ask Hermes about Act 2"** button per act column

**Planning state indicators:**
- If `planned: true` on a scene → shown with dashed border (planned but unwritten)
- If `structure_complete: false` on project → a gentle prompt banner: "Structure not fully planned — click to continue with Hermes"

**No wireframe art here, but the mental model:** think of it as a Kanban board rotated 90°, where columns are acts and cards are sequences, with scenes nested inside.

### New View: Arcs

A **character arc timeline** showing all arcs simultaneously across the act structure.

**Layout:**
- X-axis: act boundaries (vertical dividers) with scene numbers
- Y-axis: one row per character with arc (only characters where `arc_type ≠ absent`)
- Each row: a line chart-style value progression from arc_value_at_open → through arc beats → arc_value_at_close
  - Value states: positive (top), mixed (middle), negative (bottom), ironic (bottom+dotted)
  - Arc beat points plotted at their scene numbers, sized by conflict level (small=inner, medium=personal, large=extra-personal)
  - Crisis beat: ★ marker; Climax beat: ◆ marker
- Hover/click an arc beat → shows beat description + scene link
- "Ask Hermes about Mara's arc" per row

**Multi-character without clutter:** Each character gets its own row. For 2–4 protagonists (Miniplot), rows are stacked. For supporting characters, they're collapsed by default and expandable. Color follows existing role palette (Protagonist=blue, Antagonist=red, Supporting=teal).

### Integrations Into Existing Views

- **Scenes view**: each scene card gains a small tag row showing its `act_id` and `sequence_id`. Arc beat dot indicators (colored by character) appear if the scene has `arc_beats`. No new modal — just lightweight metadata.
- **Characters view** (network graph): character nodes gain an arc indicator badge (up arrow = positive arc, down = negative, flat = dash, ironic = ~). Click character node → existing profile, but now with an `## Arc` section if loaded.
- **Script view**: no changes. Fountain is the source of truth; we annotate it, we don't modify it.

**Minimum useful set:** Structure view + Arcs view + scene-level tags. The rest is existing infrastructure. Nothing gets overengineered because new data is loaded on demand — the views only render what's been designed.

---

## 7. Build List (Q7)

### Index changes
- Add structure/arc summary fields to project and character index entries (schema update in `constants.py`)
- Add `act_id`, `sequence_id`, `arc_beats`, `planned` to scene index entries
- Update `story_index` to populate these fields when regenerating

### Schema / constants
- Add `structure_type` enum to project schema
- Add `arc_type`, `arc_value`, `arc_value_at_open/close`, `arc_complete` to character schema
- Add `arc_beat_count` (derived count) to character schema
- Add `act_count`, `sequence_count`, `structure_complete`, `inciting_incident_scene`, `climax_scene`, `spine`, `controlling_idea`, `value_*` fields to project schema
- Register `## Structure` and `## Arc` as standard sections for project and character respectively

### Tools (no new tools needed)
- `story_create` — extend to auto-fill `## Structure` skeleton in `project.md` and `## Arc` skeleton in new character notes, based on `structure_type`
- `story_retrieve` — no changes; already handles arbitrary `## sections`
- `story_edit` — no changes; already handles edits to any section
- `story_index` — update to parse `## Structure` and `## Arc` sections and populate index fields
- `story_dashboard` — extend to render two new views (below)

### Dashboard (single HTML file, embedded JS)
- Add **Structure** view to sidebar nav
- Add **Arcs** view to sidebar nav
- Structure view rendering: act/sequence/scene hierarchy with value badge colors
- Arcs view rendering: multi-row timeline with arc beat points (SVG-based, similar to existing vis-network pattern)
- Extend Scenes view cards with act/sequence tags and arc beat dots
- Extend Characters network graph nodes with arc indicator badges

### Story Memory
- Add `## STRUCTURE STATE` section: current act, sequences defined, structure_complete flag
- Add `## ARC STATE` section: per-character arc status (arc_type, arc_complete, key beats designed)
- Do **not** put arc beat prose in memory — that lives in `## Arc` sections loaded on demand

---

## 8. Trade-offs and Open Questions

**What I chose and why:**

- **Sections over new entity folders.** `acts/` and `arcs/` as new folders would mean new tool logic, new index entity types, new dashboard entity grids. Sections inside existing notes cost almost nothing architecturally and fit the retrieval model perfectly. The trade-off: a project with 3 acts and 8 sequences in a single `## Structure` section is a long section, but it's still loaded in one retrieval call. If a project has 5 acts and 20+ sequences, this may warrant a dedicated `structure.md` note — easy to add later.

- **Structure type as upfront commitment.** The brief asks whether type should be inferred. I recommend against it: inference is expensive (requires reading most of the vault), and McKee treats type as a design decision, not a property to be discovered. The user can always change it — it's a frontmatter field. The trade-off: new users may not know their type yet. Solution: make it nullable at creation and prompt via dashboard.

- **No new tools.** The existing tools are sufficient. The brief hints at `story_structure` and `story_arc` tools — I'd resist adding them unless the LLM needs to invoke structure-specific operations that can't be expressed as `story_retrieve` + `story_edit`. Adding tools multiplies the LLM's decision surface without proportional benefit.

- **Arc beats as prose-in-markdown, not structured YAML frontmatter.** Arc beats are semi-structured: they need a scene reference (scalar) but also free-text description and notes. Storing them as YAML blocks inside a markdown section gives the LLM the ability to read and write them naturally while keeping them parseable for index derivation.

**What's left for you to decide:**

- **Scene mapping when plan and screenplay diverge (Q3).** I propose: on `story_index`, match by scene number first (since the plan uses scene numbers from `screenplay.fountain`), then flag unmatched planned scenes as `planned: true` orphans. But if the screenplay is reordered significantly, this breaks. You may want a manual assignment UI or a fuzzy heading-match fallback — the right answer depends on how your users actually write.

- **Whether `treatment.md` becomes the structural blueprint.** Currently it's an ordered outline of beats. It could become the authoritative source for planned scene order, with `## Structure` in `project.md` being the act/sequence wrapper. I left this as an open question because it touches an existing file's purpose.

- **Sequence granularity for Antiplot.** McKee defines sequences, but Antiplot stories with nonlinear time make sequence boundaries meaningless. You may want to suppress the sequence layer entirely for `structure_type: Antiplot` and use only acts. Easy to do in the dashboard rendering logic.

- **The `controlling_idea` field.** McKee says the controlling idea emerges from the story — it often can't be stated before writing begins. I've put it in `project.md` as a nullable field the user fills in during revision. But you may want the LLM to propose a controlling idea after analyzing the arc climaxes — that's the agent reasoning layer the brief explicitly put out of scope.