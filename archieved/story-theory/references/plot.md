---
name: plot
description: "Plot theory: definitions, characteristics, and schema mapping. Covers main plots, subplots, and their relationship to story structure."
version: 0.1.0
author: TWW, Hermes Agent
license: MIT
---

# Plot Theory

Narrative theory reference for the Story Architect plugin. Explains the theoretical framework behind the schema and provides guidance for making consistent decisions about story structure, plots, and subplots.

Source: Robert McKee, *Story* (Structure, Character, Design).

## When to Use

- Designing new fields or modifying existing schema
- Making decisions about plot categorization and propagation
- Understanding how plot elements relate to scenes, sequences, and acts
- Validating that schema changes remain theoretically sound

## Key Concepts

### Project Structure vs Main Plot

**Two different axes, conflated by name only:**

| Concept | Field | Scope | What it describes |
|---------|-------|-------|-------------------|
| **Structure Type** | `project.structure_type` | The whole story | Engine/architecture: how the story moves through time and reality. Values: `Classical`, `Miniplot`, `Antiplot`. |
| **Value Arc** | `main_plot.value_arc` | The protagonist | Payload/trajectory: where the protagonist's internal values land. Values: `Maturation`, `Redemption`, `Education`, `Punitive`, `Disillusionment`, `Testing`. |

**Analogy:** Structure Type is the vehicle (car vs boat vs plane). Value Arc is the destination (north, south, home). One does not imply the other.

**Schema rule:** These fields live in different entities (`project` vs the main `plot`). Never derive one from the other.

### Plot Scope

| Scope | Meaning | Identification |
|-------|---------|----------------|
| `main` | A-story, the protagonist's central journey | `plot_scope: main` on the plot entity |
| `sub` | B-story, thematic commentary | `plot_scope: sub` (default) |

### Value Arcs (Main Plot Only)

| Arc | Direction | Description |
|-----|-----------|-------------|
| Maturation | Positive Change | Naivety → maturity |
| Redemption | Positive Change | Moral corruption → moral recovery |
| Education | Positive Change | Cynicism → wisdom |
| Punitive | Negative Change | Bad → worse → punished |
| Disillusionment | Negative Change | Optimism → cynicism/tragedy |
| Testing | Testing Arc | Values tested against extreme hardship |

### Subplot Types (Subplot Only)

| Type | Purpose | Effect |
|------|---------|--------|
| `Contradictory` | Contrast | Runs counter to main plot values; highlights theme through opposition |
| `Resonant` | Echo | Mirrors main plot theme; deepens through variation |
| `Setup` | Preparation | Establishes elements needed for later main plot payoffs |
| `Complicating` | Obstacle | Intersects main plot to add friction; raises stakes |

### Structural Spectrum (Project Level)

| Type | Key Characteristics |
|------|---------------------|
| `Classical` (Archplot) | Active protagonist, external conflict, linear time, causal progression, closed ending |
| `Miniplot` (Minimalism) | Passive protagonist, internal conflict, multiple protagonists, open ending |
| `Antiplot` (Anti-Structure) | Non-linear time, coincidence, inconsistent reality, absurdist logic |

---

A plot has two independent dimensions:

1. **Structure** — how the story is told (architecture)
2. **Value Arc** — what changes in the protagonist (trajectory)

**Analogy:** Structure is the engine. Value arc is the destination.

```
┌──────────────────────────────────────────────────────┐
│              STRUCTURE (How)                          │
│                                                       │
│  Classical ──→ Active protagonist, linear, closed    │
│  Miniplot  ──→ Passive, internal, open               │
│  Antiplot  ──→ Non-linear, coincidence, absurdist    │
│                                                       │
│  Lives in: project.structure_type                     │
├──────────────────────────────────────────────────────┤
│              VALUE ARC (What changes)                 │
│                                                       │
│  Maturation       Naivety → Maturity                  │
│  Redemption       Corruption → Recovery               │
│  Education        Cynicism → Wisdom                   │
│  Punitive         Bad → Worse → Punished              │
│  Disillusionment  Optimism → Tragedy                  │
│  Testing          Values tested under pressure        │
│                                                       │
│  Lives in: main_plot.value_arc                        │
└──────────────────────────────────────────────────────┘
```

