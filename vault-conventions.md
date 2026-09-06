# Vault Conventions — Story Architect

> How story projects live in the vault. Frontmatter for the index, prose for the LLM.

---

## The Principle

**Frontmatter** = what the **index** needs to find and connect entities. Small, structured, always loaded.

**Prose body** = what the **LLM** needs to understand depth, voice, motivation, history. Loaded on demand.

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

## Frontmatter Schemas

### Character (`characters/<slug>.md`)

```yaml
---
name: Mara Chen                    # Display name
story_role: Protagonist            # Protagonist, Antagonist, Deuteragonist, etc.
one_sentence: >-                   # One-line summary for index/overview
  Forensic accountant who finds her firm laundering cartel money.
age: 34
relationships:
  - id: detective-oak
    feeling: Wary respect
  - id: victor-hale
    feeling: Fear — he knows what she's found
scenes:                             # Scene headings this character appears in
  - "INT. MARA'S APARTMENT - NIGHT"
  - "INT. POLICE STATION - DAY"
  - "INT. KITCHEN - NIGHT"
goals:
  short: Find the account number her brother left behind.
  long: Burn the cartel's financial network to the ground.
knowledge:                          # What this character knows (for continuity)
  - "Her brother Daniel was murdered"
  - "Victor Hale is the cartel's CFO"
---
```

**Prose body** (loaded on demand):
```markdown
## Personality
Meticulous, introverted, dry humor. Avoids conflict until cornered.

## Background
Parents immigrated from Taiwan. Older brother Daniel died in a car 
accident she believes was murder.

## Voice
Precise, clinical. Rarely uses contractions. Avoids eye contact when lying.

## Greatest Fear
That she's complicit in the system she serves.

## Secrets
Has been skimming small amounts to fund her own investigation.

## Arc
Starts believing the law protects the innocent. Ends believing the law 
is a weapon — you just have to learn to aim it.
```

### Location (`locations/<slug>.md`)

```yaml
---
name: The Kitchen
one_sentence: Commercial kitchen in a closed restaurant.
scenes:
  - "INT. KITCHEN - NIGHT"
---
```

**Prose body**:
```markdown
Stainless steel, harsh fluorescent lights, the smell of old grease. 
A place that used to feed people. Now it's where deals happen after hours.
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
---
```

**Prose body**:
```markdown
Built on the corpse of a democracy. The corporations didn't overthrow 
the government — they just bought the water supply and let the government 
come to them.
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
status: active                      # active, resolved, abandoned
setups:
  - "INT. MARA'S APARTMENT - NIGHT"
  - "INT. POLICE STATION - DAY"
payoffs:
  - "INT. KITCHEN - NIGHT"
characters:
  - mara
  - detective-oak
---
```

**Prose body**:
```markdown
Mara's brother Daniel left behind a cryptic note with an account number. 
Following it leads her into the cartel's financial network — and makes 
her the next target.
```

---

## The Project Index (`.story/index.yaml`)

This is the always-loaded graph. It contains **no prose** — only IDs, labels, and edges.

```yaml
project:
  slug: the-water-audit
  name: The Water Audit
  logline: "A forensic accountant discovers..."
  scene_count: 24
  character_count: 8
  world_count: 2

characters:
  - id: mara
    role: Protagonist
    one_sentence: "Forensic accountant who finds her firm laundering cartel money."
    scenes: [1, 3, 7, 12, 15, 22]
    related: [detective-oak, victor-hale]
    goals_short: "Find the account number her brother left behind."
  - id: detective-oak
    role: Deuteragonist
    one_sentence: "Homicide detective investigating the same cartel."
    scenes: [3, 7, 15, 22]
    related: [mara]
    goals_short: "Bring down the cartel's leadership."

locations:
  - id: kitchen
    one_sentence: "Commercial kitchen in a closed restaurant."
    scenes: [7]

worlds:
  - id: gilead
    one_sentence: "Near-future city-state where water is privatized."
    rules_count: 3

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
    status: active
    setups: [1, 3]
    payoffs: [22]
    characters: [mara, detective-oak]

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
```

---

## Retrieval Logic

When the user asks a query, the system:

1. **Reads the index** (always in context)
2. **Identifies relevant entities** from the index
3. **Loads targeted prose** from those entities' notes
4. **Reasons** about the targeted content

### Example: "What does Mara know by the end of scene 12?"

1. Index: `mara` is in scenes `[1, 3, 7, 12, 15, 22]`
2. Index: `mara` has `knowledge: ["Her brother Daniel was murdered", "Victor Hale is the cartel's CFO"]`
3. Load: `characters/mara.md` (prose body — her arc, secrets, background)
4. Load: `screenplay.md` (scenes 7-12 only)
5. Load: `.story/memory.md` (Character Knowledge section)
6. Answer — without loading the whole project

### Example: "Who's in the Kitchen scene?"

1. Index: `kitchen` → scene 7
2. Index: scene 7 → characters `[mara, detective-oak]`
3. Load: `characters/mara.md` (one_sentence + personality)
4. Load: `characters/detective-oak.md` (one_sentence + personality)
5. Load: `screenplay.md` (scene 7 only)
6. Answer

---

## Index Maintenance

The index is **regenerated** from the vault:
- After any edit (character created, scene added, relationship changed)
- On project load (to catch manual edits)
- On demand (user says "reindex project")

A script (`scripts/update_index.py`) walks the vault, reads frontmatter from all entity notes, and rebuilds `.story/index.yaml`.

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

## Summary: What Lives Where

| Data | Where | Loaded when? |
|------|-------|-------------|
| Entity IDs, roles, connections | Frontmatter | Always (via index) |
| Scene headings, characters per scene | Frontmatter + screenplay | Always (via index) |
| Character personality, voice, arc | Prose body | On demand (retrieved by index) |
| Location description, mood | Prose body | On demand |
| World rules, history | Frontmatter (rules) + Prose (history) | Rules always, history on demand |
| Scene content (dialogue, action) | `screenplay.md` | On demand (by scene range) |
| Continuity state | `.story/memory.md` | Always |
| Edit history | `.story/history.md` | On demand |
