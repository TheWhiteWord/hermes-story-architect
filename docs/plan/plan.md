# Hermes Story Architect — Plan (v6)

> **Goal**: Build a story-writing environment as a standalone Hermes plugin. Story projects live as Markdown + YAML frontmatter in a dedicated vault. Hermes provides the intelligence layer with **section-level targeted retrieval**. The preview pane provides interactive navigation.

---

## Plugin Architecture

**Standalone plugin** — registers its own tools, manages its own vault. No dependency on obsidian-vault plugin.

- Vault: `~/story-vault/` (configurable)
- Tools: `story_load`, `story_retrieve`, `story_edit`, `story_create`, `story_index`, `story_search`
- Config: Hermes plugin config
- No grants, no roles — single-user plugin

**Concepts borrowed** (ideas, not code):
- Three-stage retrieval (index → target → load)
- Frontmatter → body mapping
- Standard `##` sections for targeting
- Always-loaded project index
- Zero-dependency regex section parser

---

## Core Architecture: Three Layers + Section Targeting

```
Layer 1: Project Index (.story/index.yaml)     ← small, ALWAYS in context
    ↓ describes what exists, how it connects, what sections each note has
Layer 2: Section Targeting                      ← find relevant ## sections
    ↓ determines which sections to load from which notes
Layer 3: Content (vault notes)                  ← loaded on demand
    ↓ only the sections needed RIGHT NOW
```

The index is a graph: characters, locations, scenes, plot threads, worlds are nodes. Relationships, scene memberships, setups/payoffs are edges. Each node also lists its available `##` sections.

**Why this matters**: A 40-character story with 60 scenes is tens of thousands of tokens. We load only the `## Voice` section from one character note — maybe 4 lines.

---

## Key Architectural Decisions

### Frontmatter → Body Mapping

Every frontmatter field that summarizes or labels something has a **detailed counterpart** in a standard body section:

| Frontmatter (index label) | Body section (detailed explanation) |
|---------------------------|-----------------------------------|
| `one_sentence` | Full profile in `## Personality`, `## Background`, etc. |
| `goals.short` | Why this goal drives behavior in `## Goals` |
| `goals.long` | How the goal evolves in `## Arc` |
| `relationships.feeling` | History, tension, scenes in `## Relationships` |
| `knowledge` (facts list) | How/when learned in `## Background` or `## Arc` |
| `scenes: [1, 3, 7]` | What happens in `screenplay.md` |
| `rules` (world) | Why rules exist, history in body |
| `status` (plot) | Current state, obstacles in body |

Some frontmatter fields are **terminal** — specific values that need no prose: `age`, `story_role`, `scenes`, `sections`.

### Standard Body Sections

Enforce these headings so the index can target retrieval by name:

**Character**: `Personality`, `Background`, `Voice`, `Greatest Fear`, `Secrets`, `Arc`, `Relationships`, `Goals`, `Plot Involvement`

**Location**: `Description`, `History`, `Scenes`

**World**: `Description`, `History`, `Conflict`

**Plot**: `Summary`, `Obstacles`, `Stakes`

### Three-Stage Retrieval

```
Stage 1: Index (always loaded)
    ↓ identifies entities, connections, available sections
Stage 2: Section targeting
    ↓ determines which ## sections to load
Stage 3: Content loading
    ↓ loads only the targeted prose via regex section parser
```

### Example: "What's Mara's voice like?"

1. **Index**: `mara` → sections include `Voice`
2. **Target**: `characters/mara.md` → `## Voice` section
3. **Load**: 
   ```
   ## Voice
   Precise, clinical. Rarely uses contractions. Avoids eye contact when lying.
   Speaks in short sentences under stress. Uses accounting metaphors in 
   emotional conversations (unconscious tell).
   ```
4. **Answer** — 4 lines loaded, not the whole note, not the whole project

### Example: "What does Mara know by the end of scene 12?"

1. **Index**: `mara` → scenes `[1, 3, 7, 12, 15, 22]`, knowledge `["Her brother Daniel was murdered", "Victor Hale is the cartel's CFO"]`
2. **Target**: `characters/mara.md` → `## Background` + `## Arc`
3. **Target**: `screenplay.md` → scenes 7-12 only
4. **Target**: `.story/memory.md` → `## CHARACTER KNOWLEDGE` section
5. **Load**: 3 small sections from 3 files
6. **Answer**

### Example: "Who's in the Kitchen scene?"

