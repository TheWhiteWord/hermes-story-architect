# story_load Redesign — Specialist Brief

## Objective

Redesign the `story_load` tool's output payload to minimize token consumption at session start, while preserving the agent's ability to understand the story, navigate its structure, and infer what to retrieve on demand.

The goal: **a slim, complete-enough overview** — not a full data dump.

---

## Current Behavior (the Problem)

`story_load` currently returns, in a single JSON payload:

1. **Project metadata** — all frontmatter fields (name, logline, genre, setting, spine, controlling_idea, value, value_at_open/close, inciting_incident, story_climax, structure_type, act_count, title-page fields)
2. **ALL entities** — every row from the `entities` table: `id, type, name, one_sentence, status, order_key, parent_id, location_id, extra` (where `extra` is a JSON blob containing ALL remaining frontmatter fields for that entity)
3. **ALL relations** — every row from the `relations` table: `from_id, to_id, kind`
4. **Memory** — full text of `.story/memory.md`
5. **Unfilled fields** — per-entity list of optional fields still at default values

For a feature-length film (120+ scenes, 20+ characters, 5+ plots, arcs per character), the entities + relations arrays alone could exceed **100k tokens**. This defeats the purpose of a quick session-start overview.

---

## Data Model Reference

### Entity Types and Fields

| Entity | Column-mapped fields | Extra JSON fields |
|--------|---------------------|-------------------|
| **project** | name, one_sentence (as logline) | genre, setting, status, spine, controlling_idea, value, value_at_open/close, structure_type, act_count, screenplay_title, credit, author, contact, draft_date, draft, inciting_incident_scene_id, story_climax_scene_id |
| **character** | name, one_sentence | story_role, arc_type, arc_value, arc_value_at_open/close, arc_complete, relationships, goals_short, goals_long, knowledge |
| **location** | name, one_sentence | — |
| **world** | name, one_sentence | rules |
| **plot** | name, one_sentence, status | plot_type, plot_scope, value_arc, characters, setups, crisis, climax, payoffs |
| **scene** | name (as title), order_key, status, parent_id (sequence), location_id | heading, time_of_day, act_id, characters, value, value_open/close, conflict_levels, dramatic_role, is_inciting_incident, is_sequence_climax, is_act_climax, is_story_climax |
| **sequence** | name (as title), order_key, status, parent_id (act) | act_id, value, value_open/close, climax_scene_id, primary_plot, purpose |
| **act** | name (as title), order_key, status | value, value_open/close, climax_scene_id, act_objective |
| **arc** | name (as label), order_key, parent_id (character) | scene, action, gap, choice, shift, y, is_crisis, is_climax |

### Relation Kinds

- `character_scene` — character appears in scene
- `location_scene` — location used in scene
- `character_relationship` — character → character (note: JSON {label, feeling})
- `plot_setup`, `plot_crisis`, `plot_climax`, `plot_payoff` — plot beat → scene (note: description text)

### Structural Hierarchy

```
act → sequence → scene
  (parent_id chains: scene.parent_id = sequence.id, sequence.parent_id = act.id)
```

arc entities have `parent_id = character.id`, and a `scene` field indicating where the beat occurs.

---

## Sibling Tools (Retrieval Options)

These are available for on-demand data fetching AFTER load:

### `story_retrieve(project, entity_type, slug, sections)`
- Fetches specific `## section` bodies from a specific entity
- `sections: ["all"]` returns every section
- Granularity: per-entity, per-section
- Returns full prose content for the requested entity only

### `story_search(project, query)`
- FTS5 full-text search across ALL section bodies in the project
- Returns `{entity_id, heading, snippet}` hits
- Granularity: keyword-driven, finds content inside entity bodies

### `story_dashboard(project)`
- Opens a visual dashboard in the preview pane (HTML/JS)
- Shows structural stats, arc plots, scene status — visual, not text

---

## Design Philosophy

**This is NOT a "just dump everything and let the agent sort it out" problem, nor is it a "strip everything to the bare minimum and call it a day" problem.** The goal is a carefully considered, well-tailored payload where every field present has a justified reason for being there — one that directly serves the agent's ability to understand the story, navigate it, and proactively suggest next steps.