**Rule:** One does not imply the other. A Classical story can have a Punitive arc. An Antiplot can have a Redemption arc. Choose independently.

---

## Main Plot

The A-story. The protagonist's central dramatic journey.

**Identification:** `plot_scope: main` on the plot entity.

**Single main plot** (not enforced in code — trust the writer):
- One per story, by convention
- If multiple tagged `main`, UI shows both in the "Main Plot" section
- No runtime validation prevents dual main plots

**What it carries:**
| Field | Purpose | Applies To |
|-------|---------|------------|
| `plot_scope` | Always `"main"` | Plot identification |
| `value_arc` | Protagonist's internal change | Main plots only |
| `status` | `active` / `resolved` / `abandoned` | All plots |
| `setups` | Scenes where plot is established | All plots |
| `crisis` | Scene of maximum tension / point of no return | All plots |
| `climax` | Scene of reversal / resolution | All plots |
| `payoffs` | Scenes where plot resolves | All plots |
| `characters` | Slugs involved (frontmatter-only) | All plots |
| `one_sentence` | Index label | All plots |

**What it does NOT carry:**
- `plot_type` — that's for subplots only
- `structure_type` — that lives on `project.md`

**Schema rule:** The main plot's `value_arc` and `project.structure_type` are orthogonal. Don't conflate them.

---

## Subplot

B-story, C-story, etc. Thematic commentary on the main plot.

**Identification:** `plot_scope: sub` (or default — `sub` is the schema default).

### Subplot Types

Each type has a specific *function* relative to the main plot:

| Type | Purpose | Function |
|------|---------|----------|
| **Contradictory** | Contrast | Runs counter to main plot values. Highlights theme through opposition. |
| **Resonant** | Echo | Mirrors main plot theme. Deepens the controlling idea through variation. |
| **Setup** | Preparation | Establishes narrative elements needed for later main plot payoffs. |
| **Complicating** | Obstacle | Intersects main plot to add friction, delays, raises stakes. |

**How to choose:**
- Ask: "What is this subplot DOING to the main plot?"
- Contradicting it? → Contradictory
- Mirroring it? → Resonant
- Setting up a reveal? → Setup
- Getting in the protagonist's way? → Complicating

**Note:** A subplot can serve multiple functions (e.g., both resonant AND complicating). Pick the dominant one. The schema has a single `plot_type` field — choose the primary function.

### Subplot Schema

| Field | Purpose | Applies To |
|-------|---------|------------|
| `plot_scope` | `"sub"` (default) | Subplots |
| `plot_type` | Contradictory / Resonant / Setup / Complicating | Subplots only |
| `status` | `active` / `resolved` / `abandoned` | All plots |
| `setups`, `payoffs` | Scene beats | All plots |
| `characters` | Slugs involved | All plots |

**What it does NOT carry:**
- `value_arc` — that's for the main plot only
- `serves_plot` — subplots serve the main plot by definition (single main plot, so no need to specify which)

---

## Plot Relationships to Structure

```
Project.md
  structure_type: Classical | Miniplot | Antiplot
  │
  ├── Main Plot (plot_scope: main)
  │     value_arc: Maturation | Redemption | ...
  │     setups: [{scene_id, description}]
  │     payoffs: [{scene_id, description}]
  │
  ├── Subplot A (plot_scope: sub)
  │     plot_type: Contradictory | Resonant | ...
  │
  ├── Subplot B
  │     plot_type: Complicating
  │
  ├── Scene (sequence_id, act_id)
  │     plots[]: [{id: "main", beat: "setup"}, {id: "sub-a", beat: "payoff"}]
  │
  ├── Sequence (act_id)
  │     scenes_list: [s1, s2, s3]
  │     plots[]: derived from scenes
  │
  └── Act
        sequences_list: [seq-1, seq-2]
        scenes_list: [s1, s2, s3, s4]
        plots[]: derived from scenes
```

