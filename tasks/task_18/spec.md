# Story Architect — SQLite Migration Spec

> **Status:** Draft for review — decisions made, conflicts surfaced, open questions listed.
> **Replaces:** `brief.md` + `specialist_response.md` as the implementation contract.
> **Scope:** Data layer only. No tool schema changes unless specified. No UI/dashboard rearchitecture.
> **Working branch:** `sqlite-migration` (branched from `dev`) — all changes here, never merge to `dev` until fully tested.
> **Context:** App is pre-publication. All existing projects are test fixtures, not user data. No backward compatibility, no migration from old format, no legacy code retention. Build clean.

---

## 1. Goal

Replace the markdown+frontmatter+`##` sections storage layer and the denormalized `index.yaml` with a single SQLite database per project. All agent-facing tools keep their names and JSON shapes. The DB is the single source of truth — no index refresh, no cache invalidation, no staleness.

**Non-goals:** Changing the tool API surface, dashboard-as-editor (future possibility), screenplay processing, Fountain parsing, character/location fuzzy matching.

---

## 2. Verified Ground Truth (from code, not from docs)

Every statement below was verified against the actual source files during gap analysis.

### 2.1 Fixture save-the-children

Actual counts from `tests/fixtures/save-the-children/`:

| Entity | Files | Notes |
|--------|-------|-------|
| characters | 6 (kael, mira, marcus-chen, dr-elena-voss, the-administrator, the-outsider) | |
| locations | 2 (the-central-room, the-garden) | |
| worlds | 2 (the-i, the-real-world) | |
| plots | 2 (the-resistance, the-scientists-last-stand) | |
| scenes | 3 (central-room-day, central-room-night, the-core-day) | |
| sequences | 1 (seq-discovery) | |
| acts | 1 (act-1) | declared act_count defaults to 3 |
| arc beats | 11 | kael:3, dr-elena-voss:3, marcus-chen:2, the-administrator:3 |
| _recycle-bin/character | 1 (soren.md) | deleted character |

### 2.2 Frontmatter vs Body — CRITICAL FINDINGS

**Character `relationships` — schema says structured frontmatter, but actual data is prose in `## Relationships` body section.**

`ENTITY_SCHEMAS["character"]["relationships"]` defines typed sub-fields `{id, label, feeling}` (constants.py:70). But `characters/kael.md` has NO relationships in frontmatter — they live as markdown bullet prose in the `## Relationships` body section:

```markdown
## Relationships
- **Mira** — closest friend. Kael trusts her feelings more than their own logic.
- **The Administrator** — antagonist. Kael doesn't hate them; they pity them.
```

`_enrich_relationships` (index.py:153-159) only adds default `label=""` to existing frontmatter entries. It **never reads the body**. So the fixture data is completely invisible to the enrichment pipeline.

**Plot frontmatter uses `plot_type: Setup` (capitalized)** in `plots/the-resistance.md` fixture, but `PLOT_TYPES = ["Contradictory", "Resonant", "Complicating", "Setup"]` (constants.py:142) — this happens to be valid. Noted for validation logic.

**`plot.crisis` and `plot.climax` fields exist in frontmatter schema** (constants.py:97-98) and `_enrich_scenes_with_plots` processes them (index.py:175-179), but neither the brief nor the architecture doc mentions them. They produce `beat: "crisis"` and `beat: "climax"` entries on scene.plots[] in the index.

**Fixture `memory.md` has empty frontmatter `{}`** and minimal body — no sections. `story_create` generates `## Continuity notes`, `## Character knowledge`, `## World events`, `## Open questions`, but the existing fixture predates this.

### 2.3 Code behaviours not in brief/specialist response