If a field from `extra` belongs in the load payload because it provides meaningful signal (e.g., `arc_type` tells the agent at a glance who has a completed arc vs. an absent one, `dramatic_role` reveals whether the structure is functional), then it should stay — even if it wasn't in the original column mapping. Evaluate each field independently on its merits, not based on where it happens to be stored.

### Proactive Awareness

The agent must be aware of **what has not yet been filled in**. When a user asks "what should we work on next?" or "what's missing?", the agent should be able to answer from the load payload alone — without needing to call `retrieve` for every entity. The `unfilled` field map (which optional fields are still at default values per entity) is a critical design element, not an expendable extra. Consider how to encode this efficiently so the agent can proactively surface gaps (e.g., "Mira has no personality section yet", "Act II has no scenes", "3 scenes lack dramatic_role").

---

## Key Design Questions for You

1. **For each field in the data model, should it be in the load payload?**
   - Evaluate independently — not based on column vs. extra, but on whether it provides meaningful signal at session start
   - Some `extra` fields deserve to stay (e.g., `arc_type`, `dramatic_role`, `plot_scope`, `status`)
   - Some column fields might be droppable (e.g., `location_id` if location name is enough)
   - For each kept field, explain WHY it deserves to be there. For each dropped field, explain what retrieve call replaces it.

2. **How should unfilled fields be encoded for proactive gap surfacing?**
   - The agent MUST be able to answer "what's missing?" from load alone
   - Current format: `{entity_slug: [field1, field2, ...]}` — 100 entities × 6 fields avg = significant token cost
   - Can we compress? (e.g., only list entities WITH unfills, use bitmask, use short codes)
   - Should section-body absence be included? (e.g., "kael has no Personality section" — currently not tracked)

3. **How should relations be represented?**
   - Current: 860 raw rows × 15 tokens = ~13k tokens for feature film
   - Can we pre-aggregate? (e.g., per-character scene list, per-scene character list — denormalized but smaller)
   - Is there a compact encoding that preserves navigability without dumping every edge?
   - Should we separate structural hierarchy (parent_id) from cross-references (character_scene, plot_setup)?

4. **What's the right level of detail per entity type?**
   - Not all entity types need the same fidelity. Characters at a glance vs. scenes at a glance serve different purposes.
   - Should characters keep `story_role`, `arc_type`, `arc_complete`? (agent needs to know who matters and whether arcs are done)
   - Should scenes keep `dramatic_role`, `value_open/close`? (agent needs structural awareness)
   - Should arc beats keep `y`, `is_crisis`, `is_climax`? (agent needs to know arc shape) But what about `action/gap/choice` prose?

5. **Memory file — how much is enough?**
   - Full text of `.story/memory.md` could be 5k+ tokens for feature films
   - Is a summary/truncation acceptable, or must the agent see all continuity notes?
   - If truncated, how does the agent know what it's missing?

6. **How should the structural hierarchy be encoded?**
   - Currently: flat entities + flat relations, agent reconstructs via parent_id
   - Alternative: pre-grouped hierarchy (act → sequence → scene) so the agent doesn't need to join
   - Trade-off: grouping adds overhead but improves readability

---

## Deliverable Expected

Propose a **new payload shape** for `story_load` that:

- Keeps the load small (target **< 3k tokens** for a feature-length project, ideally < 1.5k)
- Preserves navigability (agent can answer "what scenes is Kael in?", "what's in Act II?", "which plot touches scene X?" — either directly or by knowing what to retrieve)
- Clearly separates "overview data" from "detail data available via retrieve"
- **Includes a per-field justification**: for every field kept in the load, explain why it deserves to be there. For every field removed, explain what retrieve call replaces it and why the agent doesn't need it at session start.
- **Provides efficient unfilled-field encoding** so the agent can proactively surface gaps without per-entity retrieve calls
- Includes a migration strategy: what changes in `get_project_summary()`, what the retrieve call patterns look like for the dropped fields

---

## Context Files

See attached:
- `data_model.md` — full field listing with token cost estimates
- `current_payload_example.md` — what the current load returns for the test fixture
