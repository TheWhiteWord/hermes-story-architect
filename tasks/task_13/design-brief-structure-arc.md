# Design Brief: Story Structure & Character Arc System

**Target audience:** Specialist LLM (screenwriting/story-theory expert)
**Source of truth:** Robert McKee's *Story* (provided as `Good_Writing.md`)
**Existing system:** Hermes Story Architect plugin (described below)

---

## 1. THE PLUGIN — WHAT EXISTS TODAY

### Purpose
A standalone Hermes plugin for writing longform stories/screenplays. Story projects live as Markdown + YAML frontmatter in a vault. The LLM is the intelligence layer with **section-level targeted retrieval** — it loads only the `## Voice` section from a character note, never the whole vault.

### Three-Layer Architecture

```
Layer 1: Project Index (.story/index.yaml)   ← small, ALWAYS in context
    ↓ describes what exists, how it connects, what sections each note has
Layer 2: Section Targeting                     ← find relevant ## sections
    ↓ determines which sections to load from which notes
Layer 3: Content (vault notes)                 ← loaded on demand
    ↓ only the sections needed RIGHT NOW
```

**Why this matters for your design:** A 40-character story with 60 scenes is tens of thousands of tokens. We load only what the conversation needs. Any new system must fit this budget — new data either goes in the index (small labels, graph edges) or in note body sections (loaded on demand).

### Registered Tools

| Tool | Purpose |
|------|---------|
| `story_load` | Load index + memory into context |
| `story_retrieve` | Get specific `## sections` from a note |
| `story_index` | Regenerate index from vault |
| `story_search` | Full-text search across all project notes |
| `story_edit` | Propose/apply edits (action protocol with approval loop) |
| `story_create` | Create new entity notes |
| `story_dashboard` | Open HTML dashboard in preview pane |

### Vault Structure

```
~/story-vault/
├── .story/
│   ├── index.yaml         # Project graph (always-loaded)
│   ├── memory.md          # Story Memory (continuity map)
│   └── history.md         # Edit history (gitignored)
└── projects/
    └── <project-slug>/
        ├── project.md           # Project metadata (frontmatter)
        ├── title-page.md
        ├── synopsis.md
        ├── treatment.md         # Ordered outline, one paragraph per beat
        ├── screenplay.md        # Fountain syntax (single source of truth)
        ├── characters/
        │   ├── mara.md
        │   └── detective-oak.md
        ├── locations/
        │   └── kitchen.md
        ├── worlds/
        │   └── gilead.md
        └── plots/
            └── main-plot.md
```

---

## 2. KEY DATA STRUCTURES (AND WHAT THEY ALREADY EXPOSE)

### Entity Schemas (Frontmatter)

**Character:**
```yaml
name: string                    # Display name
story_role: Protagonist | Antagonist | Supporting | Minor | Cameo
one_sentence: string            # Index label
relationships:                  # Unidirectional edges
  - id: character-slug
    label: string               # "Partner", "Rival", etc.
    feeling: string             # "Wary respect"
goals_short: string
goals_long: string
knowledge: string[]             # Facts the character knows
scenes: [{number, heading}]     # Derived from screenplay
sections: string[]              # Available ## headings (derived)
```

**Plot:**
```yaml
name: string
status: active | resolved | abandoned
characters: string[]            # Slugs
setups: [{heading, number, description}]
payoffs: [{heading, number, description}]
sections: string[]
```

**Scene (derived from screenplay.fountain, not a note):**
```yaml
id: number                      # Sequential (1, 2, 3...)
heading: "INT. KITCHEN - NIGHT"
characters: string[]            # Slugs (matched via fuzzy)
location: string                # Slug (matched via fuzzy)
plots: string[]                 # Reverse-looked-up from plot setups/payoffs
```

**Project:**
```yaml
name: string
logline: string
genre: string
setting: string
status: active | abandoned | archived
scene_count: number
character_count: number
```

### Standard Body Sections (per entity type)

**Character:** `Personality`, `Background`, `Voice`, `Greatest Fear`, `Secrets`, `Arc`, `Relationships`, `Goals`

**Location:** `Description`, `History`, `Scenes`
**World:** `Description`, `History`, `Conflict`
**Plot:** `Summary`, `Obstacles`, `Stakes`

### The Index (.story/index.yaml)

The index is a **graph**: entities are nodes, relationships/scene memberships/setups/payoffs are edges. Each entity entry is small — one-sentence labels, counts, available sections.