1. **Index**: `kitchen` → scene 7
2. **Index**: scene 7 → characters `[mara, detective-oak]`
3. **Index**: `mara` → one_sentence: "Forensic accountant..." (already in index)
4. **Answer** — zero content loads, the index has everything

---

## Stage 1: Schema & Conventions

### Vault structure for a story project

```
~/story-vault/
├── .story/
│   ├── index.yaml                      # Project graph (always-loaded)
│   ├── memory.md                       # Story Memory (continuity map)
│   └── history.md                      # Edit history (gitignored)
└── projects/
    └── <project-slug>/
        ├── project.md                  # Project metadata
        ├── title-page.md
        ├── synopsis.md
        ├── treatment.md                # Ordered outline, one paragraph per beat
        ├── screenplay.md               # Fountain syntax
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

### Frontmatter Schemas

**Character** (`characters/<slug>.md`):
```yaml
---
name: Mara Chen
story_role: Protagonist
one_sentence: Forensic accountant who finds her firm laundering cartel money.
age: 34
sections:
  - Personality
  - Background
  - Voice
  - Greatest Fear
  - Secrets
  - Arc
  - Relationships
  - Goals
relationships:
  - id: detective-oak
    feeling: Wary respect
  - id: victor-hale
    feeling: Fear — he knows what she's found
scenes:
  - "INT. MARA'S APARTMENT - NIGHT"
  - "INT. POLICE STATION - DAY"
  - "INT. KITCHEN - NIGHT"
goals:
  short: Find the account number her brother left behind.
  long: Burn the cartel's financial network to the ground.
knowledge:
  - Her brother Daniel was murdered
  - Victor Hale is the cartel's CFO
---

## Personality
Meticulous, introverted, dry humor. Avoids conflict until cornered.

## Background
Parents immigrated from Taiwan. Older brother Daniel died in a car 
accident she believes was murder.

## Voice
Precise, clinical. Rarely uses contractions. Avoids eye contact when lying.
Speaks in short sentences under stress. Uses accounting metaphors in 
emotional conversations (unconscious tell).

## Greatest Fear
That she's complicit in the system she serves.

## Secrets
Has been skimming small amounts to fund her own investigation.

## Arc
Starts believing the law protects the innocent. Ends believing 
the law is a weapon.

## Relationships
### Detective Oak
They meet at her brother's grave. Wary alliance that deepens into trust.

### Victor Hale
Her boss. She doesn't yet know he's the cartel's CFO.

## Goals
**Short-term:** Find the account number. It's the thread that unravels everything.

**Long-term:** Burn the network. Not just expose it — destroy it.
```

**Location** (`locations/<slug>.md`):
```yaml
---
name: The Kitchen
one_sentence: Commercial kitchen in a closed restaurant.
scenes:
  - "INT. KITCHEN - NIGHT"
sections:
  - Description
  - History
  - Scenes
---

## Description
Stainless steel, harsh fluorescent lights, the smell of old grease.

## History
The restaurant closed six months ago. The cartel bought the building.

## Scenes
**Scene 7:** Mara meets Oak here for the first time.
```

**World** (`worlds/<slug>.md`):
```yaml
---
name: Gilead
one_sentence: Near-future city-state where water is privatized.
rules:
  - Water rationing is enforced by biometric scanners.
  - Off-grid water extraction is a capital offense.
  - The police are funded by AquaCorp.
sections:
  - Description
  - History
  - Conflict
---

## Description
Built on the corpse of a democracy. The corporations didn't overthrow 
the government — they just bought the water supply.

## History
Twenty years ago, a drought. The city council sold the water rights.

## Conflict
The cartel controls the black-market water trade.
```

**Project** (`project.md`):
```yaml
---
name: The Water Audit
logline: A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state.
genre: Sci-fi thriller
setting: Near-future city-state
---
```

**Plot Thread** (`plots/<slug>.md`):
```yaml
---
name: Brother Investigation
status: active
setups:
  - "INT. MARA'S APARTMENT - NIGHT"
  - "INT. POLICE STATION - DAY"
payoffs:
  - "INT. KITCHEN - NIGHT"
characters:
  - mara
  - detective-oak
sections:
  - Summary
  - Obstacles
  - Stakes
---

## Summary
Mara's brother Daniel left behind a cryptic note with an account number.

## Obstacles
- The account number is encrypted.
- Victor Hale is watching her.

