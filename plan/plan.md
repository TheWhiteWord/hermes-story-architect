# Hermes Story Architect — Plan (v2)

> **Goal**: Build a story-writing environment inside Hermes Desktop, architecturally inspired by [Story Architect](https://github.com/story-apps/starc) (STARC). Story projects live as Markdown + YAML frontmatter in the vault. Hermes provides the intelligence layer with **targeted retrieval** — not full-project loading. The preview pane provides interactive navigation.

---

## Core Architecture: Three Layers

```
Layer 1: Project Index (.story/index.yaml)     ← small, ALWAYS in context
    ↓ describes what exists, how it connects
Layer 2: Retrieval (schema-guided)              ← find relevant files
    ↓ targets specific content based on query
Layer 3: Content (vault notes)                  ← loaded on demand
    ↓ only the pieces needed RIGHT NOW
```

The index is a graph: characters, locations, scenes, plot threads, worlds are nodes. Relationships, scene memberships, setups/payoffs are edges.

**Why this matters**: A 40-character story with 60 scenes is tens of thousands of tokens. We only load what the query needs.

---

## Stage 1: Schema & Conventions

### Vault structure for a story project
```
work/creative/projects/<project-slug>/
├── project.md              # Project metadata (logline, genre, etc.)
├── title-page.md
├── synopsis.md
├── treatment.md            # Ordered outline, one paragraph per beat
├── screenplay.md           # Fountain syntax, scenes + paragraphs
├── characters/
│   ├── mara.md             # YAML frontmatter + prose
│   ├── detective-oak.md
│   └── _index.md           # Character list (auto-generated)
├── locations/
│   ├── kitchen.md
│   └── _index.md
├── worlds/
│   ├── gilead.md
│   └── _index.md
├── plots/
│   └── main-plot.md
└── .story/
    ├── index.yaml          # Project graph (always-loaded)
    ├── memory.md           # Story Memory (continuity map)
    └── history.md          # Edit history (local, gitignored)
```

### Frontmatter schemas (from STARC's Character fields + our design)

**Character** (`characters/<name>.md`):
```yaml
---
name: Mara Chen
story_role: Protagonist
age: 34
nickname: 
one_sentence_description: A forensic accountant who discovers her firm is laundering money for a cartel.
long_description: |
  Brilliant but socially awkward. Trusts numbers more than people.
family: Parents immigrated from Taiwan; older brother died in a car accident she believes was murder.
personality: Meticulous, introverted, dry humor, avoids conflict until cornered.
motivation: Prove her brother's death wasn't an accident.
moral: Believes in institutional justice — the system should work.
greatest_fear: That she's complicit in the system she serves.
secrets: Has been skimming small amounts to fund her own investigation.
short_term_goal: Find the account number her brother left behind.
long_term_goal: Burn the cartel's financial network to the ground.
initial_beliefs: The law protects the innocent.
changed_beliefs: The law is a weapon — you just have to learn to aim it.
plot_involvement: Discovers the laundering, follows the money, becomes the target.
conflict: Her by-the-book nature vs. the extralegal methods needed to survive.
speech: Precise, clinical, rarely uses contractions. Avoids eye contact when lying.
relationships:
  - name: Detective Oak
    feeling: Wary respect — he's useful but represents the system she's losing faith in.
    details: They meet at her brother's grave; he's investigating the same cartel from the police side.
  - name: Victor Hale
    fear: He knows who she is and what she's found.
    details: Her boss, the cartel's CFO.
scenes:
  - "INT. MARA'S APARTMENT - NIGHT"
  - "INT. POLICE STATION - DAY"
  - "INT. KITCHEN - NIGHT"
---
```

**Location** (`locations/<name>.md`):
```yaml
---
name: The Kitchen
description: A commercial kitchen in a closed restaurant. Stainless steel, harsh fluorescent lights, the smell of old grease.
scenes: 
  - "INT. KITCHEN - NIGHT"
---
```

**World** (`worlds/<name>.md`):
```yaml
---
name: Gilead
description: A near-future city-state where water is privatized and the police answer to corporate boards.
rules:
  - Water rationing is enforced by biometric scanners.
  - Off-grid water extraction is a capital offense.
  - The police are funded by AquaCorp.
---
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

### The Project Index (`.story/index.yaml`)

This is the always-loaded heart of the system:

```yaml
project:
  name: the-water-audit
  logline: "A forensic accountant discovers..."
  scene_count: 24
  character_count: 8

entities:
  characters:
    - id: mara
      role: Protagonist
      scenes: [1, 3, 7, 12, 15, 22]
      related: [detective-oak, victor-hale, the-influencer]
    - id: detective-oak
      role: Deuteragonist
      scenes: [3, 7, 15, 22]
      related: [mara]
    # ... one line per character, no prose

  locations:
    - id: kitchen
      scenes: [7]
    - id: train-station
      scenes: [12]

  worlds:
    - id: gilead
      rules_count: 3

  scenes:
    - id: 1
      heading: "INT. MARA'S APARTMENT - NIGHT"
      characters: [mara]
      locations: []
      plot_threads: [brother-investigation]
    - id: 7
      heading: "INT. KITCHEN - NIGHT"
      characters: [mara, detective-oak]
      locations: [kitchen]
      plot_threads: [brother-investigation, cartel-discovery]

  plot_threads:
    - id: brother-investigation
      setups: [1, 3]
      payoffs: [22]
      status: active

  story_memory:
    last_updated: 2026-09-06
    continuity_risks: 2
```

### Conventions
- Every entity note has a stable filename (slug) that acts as its ID
- Relationships are expressed via `relationships:` frontmatter (character → character) and `scenes:` (location → screenplay)
- The screenplay uses Fountain syntax (scene headings, action, character cues, dialogue)
- Treatment is an ordered list of prose paragraphs, each mapping to a beat
- Story Memory is a separate note with the 8 canonical headmatter headings

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

### Index maintenance
- After any edit, the index must be updated
- A script (`scripts/update_index.py`) can regenerate the index from the vault
- The LLM can call this script after applying an edit

**Output**: `skills/story-loader/SKILL.md` + `skills/story-loader/scripts/update_index.py`

---

## Stage 3: Story Editor Skill (Schema-Guided Retrieval + Action Protocol)

### Retrieval loop (new)
When the user makes a query:
1. Hermes reads the index to find relevant files
2. Loads only those files into context
3. Reasons about the targeted content
4. Proposes an action

### Example: "What does Mara know by the end of scene 12?"
1. Index says: Mara is in scenes 1, 3, 7, 12, 15, 22
2. Index says: Scene 12 is at screenplay.md, line ~180
3. Load: `characters/mara.md` (her knowledge field), `screenplay.md` (scenes 7-12 range), `.story/memory.md` (Character Knowledge section)
4. Reason: Mara learned X in scene 7, Y in scene 12...
5. Answer without loading the whole project

### Actions (from STARC Action Protocol V3, simplified)

| Action | What it does | Target |
|--------|-------------|--------|
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
2. Hermes retrieves relevant files via index
3. Hermes returns a **proposed action** with:
   - The action type and target
   - The content (Fountain for screenplay, YAML fields for characters)
   - A summary of what it does
   - Continuity checks (impact, conflicts)
4. Hermes shows the proposal in chat
5. User approves or rejects
6. On approval, the skill applies the edit to the vault file
7. The index is updated

### Dependencies (verified)
```txt
rapidfuzz          # MIT - fuzzy name matching (40% faster than alternatives)
screenplain        # MIT - Fountain parsing (actively developed)
python-frontmatter # MIT - YAML frontmatter in Markdown (healthy, 423 stars)
```

### Safety
- No edit is applied without explicit approval
- Character removal → move to `_recycle-bin/` folder, don't delete screenplay prose
- Character merge → snapshot before merge, allow rollback
- Stale protection: if the file changed since the proposal, re-read before applying
- Transaction log for multi-step edits: before a merge, write intended operations to `.story/transaction-log.json`. If Hermes crashes mid-merge, the log can be replayed or rolled back.

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
- vis-network (MIT/Apache 2.0) loaded from CDN or local static file
- Reads from `.story/index.yaml` for structure, vault for content
- Updates when the project changes (manual refresh or file watcher)

**Output**: `src/dashboard/story-dashboard.html`

---

## Stage 5: Writer's Room Mode (Optional)

After a meaningful burst of writing + 45s quiet + 5min cooldown, Hermes offers a short advisory note:
1. Strongest recent development
2. One continuity or structural watchpoint
3. One concrete possibility for the next turn

Advisory only — no edits without approval.

---

## Stage 6: Story Method Skills (Optional)

Port from STARC's Codex fork:
- `edit-story`: continuity, canon protection, voice preservation
- `eric-edson-story-skill`: Hero Goal sequences, three-act tent poles, Stunning Surprises

---

## Immediate Next Steps

1. ✅ Create repo folder
2. ✅ Save research notes (STARC data model)
3. ✅ Verify open-source dependencies (research report)
4. ⬜ Write `vault-conventions.md` (the schemas above, refined)
5. ⬜ Build the index generator script
6. ⬜ Build the Story Loader skill
7. ⬜ Build the Story Editor skill (Action Protocol)
8. ⬜ Build the preview pane dashboard
9. ⬜ Test with a real project

---

## Open Questions

- **Fountain syntax**: Do we use a strict subset? Full Fountain? `screenplain` supports the full spec.
- **Relationships**: Frontmatter `relationships:` array vs. separate `relationships.md` note. Frontmatter is simpler but can get long.
- **Story Memory**: Auto-generated by Hermes after each edit, or manually maintained? STARC auto-generates but allows correction.
- **Edit history**: Store in `.story/history.md` (local, gitignored) or in the vault? STARC stores it in Qt settings.
- **Multi-project**: How does Hermes know which project is "active"? Via the conversation, or a `.story/active-project` pointer?
- **Index staleness**: The index is only as good as its last update. Do we auto-regenerate after every edit? Or on project load? Or on demand?