**What the index contains:** entity names, roles, connections, scene memberships, plot setups/payoffs, available `##` sections.

**What the index does NOT contain:** full personality descriptions, dialogue, scene prose, detailed relationship history. Those live in vault notes and are loaded on demand.

### Story Memory (.story/memory.md)

A plain-Markdown continuity map with sections:
- `CHARACTERS & RELATIONSHIPS`
- `CHARACTER KNOWLEDGE`
- `TIMELINE`
- `PLOT THREADS`
- `SETUPS & PAYOFFS`
- `WORLD RULES`
- `VOICE & STYLE`
- `CONTINUITY RISKS`

### Section Parser

Zero-dependency regex that splits note bodies by `## Headings`. The tool `story_retrieve` loads only the requested sections. This is how we keep context small.

---

## 3. THE DASHBOARD — UI AS IT EXISTS

### Views (sidebar navigation)

| View | Content | Interaction |
|------|---------|-------------|
| **Story** | Project overview: logline, synopsis, treatment outline, scene count | — |
| **Characters** | vis-network force-directed graph. Nodes = characters, edges = relationships | Click node → profile + scenes |
| **Scenes** | Filterable scene list with headings, characters, locations | Click → full scene text, "Ask Hermes" |
| **Locations** | Entity grid: each location with scenes it appears in | Click → full note |
| **Plots** | Entity grid: each plot with setup/payoff scenes, status | Click → full note |
| **Worlds** | Entity grid: each world with rules | Click → full note |
| **Script** | Fountain-rendered screenplay with full statistics panel | Side panel: Overview / Characters / Scenes tabs |

### Interaction Patterns

- **"Ask Hermes about X" buttons** — pre-formulated prompts sent via `data-hermes-send`
- **Auto-refresh** — after any `story_edit`, `story_create`, or `story_index`, the dashboard regenerates and reopens
- **Statistics panel** (in Script view) — 3 tabs: Overview (length, duration, action/dialogue ratio), Characters (speaking time, monologues, detail table), Scenes (INT/EXT/Mixed, time of day, location counts)

### Visual Language

- CSS variables for theming (foreground, muted, accent, border, card, background)
- Role-specific colors (Protagonist=blue, Antagonist=red, Supporting=teal)
- Status colors (active=green, building=amber, resolved=muted)
- Transparent background, inherits Hermes app theme

---

## 4. THE INTENT — WHAT WE WANT TO BUILD

### Goal

A system that helps the user **construct** and **track** story structure and character arcs, grounded in established story theory (McKee). The system should work across three phases:

1. **Pre-writing / Planning** — help design the structure (acts, sequences, scenes) and character arcs
2. **During writing** — track whether the writing matches the intended structure, flag deviations, suggest next steps
3. **Post-draft / Revision** — analyze the actual screenplay against the intended structure and arcs, identify gaps

### Two Intertwined Systems

**A. Story Structure**
- Story → Act → Sequence → Scene hierarchy (cumulative turning of values)
- Each level has expectations based on its type (Classical / Minimalist / Anti-Structure)
- Scenes turn values; sequences build to moderate reversals; acts build to major reversals; story climax is absolute and irreversible change

**B. Character Arc**
- How a character's inner nature changes over the story (for better or worse)
- Revealed through choices under pressure — structure forces progressively increasing pressure
- Arc and structure are inseparable: structure creates pressure → pressure forces choices → choices reveal character → character changes

### Constraints

- Must fit the existing plugin architecture (three-layer retrieval, section-based loading)
- Index stays small — new awareness data only, not content dumps
- No new entity types unless absolutely necessary (reuse existing: character, scene, plot, project)
- UI must fit the existing dashboard (sidebar views, entity grids, "Ask Hermes" pattern)
- Ground truth is McKee's theory (`Good_Writing.md`), not ad-hoc invention

---

## 5. THE QUESTIONS — WHAT WE NEED YOU TO ANSWER

### Q1: How Does Structure Type Shape the System?

McKee identifies 3 story structure types (Classical/Archplot, Minimalism/Miniplot, Anti-Structure/Antiplot) with different expectations for ending, conflict, protagonist, time, causality, and reality.

