# Architecture Deep-Dive — Index, Retrieval, and Data Flows

> Companion to `brief.md`. This file provides the implementation-level detail a specialist needs to reason about optimizations.

---

## 1. Data Structures

### 1.1 Index YAML (generated)

```yaml
project:
  id: save-the-children
  name: "Save the Children"
  logline: "..."
  scene_count: 9
  character_count: 5
  # ... all project frontmatter + counts

characters:
  - id: dr-elena-voss
    name: "Dr. Elena Voss"
    story_role: Supporting
    one_sentence: "Lead scientist..."
    sections: [Personality, Background, Voice, Greatest Fear, Secrets, Arc, Relationships, Goals]
    scenes:                          # enriched
      - id: central-room-day
        title: "Central Room - Day"
        heading: "INT. THE CENTRAL ROOM - DAY"
    arc_beats_list:                  # enriched
      - id: "1"
        label: "The Choice"
        scene: central-room-day
        shift: "positive → negative"
        y: 0.8
        order: 1
    arc_beat_count: 1

locations:
  - id: the-central-room
    name: "The Central Room"
    one_sentence: "..."
    sections: [Description, History, Scenes]
    scenes:                          # enriched
      - { id: central-room-day, title: "...", heading: "INT. ..." }

worlds: [...]

plots:
  - id: the-resistance
    name: "The Resistance"
    one_sentence: "..."
    status: active
    characters: [kael, mira]
    setups:                          # normalized
      - scene_id: central-room-day
        description: "Kael discovers the door isn't locked"
    payoffs:
      - scene_id: the-core-day
        description: "..."
    sections: [Summary, Obstacles, Stakes]

scenes:
  - id: central-room-day
    title: "Central Room - Day"
    order: 1
    status: drafted
    sequence_id: seq-discovery
    act_id: act-1
    heading: "INT. THE CENTRAL ROOM - DAY"
    characters: [kael, mira]          # from frontmatter
    plots: []                         # enriched (reverse from plot)
    location: the-central-room
    sections: [Description, Dramatic Function, Notes, Content]

sequences:
  - id: seq-discovery
    title: "The Discovery"
    order: 1
    status: in-progress
    act_id: act-1
    scenes_list: [central-room-day, central-room-night, the-core-day]  # enriched
    scene_count: 3
    plots: [...]                      # enriched

acts:
  - id: act-1
    title: "Act I"
    order: 1
    status: planned
    sequences_list: [seq-discovery]   # enriched
    scenes_list: [...]                # enriched
    sequence_count: 1
    scene_count: 3
    plots: [...]                      # enriched

arcs:
  - id: "1"
    character: dr-elena-voss
    scene: central-room-day
    label: "The Choice"
    action: "..."
    gap: "..."
    choice: "..."
    shift: "positive → negative"
    y: 0.8
    order: 1
    is_crisis: false
    is_climax: false
    sections: [Action, Gap, Choice, Shift, Development Log]
```

### 1.2 Entity Note Format

```markdown
---
# Schema-defined frontmatter fields (validated against ENTITY_SCHEMAS in core/constants.py)
name: Dr. Elena Voss
story_role: Supporting
one_sentence: "Lead scientist..."
arc_type: negative
arc_value: Redemption
# ... entity-specific required/optional fields
---

## Personality
<prose>

## Background
<prose>

## Voice
<prose>

## Greatest Fear
<prose>

## Secrets
<prose>

## Arc
<prose>

## Relationships
- **<character-name>** — <description>

## Goals
- Short: <goal>
- Long: <goal>
```

### 1.3 Memory File

```markdown
## Continuity Notes
<Facts the agent needs to track across sessions>

## Character Knowledge
<Per-character state changes, decisions>

## World Events
<Timeline of in-story events>

## Open Questions
<Unresolved issues the agent should remember>
```

---

## 2. Index Generation: Step by Step

