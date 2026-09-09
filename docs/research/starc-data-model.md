# STARC Data Model — Research Notes

Source: `story-apps/starc` (master) — C++/Qt, GPLv3
Reverse-engineered from: `src/corelib/data_layer/database.cpp`, `src/corelib/domain/document_object.h`

---

## 1. Database Schema (SQLite)

The `.starc` file is a SQLite database with three core tables:

### `system_variables`
| Column | Type | Notes |
|--------|------|-------|
| variable | TEXT PK | e.g. `"application-version"` |
| value | TEXT | app version string |

### `documents`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | internal row id |
| uuid | TEXT UNIQUE NOT NULL | **stable identifier** (QUuid) |
| type | INTEGER NOT NULL DEFAULT(0) | enum `DocumentObjectType` |
| content | BLOB DEFAULT(NULL) | JSON blob — the actual entity data |
| synced_at | TEXT DEFAULT(NULL) | ISO datetime, for cloud sync |

### `documents_changes` (undo/redo journal)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| fk_document_uuid | TEXT NOT NULL | FK → documents.uuid |
| uuid | TEXT UNIQUE NOT NULL | change id |
| undo_patch | BLOB NOT NULL | diff to reverse the change |
| redo_patch | BLOB NOT NULL | diff to apply the change |
| date_time | TEXT NOT NULL | `"yyyy.mm.dd.hh.mm.ss.zzz"` |
| user_name | TEXT NOT NULL | |
| user_email | TEXT DEFAULT(NULL) | |
| is_synced | INTEGER NOT NULL DEFAULT(0) | |

Indexes:
- `documents_changes_fk_document_uuid_idx` on `fk_document_uuid`
- `documents_changes_date_time_idx` on `date_time`

---

## 2. Document Type Hierarchy (the taxonomy)

From `src/corelib/domain/document_object.h` (enum `DocumentObjectType`):

```
Structure = 1

// Raw
ImageData = 101, BinaryData = 102

// Project root
Project = 10000
RecycleBin = 10001

// Screenplay module
Screenplay = 10100
├── ScreenplayTitlePage = 10101
├── ScreenplaySynopsis = 10102
├── ScreenplayTreatment = 10103       ← ordered outline, tied to paragraphs
├── ScreenplayText = 10104             ← scenes → paragraphs
├── ScreenplayDictionaries = 10105
└── ScreenplayStatistics = 10106

// Series
ScreenplaySeries = 10110
├── ScreenplaySeriesEpisodes = 10111
├── ScreenplaySeriesTitlePage = 10112
├── ScreenplaySeriesSynopsis = 10113
├── ScreenplaySeriesTreatment = 10114
├── ScreenplaySeriesText = 10115
└── ScreenplaySeriesStatistics = 10116

// Other modules (ComicBook, Audioplay, Stageplay, Novel) follow same pattern
ComicBook = 10200, Audioplay = 10300, Stageplay = 10400, Novel = 10500

// Narrative elements
Plots = 20000
├── Plot = 20001

Characters = 30000
└── Character = 30001

Locations = 40000
└── Location = 40001

Worlds = 50000
└── World = 50001

// Generic content
Folder = 100001
SimpleText = 100002
MindMap = 100003
Image = 100004
ImagesGallery = 100005
Presentation = 100006
Link = 100007
```

### Key insight: the hierarchy is flat in the DB

Parent-child relationships are encoded in the JSON `content` blob, not via SQL foreign keys. The `type` enum tells you what kind of entity a row is. The `uuid` is the universal reference.

---

## 3. Entity Structure (from `content` blobs — inferred)

### Project (`type=10000`)
```json
{
  "name": "My Screenplay",
  "logline": "...",
  "cover": null,
  "genre": null,
  "setting": null
}
```

### Character (`type=30001`)
The Action Protocol V3 defines these fields (from `codex_service_manager.cpp`):

```yaml
name: string               # character display name
story_role: string         # e.g. "Protagonist", "Antagonist", "Sidekick", "Mentor"
age: string
nickname: string
one_sentence_description: string
long_description: string
family: string             # family background
personality: string
motivation: string
moral: string
greatest_fear: string
secrets: string
short_term_goal: string
long_term_goal: string
initial_beliefs: string
changed_beliefs: string    # how their worldview shifts
plot_involvement: string
conflict: string
speech: string             # dialogue style / voice notes
```