| Code | What it actually does | Brief says | Specialist says |
|------|----------------------|------------|-----------------|
| `story_search` | `folder_path.glob("*.md")` on `ENTITY_FOLDERS["arc"] = "arcs"` — misses all nested `arcs/{character}/{beat}.md` files | "iterates all folders" | "FTS5 fixes this" |
| `_parse_project` | `project["act_count"] = max(declared, acts_count)` — auto-adjusts upward if more act files exist (index.py:79-80) | Not mentioned | Not mentioned |
| `story_dashboard._extract_sections` | Reads EVERY note file body via `frontmatter.load` + `get_section`, builds `{type: {slug: {section: content}}}` | Not analyzed | "queries the DB directly" |
| `_compute_screenplay_stats` | Takes Fountain text string → returns dict with template literal `f'## {slug}'` from a global `PROJECT_SLUG` (likely a bug or undefined var) | Assumes it reads `screenplay.fountain` | Not analyzed |
| `assemble_scene_content` (index.py:441-486) | Reads individual scenes' `## Content` sections — NOT `screenplay.fountain` → concatenates in act→sequence→scene order | Not analyzed | Not analyzed |
| `_enrich_structure` | `act.scenes_list` sorted by scene.order, but scenes_list is just IDs — sorted by looking up each scene's order in a loop (inefficient) | Not analyzed | Not analyzed |
| Character `relationships` | Prose in body, schema says FM, enrichment only touches FM | Assumes FM | Assumes FM |
| `story_resolve` | rapidfuzz on slug + `project.metadata["name"]` from `project.md` | Implied to be affected by migration | "Unaffected" |

### 2.4 Dashboard data flow (actual)

1. Regenerates index from files (story_dashboard.py:319-325)
2. Reads `index.yaml` → `window.__STORY_DATA__` (YAML dump as JSON) (line 355)
3. Reads individual note sections → `window.__SECTIONS__` (lines 358-363)
4. `assemble_scene_content` → scene `## Content` sections concatenated → `_compute_screenplay_stats` → `window.__SCREENPLAY_STATS__` (lines 368-376)
5. `compute_structural_stats` → `window.__STRUCTURAL_STATS__` (lines 380-384)
6. `_build_title_page` reads `project.md` frontmatter for: `screenplay_title`, `credit`, `author`, `draft_date`, `draft`, `contact` (lines 248-279)

---

## 3. Conflicts — code vs brief vs spec (SURFACED, not silently resolved)

Each conflict states what the code actually does and what the proposed resolution is. These need user confirmation where noted.

### Conflict 1: Character relationships data location — RESOLVED

- **Code:** Stored as prose bullets in `## Relationships` body. Schema defines typed frontmatter. Enrichment only touches frontmatter.
- **Brief:** Implies frontmatter storage.
- **Specialist:** Assumes frontmatter storage.
- **Resolution:** User confirmed — body prose stays as `sections.body` (analysis, reasoning, discussion). Typed frontmatter `relationships: [{id, label, feeling}]` → `relations` table rows with `kind='character_relationship'`. No prose-to-structure parsing. This is not a parsing problem — it's a conceptual model: structured data in `entities`/`relations`, prose analysis in `sections.body`. Unification applies to all entity fields: FM fields → structured columns, body sections → sections table.

### Conflict 2: Plot `crisis`/`climax` fields

- **Code:** `ENTITY_SCHEMAS["plot"]` has `crisis` and `climax` list fields with `{scene_id, description}` sub-fields. `_enrich_scenes_with_plots` processes them as beat types.
- **Brief architecture doc §1.1:** Only shows `setups` and `payoffs` — `crisis`/`climax` not mentioned.
- **Specialist:** Says "don't over-normalize" but doesn't mention these fields.
- **Resolution:** These go in `relations` table with `kind='plot_crisis'` / `kind='plot_climax'`, same as setups/payoffs. **No conflict with code — brief was simply incomplete.** Resolved in favor of code.

### Conflict 3: `story_search` silently misses arcs

- **Code:** `folder_path.glob("*.md")` on `arcs/` returned 0 results for nested beats.
- **Brief:** Claims search "iterates all entity folders."
- **Specialist:** Says FTS5 fixes this naturally.
- **Resolution:** Fixed by DB. Sections table stores all body content regardless of nesting. FTS query covers everything. No code change needed. Resolved.

### Conflict 4: `_compute_screenplay_stats` and `PROJECT_SLUG`

- **Code:** Contains `f'## {slug}'` referencing a module-level `PROJECT_SLUG` that is never defined in the file. If reached, this would `NameError`.
- **Resolution:** Not a migration concern — existing bug in dashboard stats code. Should be fixed separately, not as part of SQLite migration. Flagged, not resolved here.

### Conflict 5: memory.md structure

- **Code:** `story_create` writes 4 sections. `story_edit` has `update_story_memory` action doing section-replace. Fixture is minimal.
- **Brief architecture doc §1.3:** Shows 4 sections (Continuity Notes, Character Knowledge, World Events, Open Questions).
- **Specialist:** Does not mention memory.md at all.
- **Resolution:** Keep as markdown file. Section-replace via `section_parser.replace_section` continues to work. `story_load` returns its content as `"memory"` blob. Not migrated to DB. Resolved — keeps agent-authored continuity notes as free text.