## Stakes
If Mara fails, the cartel keeps laundering. Daniel's death stays unsolved.
```

### The Project Index (`.story/index.yaml`)

The index maintains **basic visibility** — enough to navigate the project, answer simple queries, and target retrieval without loading content.

```yaml
project:
  slug: the-water-audit
  name: The Water Audit
  logline: "A forensic accountant discovers..."
  genre: Sci-fi thriller
  setting: Near-future city-state
  scene_count: 24
  character_count: 8
  world_count: 2
  plot_count: 3

characters:
  - id: mara
    name: Mara Chen
    role: Protagonist
    one_sentence: "Forensic accountant who finds her firm laundering cartel money."
    sections: [Personality, Background, Voice, Greatest Fear, Secrets, Arc, Relationships, Goals]
    scenes: [1, 3, 7, 12, 15, 22]
    related:
      - {id: detective-oak, feeling: Wary respect}
      - {id: victor-hale, feeling: Fear — he knows what she's found}
    goals_short: "Find the account number her brother left behind."
    goals_long: "Burn the cartel's financial network to the ground."
    knowledge:
      - "Her brother Daniel was murdered"
      - "Victor Hale is the cartel's CFO"

locations:
  - id: kitchen
    name: The Kitchen
    one_sentence: "Commercial kitchen in a closed restaurant."
    sections: [Description, History, Scenes]
    scenes: [7]

worlds:
  - id: gilead
    name: Gilead
    one_sentence: "Near-future city-state where water is privatized."
    sections: [Description, History, Conflict]
    rules:
      - "Water rationing is enforced by biometric scanners."
      - "Off-grid water extraction is a capital offense."
      - "The police are funded by AquaCorp."

scenes:
  - id: 1
    heading: "INT. MARA'S APARTMENT - NIGHT"
    characters: [mara]
    locations: []
    plots: [brother-investigation]
  - id: 7
    heading: "INT. KITCHEN - NIGHT"
    characters: [mara, detective-oak]
    locations: [kitchen]
    plots: [brother-investigation, cartel-discovery]

plots:
  - id: brother-investigation
    name: Brother Investigation
    status: active
    setups: [1, 3]
    payoffs: [22]
    characters: [mara, detective-oak]
    sections: [Summary, Obstacles, Stakes]
    one_sentence: "Mara follows her brother's account number into the cartel's network."

story_memory:
  last_updated: 2026-09-06T14:30:00
  continuity_risks: 2
  headings:
    - CHARACTERS & RELATIONSHIPS
    - CHARACTER KNOWLEDGE
    - TIMELINE
    - PLOT THREADS
    - SETUPS & PAYOFFS
    - WORLD RULES
    - VOICE & STYLE
    - CONTINUITY RISKS
  summary: |
    Mara and Oak are allied but don't fully trust each other. Victor 
    Hale is the cartel's CFO — Mara doesn't know yet.
```

### What "basic visibility" means in the index

The index contains enough to:

1. **See all entities** — names, roles, one-sentence descriptions
2. **See all connections** — who's related to whom, who's in which scene
3. **Answer simple queries** — "Who's the protagonist?" → Mara Chen, forensic accountant...
4. **Target retrieval** — "What's Mara's voice?" → `characters/mara.md` → `## Voice` section
5. **Navigate the story** — scene list, plot status, world rules
6. **Check continuity** — knowledge states, timeline, risks

The index does **not** contain:
- Full personality descriptions
- Dialogue or scene content
- Detailed relationship history
- World history prose

---

## Stage 2: Story Loader Skill

### Behavior
1. User says "load project the-water-audit"
2. The skill reads `.story/index.yaml` into context
3. The skill reads `.story/memory.md` into context
4. Hermes confirms: "Loaded project X — 24 scenes, 8 characters, 3 worlds. Ready."

### What the LLM now knows
- All entity IDs and their connections (from index)
- Current continuity state (from memory)
- Where to find any piece of content (from index)
- What sections each note has (from index)

### Index maintenance
- After any edit, the index must be updated
- A script (`scripts/update_index.py`) can regenerate the index from the vault
- The LLM can call this script after applying an edit

**Output**: `skills/story-loader/SKILL.md` + `skills/story-loader/scripts/update_index.py`

---

## Stage 3: Story Editor Skill (Schema-Guided Retrieval + Action Protocol)

### Retrieval loop
When the user makes a query:
1. Hermes reads the index to find relevant entities and sections
2. Loads only those sections into context (via section parser)
3. Reasons about the targeted content
4. Proposes an action

### Section Parser

Zero-dependency regex section parser:

```python
import re

SECTION_RE = re.compile(r'^(##\s+.+)$', flags=re.MULTILINE)

def list_sections(content: str) -> list[str]:
    return SECTION_RE.findall(content)

def get_section(content: str, section: str) -> str:
    parts = SECTION_RE.split(content)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        body_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.lower() == section.lower():
            return f"## {heading}\n{body_text}"
    return ""

def replace_section(content: str, section: str, new_body: str) -> str:
    parts = SECTION_RE.split(content)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        if heading.lower() == section.lower():
            parts[i + 1] = '\n\n' + new_body
            return ''.join(parts)
    return content
```

### Actions

| Action | What it does | Target |
|--------|-------------|--------|
| `edit_note` | Edit any project/character/location/world/plot note | note path |
| `edit_screenplay` | Add/replace/delete screenplay content | scene range |
| `create_entity` | Add a new character/location/world/plot | entity type |
| `delete_entity` | Move entity to `_recycle-bin/` | entity id |
| `answer` | Conversational response, no edit | — |
| `suggest_ideas` | Brainstorm possibilities, no edit | — |
| `insert_screenplay` | Add new scene/paragraphs | `cursor`, `beginning`, `end` |
| `replace_selection` | Replace selected text | `selection` |
| `delete_selection` | Remove selected text | `selection` |
| `update_logline` | Change the logline | `logline` |
| `replace_synopsis` | Rewrite the synopsis | `synopsis` |
| `revise_treatment` | Revise treatment paragraphs | `treatment` |
| `create_character` | Add a new character note | `characters` |
| `update_character` | Edit character fields | `characters` |
| `remove_character` | Move character to recycle bin | `characters` |
| `merge_character` | Merge two characters | `characters` |
| `update_character_relationship` | Add/edit relationship | `character_relationships` |
| `update_story_memory` | Refresh Story Memory | `story_memory` |

### Review loop
1. User makes a request
2. Hermes retrieves relevant sections via index
3. Hermes returns a **proposed action** with:
   - The action type and target
   - The content (Fountain for screenplay, YAML fields for characters)
   - A summary of what it does
   - Continuity checks (conflicts + notes)
4. Hermes shows the proposal in chat
5. User approves or rejects
6. On approval, the skill applies the edit to the vault file
7. The index is updated

### Safety
- No edit is applied without explicit approval
- Character removal → move to `_recycle-bin/` folder, don't delete screenplay prose

**Output**: `skills/story-editor/SKILL.md` + `skills/story-editor/scripts/`

---

## Stage 4: Preview Pane Dashboard

### Views
1. **Project overview**: logline, synopsis, treatment outline, scene count
2. **Character map**: vis-network force-directed graph. Nodes = characters, edges = relationships. Click to see full profile + scenes.
3. **Scene list**: all scenes with headings, click to see full scene content
4. **Timeline**: chronological view of scenes (if time-of-day is parseable from Fountain headings)
5. **Continuity report**: current setups/payoffs, knowledge states, risks

### Interaction
- Click a character node → see their profile, relationships, scenes
- Click a scene → see the full scene text
- Click a location → see where it appears
- "Ask Hermes about this" buttons send a pre-formulated prompt

### Technical
- Single HTML file with embedded CSS/JS
- vis-network (MIT/Apache 2.0) loaded from CDN
- Reads from `.story/index.yaml` for structure, vault for content
- Updates when the project changes (manual refresh or file watcher)

**Output**: `src/dashboard/story-dashboard.html`

---

## Dependencies

```python
rapidfuzz>=3.0
python-frontmatter>=1.0
screenplay-tools>=0.0.10
```

- `screenplay-tools`: Fountain parse + write (round-trip editing)
- `python-frontmatter`: YAML frontmatter load/modify/dump
- `rapidfuzz`: Fuzzy name matching (typo tolerance)
- `vis-network`: Graph visualization, loaded via CDN in HTML dashboard (not pip)

---

## Immediate Next Steps

1. ✅ Create repo folder
2. ✅ Save research notes (STARC data model)
3. ✅ Verify open-source dependencies (research report)
4. ✅ Write `vault-conventions.md` (schemas + section retrieval + frontmatter→body mapping)
5. ✅ Deep-dive dependency research (APIs, constraints, integration patterns)
6. ⬜ Build the index generator script
7. ⬜ Build the Story Loader skill
8. ⬜ Build the Story Editor skill (Action Protocol)
9. ⬜ Build the preview pane dashboard
10. ⬜ Test with a real project
