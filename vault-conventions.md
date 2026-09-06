# Vault Conventions — Story Architect

> How story projects live in the vault. Frontmatter for the index, standard body sections for targeted retrieval, prose for depth.

---

## The Principle

**Frontmatter** = what the index needs to find and connect entities. Small, structured, machine-readable.

**Standard body sections** = retrieval targets the LLM loads by name. Not whole notes — just the `## Heading` that answers the query.

**Prose within sections** = depth. Personality, voice, history, motivation — the "why" behind the frontmatter label.

---

## Project Structure

```
work/creative/projects/<project-slug>/
├── project.md                  # Project metadata
├── title-page.md
├── synopsis.md
├── treatment.md                # Ordered outline, one paragraph per beat
├── screenplay.md               # Fountain syntax
├── characters/
│   ├── mara.md
│   ├── detective-oak.md
│   └── _index.md               # Auto-generated character list
├── locations/
│   ├── kitchen.md
│   └── _index.md
├── worlds/
│   ├── gilead.md
│   └── _index.md
├── plots/
│   └── main-plot.md
└── .story/
    ├── index.yaml              # Project graph (always-loaded)
    ├── memory.md               # Story Memory (continuity map)
    └── history.md              # Edit history (gitignored)
```

---

## Frontmatter → Body Mapping

Every frontmatter field that summarizes or labels something has a **detailed counterpart** in the body. This is the core pattern:

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

Some frontmatter fields are **terminal** — specific values that need no prose:
- `age: 34`
- `story_role: Protagonist`
- `scenes: [1, 3, 7]` (references)
- `sections: [...]` (retrieval target list)

---

## Standard Body Sections

Enforce these headings so the index can target retrieval by name:

### Character

Required sections (use all that apply):

| Section | What it contains |
|---------|-----------------|
| `## Personality` | Traits, habits, mannerisms |
| `## Background` | History, family, formative events |
| `## Voice` | Dialogue style, speech patterns, vocabulary |
| `## Greatest Fear` | Core fear, how it manifests |
| `## Secrets` | What they hide, from whom |
| `## Arc` | Belief change, growth, transformation |
| `## Relationships` | Per-character subsections with depth |
| `## Goals` | Why the short/long-term goals matter |
| `## Plot Involvement` | Their role in the narrative |

### Location

| Section | What it contains |
|---------|-----------------|
| `## Description` | Sensory details, mood, atmosphere |
| `## History` | What happened here, why it matters |
| `## Scenes` | Dramatic purpose in each scene |

### World

| Section | What it contains |
|---------|-----------------|
| `## Description` | The world's feel, scale, tone |
| `## History` | How it became what it is |
| `## Conflict` | Tensions, factions, power dynamics |

### Plot

| Section | What it contains |
|---------|-----------------|
| `## Summary` | The thread in prose |
| `## Obstacles` | What stands in the way |
| `## Stakes` | What happens if it fails/succeeds |

---

## Entity Schemas

### Character (`characters/<slug>.md`)

```yaml
---
name: Mara Chen
story_role: Protagonist
one_sentence: Forensic accountant who finds her firm laundering cartel money.
age: 34
sections:                          # Standard headings available in body
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
Trusts numbers more than people — they don't lie, they don't have agendas.

## Background
Parents immigrated from Taiwan in the 80s. Older brother Daniel died in a 
car accident when Mara was 19. She's always believed it was murder — 
Daniel had been asking questions about his employer's finances.

## Voice
Precise, clinical. Rarely uses contractions. Avoids eye contact when lying.
Speaks in short sentences under stress. Uses accounting metaphors in 
emotional conversations (unconscious tell).

## Greatest Fear
That she's complicit in the system she serves. That by the time she 
acts, it's already too late. That Daniel died for nothing.

## Secrets
Has been skimming small amounts from client accounts to fund her own 
investigation. If discovered, she loses everything — license, freedom, 
the only career she's ever had.

## Arc
**Starts:** Believes the law protects the innocent. The system works 
if you work it correctly.

**Ends:** Believes the law is a weapon — you just have to learn to aim 
it. The system is broken, but you can still use its pieces.

## Relationships
### Detective Oak
They meet at her brother's grave. Wary alliance that deepens into trust 
— the only person Mara relies on. But Oak is being watched, and 
association with him puts her at risk.

### Victor Hale
Her boss. Mentor figure. She doesn't yet know he's the cartel's CFO.
When she finds out, it breaks something fundamental.

## Goals
**Short-term:** Find the account number. It's the thread that unravels 
everything. She needs it before the cartel notices she's looking.

**Long-term:** Burn the network. Not just expose it — destroy it so it 
can't be rebuilt. This is personal.
```

