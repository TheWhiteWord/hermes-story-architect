# Subtask: Index Schema Design — RESOLVED

> Define the structure of `.story/index.yaml`. References: `task_1/04_decisions.md §5` (entity schemas), `§7` (screenplay format).

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Scene reference format | Both (number + heading) | `screenplay-tools` gives us both; numbers for display, headings for stable cross-refs |
| 2 | Relationship directionality | Unidirectional | Bidirectional inference is wrong (A→B ≠ B→A); explicit is writer burden |
| 3 | Story Memory in index | Summary only | Full content in `.story/memory.md`; index has metadata + summary |

---

## Final Index Schema

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
    scenes:
      - number: 1
        heading: "INT. MARA'S APARTMENT - NIGHT"
      - number: 3
        heading: "INT. POLICE STATION - DAY"
      - number: 7
        heading: "INT. KITCHEN - NIGHT"
    related:
      - id: detective-oak
        feeling: Wary respect
      - id: victor-hale
        feeling: Fear — he knows what she's found
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
    scenes:
      - number: 7
        heading: "INT. KITCHEN - NIGHT"

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
    setups:
      - number: 1
        heading: "INT. MARA'S APARTMENT - NIGHT"
      - number: 3
        heading: "INT. POLICE STATION - DAY"
    payoffs:
      - number: 22
        heading: "INT. KITCHEN - NIGHT"
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

---

## Key Design Points

### 1. Scenes use both number AND heading

- `number`: Sequential, regenerated on each index update (for display)
- `heading`: Stable, from `screenplay-tools` Parser (for cross-references)
- Cross-references in frontmatter use headings → index generator maps to numbers

### 2. Relationships are unidirectional

Each character lists their own relationships. No inference, no duplication.

```yaml
# characters/mara.md
related:
  - id: detective-oak
    feeling: Wary respect

# characters/detective-oak.md
related:
  - id: mara
    feeling: Wary respect — she's useful but unpredictable
```

Different feelings are valid — relationships are asymmetric.

### 3. Story Memory is summary-only

The index stores metadata (last_updated, continuity_risks, headings, summary). Full content lives in `.story/memory.md`.

### 4. Leveraging screenplay-tools

- Scene headings: From `FountainParser` elements with `type == "HEADING"`
- Scene numbers: From `element.scene_number` if present (Fountain `#1a#`), else sequential
- Character names: From `FountainParser` elements with `type == "CHARACTER"`
- Location extraction: Regex on heading (library doesn't parse location from heading)

---

## What this means for other subtasks

- **02_index_generator.md**: Has clear schema to generate
- **03_section_parser.md**: Section parser feeds into `sections` field
- **04_screenplay_integration.md**: Parser output maps to schema

---

## Status: RESOLVED