```
generate_index(project_path)
│
├─ Phase 1: PARSE (I/O bound)
│   ├─ _parse_entities("characters")     → list[dict]  (id + frontmatter + sections)
│   ├─ _parse_entities("locations")      → list[dict]
│   ├─ _parse_entities("worlds")         → list[dict]
│   ├─ _parse_entities("plots")          → list[dict]
│   ├─ _parse_entities("scenes")         → list[dict]
│   ├─ _parse_entities("sequences")      → list[dict]
│   ├─ _parse_entities("acts")           → list[dict]
│   ├─ _parse_arcs("arcs/")              → list[dict]  (nested: arcs/{character}/{beat}.md)
│   └─ _parse_project(..., counts...)   → dict
│
├─ Phase 2: ENRICH (CPU bound, in-memory)
│   ├─ _enrich_entity_scenes             → char.scenes[], loc.scenes[]
│   ├─ _enrich_relationships             → rel.label defaults
│   ├─ _enrich_plots                     → normalize setups/payoffs
│   ├─ _enrich_scenes_with_plots         → scene.plots[] (reverse lookup)
│   ├─ _enrich_structure                  → seq.scenes_list[], act.sequences_list[], act.scenes_list[]
│   ├─ _enrich_sequences_with_plots       → seq.plots[]
│   ├─ _enrich_acts_with_plots           → act.plots[]
│   ├─ _enrich_characters_with_arcs       → char.arc_beats_list[], char.arc_beat_count
│   └─ _enrich_scenes_with_arcs           → scene.arc_beats[]
│
├─ Phase 3: VALIDATE
│   └─ _validate_index                   → cross-ref integrity (character IDs, scene IDs, etc.)
│
└─ Phase 4: WRITE
    └─ write_index                       → .story/index.yaml (YAML dump)
```

**Performance characteristics**:
- Phase 1: Reads 50-200 files. Each is 1-5KB. Total I/O: ~1MB worst case. Negligible.
- Phase 2: All in-memory dict/list operations. Negligible.
- Phase 3: Set lookups. Negligible.
- Phase 4: Single YAML dump of ~50-200KB. Negligible.

**Conclusion**: Index generation is NOT the bottleneck. It runs in <100ms for any realistic project size.

---

## 3. Retrieval Flows (Current)

### 3.1 Project Load (`story_load`)

```
story_load(project="save-the-children")
│
├─ resolve_project()                    → Path  (fuzzy match)
├─ read .story/index.yaml               → dict  (full navigation graph)
├─ read .story/memory.md                → str   (continuity notes)
│
└─ return JSON: {
     "loaded": true,
     "confirmation": "Loaded Save the Children — 9 scenes, ...",
     "project": { ... },               ← project frontmatter
     "index": { ... },                  ← FULL index (all entities, all enrichments)
     "memory": "..."                    ← memory.md content
   }
```

**Context cost**: The full `index` object is serialized to JSON and returned as the tool result → goes into the LLM context. For a 50-scene project, this is typically 30-80K tokens.

### 3.2 Entity Section Retrieval (`story_retrieve`)

```
story_retrieve(project, entity_type, slug, sections=["Voice", "Secrets"])
│
├─ resolve_project()                    → Path
├─ find_entity_path()                   → Path  (flat or nested)
├─ frontmatter.load(file_path)          → Post (metadata + content)
├─ get_section(body, "Voice")           → str   (regex split on ## headings)
├─ get_section(body, "Secrets")         → str
│
└─ return JSON: {
     "entity_type": "character",
     "slug": "dr-elena-voss",
     "sections": {
       "Voice": "## Voice\nMeasured, precise...",
       "Secrets": "## Secrets\nElena knew..."
     }
   }
```

**Context cost**: Targeted. Only requested sections returned. ~200-2000 tokens.

### 3.3 Search (`story_search`)

```
story_search(project, query="elena")
│
├─ resolve_project()                    → Path
├─ for each entity_folder:
│     for each *.md in folder:
│       content = note.read_text()
│       if query in content.lower():
│         matching_lines = [...first 5...]
│         results.append({entity_type, slug, matches})
│
└─ return JSON: {
     "query": "elena",
     "results": [...all matching files...],
     "total": N
   }
```

**Context cost**: Variable. If "elena" appears in 20 notes, returns 20 result objects + matching lines (up to 5 each = 100 lines). Could be 5-20K tokens.

### 3.4 Entity Edit (`story_edit`)

