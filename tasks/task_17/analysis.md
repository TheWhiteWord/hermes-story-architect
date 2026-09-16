# Task 17 — Skill Structure Analysis

## 1. Domain Analysis

**What the plugin does**: Story projects as Markdown + YAML frontmatter in a dedicated vault. Hermes provides the intelligence layer. The preview pane provides interactive navigation.

**Vault structure**: `~/story-vault/projects/<slug>/` with entity folders (`characters/`, `locations/`, `worlds/`, `plots/`, `scenes/`, `sequences/`, `acts/`, `arcs/`) plus `.story/index.yaml` (always-loaded graph) and `.story/memory.md` (continuity map).

**Entity types** (9 total): project, character, location, world, plot, scene, sequence, act, arc.

**Key architectural concept — Frontmatter → Body Mapping**: Frontmatter holds summary/label data (the "what"), body holds detailed prose in standard `##` sections (the "how/why"). The index maps frontmatter fields to body section names so retrieval can be targeted: "What's Mara's voice?" → index says `Voice` section exists → retrieve only that section, not the whole note.

**Three-stage retrieval**: index (always loaded) → section targeting (which `##` sections from which notes) → content load (only the needed prose).

**Action protocol**: No edit is applied without explicit human approval. Propose → review → apply.

**Screenplay**: Scenes contain Fountain syntax in their `## Content` section. The dashboard assembles these for stats/visualization.

---

## 2. Tool Surface

8 registered tools, mapped to user tasks:

| Tool | User intent | Complexity |
|------|-------------|------------|
| `story_load` | "Load project X" — ALWAYS the first step | Low |
| `story_retrieve` | "Show me Mara's Voice section" — targeted content | Low |
| `story_create` | "Add a character/scene/plot" — scaffolding | Medium (parent validation, auto-order, project init) |
| `story_edit` | "Change X to Y" — edits + delete + reorder + memory | HIGH (data bag routing: key ∈ schema → frontmatter, key ∈ sections → body) |
| `story_search` | "Find all scenes with Oak" — grep across notes | Low |
| `story_index` | "Refresh the index" — regenerate graph | Low |
| `story_dashboard` | "Show dashboard" — preview pane | Low |
| `story_describe` | Schema discovery | Low |

---

## 3. User Workflows (from most to least common)

1. **Load + Explore + Edit** (80%): load → read index → retrieve sections → answer or propose edit → apply → refresh index
2. **Create entity**: create → confirm → (optional: edit to fill details)
3. **Search/answer**: search or retrieve → answer (no edit)
4. **Dashboard**: dashboard → show preview
5. **Create project**: initialize full scaffold (rare)

Workflows 1-2-3 share the same retrieval pattern and almost always start with `story_load`. They belong in one skill.

---

## 4. Proposed Skill Structure

### One skill, two reference zones

```
hermes-story-architect/
├── SKILL.md                           ← index + workflow + decision tree + pointers
├── references/
│   ├── operational/
│   │   ├── schemas.md                 ← full field schemas (all 9 entity types)
│   │   └── action-protocol.md         ← review loop, data bag semantics, reorder rules
│   ├── theory/
│   │   ├── values.md                  ← value arcs + charges (maps to arc_type, value fields)
│   │   └── plot.md                    ← plot types/scope (maps to plot_type, plot_scope fields)
│   └── screenplay.md                  ← fountain formatting conventions (scene headings, cues, transitions)
└── examples/
    └── character-note.md              ← worked example showing frontmatter → body mapping
```

**Why screenplay sits at `references/` root**: It's neither operational (not about tool workflows) nor theory (not about story concepts). It's a formatting convention — rules for writing Fountain correctly so the parser handles it. Cross-cutting: needed when editing scene content AND when understanding dashboard output. No subfolder needed for a single file.

**Why this is right:**
- Single skill — load/edit/retrieve always share context, no double-load
- Theory stays coupled to operations: `values.md` documents what `arc_type`, `arc_value_at_open/close`, `value` fields mean *and when to use them*
- Theory is consulted during editing ("what value charge fits this beat?") — same skill, different reference folder, lazy-loaded
- `references/operational/` vs `references/theory/` is the classification the agent uses at decision time: "do I need to know HOW to edit, or WHAT to write?"