### Location (`locations/<slug>.md`)

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
A place that used to feed people. Now it's where deals happen after hours.

## History
The restaurant closed six months ago when the owner couldn't pay his 
water bill. The cartel bought the building. They use the kitchen for 
meetings — the industrial fans cover conversation, the back alley 
offers a quick exit.

## Scenes
**Scene 7:** Mara meets Oak here for the first time. The empty kitchen 
mirrors the emptiness of the case — no leads, no evidence, just two 
people who don't trust each other.
```

### World (`worlds/<slug>.md`)

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
the government — they just bought the water supply and let the government 
come to them. Now the city runs on recycled rainwater and corporate 
generosity.

## History
Twenty years ago, a drought. The city council sold the water rights 
to AquaCorp in exchange for infrastructure investment. The investment 
never came. The rights never returned.

## Conflict
The cartel controls the black-market water trade. The police are paid 
to look the other way — but some cops are starting to ask questions. 
The water isn't just a resource; it's the leash.
```

### Project (`project.md`)

```yaml
---
name: The Water Audit
logline: A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state.
genre: Sci-fi thriller
setting: Near-future city-state
---
```

### Plot Thread (`plots/<slug>.md`)

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
Following it leads her into the cartel's financial network — and makes 
her the next target.

## Obstacles
- The account number is encrypted.
- Victor Hale is watching her.
- Oak's captain is on the cartel's payroll.