### Conflict 6: `story_index` tool behavior

- **Code:** Regenerates index from files, writes YAML, returns full index dict in JSON result.
- **Brief:** Lists it as a tool.
- **Specialist:** Says "no story_index tool anymore."
- **Resolution:** Remove the tool. The DB is always fresh — there is nothing to re-index. Tests that call story_index must be updated or removed. Resolved.

### Conflict 7: `history.md`

- **Code:** No code references `.story/history.md` at all.
- **Brief:** Lists it as "Edit history (gitignored)."
- **Resolution:** Dead file. Remove from vault layout docs. Do not create in new project scaffolding. Resolved.

---

## 4. Schema

### 4.1 Database location

One SQLite file per project: `<project_path>/.story/story.db`

Existing projects: migration script converts `index.yaml` + note files → SQLite. `story_resolve` resolves to the folder path; targeting the DB inside is trivial.

New projects (`story_create(entity_type="project")`): creates `.story/story.db` with schema, no index.yaml.

### 4.2 Tables

```sql
CREATE TABLE entities (
    id TEXT PRIMARY KEY,           -- slug (e.g. "kael", "central-room-day", "1" for arcs)
    type TEXT NOT NULL,            -- character|location|world|plot|scene|sequence|act|arc
    name TEXT NOT NULL DEFAULT '',
    one_sentence TEXT NOT NULL DEFAULT '',
    order_key REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT '',
    parent_id TEXT,                   -- scene→sequence, sequence→act, arc→character
    location_id TEXT,              -- scene→location
    is_deleted INTEGER NOT NULL DEFAULT 0,  -- soft delete
    deleted_at TEXT,
    extra JSON NOT NULL DEFAULT '{}'
);

CREATE TABLE relations (
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    kind TEXT NOT NULL,            -- character_relationship, plot_setup, plot_payoff, plot_crisis, plot_climax, arc_beat, location_scene, character_scene
    note TEXT NOT NULL DEFAULT '',
    "order" INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (from_id, to_id, kind)
);

CREATE TABLE sections (
    entity_id TEXT NOT NULL,
    heading TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (entity_id, heading)
);
```

```sql
CREATE VIRTUAL TABLE sections_fts USING fts5(
    body,
    content='sections',
    content_rowid='rowid'
);
```

```sql
CREATE TRIGGER sections_ai AFTER INSERT ON sections BEGIN
    INSERT INTO sections_fts(rowid, body) VALUES (new.rowid, new.body);
END;
CREATE TRIGGER sections_ad AFTER DELETE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, body) VALUES ('delete', old.rowid, old.body);
END;
CREATE TRIGGER sections_au AFTER UPDATE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, body) VALUES ('delete', old.rowid, old.body);
    INSERT INTO sections_fts(rowid, body) VALUES (new.rowid, new.body);
END;
```

### 4.3 `extra` JSON field — what goes in

Per-entity-type columns are only created when there are ≥2 fields that are entity-scoped scalars nobody searches or joins on. All fields listed below were verified against `ENTITY_SCHEMAS` in constants.py:

```json
// character
{"story_role": "Protagonist", "arc_type": "positive", "arc_value": "Redemption",
 "arc_value_at_open": "positive", "arc_value_at_close": "negative",
 "arc_complete": false}

// location — no extra fields (only name + one_sentence, both columns)

// world
{"rules": ["rule1", "rule2"]}

// plot
{"plot_type": "Setup", "plot_scope": "sub", "value_arc": "Maturation",
 "characters": ["kael", "mira"]}

// project
{"genre": "Sci-fi drama", "setting": "...", "status": "active",
 "screenplay_title": "...", "credit": "...", "author": "...",
 "contact": "...", "draft_date": "...", "draft": "...",
 "spine": "...", "controlling_idea": "...", "value": "Trust",
 "value_at_open": "positive", "value_at_close": "negative",
 "inciting_incident_scene_id": "...",  -- FK to scene (app-level, not DB-level)
 "story_climax_scene_id": "...",       -- FK to scene (app-level)
 "structure_type": "Classical", "act_count": 3}

// scene — no extra. All scene fields become columns.

// sequence
{"value": "Trust", "value_open": "positive", "value_close": "negative",
 "climax_scene_id": "...",  -- FK, app-level
 "primary_plot": "...",     -- FK, app-level
 "purpose": "..."}

// act
{"value": "Trust", "value_open": "positive", "value_close": "negative",
 "climax_scene_id": "...",  -- FK, app-level
 "act_objective": "..."}

// arc
{"id": "1", "action": "...", "gap": "...", "choice": "...",
 "shift": "positive → negative", "y": 0.8,
 "is_crisis": false, "is_climax": false}
```