**Specific questions:**
- Should the user pick a structure type upfront, and should that choice change what fields/expectations the system enforces?
- Or should the system be type-agnostic and let the LLM infer the type from the story's content?
- How does structure type affect arc expectations? (Classical = clear positive/negative arc; Miniplot = ambiguous/internal; Antiplot = fragmented/ironic)
- Can a story's type change during development, or is it a foundational commitment?

### Q2: What New Data Structures Need to Be Created?

Today we have: character, location, world, plot, project, scene (derived from screenplay).

We need to represent: **acts**, **sequences**, **character arcs** (as structured data, not just prose), and potentially **story-level metadata** (genre type, controlling idea, inciting incident, climax scene).

**Specific questions:**
- Are acts/sequences/arcs **new entity types** (new note folders like `acts/`, `sequences/`, `arcs/`)? Or are they **new sections** inside existing entities (e.g., `## Structure` in `project.md`, `## Arc Progress` in character notes)?
- Does the concept of "arc" belong to a single character, or can it be shared (e.g., a relationship arc)?
- Do scenes need to know what act/sequence they belong to? (Currently scenes only know characters, location, plots.)
- Is a "sequence" a meaningful unit to the user, or is it an implementation detail the LLM tracks internally?
- How do subplots (existing plot threads) relate to the main story structure? Are they children of acts? Independent?

### Q3: How Do Planned Structure and Actual Screenplay Relate?

The system must work for users who write from zero (plan first, write later) and users who have an existing screenplay (write first, analyze later).

**Specific questions:**
- Can planned structure and actual screenplay diverge? How does the user sync them?
- Is there a "planning mode" vs "writing mode" distinction in the UI, or is it seamless?
- When a user adds a scene to the plan but hasn't written it yet, what does that scene look like? (Just a heading? A beat description? A full scene note?)
- When the screenplay is written, how does the system map planned scenes to actual scenes? (By heading match? By order? Manual assignment?)
- Should `treatment.md` (existing: ordered outline, one paragraph per beat) be the structural blueprint, or is that a separate concept?

### Q4: How Do Structure Levels and Character Arcs Interact — and Exist Separately?

McKee says structure and character are inseparable. But in practice, a user might want to:
- Design the structure first, then assign arcs
- Design arcs first, then build structure around them
- Work on both simultaneously
- Track them independently (e.g., "the structure is fine but the arc is weak")

**Specific questions:**
- What does the **relationship** between a scene's structural role and a character's arc look like as data? Is it a field? An edge? A cross-reference?
- When a user asks "is Mara's arc working?", what data does the LLM need? When they ask "is Act 2 working?", what data? How much overlap?
- Can you have a well-structured story with flat arcs? Can you have a messy structure with great arcs? How should the system represent these states?
- McKee's "spine" (protagonist's desire) is a story-level concept. Is it a field on the project? A relationship between protagonist and story structure?
- How does the system handle multi-protagonist stories (Miniplot) where multiple arcs coexist?

### Q5: How Do We Present This to the User Intuitively?

We want **new panels** for structure and arc. The dashboard currently has 7 views; we're open to adding more or integrating into existing ones.

**Specific questions:**
- Should we have separate panels for story level, act level, and scene level? Or fewer/more?
- How do we represent **character arcs** graphically (not just text)? Multiple characters means multiple arcs — how do we show them without clutter? Graphs, charts, timelines, overlays?
- Do we integrate structure/arc data into existing views or keep them separate? For example: does scene-level structure go into the Scenes panel, or stay in its own interface, or both? If integrated, what does that look like?
- How do we avoid over-engineering? What's the minimum useful set of panels/widgets that actually helps the user, vs. what's just impressive?

### Q6: What Goes in the Index, and What Does Not?

This is the most important architectural question. The index is always in context (~200-500 lines). It must stay small.

**Specific questions:**
- Should the index contain the full structure tree (all acts, all sequences, all scenes with their roles)? Or just top-level summary (act count, arc count, key structural beats)?
- Arc data: should the index know "Mara's arc: positive → negative" (charge states at start/end), or the full arc prose ("Starts believing the law protects the innocent...")?
- Scene structure role: should the index store each scene's act/sequence assignment, or is that derivable from the screenplay (e.g., by page count heuristics)?
- McKee's "progressive complication" — should the index track the escalation pattern (each act's crisis magnitude), or is that an LLM inference from scene content?

### Q7: What Needs to Be Built (Code Changes vs. New Elements)?