**What goes in SKILL.md** (the always-loaded index, ~200-300 lines):
- One-line purpose + when to trigger (story projects, characters, scenes, plots, etc.)
- The common workflow (load → index → retrieve → answer/edit) written as executable steps
- Standard sections per entity type (compact table — needed on every retrieval)
- Frontmatter → body mapping rule (the core concept)
- Decision tree: "If user wants to create → do X. If edit → see action-protocol.md. If dashboard → call story_dashboard."
- One-line pointer to each reference file with when to open it

**What goes in `references/operational/schemas.md`** (Level 3 — loaded only when agent needs field detail):
- Full field list per entity type with types, defaults, descriptions
- This is the "filing cabinet" the agent consults when it needs to know what fields a scene has

**What goes in `references/operational/action-protocol.md`** (Level 3 — loaded only when editing):
- The review loop: propose → show in chat → user approves → apply → confirm
- Data bag semantics: how `story_edit` routes keys (schema field vs. body section)
- Delete rules (cascade blocking for structural types)
- Reorder rules (ordered_ids semantics)
- Story memory update pattern

**What goes in `references/screenplay.md`** (Level 3 — loaded when editing scene content or understanding dashboard output):
- Fountain formatting rules: scene headings (`INT. PLACE - TIME`), character cues (`NAME`), parentheticals, transitions, emphasis
- How to write `## Content` sections so the parser handles them correctly
- What the dashboard does (assembles scene content for stats/visualization) — so the agent knows why formatting matters

**What goes in `references/theory/values.md`** (Level 3 — loaded when agent needs to understand value fields):
- Value charges (positive/negative/mixed/ironic) — maps to `arc_value_at_open`, `arc_value_at_close`, `value_open`, `value_close`
- Value arcs (Maturation/Redemption/Education/Punitive/Disillusionment/Testing) — maps to `value_arc`
- When to use each, with field references

**What goes in `references/theory/plot.md`** (Level 3 — loaded when agent needs to understand plot fields):
- Plot types (Contradictory/Resonant/Complicating/Setup) — maps to `plot_type`
- Plot scopes (main/sub) — maps to `plot_scope`
- Setups/payoffs structure — maps to `setups`/`payoffs` fields

**What goes in `examples/character-note.md`**:
- A fully worked character note showing frontmatter fields + all standard body sections
- Serves as a pattern to imitate when creating/editing

---

## 5. Key Design Decisions

1. **Single skill with two reference zones** — load/edit/search are coupled (no double-load), and theory fields map directly to operational fields (`value_arc` field ↔ `Maturation/Redemption` theory). Splitting into two skills would break the coupling.

2. **SKILL.md stays under ~300 lines** — the guide's "aim under 500" gives us headroom. Standard sections table + workflow + pointers is compact.

3. **Schemas in references, not SKILL.md** — 186 lines of field definitions is Level 3 material. The agent discovers fields via `story_describe` at runtime or reads the reference when it needs detail. SKILL.md only has the compact standard-sections table.

4. **Screenplay at `references/` root** — It's neither operational (tool workflows) nor theory (story concepts). It's a formatting convention for writing Fountain correctly. Cross-cutting: needed when editing scene content AND understanding dashboard output. No subfolder for a single file.

5. **No skill-level scripts** — all deterministic logic already lives in plugin-level Python (core/index.py, core/section_parser.py, tools/). The guide's rule: "if the same logic needs to be exposed as a first-class capability the model can call directly, it belongs in the plugin's Python code as a registered tool, not as a skill script."

6. **One worked example** — character notes are the richest entity type (most fields + most sections). One complete example establishes the frontmatter → body pattern that applies to all other types.

---

## 6. Open Questions

1. **Should `story_describe` be mentioned in SKILL.md as a runtime schema discovery tool, or should the agent always use the reference file?** Pro: mention it as a fallback ("if you need runtime field validation, use story_describe"). Con: might encourage unnecessary tool calls.

2. **Screenplay is a reference, not a separate skill.** Screenplay isn't a workflow — it's a formatting convention. The agent only needs to know: scene content lives in `## Content` sections as Fountain syntax, the dashboard assembles it for stats/visualization. The reference is "how to format Fountain correctly so the parser doesn't choke" (scene headings, character cues, transitions), not a separate skill.