`relations.note` is indexed for full-text search on plot setup/payoff/crisis/climax descriptions and arc labels. `relations."order"` controls display sequence for multi-beat relations.

### 4.4 Relations table — verified against code

(from specialist_response.md Q5, verified against index.py enrichment logic)

| from_id | to_id | kind | note | order |
|---------|-------|------|------|-------|
| character-A | character-B | character_relationship | label + feeling | 0 |
| plot-X | scene-Y | plot_setup | description | 1 |
| plot-X | scene-Z | plot_payoff | description | 1 |
| plot-X | scene-W | plot_crisis | description | 1 |
| plot-X | scene-V | plot_climax | description | 1 |
| character-A | scene-Y | character_scene | "" | 0 |
| location-X | scene-Y | location_scene | "" | 0 |
| character-A | scene-Y | arc_beat | label | 1 |

Single PK `(from_id, to_id, kind)`. Reverse lookups ("scenes for character-A") = `WHERE to_id = ? AND kind='character_scene'`.

### 4.5 What does NOT go in relations

- **Character `relationships` body prose** (kael.md `## Relationships` bullets) — stays in `sections.body`. Not parsed into relations. Structured relationship data comes from typed frontmatter `relationships: [{id, label, feeling}]` only.
- **Plot `characters` list** (`plot.characters: [kael, mira]`) — these become `relations` rows with `kind='plot_character'` and empty note, OR stay in `extra` JSON as they are display-only labels pointing to character slugs. Verified: `_enrich_entity_scenes` builds character.scenes from `scene.characters` frontmatter, not the reverse. **Resolution:** `extra` JSON on plot entity. Not queried, just loaded for display.

### 4.6 Constraints that CANNOT be schema-enforced (app validation needed)

Cross-table check: `scene.act_id` must match `scene.sequence_id → sequence.act_id`. Can't be CHECK (cross-table). Implemented as: one query in `story_edit`/`story_create` before write.

All other validations from `_validate_index` (index.py:357-424) become FK constraints or are redundant:
- Character refs in relationships → app validation (no FK from relations to entities until data is migrated; body-prose relationships are not in relations table — see Conflict 1)
- Plot character refs → app validation
- Scene refs in setups/payoffs → FK (relations.to_id → entities.id)
- Sequence act_id → FK (entities.parent_id → entities.id WHERE type='act')
- Act climax_scene_id → app validation (project-type cross-ref)
- Project scene refs → app validation
- Scene sequence_id → FK (entities.parent_id)
- Arc character/scene → FK via parent_id and relations

### 4.7 Entity creation context (`build_entity_path`, `NESTED_ENTITIES`)

entities.parent_id carries the nesting context. `NESTED_ENTITIES = {"arc": "character"}` means arc's parent_id stores the character slug. This replaces the folder-based nesting (`arcs/{character}/{beat}.md`).

---

## 5. Decisions

### D1: Storage format — SQLite per project

**Decision:** `.story/story.db` — one file per project, stdlib `sqlite3`.

**Why:** Denormalized index is the root cause of 5/7 identified problems (confirmed by code reading, not just assertion). YAML index is a cache that goes stale. SQLite gives transactions, FTS5, and zero-cost freshness.

**Verified against code:** `core/index.py` 500+ lines of enrichment logic all become SQL JOINs. `story_load` reading YAML (story_load.py:44-45) becomes a summary query. `story_index` regenerating index (story_index.py:46-51) is deleted.

**Conflicts with brief:** None on format. Brief explicitly leaves storage format as open question. Specialist recommends SQLite. Code confirms index.yaml is the staleness source.

### D2: Session-start payload — project metadata + column-oriented entities + full relations

**Decision:** `story_load` returns three things:

1. **Project metadata** — name, logline, genre, status, counts
2. **Entities table** — column-oriented, all columns, no enrichment arrays, no sections list
3. **Relations table** — column-oriented, all kinds, no `note` field