```
story_edit(action="edit_note", target={entity_type, slug}, data={...})
│
├─ find_entity_path()
├─ frontmatter.load()
├─ for key, value in data.items():
│     if key in ENTITY_SCHEMAS[entity_type]: → frontmatter update
│     else:                                    → body section replace (replace_section)
├─ frontmatter.dump()
├─ _refresh_index()                     → regenerate index.yaml
└─ auto-refresh hook fires              → re-open dashboard (but NOT re-load index into context)
```

**Critical gap**: After edit + index regeneration, the agent's context still has the OLD index from the last `story_load`. The on-disk index is fresh, but the in-context index is stale until the next explicit `story_load` call.

---

## 4. Data Scale Analysis

### 4.1 Index Size Estimation

For the `save-the-children` fixture (a real small project):

| Entity | Count | Size per entity (YAML) | Total |
|--------|-------|----------------------|-------|
| Project | 1 | ~1 KB | 1 KB |
| Characters | 5 | ~0.8 KB (with enriched scenes, arc beats) | 4 KB |
| Locations | 2 | ~0.5 KB (with enriched scenes) | 1 KB |
| Worlds | 2 | ~0.3 KB | 0.6 KB |
| Plots | 2 | ~0.6 KB | 1.2 KB |
| Scenes | 3 | ~0.7 KB | 2.1 KB |
| Sequences | 1 | ~0.8 KB | 0.8 KB |
| Acts | 1 | ~0.9 KB | 0.9 KB |
| Arc beats | 9 | ~0.4 KB | 3.6 KB |
| **Total** | **26 entities** | | **~15 KB YAML** |

15 KB YAML ≈ ~4K tokens (YAML is token-dense due to keys and indentation).

For a large project (100 scenes, 30 characters, 50 arc beats):

| Component | Estimated YAML size |
|-----------|-------------------|
| Scenes (100 × 1KB) | 100 KB |
| Characters (30 × 2KB with enrichment) | 60 KB |
| Arc beats (50 × 0.5KB) | 25 KB |
| Other entities | 25 KB |
| **Total** | **~210 KB YAML** |

210 KB YAML ≈ **~50-70K tokens**. That's a significant chunk of a 200K context window.

### 4.2 What's in the Index vs. What's Needed

When the agent is working on dialogue for Elena, what does it actually need?

| In the index | Needed for dialogue work? |
|-------------|--------------------------|
| All 50 characters' full summaries | No — just Elena's `## Voice` section |
| All 100 scenes' metadata | No — just the scene being written |
| All 50 arc beats | No — just Elena's beats |
| All plot setups/payoffs | Maybe — for context |
| All location descriptions | No |
| **Just Elena's frontmatter + Voice section** | **Yes** |

The index gives the agent **broad awareness** but the agent then uses `story_retrieve` to get **specific depth**. The question is: how much of the broad awareness is actually used? In practice, the LLM attends to fragments of the large JSON, ignoring most of it — but it STILL pays the token cost to receive it.

---

## 5. Staleness Analysis

### 5.1 When Staleness Occurs

1. **External edit** — user edits a note in Obsidian directly. No hook fires. Index is stale until next `story_index`.
2. **Edit via `story_edit`** — index auto-refreshes (hook fires), on-disk index is fresh, but agent's in-context index is STALE. The agent reads old index data.
3. **Create via `story_create`** — same situation.
4. **Edit sequence membership** — adding/removing a scene from a sequence changes `seq.scenes_list[]` in the index. This is ONLY in the index. If stale, the agent navigates a non-existent scene.

### 5.2 Impact

- Agents may reference entities that don't yet exist or have wrong metadata.
- Navigation (e.g., "what scenes are in sequence X?") returns stale results.
- Relationship lookups (character ↔ scene, scene ↔ plot) are wrong.
- After `story_edit`, the agent's next `story_retrieve` reads the NOTE (which is fresh) but its understanding of the GRAPH is stale.

### 5.3 Current Mitigation