## Stakes
If Mara fails, the cartel keeps laundering. Daniel's death stays 
unsolved. The water stays privatized. The leash stays on.
```

---

## The Project Index (`.story/index.yaml`)

The index maintains **basic visibility** — enough to navigate the project, answer simple queries, and target retrieval without loading content.

```yaml
project:
  slug: the-water-audit
  name: The Water Audit
  logline: "A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state."
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

  - id: detective-oak
    name: Detective Oak
    role: Deuteragonist
    one_sentence: "Homicide detective investigating the same cartel."
    sections: [Personality, Background, Voice, Arc, Relationships]
    scenes: [3, 7, 15, 22]
    related:
      - {id: mara, feeling: Wary respect — she's useful but unpredictable}
    goals_short: "Bring down the cartel's leadership."
    goals_long: "Redeem his failure to protect his last partner."
    knowledge:
      - "The cartel has a financial network"
      - "Someone inside the firm is asking questions"

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
  - id: 12
    heading: "INT. TRAIN STATION - DAY"
    characters: [mara]
    locations: [train-station]
    plots: [cartel-discovery]

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
    Hale is the cartel's CFO — Mara doesn't know yet. Two continuity 
    risks: Mara's skimming hasn't been discovered (ticking clock), 
    and Oak's investigation is off-books (if his captain finds out, 
    he's burned).
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

## Retrieval Logic

### Three-stage retrieval

```
Stage 1: Index (always loaded)
    ↓ identifies entities, connections, available sections
Stage 2: Section targeting
    ↓ determines which ## sections to load
Stage 3: Content loading
    ↓ loads only the targeted prose
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
2. **Target**: `characters/mara.md` → `## Background` (how she learned it) + `## Arc` (what she does with it)
3. **Target**: `screenplay.md` → scenes 7-12 only
4. **Target**: `.story/memory.md` → `## CHARACTER KNOWLEDGE` section
5. **Load**: 3 small sections from 3 files
6. **Answer**

### Example: "Who's in the Kitchen scene?"

1. **Index**: `kitchen` → scene 7
2. **Index**: scene 7 → characters `[mara, detective-oak]`
3. **Index**: `mara` → one_sentence: "Forensic accountant..." (already in index, no load needed)
4. **Index**: `detective-oak` → one_sentence: "Homicide detective..." (already in index, no load needed)
5. **Answer** — zero content loads, the index has everything

### Example: "Tell me everything about Mara"

1. **Index**: `mara` → all sections listed
2. **Target**: `characters/mara.md` → full note (all sections)
3. **Load**: the whole note
4. **Answer** — full load, but only one note, not the whole project

---

## Section Parser

```python
import re
from pathlib import Path

def load_section(note_path: str, section: str) -> str:
    """Load a single ## section from a markdown note."""
    content = Path(note_path).read_text()
    # Split on ## headings, keep the heading name with its content
    parts = re.split(r'^(## \w+(?:\s+\w+)*)', content, flags=re.MULTILINE)
    # parts[0] is frontmatter + preamble
    # parts[1:] alternate: heading, content, heading, content...
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.lower() == section.lower():
            return f"## {heading}\n{body}"
    return ""

def load_note(note_path: str) -> str:
    """Load the full note (all sections)."""
    return Path(note_path).read_text()

def list_sections(note_path: str) -> list[str]:
    """List all ## section headings in a note."""
    content = Path(note_path).read_text()
    return re.findall(r'^## (.+)$', content, flags=re.MULTILINE)
```

---

## Fountain Screenplay (`screenplay.md`)

Standard Fountain syntax. Scene headings must match the index exactly.

```fountain
INT. MARA'S APARTMENT - NIGHT

Mara sits at her desk, laptop glowing. She stares at a spreadsheet.

MARA
These numbers don't add up.

She highlights a column. Copies it. Pastes it into a new file.

EXT. CITY STREET - DAY

Rain. Mara walks, collar up, phone to her ear.

MARA (INTO PHONE)
I need to see the original filings.

CUT TO:
```

The index tracks which characters and locations appear in each scene. The screenplay is the source of truth for scene content.

---

## Treatment (`treatment.md`)

Ordered outline. Each paragraph maps to a beat or scene.

```markdown
# Treatment

## Act One

MARA CHEN, 34, forensic accountant, lives alone with her spreadsheets. 
She's good at her job — too good. While auditing a client, she finds 
a discrepancy that leads to a shell company.

She follows the money. It leads to her own firm.

## Act Two

Mara teams up with DETECTIVE OAK, who's been investigating the same 
cartel from the police side. They don't trust each other, but they 
need each other.

The cartel notices. People start dying.

## Act Three

Mara has the evidence. But exposing it means exposing her own 
complicity — she's been skimming to fund her investigation. 
She has to choose: the truth, or her freedom.
```

---

## Story Memory (`.story/memory.md`)

Eight canonical headings (from STARC's Continuity Gate):

```markdown
# Story Memory

## CHARACTERS & RELATIONSHIPS
- Mara and Detective Oak meet at her brother's grave. Wary alliance.
- Victor Hale is Mara's boss AND the cartel's CFO. She doesn't know yet.

## CHARACTER KNOWLEDGE
- Mara knows: brother was murdered, account number exists.
- Mara doesn't know: Victor is CFO, Oak is being watched.

## TIMELINE
- Day 1: Mara finds the account number.
- Day 3: First contact with Oak.
- Day 7: Kitchen scene — the cartel knows someone is asking questions.

## PLOT THREADS
- Brother investigation: ACTIVE. Setup in scene 1, payoff pending.
- Cartel discovery: ACTIVE. Setup in scene 7, payoff pending.

## SETUPS & PAYOFFS
- Setup (scene 1): Daniel's note with account number.
- Setup (scene 3): Oak mentions the cartel's financial network.
- Payoff: Pending — Mara uses the account number to trace the money.

## WORLD RULES
- Water rationing is enforced by biometric scanners.
- Off-grid water extraction is a capital offense.
- The police are funded by AquaCorp.

## VOICE & STYLE
- Mara: precise, clinical, no contractions under stress.
- Oak: dry, sardonic, cop cadence.
- Narration: close third person, present tense.

## CONTINUITY RISKS
- Mara's skimming (scene 3) hasn't been discovered yet — ticking clock.
- Oak's investigation is off-books — if his captain finds out, he's burned.
```

---

## Summary: What Lives Where

| Data | Where | Loaded when? |
|------|-------|-------------|
| Entity IDs, roles, connections | Frontmatter | Always (via index) |
| Scene headings, characters per scene | Frontmatter + screenplay | Always (via index) |
| One-sentence summaries | Frontmatter | Always (via index) |
| Available sections list | Frontmatter (`sections:`) | Always (via index) |
| Personality, voice, arc, depth | Body sections | On demand (by section name) |
| Location description, mood | Body sections | On demand |
| World rules | Frontmatter | Always (via index) |
| World history, conflict | Body sections | On demand |
| Scene content (dialogue, action) | `screenplay.md` | On demand (by scene range) |
| Continuity state | `.story/memory.md` | Always |
| Edit history | `.story/history.md` | On demand |

---

## Index Maintenance

The index is **regenerated** from the vault:
- After any edit (character created, scene added, relationship changed)
- On project load (to catch manual edits)
- On demand (user says "reindex project")

A script (`scripts/update_index.py`) walks the vault, reads frontmatter from all entity notes, and rebuilds `.story/index.yaml`.