```json
{
  "project": {"name": "...", "logline": "...", "genre": "...", "status": "..."},
  "entities": {
    "cols": ["id", "type", "name", "one_sentence", "status", "order_key", "parent_id", "location_id", "extra"],
    "rows": [
      ["dr-elena-voss", "character", "Dr. Elena Voss", "Lead scientist...", "", null, null, null, {"story_role": "Supporting"}],
      ["central-room-day", "scene", "Central Room - Day", null, "drafted", 1, "seq-discovery", "the-central-room", null],
      ["seq-discovery", "sequence", "The Discovery", null, "in-progress", 1, "act-1", null, null],
      ["kael-3-1", "arc", "First Doubt", null, "", 1, "kael", null, {"y": 0.8}],
      ...
    ]
  },
  "relations": {
    "cols": ["from_id", "to_id", "kind"],
    "rows": [
      ["the-resistance", "central-room-day", "plot_setup"],
      ["the-resistance", "the-core-day", "plot_payoff"],
      ["dr-elena-voss", "central-room-day", "arc_beat"],
      ["kael", "central-room-day", "character_scene"],
      ["central-room-day", "the-central-room", "location_scene"],
      ["kael", "mira", "character_relationship"],
      ...
    ]
  }
}
```

**Column-oriented rationale:** the same columns repeat across every JSON-object-row in traditional `[{...}, {...}, ...]` format. Sending a header once and rows as plain arrays saves a meaningful fraction of the token budget with no information loss — verified against our schema (6 entity columns are strings, the remainder are scalars).

**What's NOT included:**
- Per-entity `sections` list — every character has the same section set, every scene has the same section set. This is schema, not data. The agent already knows which section names to request from `story_retrieve`.
- Any enriched/derived array (no `character.scenes[]`, no `scene.plots[]`, no `act.sequences_list[]`). One edge, one encoding.
- `relations.note` — that's retrieval-level prose. `story_retrieve` covers it.
- The act→sequence→scene structural hint we floated earlier is now redundant — `parent_id` + `order_key` columns already give you that chain; sorting by `parent_id`→`order_key` client-side reconstructs the hierarchy with zero extra data.

**Verified against code:** Current `story_load` reads index.yaml ~(50-200KB YAML). For 100-scene project: 50-70K tokens. With this design, we estimate 2-3K tokens at typical scale (70 entities + 120 relation edges):

| Component | Rows | Per-row token cost | Total tokens |
|-----------|------|--------------------|--------------|
| Entities (flat cols) | ~70 | ~18 | ~1,260 |
| Relations (flat cols) | ~120 | ~12 | ~720 |
| Project meta | — | ~30 | ~30 |
| Column headers | 2 | ~20 | ~40 |
| **Total** | | | **~2,050** |

Specialist quote: "the constraint that seemed to be in tension — 'complete graph' vs. 'small' — was never real; it was an artifact of how the old index encoded the graph, not of the graph's size." Verified: our schema has the relations as a first-class table; the summary just dumps it, once per edge.

**What the agent can immediately do from the summary:**
- "Which scenes does this plot touch?" → filter `relations WHERE from_id=<plot>` → instant
- "What scenes has Kael been in?" → filter `relations WHERE to_id=<character> AND kind='character_scene'` → instant
- "Which plot moments occur in Scene X?" → filter `relations WHERE to_id=<scene> AND kind LIKE 'plot_%'` → instant
- "What's the overall scene structure?" → filter `entities WHERE type='act'/'sequence'/'scene'` and reconstruct from parent_id + order_key → instant
- "What arc beats does this scene host?" → filter `relations WHERE to_id=<scene> AND kind='arc_beat'` → instant

**What the agent must retrieve via `story_retrieve`:**
- Prose (any `##` body section — descriptions, analysis, voice notes)
- `relations.note` text (plot beat descriptions, arc beat labels)
- `memory.md` content (continuity notes, world events)

**Specialist round-trip:** This design is the second opinion we asked the specialist for after flagging the flat-summary risk. The specialist explicitly pushed back on the flat-only proposal, and this design is the result. Earlier recommendation in the first review ("add one structural hint, e.g. act→sequence→scene ordering") is superseded — those columns already carry that information, no bespoke enrichment needed.

### D3: `story_edit` → DB operations