### Character Relationship (from Protocol V3)
```yaml
related_character_id: uuid  # FK to another character document
feeling: string             # how this character feels about the other
details: string
```

### Location (`type=40001`)
```json
{
  "name": "Kitchen",
  "description": "...",
  "references": []          # scenes referencing this location
}
```

### World (`type=50001`)
```json
{
  "name": "Gilead",
  "description": "...",
  "rules": []
}
```

### Synopsis (`type=10102`)
```json
{
  "paragraphs": [
    {"text": "In a near-future...", "index": 0}
  ]
}
```

### Treatment (`type=10103`)
```json
{
  "paragraphs": [
    {"text": "ACT ONE\n\nWe meet LENA, a 30-year-old...", "index": 0}
  ]
}
```
> Treatment is an ordered outline where each paragraph maps to a beat/scene.

### Screenplay (`type=10104`) — the scenes + paragraphs

Each scene is a document within the screenplay container. Paragraph types (from `updateDatabaseTo_0_1_3`):

| Type | Russian label | What it is |
|------|---------------|------------|
| Scene heading | `sequence_heading` / `folder_header` | `INT. KITCHEN - NIGHT` |
| Action | | descriptive prose |
| Character cue | | name above dialogue |
| Parenthetical | | direction inside dialogue |
| Dialogue | | spoken text |
| Shot | | camera direction |
| Transition | | `CUT TO:`, `FADE OUT.` |

The content blob for a scene contains an ordered list of typed paragraph objects.

---

## 4. The Codex Fork's Action Protocol V3

From `jeffkimkimo/starc` (`codex_service_manager.cpp`):

### Actions the assistant can return:
```json
{
  "version": 3,
  "action": "insert_screenplay|replace_selection|delete_selection|clear_screenplay|update_logline|replace_synopsis|revise_treatment|create_character|update_character|remove_character|merge_character|update_character_relationship|update_story_memory|answer|suggest_ideas|request_clarification",
  "target": "none|selection|cursor|beginning|end|logline|synopsis|treatment|characters|character_relationships|story_memory",
  "content": "...",          // production-ready Fountain or entity fields
  "summary": "...",          // human-readable description
  "requiresApproval": true,  // always true for editor actions
  "entityId": "uuid",        // for character actions
  "entityName": "...",
  "fieldChanges": [
    {"field": "motivation", "value": "To protect her sister"}
  ],
  "impactSummary": "...",
  "continuityChecks": [
    {"severity": "critical|caution|suggestion", "category": "character_knowledge|chronology|location|world_rules|setups/payoffs|voice", "evidence": "...", "finding": "..."}
  ]
}
```

### Story Memory headings (from protocol developer instructions):
```
CHARACTERS & RELATIONSHIPS
CHARACTER KNOWLEDGE
TIMELINE
PLOT THREADS
SETUPS & PAYOFFS
WORLD RULES
VOICE & STYLE
CONTINUITY RISKS
```

### Continuity Gate:
- Every editor-changing action self-audits against the live screenplay, linked tabs, and Story Memory
- `severity: critical` = direct conflict with confirmed canon
- `severity: caution` = likely inconsistency / weak motivation
- `severity: suggestion` = optional improvement
- Categories: character knowledge, chronology, location, world rules, setups/payoffs, voice
- Evidence must cite a scene heading or linked tab; distinguish confirmed canon from inference

### Safety rules:
- Character removal → Recycle Bin (NOT search-and-delete prose)
- Character merge → transaction journal + rollback
- Stale response protection (revision check before apply)
- Conflict with canon → extra intentional-conflict approval

---

## 5. What this means for Hermes

We are NOT reading/writing `.starc` files. We are taking the **taxonomy, the field definitions, the action protocol, and the continuity model** and re-implementing them as:

1. Vault conventions (folder structure, frontmatter schemas)
2. Hermes skills (story loading, story editing, continuity checking)
3. Optionally: preview-pane dashboards for interactive project navigation

The Starc model is good. It was built by writers, for writers, and refined over years. Porting the conceptual architecture to the vault + Hermmes is the right call.