### Derivation Flow

1. **Plot → Scene:** Plot's `setups`/`payoffs` reference scene slugs. The index reverse-lookups these to populate `scene.plots[]` with beat types.
2. **Scene → Sequence:** Sequence's `scenes_list` is built from `scene.sequence_id`. Sequence's `plots[]` is derived by aggregating its scenes' plot references.
3. **Scene → Act:** Act's `scenes_list` is built from `scene.act_id`. Act's `plots[]` is derived by aggregating its scenes' plot plots.
4. **Sequence → Act:** Act's `sequences_list` is built from `sequence.act_id`.

**Key insight:** Plot → Scene linkage is explicit (in plot setups/payoffs). Everything else is derived. If you add a scene to a sequence, the sequence automatically picks up that scene's plots on next index refresh.

---

## Traceability

Subplots are traceable through the act/sequence structure via the enriched `plots[]` arrays on sequences and acts. These include:

```yaml
plots:
  - id: main-plot
    has_setup: true
    has_payoff: false
    plot_scope: main
    plot_type: ""  # empty for main plots
  - id: sub-b-romance
    has_setup: true
    has_payoff: true
    plot_scope: sub
    plot_type: Resonant
```

The dashboard renders these with:
- Main plots: purple pip, MAIN badge, value_arc shown
- Subplots: type-colored pip, type badge (CONTRADICTORY, RESONANT, etc.)

---

## Stats: Plot Coverage

`compute_structural_stats()` now includes a `plotCoverage` array:

```json
{
  "plotCoverage": [
    {
      "id": "main-plot",
      "name": "Main Plot",
      "plot_scope": "main",
      "value_arc": "Maturation",
      "sceneCount": 18,
      "coveragePct": 75
    },
    {
      "id": "sub-romance",
      "name": "Romance Subplot",
      "plot_scope": "sub",
      "plot_type": "Resonant",
      "sceneCount": 8,
      "coveragePct": 33
    }
  ]
}
```

**Use case:** See at a glance how much of the story each plot occupies. Main plot should typically have high coverage (50%+). Subplots cluster around 15-40%.

---

## Schema Decision Framework

When adding or modifying fields, ask:

1. **Is this about the whole story or a specific element?**
   - Whole story → `project.md`
   - Protagonist's journey → main `plot`
   - Thematic commentary → subplot `plot_type`

2. **Is this about architecture or trajectory?**
   - How it's told → `project.structure_type`
   - Where it ends → `main_plot.value_arc`

3. **Does this apply to main plots, subplots, or both?**
   - Main only: `value_arc`
   - Sub only: `plot_type`
   - Both: `plot_scope`, `status`, `setups`, `payoffs`, `characters`

4. **Is this derivable from existing data?**
   - If yes → don't store it (compute in index generator)
   - If no → store it on the entity where it belongs

## Summary: Schema Decision Table

| Question | Answer | Field Location |
|----------|--------|----------------|
| How is the story told? | Classical / Miniplot / Antiplot | `project.structure_type` |
| What changes in the protagonist? | Maturation / Redemption / ... | `main_plot.value_arc` |
| Is this the A-story or B-story? | main / sub | `plot.plot_scope` |
| What does the subplot DO to the main? | Contradictory / Resonant / Setup / Complicating | `plot.plot_type` |
| Where is the plot established/paid off? | Scene slugs + descriptions | `plot.setups`, `plot.payoffs` |
| Who's involved? | Character slugs | `plot.characters` |
| Is it active, resolved, or abandoned? | Status | `plot.status` |