| Action | Current (code) | New (DB) |
|--------|---------------|----------|
| edit_note | `frontmatter.load` → loop over data.items → `frontmatter.dump` | `UPDATE entities SET ... WHERE id=?` + `INSERT/UPDATE sections` |
| delete_entity | `shutil.move` to `_recycle-bin/` | `UPDATE entities SET is_deleted=1, deleted_at=?` |
| reorder | Loop over items → `frontmatter.dump` each | Single `UPDATE entities SET order_key=? WHERE id=?` in transaction |
| update_story_memory | `frontmatter.load` → section replace → dump | Still operates on `memory.md` file — see D4 |

**Transaction scope:** Each action is one DB transaction. If any statement fails, rollback. Replaces the silent partial-write behavior verified in code (story_edit.py:112-121).

### D4: `update_story_memory` — stays as file operation

**Decision:** memory.md NOT migrated to DB. Remains `.story/memory.md`.

**Why:** Agent-authored free text with standardized section structure. No DB query benefits from it. `story_load` reads as blob. `story_edit(update_story_memory)` does section-replace via `section_parser`.

**Code verified:** `story_edit.py:240-260` reads file, replaces section, writes back. No frontmatter schema for memory. `story_load.py:60-63` reads as `"memory"` string.

**Impact:** DB is source of truth for structured entities; memory.md remains a flat file alongside it. Not a conflict — hybrid is pragmatic.

### D5: `story_create` → DB inserts

Creating a project: creates `.story/story.db` with schema.

Creating an entity:
- INSERT into `entities` (id, type, name, one_sentence, order_key, status, parent_id, extra)
- INSERT standard sections into `sections` (from `_get_standard_sections`)
- INSERT relations (character→scenes, plot→setups, etc.) into `relations`
- Auto-order: `SELECT COALESCE(MAX(order_key),0)+1 FROM entities WHERE type=? AND parent_id=?`
- Parent validation: `SELECT 1 FROM entities WHERE id=? AND type=?`

**Verified against code:** `story_create.py:80-169` does all of these via file writes. Auto-order (`_get_next_order`, lines 241-258) is one SQL query.

### D6: `delete_entity` → soft delete

**Decision:** `UPDATE entities SET is_deleted=1, deleted_at=current_timestamp WHERE id=?`

**Verified against code:** Current behavior moves file to `_recycle-bin/<type>/<slug>.md` (story_edit.py:181-214). Fixture has `_recycle-bin/character/soren.md`. Tests assert file moved, not deleted (test_core.py:983-1013).

**Migration:** Existing `_recycle-bin/` content imported with `is_deleted=1`.

**User-facing behavior:** Entity disappears from queries. "Show deleted" = `WHERE is_deleted=1`. Recycle-bin listing tool (future) = `SELECT * FROM entities WHERE is_deleted=1`.

### D7: `story_search` → FTS5

**Decision:** `SELECT entity_id, heading, body FROM sections_fts WHERE body MATCH ?`

**Verified against code:** Current search (story_search.py:22-66) reads every note file, `query in content.lower()` — misses arc beats entirely (glob bug, Conflict 3). Returns max 5 matching lines per file.

**New behavior:** One FTS5 query across all section bodies. Returns `entity_id`, `heading`, `body` (or snippet). No file reading. Covers nested entities naturally.

**Assumption:** FTS5 is available in the Python `sqlite3` build. It's compiled by default on Linux/macOS. Need to verify on user's system.

### D8: `story_dashboard` → DB queries

All 6 data sources mapped:

| Current (yaml+files) | New (SQL) |
|---------------------|-----------|
| `index.yaml` → `__STORY_DATA__` | Summary query: `SELECT id, type, name, one_sentence, order_key, status, parent_id FROM entities WHERE is_deleted=0` |
| Note sections → `__SECTIONS__` | `SELECT heading, body FROM sections WHERE entity_id IN (?)` |
| `assemble_scene_content` | `SELECT s.id, sec.body FROM sections sec JOIN entities s ON sec.entity_id=s.id WHERE sec.heading='Content' AND s.type='scene' AND s.is_deleted=0 ORDER BY (SELECT order_key FROM entities WHERE id=s.parent_id), s.order_key` |
| `_compute_screenplay_stats` | Unchanged — receives Fountain text string, returns dict |
| `compute_structural_stats` | `SELECT status, COUNT(*) FROM entities WHERE type='scene' AND is_deleted=0 GROUP BY STATUS` + role equivalents |
| `_build_title_page` | `SELECT json_extract(extra, '$.screenplay_title'), ... FROM entities WHERE type='project'` |