- Post-tool-call hook auto-refreshes index on edits (but doesn't re-load into context).
- The `story_load` tool can be called explicitly to re-load (agent-initiated).
- The LLM is often smart enough to note "index may be stale, verify by reading the note directly" — but not always.

---

## 6. Context Token Economy

### 6.1 Token Costs by Operation (estimates for 50-scene project)

| Operation | Tokens in result | Notes |
|-----------|-----------------|-------|
| `story_load` (full index) | 30,000-60,000 | Single biggest cost |
| `story_retrieve` (2 sections) | 500-2,000 | Cheap and targeted |
| `story_search` (10 hits, 5 lines each) | 3,000-8,000 | Moderate |
| `story_edit` | 200-500 | Cheap |
| `story_create` | 200-500 | Cheap |
| **Total for typical session** | **~40,000-80,000** | Just data retrieval, before actual work |

### 6.2 The Tension

- **Agent needs the graph** to know what exists and navigate. Without it, each step is blind.
- **Agent doesn't need the whole graph** at full detail for every task.
- The LLM's context is the budget. Spending 50K tokens on the index means 50K fewer tokens for actual story content, discussion, and reasoning.

### 6.3 What the Agent Actually Needs at Each Phase

| Phase | What the agent needs from the index |
|-------|-------------------------------------|
| Starting a session on a project | Project metadata, entity names + IDs, counts. NOT enrichment lists. |
| Writing dialogue for a character | That character's name + relevant scenes. NOT all 50 characters. |
| Checking plot continuity | Affected plot's setups/payoffs + scenes. NOT all plots. |
| Editing a scene | Scene's current state + sequence/act membership. NOT all scenes. |
| Navigating structure | sequences → scenes, acts → sequences lists. These ARE needed. |
| Searching for	info | No index needed (search reads notes directly). |

---

## 7. File Format Constraints

### 7.0 The Dashboard — current role and future potential

The plugin has a full HTML dashboard (`story_dashboard` tool), opened in the Hermes Desktop preview pane. It is **read-only** but already consumes note data:

**What it does today:**
- Reads `index.yaml` + note sections + project frontmatter
- Injects data as `window.__STORY_DATA__` (navigation graph), `window.__SECTIONS__` (section content), `window.__SCREENPLAY_STATS__` (duration, character speaking time, INT/EXT, location stats from Fountain content), `window.__STRUCTURAL_STATS__` (scene status, dramatic roles, plot coverage)
- Renders entity navigation, screenplay view with pre-rendered HTML, stats panels

**What it reveals about the architecture:**
- The dashboard is already a **view layer** over the same data the agent reads
- Notes are the only source of truth; the dashboard derives everything from them
- Some metrics the agent would need to compute (duration, speaking time) are already computed here — a sign of context overlap

**Relevance to storage format:**
- **Current (markdown)**: user edits notes in a text editor → tells agent → agent calls `story_edit` → file write → index refresh → context reload. Every simple correction is an agent round-trip.
- **Structured store (JSON/SQLite)**: user could edit directly in the dashboard → write to store → agent queries fresh data next time. Dashboard becomes the editor.
- This is a FUTURE possibility, not a current requirement. But it argues for choosing a storage format that doesn't close the door on it.
- The key consideration: **if we keep markdown, can the dashboard still become an editor later?** With an intermediate translation layer (dashboard → note writer), yes — but that's another layer of code. With JSON, the dashboard writes the same format the agent reads. With SQLite, same — direct read/write.

### 7.1 Current format — inherited, not required
The current format (markdown + YAML frontmatter + `##` body sections) was inherited from the plugin's origin as an Obsidian plugin. It is NOT a hard requirement. Rationale for keeping it so far:
- Git diffs are human-readable.
- Python's `frontmatter` library handles it with ~5 lines of code.
- No DB file that gets corrupted or needs migration.
- Familiar to Obsidian users.

**But**: the plugin has a dashboard that already provides visual access. The user does not need to edit files in Obsidian. This is now an open question for the specialist — the format was kept by convention, not by necessity.

### 7.2 The cost of the current format
Every downstream problem traces back to the storage choice:

| Symptom | Root cause |
|---------|-----------|
| Stale index after edits | The index (`index.yaml`) is a denormalized cache of note contents. Two representations of the same data = divergence risk. |
| Section parser module | Markdown has no structured sub-note format, so we regex-split on `##` headings |
| Context bloat from `story_load` | YAML is token-dense (keys, indentation, quoting) — 210KB YAML ≈ 50-70K tokens |
| Naive `story_search` | No structured query layer; search reads entire files because there's no DB index |
| Frontmatter minimalism | Structured data was squeezed into YAML frontmatter, forcing a split between "what the index needs" (FM) and "what the agent needs to read" (body sections) |
| Duplicated mental model | The index duplicates the relationship graph already present in the notes. If `story_edit` updates a scene's characters, the index is stale until refresh. |

**If the storage format is the root cause of 5 of 7 identified problems, the specialist should evaluate whether to fix the symptoms or the cause.**

### 7.3 Why `##` Sections (not structured sub-key)
- Markdown is the current format; section headings are visually clear in the editor.
- The regex-based `section_parser` (20 lines) handles extraction.
- **Cost**: This is a workaround for lack of structured sub-note format. If we used JSON or SQLite, we'd query sub-objects directly.

### 7.4 Why YAML Index (not SQLite)
- YAML is human-readable in a text editor.
- The index can be opened and understood without any tooling.
- Python's `yaml` library handles dump/load trivially.
- **Cost**: YAML is 40% more token-dense than JSON for the same data. For 210KB YAML → ~50-70K tokens in context.
- **Cost**: Denormalized cache = staleness risk. If the underlying note is edited, the index diverges until refreshed.

---

## 8. Key Design Decisions for Critique

These are the decisions a specialist should evaluate — **in priority order**:

1. **Storage format itself** (markdown+frontmatter vs. JSON vs. SQLite vs. other) — the #1 question. Everything downstream is constrained by this choice.
2. **Full-index load into context** (vs. summary + on-demand detail)
3. **On-demand `story_retrieve`** (sections only — good granularity, but depends on storage format)
4. **O(n) substring search** (works at this scale, but: no filtering, no ranking, no section-scoping)
5. **Index as denormalized cache** (fast navigation, but: staleness risk — only exists because storage format requires it)
6. **No query API** (agent can only load-full or retrieve-one; no "get_scenes_in_sequence" tool)
7. **Staleness handled by hooks** (auto-refresh after edit, but: doesn't re-load into context)
8. **Validation prints warnings** (prints to stdout — where does this go in Hermes Desktop?)


---

## 9. End-to-End Data Flow

```
[User: "Write Elena's dialogue for scene 3"]
        │
        ▼
[Agent calls story_load("save-the-children")]
        │
        ▼
[Reads .story/index.yaml → full graph in context]
        │
        ▼
[Agent identifies scene 3 = "central-room-day"]
[Agent reads index.scene["central-room-day"] → metadata]
[Agent needs Elena's voice → calls story_retrieve]
        │
        ▼
[story_retrieve("character", "dr-elena-voss", ["Voice"])]
        │
        ▼
[Reads characters/dr-elena-voss.md]
[Extracts "## Voice" section → returns to context]
        │
        ▼
[Agent writes dialogue using Voice context]
        │
        ▼
[Agent calls story_edit to update scene content]
        │
        ▼
[story_edit reads note → replaces "## Content" → saves → refreshes index.yaml]
[Context now has stale index (old content gone, new not loaded)]
        │
        ▼
[Agent calls story_retrieve to verify the edit]
        │
        ▼
[ story_retrieve reads the fresh note → returns updated Content]
```

---

## 10. Summary for Quick Reference

| Aspect | Current state |
|--------|--------------|
| Storage | Markdown files + YAML frontmatter + `##` body sections |
| Index | Single `index.yaml`, pre-computed denormalized cache |
| Load | Full index into LLM context via `story_load` |
| Targeted read | `story_retrieve` — one note, specific sections |
| Search | `story_search` — O(n) substring across all notes |
| Edit | Frontmatter OR section body + auto index refresh |
| Staleness | Hook fires on edit → refreshes file but NOT context |
| Scale ceiling | ~200 notes, ~50-200 KB index YAML (~15-70K tokens) |
| Key weakness | Context bloat from full load + stale in-context index after edits; section-parser complexity from markdown format |
| Key strength | Simplicity, zero infrastructure, git-diffable, human-readable |
| Root question | Is the inherited markdown+frontmatter format the right storage layer, given the dashboard already provides visual access? |
