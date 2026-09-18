# Story Architect — Data Architecture Brief for Specialist Review

> **Purpose**: External specialist review of data storage and retrieval architecture with optimization proposals and alternative designs.
>
> **Scope**: Data layer only — storage format, index generation, retrieval/search patterns, and their interplay. Not UI, not tool schema, not business logic.

---

## 1. Project Overview

### What it is

Story Architect is a plugin for **Hermes Desktop** — an LLM agent platform. It provides the agent with structured story-management capabilities: characters, locations, worlds, plots, scenes, sequences, acts, arc beats. The agent uses these tools to help a human writer develop narrative fiction (novels, screenplays, etc.).

### What it is NOT

- Not a web application — no HTTP API, no concurrent users
- Not a DB-backed system — no SQLite, no Postgres, no external service
- Not a file-sync system — lives entirely inside a single local vault directory
- Not a million-user platform — single user, single agent, one active project at a time
- Not a screenplay formatter — Fountain is stored but渲染 is handled elsewhere

### Goals

1. Give the LLM agent **structured awareness** of the story's entities and relationships
2. Enable **targeted retrieval** of specific data slices (a character's voice, a scene's content, a plot'sObstacles)
3. Support **broad search** across all project notes
4. Keep data in a **format that serves the agent first** — human-readable if possible, but agent efficiency is the priority
5. Minimize **context token cost** — the LLM's context window is the scarce resource

### Scale

| Dimension | Typical | Max expected |
|-----------|---------|--------------|
| Projects in vault | 1-3 | ~10 |
| Characters per project | 5-12 | ~30 |
| Scenes per project | 10-40 | ~100 |
| Total entity notes per project | 30-80 | ~200 |
| Index.yaml size | 50-200 KB | ~1 MB |
| Memory.md size | 5-30 KB | ~100 KB |

This is **small-data territory**. Linear scans are fine. The bottleneck is LLM context volume, not disk I/O.

---

## 2. Current Architecture

### 2.1 Storage Layout

```
<vault>/projects/<slug>/
├── project.md                  # Frontmatter: name, logline, genre, status, spine, value, etc.
├── .story/
│   ├── index.yaml              # Pre-computed navigation graph (the "always-loaded" index)
│   ├── memory.md               # Agent continuity map (sections: Continuity notes, Character knowledge, World events, Open questions)
│   └── history.md              # Edit log (gitignored)
├── characters/
│   └── <slug>.md               # Frontmatter + ## sections (Personality, Background, Voice, Arc, Relationships, Goals)
├── locations/
│   └── <slug>.md               # Frontmatter + ## sections (Description, History, Scenes)
├── worlds/
│   └── <slug>.md               # Frontmatter + ## sections
├── plots/
│   └── <slug>.md               # Frontmatter (setups, payoffs, crisis, climax) + ## sections (Summary,ObStakes)
├── scenes/
│   └── <slug>.md               # Frontmatter (id, title, order, sequence_id, act_id, characters, plots) + ## sections (Description, Content, Notes)
├── sequences/
│   └── <slug>.md               # Frontmatter (id, title, order, act_id) + ## sections
├── acts/
│   └── <slug>.md               # Frontmatter (id, title, order) + ## sections
└── arcs/
    └── <character-slug>/
        └── <beat-id>.md        # Frontmatter (id, character, scene, label, action, gap, choice, shift, y, order) + ## sections
```

### 2.2 The Dual System: Frontmatter + Body

Every note has two data layers:

**Frontmatter** (YAML metadata):
- Machine-readable, structured, schema-validated
- Single-value fields: `name`, `story_role`, `status`, `order`, `sequence_id`, etc.
- Relational references: `characters: [kael, mira]`, `location: the-central-room`
- Rich semantic fields in plots/arcs: `setups: [{scene_id, description}]`, `payoffs: [...]`
- Serves as the **index label** — the minimal identifier the agent needs to locate, filter, and cross-reference

**Body** (`##` sections):
- Prose-style, human-readable, arbitrarily divisible via `## Heading` markers
- Standard section names per entity type (Personality, Background, Voice, Arc for characters; Description, Dramatic Function, Content, Notes for scenes)
- The agent retrieves **by section name** — e.g., only fetch `## Voice` when it needs dialogue style, not the whole note

This maps to a deliberate philosophy: **the vault-conventions.md file states:** "Frontmatter = what the index needs to find and connect entities. Standard body sections = retrieval targets the LLM loads by name. Prose within sections = depth."

### 2.3 Index Generation

**`core/index.py` — `generate_index(project_path)`:**

1. Parse all entity folders → list of entity dicts (id + frontmatter + section list)
2. Parse `project.md` → project metadata + counts
3. **Enrichment phase** (in-memory, across the full graph):
   - `_enrich_entity_scenes` → characters/locations get their scenes list
   - `_enrich_relationships` → labels added to relationship entries
   - `_enrich_plots` → normalize setups/payoffs to `{scene_id, description}`
   - `_enrich_scenes_with_plots` → reverse-lookup: scenes get their plots
   - `_enrich_structure` → sequences/acts get derived scene lists
   - `_enrich_sequences_with_plots` / `_enrich_acts_with_plots` → plots rolled up
   - `_enrich_characters_with_arcs` → beats attached to characters
   - `_enrich_scenes_with_arcs` → beats attached to scenes
4. `_validate_index` → cross-reference integrity checks
5. Output: a single nested dict written to `.story/index.yaml`

The index is a **denormalized pre-computation** — it trades disk-reads (reading 50+ files at load time) for a single YAML read that gives the agent the full navigation graph.

### 2.4 Retrieval Paths (Current)

| Need | Tool | What it does |
|------|------|--------------|
| **Project load** | `story_load` | Reads `index.yaml` + `memory.md` → dumps index JSON into LLM context |
| **Specific entity section** | `story_retrieve` | Reads single note, extracts named sections via regex (`##` split) |
| **Broad search** | `story_search` | Iterates all `*.md` files in entity folders, case-insensitive substring match, returns file + line numbers |
| **Re-index** | `story_index` | Re-runs `generate_index` → writes `index.yaml` |

### 2.5 The Dashboard — Current Role and Future Potential

The plugin already has a full HTML dashboard (`story_dashboard` tool), opened in the Hermes Desktop preview pane. It is **read-only** but already acts as a data consumer:

**What it does today:**
- Reads `index.yaml` + note sections + project frontmatter
- Injects data as `window.__STORY_DATA__` (navigation graph), `window.__SECTIONS__` (retrievable section content), `window.__SCREENPLAY_STATS__` (duration, character speaking time, INT/EXT, location stats from Fountain content), `window.__STRUCTURAL_STATS__` (scene status, dramatic roles, plot coverage)
- Renders entity navigation, screenplay view with pre-rendered HTML, stats panels

**What it reveals about the architecture:**
- The dashboard is already a **view layer** over the same data the agent reads
- Notes are the only source of truth; the dashboard derives everything from them
- Simple metrics the agent has to compute (duration, speaking time) are already computed here — a sign that some of the agent's context load is overlapping with what the dashboard already knows

**Relevance to storage format decision:**
- If data lives in files, the user edits notes in a text editor and tells the agent what changed → agent calls `story_edit` → file write → index refresh → context reload
- If data lives in a queryable/structured store, the user could edit directly in the dashboard → write to store → agent queries the store next time it needs data
- **Dashboard-as-editor is a future possibility that argues for a structured storage format** (JSON/SQLite over markdown), but it's not a current requirement — it's an argument for keeping the door open

### 2.6 Current Search Implementation

```python
for entity_type, folder in ENTITY_FOLDERS.items():
    for note in folder_path.glob("*.md"):
        content = note.read_text()
        if query in content.lower():
            lines = content.split('\n')
            matches = [f"{i+1}: {line}" for i, Line in enumerate(lines) if query in line.lower()]
```

- **O(n)** scan of all project notes
- Case-insensitive substring only
- No ranking, no scoring
- Returns max 5 matching lines per file
- Searches **both frontmatter and body** (reads entire file)
- No regex support

---

## 3. Key Architectural Decisions (and Their Rationale)

### Decision 1: Markdown files as the database

**Choice**: Every entity is a `.md` file with YAML frontmatter. No SQLite, no JSON store, no index DB.

**Why (historical)**:
- The plugin originated as an Obsidian plugin — markdown+frontmatter was the native format
- Git-diffable — every change is a line diff
- Zero infrastructure — no server, no daemon, no connection pool
- Frontmatter = structured data, body = prose — best of both worlds
- The agent reads files directly via `Path.read_text()` / `frontmatter.load()`

**Why (current)**: The plugin is now a Hermes Desktop plugin with a dashboard. The user does not need to edit in Obsidian. The format was kept by convention, not by necessity. **This is now an open question for the specialist.**

**Trade-off**: No ACID transactions. No concurrent write safety. Fine for single-user single-agent. But the format cost is: section-parser workaround, YAML token density, denormalized index staleness, and naive search.

### Decision 2: Pre-computed index vs. on-the-fly resolution

**Choice**: A `generate_index()` function scans ALL notes, builds a denormalized graph, writes `index.yaml`. The agent loads the YAML at session start.

**Why**:
- One file read instead of 50+ at load time
- Cross-references (character→scenes, scene→plots) pre-computed → O(1) navigation
- The agent gets the full graph instantly for context

**Trade-off**: **Staleness**. The index is a cache. Between the last `story_index` call and any `story_edit`, the index is out of date. The plugin has a `post_tool_call` hook to auto-refresh after `story_edit`/`story_create`/`story_index`, but that's cache invalidation by convention, not guaranteed consistency.

### Decision 3: Whole-index load into context

**Choice**: `story_load` reads the entire `index.yaml` and serializes it as JSON into the tool result (which goes to the LLM).

**Why**: The agent needs the graph to navigate. Without it, it can't know which entities exist.

**Trade-off**: **Context volume**. For a 50-scene project, the index can be 100-200KB of YAML → ~50-100K tokens. That's a significant fraction of the agent's context budget. And most of it may be irrelevant to the current task.

### Decision 4: Section-level retrieval granularity

**Choice**: `story_retrieve` reads one note, extracts only the requested `##` sections.

**Why**: Avoids loading whole notes when you only need one piece. A character note might be 2KB; only `## Voice` is needed for dialogue → ~200 bytes.

**Trade-off**: Requires knowing section names. If the user asks for something not in a section's body, the agent must fall back to searching.

### Decision 5: Project-scoped resolution only

**Choice**: All tools require a `project` parameter. You can't search across projects. The fuzzy matcher (`story_resolve`) finds the project folder from a slug or name.

**Why**: Stories are self-contained. Cross-project queries are rare.

**Trade-off**: Cross-project search requires a new tool or manual vault-level search.

---

## 4. Identified Problems

### 4.1 Index Staleness

- After editing an entity's frontmatter, sequences, or plots, `index.yaml` is out of sync until `story_index` is called.
- The auto-refresh hook helps, but it regenerates the index, writes it, and tries to open the dashboard — it does NOT re-load the fresh index into the agent's context.
- So: the agent might stale-navigate using old index data within a session.

### 4.2 Context Bloat

- Loading the full index (potentially 100K+ tokens) for a large project eats context before any real work begins.
- The agent gets ALL entities — characters it doesn't need, locations it won't touch, all arc beats.
- `story_search` additionally dumps matching lines from all hits, which can grow unbounded for common queries.

### 4.3 Search is Naive

- Substring-only, no ranking, no scoring, no regex.
- For a search like "Elena" it returns every line in every file where she's mentioned — including plot descriptions, scene content, arc beats. No way to filter by "only in `## Secrets`" or "only in character notes."
- Result: irrelevant hits drown relevant ones.

### 4.4 No Semantic/Filtered Retrieval

- You can't ask: "Show me all scenes where Elena appears" — you have to load the index and filter client-side, or `story_search("elena")` and sift through noise.
- You can't ask: "What are Kael's relationships?" — you load the character note and scan the body yourself.
- The agent does this filtering internally (it's an LLM after all), but it costs context and tokens to receive the raw data to filter.

### 4.5 Frontmatter is Minimal

- Character frontmatter has: name, story_role, one_sentence, arc_type, arc_value, relationships (ids only).
- Scene frontmatter has: id, title, order, status, sequence_id, act_id, characters, plots, location.
- There's no `current_location`, no `emotional_state`, no `knowledge_graph`.
- The agent must infer everything from prose sections.

### 4.6 Mental Model Duplication

- The index is a **denormalized cache** of what's already derivable from the notes. It duplicates the relationship graph: character notes list `relationships: [{id: ...}]`; the index also has `character.scenes[]` matching `scene.characters[]`.
- This duplication is the source of staleness bugs (if `story_edit` updates a scene's characters, the index is stale until refresh).

---

## 5. Questions for the Specialist

These are the specific areas where I want design feedback:

### 5.1 Storage Format — THE core question (with dashboard consideration)

The current format (markdown + YAML frontmatter + `##` body sections) is inherited from the plugin's origin as an Obsidian plugin. It is NOT a hard requirement. The question: is it the right storage layer for a Hermes Desktop plugin with a dashboard?

**Context**: The user has a dashboard for visual interaction. They do not need to edit files in Obsidian. The markdown format was kept by convention from an earlier design context, not by necessity.

**Dashboard-as-editor consideration**: If the data lives in a structured store (JSON/SQLite), the dashboard could become the primary editing interface — the user edits directly in the dashboard, writes go to the store, and the agent reads the fresh data on its next query. This eliminates the current round-trip: user sees something wrong → tells agent → agent calls story_edit → file write → index refresh. But this is a FUTURE possibility, not a current requirement. It's an argument for choosing a storage format that doesn't close this door.

| Alternative | Pros | Cons | Disruption |
|-------------|------|------|------------|
| **SQLite** | Index staleness solved (queries are always fresh); powerful SQL search; single file; stdlib (`sqlite3`). | Loses human-readable files; needs migration. | Medium-High |
| **Single JSON project file** | Structured, queryable, no denormalization needed, ~40% smaller than YAML, native Python dict access. | Not human-editable in Obsidian; single file could grow large. | Medium |
| **Per-entity JSON files** | Keep file-per-entity structure; structured data; no frontmatter parsing. | More files to manage; no relational DB capabilities. | Low-Medium |
| **Standalone index DB** (keep markdown notes + SQLite index) | Best of both worlds? Human-readable notes + fast queries. | Two systems to keep in sync. | Medium |
| **Current (unchanged)** | Simplicity. Every note is self-describing. Git-diffable. | Staleness, context bloat, section-parser complexity. | None |

### 5.2 Index Load Strategy

The full-index load into context is the single biggest context cost. Options:

| Strategy | Description | Pros | Cons |
|----------|-------------|------|------|
| **Full load** (current) | Entire `index.yaml` → context | Always have full graph; simple. | Context heavy for large projects. |
| **Summarized load** | Load only project metadata + entity names + IDs + counts. No enriched lists (scenes[], arc_beats[], plots[]). | Tiny context cost. Flat map. | Agent must query for details on demand. |
| **Layered load** | Load summarized index at session start, then `story_retrieve` for detail slices as needed. | Context scales with actual need. | More tool calls per session. |
| **Query-driven** | Agent issues structured queries (`list_scenes`, `get_character_scenes`, `get_scenes_in_sequence`) against the index file without loading it into context. | Zero context cost. | New tool API surface; agent must know to query. |

**Key tension**: Context optimization vs. navigation fluency. The agent is good at chunking attention over large structures. Is 100K tokens of index actually wasteful if the agent can attend to only the relevant parts? Or is it genuinely crowding out actual story work?

### 5.3 Search Architecture

The current search is O(n) substring scan. For 200 notes of ~2KB each, that's ~400KB of reading — a 0.4s operation. Not the bottleneck. The bottleneck is what gets returned:

| Approach | Pros | Cons |
|----------|------|------|
| **Filtered search** — restrict to specific entity types, section names (e.g., only in `## Secrets`) | Much more precise hits. | New query params. More complex schema. |
| **Regex support in search** | Powerful for finding patterns (dialogue, stage directions). | Regex injection/user error risk. |
| **FTS/embedding index** — build a SQLite FTS5 index or use embeddings | Full-text ranking, contextual snippets. | Dependency chain (sqlite3/onnxruntime). Kills the zero-infra property. |
| **Metadata-aware search** — use frontmatter structured fields for filtering ("scenes where `characters` contains X") | Precision. Requires parsing all notes. | Already possible via index load + client filter. |

### 5.4 Staleness Management

| Approach | Description | Disruption |
|----------|-------------|------------|
| **Event-driven refresh** — `story_edit`/`story_create` always regenerate index + re-load into context | Solves staleness completely. | Adds a re-load step after every edit. |
| **TTL / dirty flag** — index has a timestamp; tools check freshness | Lazy consistency. | Race conditions in concurrent scenarios (unlikely here). |
| **Query-time join** — tools merge index + live note reads for the queried entity | Always accurate for what's queried. | More complex retrieval paths; some queries need both index and notes. |

### 5.5 Context Budget Management

The real scarce resource is LLM context. Current issuance:

- `story_load` result can be 50-200K tokens (full index).
- `story_retrieve` result is targeted (good).
- `story_search` result can be large for broad queries.
- Then actual work (writing, editing, discussing) competes for the remaining context.

Should there be a **context budget** system? E.g., index-load caps at N tokens, truncates enrichment lists to summaries, or the agent gets a "lite" index by default with option to expand?

---

## 6. Constraints and Non-Negotiables

These are the boundaries within which solutions must operate:

1. **Local-only, no external services** — no cloud, no API servers, no hosted DB.
2. **Python only** — the plugin runs inside Hermes Desktop (Python process).
3. **Single user, single agent, single active project** — no concurrency to worry about.
4. **Tool-based API** — all agent interaction goes through Hermes tools (JSON in/out). No direct code execution from the LLM.
5. **Storage format is OPEN** — the current markdown+frontmatter+Obsidian-native format is an inherited design choice, NOT a hard requirement. The user has a dashboard for visual interaction. Files should be human-inspectable if possible, but context efficiency and structural clarity come first. JSON, SQLite, a single project file, or keeping markdown are all on the table.
6. **Low dependency count** — current: rapidfuzz, python-frontmatter, pyyaml, regex. Adding heavy deps (numpy, sqlite wrappers, embedding models) is a significant cost. (Note: sqlite3 is stdlib.)

Rationale for opening the storage format: the plugin has a dashboard that already provides visual access to the data. The user does not need to edit files in Obsidian. The markdown format was inherited from an earlier design context (Obsidian plugin) and has been kept by convention, not by necessity. This is the #1 question for the specialist.

---

## 7. What We Want from You

### Deliverables

1. **Assessment** — your opinion on whether the current architecture has fundamental problems or is "good enough for the stated scale."

2. **Optimization proposals** — for each area (storage, index, retrieval, search, staleness):
   - What you would change
   - Why (with reasoning)
   - Level of disruption (low/medium/high)
   - Implementation cost (rough estimate)
   - Context-token impact (reduces/increases/maintains)

3. **Alternative designs** — if you were building this from scratch today (knowing the constraints above), what would you do differently? Be opinionated. Tell us what we're doing wrong, not just what we could do better.

4. **Context budget strategy** — your recommendation for how to balance "agent awareness" vs. "context economy" given the project's data scale.

5. **Search design** — given that search is mostly for finding "where is X mentioned across the story," what's the right architecture?

---

## 8. Supporting Files in This Directory

- `architecture.md` — detailed breakdown of index generation, enrichment phases, and data structures
- `fixtures/` — actual note samples from a real project (save-the-children)

---

## 9. Summary for Quick Reading

**Current state**: Obsidian vault + YAML frontmatter + `##` body sections = the database. A pre-computed `index.yaml` is the navigation cache. `story_load` loads the full index into context. `story_retrieve` reads individual notes by section. `story_search` does O(n) substring scan. Staleness is handled by auto-refresh hooks (imperfectly).

**Tension**: More awareness (full index, detailed search results) costs context tokens. Less awareness costs navigation fluency (the agent can't see the whole structure and may miss connections).

**Question**: For a single-user, single-project personal tool with <200 notes, are we over-engineering (could be simpler) or under-engineering (should be smarter)? The truth is probably somewhere in between — and I want your opinion on where that line is.