**Dashboard HTML:** Stays as-is. Only the data injection layer changes (`window.__STORY_DATA__` etc. now populated from SQL results instead of `yaml.safe_load`).

**Bug in current code:** `_compute_screenplay_stats` contains `PROJECT_SLUG` (likely `NameError`). Separate bug, not migration scope.

### D9: Validation — schema + app

Schema-enforced:
-实体 type validity → CHECK constraint or application validation
- FK constraints (parent_id, relations.to_id → entities.id)
- Required fields → NOT NULL constraints
- Enum values → CHECK constraints on status fields
- `order_key` numeric → REAL column
- Arc `y` value range → app validation on `extra` JSON

App-enforced:
- scene.act_id consistency check (cross-table)
- plot characters reference valid characters
- arc character/scene reference valid entities
- required fields per entity type

### D10: No migration needed

App is pre-publication. All existing projects are test fixtures. No user data to preserve, no backward compatibility, no legacy format retention. `story_create(entity_type="project")` creates the DB directly. Old markdown-based tool paths are deleted, not migrated.

**What this removes from the plan:**
- No migration script
- No `index.yaml` import path
- No round-trip verification against old format
- No `_recycle-bin/` import code
- No "markdown-compatibility layer"

**What stays:**
- `story_export` tool — writes DB → markdown vault on demand (for git, backup, inspection)
- `schema.sql` + `core/db.py` — create fresh DB for new projects
- Fixture `tests/fixtures/save-the-children/` — rebuilt directly as a new fixture, or kept as a test-only vault for round-trip export/import testing

### D11: Export/import (symmetrical, on-demand)

**Export:** `story_export` tool — reads DB, writes markdown vault (same format as current notes). Used for git snapshots, backup, or vault inspection.

**Import:** `story_import` tool — reads markdown vault, populates DB. Used for restoring from export or creating projects from shared markdown.

Both are one-shot tools the agent calls on demand. Not automatic. Not a migration path.

### D12: Multi-project

**Decision:** One DB per project. `resolve_project` finds the folder; DB lives at `<folder>/.story/story.db`.

**Verified against code:** `story_resolve.py` already finds project folder from slug/name. Adding `.story/story.db` is trivial.

**No switch_project tool** (specialist Q4). `resolve_project` already handles cross-project navigation.

### D13: Concurrent access

`PRAGMA journal_mode=WAL;` + `PRAGMA busy_timeout=3000;`

**Rationale:** Single user, single agent, but dashboard reads may coincide with agent writes. WAL allows concurrent readers + one writer. No app-level locking.

**Verified against code:** Dashboard runs in preview pane (read-only). Agent executes single tool at a time (Hermes serializes tool calls). Contention window is tiny.

### D14: Dependency changes

Remove: `pyyaml` (no YAML parsing in live path).
Keep: `python-frontmatter` (migration script, export), `rapidfuzz` (story_resolve + screenplay matching), `regex` (Fountain lexer).
Add: none (sqlite3, json1 are stdlib).

**Assumption:** `frontmatter` library still needed for import/export. Live read/write path uses only stdlib `sqlite3`.

### D15: What to delete from codebase

| File/Module | Reason |
|-------------|--------|
| `core/index.py` (`generate_index`, `_parse_entities`, `_enrich_*`, `write_index`, `refresh_index`) | All replaced by SQL. `assemble_scene_content` + `compute_structural_stats` stay (used by dashboard). |
| `core/section_parser.py` | Live path uses DB. Keep for `update_story_memory` (if memory.md stays) and export. |
| `core/paths.py` | `build_entity_path`/`find_entity_path` file-based. Replace with DB lookup. |
| `tools/story_index.py` | No-op in DB model. Remove. |
| `core/constants.py` `ENTITY_FOLDERS`, `NESTED_ENTITIES` | No longer map to folders. Remove. |
| `core/constants.py` `ENTITY_SCHEMAS` | Column defaults extracted to schema. Extra `type` field removed. Validate enums stay. |

---

## 6. Entity-specific schema details

### Scene → columns verified against frontmatter

| Column | Source FM field | Fixture value |
|--------|-----------------|---------------|
| id | id | central-room-day |
| type | type | scene |
| name | title | "Central Room - Day" |
| one_sentence | (none) | "" |
| order_key | order | 1 |
| status | status | drafted |
| parent_id | sequence_id | seq-discovery |
| location_id | location | the-central-room |
| is_deleted | (new) | 0 |
| extra | heading, time_of_day, act_id, characters, value, value_open, value_close, conflict_levels, dramatic_role, is_inciting_incident, is_sequence_climax, is_act_climax, is_story_climax | (JSON) |

