# Hermes Story Architect — Plan

> **Goal**: Build a story-writing environment inside Hermes Desktop, using STARC's data model and action protocol as the architectural reference. The writer works with Markdown + YAML frontmatter in the vault; Hermes provides the intelligence layer; the preview pane provides interactive navigation.

---

## Stage 1: Schema & Conventions

**What**: Define the entity types, fields, and vault structure. No code — just conventions.

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
    ├── memory.md           # Story Memory (continuity map)
    └── history.md          # Edit history (local, not in vault)
```

### Frontmatter schemas (from STARC's Character fields)

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
---
```

**Location** (`locations/<name>.md`):
```yaml
---
name: The Kitchen
description: A commercial kitchen in a closed restaurant. Stainless steel, harsh fluorescent lights, the smell of old grease.
scenes: 
  - "INT. KITCHEN - NIGHT"   # scene headings where this appears
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

### Conventions
- Every entity note has a stable filename (slug) that acts as its ID
- Relationships are expressed via `relationships:` frontmatter array (character → character) and `scenes:` (location → screenplay)
- The screenplay uses Fountain syntax (scene headings, action, character cues, dialogue)
- Treatment is an ordered list of prose paragraphs, each mapping to a beat
- Story Memory is a separate note with the 8 canonical headings

**Output**: A `vault-conventions.md` document in the repo. A Hermes skill that scaffolds a new project from these templates.

---

## Stage 2: Story Loader Skill

**What**: A Hermes skill that loads a project's full story package into context.

### Behavior
1. User opens a project (or says "load project X")
2. The skill reads: `project.md`, `synopsis.md`, `treatment.md`, `screenplay.md`, all `characters/*.md`, all `locations/*.md`, all `worlds/*.md`, `.story/memory.md`
3. Assembles a structured story context object
4. Injects it into the conversation (or keeps it ready for the current session)

### Story context object
```yaml
project:
  name, logline, genre, setting
synopsis: <full text>
treatment:
  - paragraph 1
  - paragraph 2
screenplay:
  - scene: "INT. KITCHEN - NIGHT"
    paragraphs:
      - {type: action, text: "..."}
      - {type: character, name: "MARA"}
      - {type: dialogue, text: "..."}
characters:
  - name, story_role, motivation, fear, goal, ...
    relationships: [{name, feeling, details}]
locations:
  - name, description, scenes
worlds:
  - name, rules
story_memory:
  - CHARACTERS & RELATIONSHIPS: ...
  - CHARACTER KNOWLEDGE: ...
  - TIMELINE: ...
  - PLOT THREADS: ...
  - SETUPS & PAYOFFS: ...
  - WORLD RULES: ...
  - VOICE & STYLE: ...
  - CONTINUITY RISKS: ...
```

### Continuity checks (from STARC's Continuity Gate)
The skill can run a continuity audit:
- Character knowledge: does a character know something they shouldn't?
- Chronology: are events in a logical order?
- Location: is a character where they can't be?
- World rules: does something violate established rules?
- Setups/payoffs: is a setup without a payoff?
- Voice: is dialogue out of character?

**Output**: `skills/story-loader/SKILL.md` + `skills/story-loader/scripts/load_project.py`

---

## Stage 3: Story Editor Skill (Action Protocol)

**What**: A Hermes skill that lets the LLM propose and apply structured edits to the project.

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
1. User makes a request ("Generate a scene where Mara confronts Victor")
2. Hermes returns a **proposed action** with:
   - The action type and target
   - The content (Fountain for screenplay, YAML fields for characters)
   - A summary of what it does
   - Continuity checks (impact, conflicts)
3. Hermes shows the proposal in chat
4. User approves or rejects
5. On approval, the skill applies the edit to the vault file

### Safety
- No edit is applied without explicit approval
- Character removal → move to `_recycle-bin/` folder, don't delete screenplay prose
- Character merge → snapshot before merge, allow rollback
- Stale protection: if the file changed since the proposal, re-read before applying

**Output**: `skills/story-editor/SKILL.md` + `skills/story-editor/scripts/apply_action.py`

---

## Stage 4: Preview Pane Dashboard

**What**: An interactive HTML dashboard that renders in the Hermes preview pane.

### Views
1. **Project overview**: logline, synopsis, treatment outline, scene count
2. **Character map**: list of characters with roles, click to see full profile + scenes
3. **Scene list**: all scenes with headings, click to see full scene content
4. **Timeline**: chronological view of scenes (if time-of-day is parseable)
5. **Continuity report**: current setups/payoffs, knowledge states, risks

### Interaction
- Click a character → see their profile, relationships, scenes
- Click a scene → see the full scene text
- Click a location → see where it appears
- "Ask Hermes about this" buttons that send a pre-formulated prompt

### Technical
- Single HTML file with embedded CSS/JS
- Reads from the vault via Hermes' `obsidian_*` tools or by reading files directly
- Updates when the project changes (file watcher or manual refresh)

**Output**: `src/dashboard/story-dashboard.html`

---

## Stage 5: Writer's Room Mode (Optional)

**What**: Hermes observes your writing and offers advisory notes after a quiet period.

### Behavior
- After a meaningful burst of writing (new scene, new character, etc.)
- Wait ~45 seconds of inactivity
- Hermes offers a short note:
  1. Strongest recent development
  2. One continuity or structural watchpoint
  3. One concrete possibility for the next turn
- Advisory only — no edits without approval
- 5-minute cooldown between notes

**Output**: Integrated into the Story Editor skill.

---

## Stage 6: Story Method Skills (Optional)

**What**: Port the `edit-story` and `eric-edson-story-skill` methods as Hermes skills.

### `edit-story` method
- Protects canon, author voice, character knowledge, chronology, relationships, world rules, setups/payoffs
- General-purpose for continuing or rewriting scenes

### `eric-edson-story-skill` method
- Hero Goal sequences
- Three-act tent poles
- Stunning Surprises
- Character-function analysis (adversary, love interest, sidekick, mentor, endangered innocent)

### Why separate?
- A visible selection makes the creative lens predictable
- Keeps the edit record meaningful
- Lets the writer compare approaches

**Output**: `skills/edit-story/SKILL.md`, `skills/eric-edson-story-skill/SKILL.md`

---

## Immediate Next Steps

1. ✅ Create repo folder
2. ✅ Save research notes (STARC data model)
3. ⬜ Write `vault-conventions.md` (the schemas above, refined)
4. ⬜ Build the Story Loader skill
5. ⬜ Build the Story Editor skill (Action Protocol)
6. ⬜ Build the preview pane dashboard
7. ⬜ Test with a real project (your TV series?)

---

## Open Questions

- **Fountain syntax**: Do we use a strict subset? Full Fountain? The screenplay.md is the only file that needs Fountain parsing.
- **Relationships**: Frontmatter `relationships:` array vs. separate `relationships.md` note. Frontmatter is simpler but can get long.
- **Story Memory**: Auto-generated by Hermes after each edit, or manually maintained? STARC auto-generates but allows correction.
- **Edit history**: Store in `.story/history.md` (local, gitignored) or in the vault? STARC stores it in Qt settings, not in the project file.
- **Multi-project**: How does Hermes know which project is "active"? Via the conversation, or a `.story/active-project` pointer?