**Specific questions:**
- Do we need **new tools** (e.g., `story_structure`, `story_arc`) or can this be handled by extending `story_edit` / `story_create` with new actions/entity types?
- Do we need **new entity folders** (`acts/`, `sequences/`) or do we treat structure as metadata on existing entities?
- The existing `story_create` auto-fills all expected fields with empty defaults and adds standard body sections. If we add entity types, the schema must be self-documenting in `constants.py`.
- The dashboard HTML is a single file with embedded CSS/JS. New views require JS rendering logic. Are there interactions that don't fit the current "list + filter + click" pattern?
- Story Memory currently tracks continuity (knowledge, timeline, voice). Should it also track structure/arc state, or should that be separate?

---

## 6. CONTEXT — WHAT WE ALREADY KNOW

### Existing Implementation (Not a Constraint)

Today the plugin is built with these implementation choices. They exist. They are not sacred. If the design requires changing them, propose how:

- **Relationships are unidirectional.** Character A's feeling about B is stored in A's frontmatter, not duplicated. Could become bidirectional.
- **The index is a graph, not a hierarchy.** Edges, not parent-child trees. If acts/sequences are hierarchical, we need to decide: tree or graph?
- **Scenes derived from screenplay.** Today scenes are parsed from `screenplay.fountain`. This is a useful feature when a user has an existing screenplay, but the new system must work without one.
- **Plots as structure.** Plot threads with setups/payoffs are the current closest thing to story structure. They may be the seed of the new system, or they may need to be rebuilt/integrated into it.
- **Continuity checks.** Currently a self-audit before edits. Underdeveloped. Don't design around it. If structure/arc tracking replaces it, fine.

### What McKee Gives Us (Theory Ground Truth)

- **Value turning** as the atomic unit of structure (scene = value shift)
- **Progressive complication** (scenes → sequences → acts → story, each level = bigger reversal)
- **Three structure types** (Classical/Archplot, Minimalism/Miniplot, Anti-Structure/Antiplot) with different expectations
- **Three conflict levels** (inner, personal, extra-personal) — arcs should engage all three for depth
- **Character arc** = change in inner nature, revealed through choices under pressure
- **Structure function** = create progressively increasing pressure
- **Character function** = embody qualities to enact choices convincingly
- **Crisis** = true dilemma (irreconcilable goods / lesser evils), maximum pressure, last effort
- **Climax** = revolution in values, absolute and irreversible
- **Controlling Idea** = the story's ultimate meaning, expressed through action
- **Scene analysis method** = define conflict → note opening value → break into beats → note closing value → locate turning point

---

## 7. DELIVERABLE FORMAT

We want a **design proposal**, not code. Specifically:

1. **Data model**: what new fields, entities, or relationships exist. Show the schema (pseudocode or YAML sample).
2. **Index design**: what goes in the index vs. what stays in notes. Show a sample index entry for a character and a scene with the new system.
3. **UI design**: where the user interacts with structure/arc data. Describe the views, panels, or interactions. Wireframe-style text is fine.
4. **Retrieval examples**: show 2-3 user queries and what the LLM would load to answer them (index → sections → content).
5. **Interaction map**: how structure levels and arcs reference each other. Show the graph/tree.
6. **Build list**: what code changes are needed (new tools, new entity types, dashboard views, index changes, skill updates).
7. **Trade-offs**: what you chose and why, what you rejected, what's left flexible for us to decide.

---

## 8. WHAT'S OUT OF SCOPE

We're not trying to solve everything at once. Specifically, the following are explicitly **not** part of this design:

- **Theory-awareness in the LLM.** How does the LLM know McKee's rules to detect whether a structure is valid? How does it know whether an arc is "working"? That's a separate problem — retrieval, verification, inference — and we want to keep it separate. For now, assume the LLM can be made aware of story theory through system prompts or skill loading. Design the **data and UI**, not the agent's reasoning.

- **Automated structure detection.** Don't design the LLM's pipeline for analyzing screenplay content and inferring acts/sequences/arcs. That's an inference layer on top. Here we're building the skeleton it operates on.

- **Continuity checks.** Mentioned above — not a constraint, not a goal. If the new system subsumes it, fine. If not, that's future work.

## 9. NON-GOALS

- We are NOT building a general-purpose story-theory encyclopedia. The system is practical: help the user construct and track their specific story.
- We are NOT replacing Fountain as the screenplay format. Structure/arc metadata is a layer on top, not a replacement.
- We are NOT building a full screenwriting application. This is an assistant, not Final Draft.