`characters: [kael, mira]` in frontmatter → relations rows `(character, scene_Y, character_scene, '')`.
`plots: []` derived from plot setups/payoffs reversed.

### Character relations from frontmatter — CONFLICT

See Conflict 1. The fix is either:
(a) Parse `## Relationships` body prose into relations rows during migration
(b) Accept body-only relationships, don't put in relations table

**User decision required.** FLAGGED.

---

## 7. Assumptions

1. **FTS5 is available in the user's Python sqlite3 build** — virtually guaranteed on Linux/macOS, verify with `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`.
2. **Single agent + single user** — no concurrent writes. Hermes serializes tool calls. WAL is belt-and-suspenders.
3. **Migration is one-time** — existing projects migrated on first `story_load` after plugin update. Backup index.yaml.
4. **Export preserves git history** — markdown export is for snapshots, not the live format. Git diffs on prose are clean. No diff noise from index.yaml regeneration.
5. **No concurrent dashboard + agent writes during migration** — agent runs migration, then user opens dashboard.
6. **`frontmatter` library stays for export** — migration and export use it. Live path uses only stdlib.
7. **No cross-project query requirement** — specialist confirmed, brief confirms, code confirms.

---

## 8. Open Questions

| # | Question | Why it matters | Blocking? |
|---|----------|----------------|-----------|
| 1 | ~~Character `relationships`~~ — Resolved: body prose stays as `sections.body`; typed FM `relationships` → `relations` table. No parsing. | Resolved — blocks migration script | Resolved |
| 1b | ~~Scene `## Content`~~ — Resolved: keep as regular section. No special case. Screenplay assembly queries `WHERE heading='Content'`, pipeline is pure text-in/text-out, FTS covers it, `story_retrieve` works unchanged. | Resolved | Resolved |
| 2 | Is `_compute_screenplay_stats` `PROJECT_SLUG` bug in scope? | It's a latent NameError if reached | No — separate fix, just note it |
| 3 | Should `story_create(entity_type="project")` auto-migrate existing index.yaml | Smaller code path if user always creates new projects | No — migration script handles both |
| 4 | Recycle bin — add `story_undelete` tool? | Soft-deleted entities can't be restored currently | No — can be added later, not blocking schema |

---

## 9. Test impact

| Test file | Impact |
|-----------|--------|
| test_core.py | Calls `create_handler`, `load_handler`, `edit_handler`. Tests assert on `frontmatter.load` results. Must update to assert on DB state. Integration tests via `generate_index` — rewrite to use DB. |
| test_arcs.py | Tests `_parse_arcs`, `_enrich_characters_with_arcs`, `_enrich_scenes_with_arcs`, `_validate_index`. All removed. Replace with DB-level tests: create arc beat → query character.arc_beats_list equivalent. |
| test_fountain_lexer.py | Unaffected (pure text processing). |
| test_story_dashboard_stats.py | Tests `_compute_screenplay_stats` — unaffected (still Fountain text in, dict out). |
| test_story_dashboard_integration.py | Tests dashboard data injection — update to provide DB-backed data instead of YAML files. |
| conftest.py | `project_path` fixture points at `fixtures/save-the-children/`. Add `db_path` fixture or migration helper. |

---

## 10. Phased delivery

The migration is delivered in 4 checkpointable phases. Each phase is independently shippable and reversible; prior-phase checkpoints must remain green. See `tasks/task_18/plan.md` for the full plan with per-phase verification, stated assumptions, and open questions.

| Phase | Name | What changes | Old tools still working? |
|-------|------|--------------|--------------------------|
| 1 | Schema + Migration/Diff Loop | `core/db.py`, `story_import`, `story_export`, round-trip verifier | Yes — untouched |
| 2 | Swap Read Paths (shadow reads) | `story_load`/`retrieve`/`search`/`dashboard` read DB; writes still markdown + reimport | Yes |
| 3 | Swap Write Paths + Retire Markdown | `story_edit`/`create` write DB; delete index machinery + `story_index` | No — write paths migrated |
| 4 | Cleanup + Regression Coverage | Remove dead code, update tests, real-project validation | No — all markdown paths gone |

---
