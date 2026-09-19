# `story_load` Redesign — Consolidated Specification

Target: reduce feature-scale load payload from ~47,000 tokens to ~8,000–8,500 tokens while preserving structural navigability and proactive gap-awareness.

---

## 1. Core Principles

1. **No flat `relations` table.** Every relation is an attribute of one of its two endpoints and gets embedded there (scene carries `chars`, plot carries scene-id arrays, character carries `rel`). This removes ~12.9k tokens with no loss of navigability, since reverse lookups ("what scenes is this character in?") become a scan of the already-present scene list rather than a join.
2. **Structure is implied by nesting, not by `parent_id`.** `act → sequences → scenes` is expressed as literal JSON nesting. `sequence_id`, `act_id`, and `parent_id` fields disappear entirely — containment *is* the pointer.
3. **Order is implied by array position, not an `order` field.** Progression (scene order, arc-beat order) is real signal worth keeping, but position in an array carries it for free.
4. **Hybrid full/stub representation for scenes and arc beats.** Entities with no creative work done yet collapse to a bare id string inside the same ordered array as fully-detailed entities. Consumers branch on `typeof`. This is the same classifier used for unfilled-field surfacing (§4), so it's one mechanism serving two purposes, not two systems.
5. **Omitted field = unfilled.** Defaults/empties are never emitted — except `status`, which is always emitted because it's a user-facing progress signal, not just data. This makes per-field unfilled-detection close to free rather than a parallel bookkeeping structure.
6. **Every kept field earns its place on session-start signal value, not on where it happens to be stored** (column vs. extra JSON) — per the brief's original design philosophy.

---

## 2. Full Payload Schema

```json
{
  "loaded": true,
  "confirmation": "Loaded <project-name> — N scenes (M developed), N sequences, N acts, N characters, N locations, N plots, N worlds.",

  "project": {
    "name": "<project-name>",
    "logline": "<one-sentence summary>",
    "genre": "<genre>",
    "setting": "<setting>",
    "status": "<active|abandoned|archived>",
    "spine": "<protagonist's desire>",
    "controlling_idea": "<thematic argument>",
    "value": "<value-at-stake>",
    "value_at_open": "<positive|negative|mixed|ironic>",
    "value_at_close": "<positive|negative|mixed|ironic>",
    "structure_type": "<Classical|Miniplot|Antiplot>",
    "act_count": 3,
    "inciting_incident_scene_id": "<scene-slug>",
    "story_climax_scene_id": "<scene-slug>"
  },

  "acts": [
    {
      "id": "<act-slug>",
      "title": "<display title>",
      "status": "<planned|in-progress|complete>",
      "value": "<optional>",
      "value_open": "<optional>",
      "value_close": "<optional>",
      "sections": ["<section-name>"],
      "sequences": [
        {
          "id": "<seq-slug>",
          "title": "<display title>",
          "status": "<planned|in-progress|complete>",
          "value": "<optional>",
          "value_open": "<optional>",
          "value_close": "<optional>",
          "sections": ["<section-name>"],
          "scenes": [
            {
              "id": "<scene-slug>",
              "title": "<display title>",
              "status": "<planned|drafted|written|locked>",
              "dramatic_role": "<optional>",
              "chars": ["<char-slug>", "<char-slug>"],
              "loc": "<location-slug>",
              "climax": "<inciting|seq|act|story|null>",
              "sections": ["<section-name>"]
            },
            {"id": "<scene-slug-stub-without-dramatic-role>"},
            {"id": "<scene-slug-stub-planned>", "chars": ["<char-slug>"]}
          ]
        }
      ]
    }
  ],

  "characters": {
    "<char-slug>": {
      "name": "<display name>",
      "one_sentence": "<summary>",
      "story_role": "<Protagonist|Antagonist|Supporting|Minor|Cameo>",
      "arc_type": "<optional>",
      "arc_complete": false,
      "rel": [
        {"id": "<char-slug>", "label": "<relationship-label>", "feeling": "<feeling-text>"}
      ],
      "sections": ["<section-name>"],
      "arc": [
        {
          "label": "<beat-label>",
          "scene": "<scene-slug>",
          "shift": "<value-shift>",
          "y": 0.8,
          "sections": ["<section-name>"]
        },
        "<arc-beat-stub>"
      ]
    }
  },

  "plots": {
    "<plot-slug>": {
      "name": "<display name>",
      "one_sentence": "<summary>",
      "status": "<active|resolved|abandoned>",
      "plot_type": "<optional>",
      "plot_scope": "<main|sub>",
      "value_arc": "<optional>",
      "characters": ["<char-slug>"],
      "setups": ["<scene-slug>"],
      "crisis": ["<scene-slug>"],
      "climax": ["<scene-slug>"],
      "payoffs": ["<scene-slug>"],
      "sections": ["<section-name>"]
    }
  },

  "locations": {
    "<loc-slug>": {
      "name": "<display name>",
      "one_sentence": "<summary>",
      "sections": ["<section-name>"]
    }
  },

  "worlds": {
    "<world-slug>": {
      "name": "<display name>",
      "one_sentence": "<summary>",
      "sections": ["<section-name>"]
    }
  },

  "unfilled": {
    "<field-name>": ["<entity-slug>", "<entity-slug>"]
  },

  "memory_outline": {
    "status": "placeholder — design deferred, see §5",
    "sections": [
      {"heading": "<heading>", "preview": "<preview-line>"}
    ]
  }
}
```

**Implementation note — scene stubs:** scene stubs are compact objects, not bare strings. They always have `id`, optionally `chars` when characters are assigned. Arc beat stubs remain bare strings (unnamed skeletons have no useful partial data). Any code consuming the `scenes` array checks `dramatic_role` presence to distinguish full from stub — if absent, it's a stub regardless of status.

### `sections` field — what it is and isn't

`sections` is a per-entity array of section names that currently have content — **it is a notes-availability index, not a completeness or quality judgment.** It tells the agent what's there to pull via `story_retrieve` before it guesses a section name; it says nothing about whether that content is "enough." Omit the key entirely when an entity has zero sections written.

The section names are derived from the actual headings the user/agent wrote (parsed from `## ` headings in the entity's body). They are NOT hardcoded — the builder reads the `sections` table to get whatever headings exist. Custom headings (e.g., "Backstory" instead of "Background") appear in the array just like standard ones. No mapping, no encoding — just the raw heading names.

**Interaction with full/stub tiering:** sections existence does NOT affect stub classification. A stub scene may still have prose sections (e.g., a planned scene with rough Description notes but no assigned dramatic role yet). Stub classification is based on frontmatter signal only (`status=="planned"` OR no `dramatic_role` for scenes, `label` empty for arc beats).

---

## 3. Field-by-Field Decisions

### Project

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| name, logline, genre, setting, status | keep | Core identity, cheap, always relevant |
| spine, controlling_idea, value, value_at_open/close | keep | Distinct functional signal from logline (mechanical throughline vs. marketing summary); cheap |
| structure_type, act_count | keep | Needed to reason about structural completeness at a glance |
| inciting_incident_scene_id, story_climax_scene_id | keep | Cross-reference anchors; redundant with per-scene `climax` marker but cheap enough (2 ids) to keep as a fast top-level pointer |
| screenplay_title, credit, author, contact, draft_date, draft | **drop** | Title-page/export metadata, not story-understanding signal. **Gap:** none of the current retrieve sections (Synopsis, Themes, Structure, Notes) map to these — see §6 migration note. |

### Character

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| name, one_sentence | keep | Identity |
| story_role | keep | "Who matters at a glance" — explicitly called out in brief |
| arc_type, arc_complete | keep | Arc-completion signal without arc prose |
| rel (id + label + feeling) | keep | Relationship *map* is structural. The `relationships` list has sub-fields: `id`, `label`, `feeling`. All three are kept — `feeling` is a short structured sub-field, not prose, and cheap to include. |
| arc_value, arc_value_at_open/close | **drop** | → `story_retrieve(character, slug, sections=["Arc"])` |
| goals_short, goals_long | **drop** | → `story_retrieve(character, slug, sections=["Goals"])` |
| knowledge | **drop** | → `story_retrieve(character, slug, sections=["Background"])` |

### Scene (full form)

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| id, title, status | keep | Identity, readability without a retrieve round-trip |
| dramatic_role | keep | Reveals whether structure is functional |
| chars, loc | keep | Structural cross-reference, replaces `character_scene`/`location_scene` relations |
| climax (single marker: `"inciting"\|"seq"\|"act"\|"story"\|null`) | keep | Replaces 4 booleans with 1 field. Derived from the scene's boolean frontmatter; if multiple are true, priority is `inciting > story > act > seq`. |
| order, sequence_id, act_id, parent_id | **drop** | Implicit via nesting + array position |
| heading, time_of_day | **drop** | Screenplay-formatting detail → `story_retrieve(scene, slug, sections=["Content"])` |
| value, value_open, value_close | **drop** | → `story_retrieve(scene, slug, sections=["Description"])` |
| conflict_levels | **drop** | → same retrieve call as above |

### Scene (stub form)
Compact object. Criterion: `status == "planned"` OR no `dramatic_role` (either condition is sufficient — a planned scene is a stub even with a dramatic_role assigned; a scene in any status without a dramatic_role is also a stub). Shown in the nested tree as `{"id": "<scene-slug>"}` or `{"id": "<scene-slug>", "chars": ["<char-slug>"]}` when characters are present. Characters are included for context but do not affect stub classification.

### Sequence / Act

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| id, title, status | keep | Identity |
| value, value_open, value_close | keep | Cheap (~2-3 tokens each), gives sequence/act-level value-shift signal |
| sections | keep | Notes-availability index (S=Summary, F=Thematic Function, N=Notes) |
| climax_scene_id | **drop** | Redundant — derivable by scanning nested scenes for `climax: "seq"` / `"act"` |
| purpose (sequence), act_objective (act) | **drop** | → `story_retrieve(sequence\|act, slug, sections=["Summary"])` |
| primary_plot | **drop** | Derivable by cross-referencing plot scene-id arrays against this sequence's scene ids |

### Arc beat (full form)

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| label, scene (ref) | keep | Identity + anchor point |
| shift, y, is_crisis, is_climax | keep | Lets the agent read arc *shape* (rising/flat, where the crisis sits) without prose |
| action, gap, choice | **drop** | Long prose, only needed when actively drafting → `story_retrieve(arc, slug, sections=["Action","Gap","Choice"])` |

### Arc beat (stub form)
Bare id string. Criterion: `label` is empty (no beat name assigned). A beat with no label is an auto-generated skeleton — nothing creative has happened yet. Sections existence is NOT a criterion — a beat may have prose sections but still be unnamed. **Note:** earlier draft used `y` unset as the signal, but `y=0.0` is both the schema default *and* a semantically meaningful value (neutral charge), making it ambiguous. `label` is unambiguous — an empty label means "unnamed skeleton."

### Plot

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| name, one_sentence, status | keep | Identity |
| plot_type, plot_scope, value_arc | keep | Cheap, gives "what kind of plot, how central" signal |
| characters | keep | Structural cross-reference (frontmatter-sourced, not relation) |
| setups, crisis, climax, payoffs (scene-id arrays) | keep, **but ids only** | Replaces relation rows; drop the description prose per beat |
| beat description text | **drop** | Stored as relation note, not section → future `story_retrieve` expansion needed (see §6) |

### Location / World

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| id, name, one_sentence | keep | Already minimal, cheap |
| sections | keep | Notes-availability index (D=Description, H=History, C=Conflict) |
| rules (world) | **drop** | Stored as frontmatter, not section → future `story_retrieve` expansion needed (see §6) |

---

## 4. Unfilled Field Encoding

**Naming note:** the earlier draft of this spec called this structure `gaps`, which collided with "gap" already being a specific arc-beat field name (`action`/`gap`/`choice`) and also implied a category of story-terminology "gap" this data has nothing to do with. Renamed to `unfilled`, matching the term the brief and the existing `unfilled_fields()` function already use. It's about incomplete data (optional fields still at their schema default), nothing else.

An earlier version of this spec also introduced a `structural` tier (things like "Act II has no scenes") and a `section`-presence tier as parts of this structure. Both are dropped here — not because the underlying observations are wrong, but because they don't need new inference logic. Once the nested full/stub tree (§2, §3) and the per-entity `sections` field (§2) exist, both are already directly visible in the payload: an act with `"sequences": []` or a sequence whose `scenes` array is all bare strings *is* the "undeveloped" signal, and a missing letter in an entity's `sections` string *is* the "no notes written yet" signal. No separate computed record is needed to restate what the structure already shows.

**What `unfilled` actually is:** a direct, inverted transform of the existing `unfilled_fields(entity)` function (`core/entity.py`) — for each optional schema field still equal to its default (`""`, `[]`, `False`, "not set", etc.), the entity id is added under that field name:

```json
"unfilled": {
  "goals_short": ["char-a", "char-b", "char-c"],
  "knowledge": ["char-a", "char-b"]
}
```

reads as: `goals_short` is unset for three characters; `knowledge` is unset for two. This runs across the **full schema for each entity type** (not just the fields kept in the load payload), since the point is proactive surfacing of what an author hasn't written yet, regardless of whether that field would ever appear in load.

**Restricted to non-stub entities.** A stub (bare id string) is already maximally "unfilled" by definition — running `unfilled_fields()` against it and reporting the result would just restate its stub-ness in a different place. Skip it.

Estimated cost at feature scale: ~150–250 tokens, down from ~800.

---

## 5. Memory — Deferred, Placeholder Design

Per your note: `.story/memory.md` is not yet fully fleshed out and its final shape is still open, so this section is intentionally minimal rather than fully designed.

For now: replace full-text inclusion with a **headers-only outline** — `## ` section titles plus a short preview line each (see `memory_outline` in §2). Preview line = first non-empty line after the heading, truncated to ~120 chars. This keeps the load payload honest about what continuity topics exist without paying for the bodies.

**Open gap to flag for backlog, not to solve now:** none of the three sibling tools currently expose a clean way to fetch memory *sections* specifically (`story_retrieve` is entity-scoped; `story_search` is unclear whether it indexes `memory.md` at all). If the outline stays, something like `story_retrieve(entity_type="memory", sections=[...])` will eventually be needed, or the outline becomes a dead end with no way to drill in. Not a blocker for this redesign, but worth a ticket.

---

## 6. Migration Strategy

**Changes to `get_project_summary()` (or equivalent load-building function):**
1. Replace the flat entity query + relation join with three passes: (a) build nested act→sequence→scene tree, (b) build character/plot/location/world dicts, (c) embed cross-references (chars, rel, plot scene-arrays) directly rather than joining a relations table.
2. Add a `sections` computation per entity: query its `sections` table, emit the heading names as a string array. Omit the `sections` key entirely when the entity has zero sections. No new content store needed — the data already lives in the `sections` table.
3. Add a classifier pass marking each scene/arc-beat as full or stub per the criteria in §3, and emit accordingly (scene stub object vs. bare arc-beat string). **Scene stub is frontmatter-signal only:** stub when `status=="planned"` OR no `dramatic_role` (either condition is sufficient — planned scenes are stubs even with a dramatic_role; scenes in any status without a dramatic_role are also stubs). Include `chars` on stub objects for context when assigned. Arc beat stubs are bare strings when `label` is empty. **Sort children by `order_key` (then `id` for stability) before emitting arrays** — order is implied by position, so sorting must happen upstream.
4. Add the `unfilled` computation pass by calling the existing `unfilled_fields()` and inverting its output (`entity → [fields]` becomes `field → [entities]`), skipping stub entities.
5. Add `memory_outline` extraction (regex/parse on `## ` headers, first line = preview).
6. Drop all fields marked "drop" above from the load query entirely — don't fetch what you won't emit.
7. Always emit `status` even when at default (overrides §1.5 omit-defaults rule).

**New retrieve call patterns the agent will need to generate for dropped fields** (for prompting/testing the agent against the new schema):

| Dropped field(s) | Call |
|---|---|
| Character goals | `story_retrieve("character", slug, sections=["Goals"])` |
| Character knowledge/background | `story_retrieve("character", slug, sections=["Background"])` |
| Character arc_value* | `story_retrieve("character", slug, sections=["Arc"])` |
| Scene heading/content/value | `story_retrieve("scene", slug, sections=["Description","Content"])` |
| Arc beat action/gap/choice | `story_retrieve("arc", slug, sections=["Action","Gap","Choice"])` |
| Plot obstacles/stakes | `story_retrieve("plot", slug, sections=["Summary","Obstacles"])` |
| Sequence/act purpose | `story_retrieve("sequence"/"act", slug, sections=["Summary"])` |
| World rules | **no current retrieve path — future `story_retrieve` expansion (see below)** |
| Project title-page fields | **no current retrieve path — future `story_retrieve` expansion (see below)** |
| Plot beat descriptions | **no current retrieve path — future `story_retrieve` expansion (see below)** |
| Memory detail | **no current retrieve path — flagged in §5, backlog item** |

**Future `story_retrieve` expansion (out of scope for this redesign):** Several dropped fields are stored as relation `note` or frontmatter `extra` JSON — not as section bodies. The current `story_retrieve` tool only returns section bodies from the `sections` table. After this redesign, those fields become inaccessible until `story_retrieve` expands to cover relation notes and frontmatter fields. This is a known gap, tracked for future development. As this redesign is implemented, additional retrieval gaps may surface — capture them in the same backlog.

---

## 7. Token Budget (feature scale: 120 scenes, 20 chars, 100 arc beats, 8 plots)

| Component | Original | Redesigned |
|---|---|---|
| Project | ~200 | ~150 |
| Characters (20) | ~1,600 | ~650 |
| Scenes (120, ~40% full / 60% stub) | ~9,000 | ~1,950 |
| Sequences/Acts | ~890 | ~550 |
| Arc beats (100, similar full/stub split) | ~12,000 | ~2,100 |
| Plots (8) | ~1,120 | ~530 |
| Locations/Worlds | ~850 | ~650 |
| Relations | ~12,900 | **0** (embedded) |
| Unfilled | ~800 | ~180 |
| Memory | ~5,000 | ~300 (outline only) |
| JSON overhead | ~3,000 | ~1,000 |
| **Total** | **~47,000** | **~8,000–8,300** |

Note the per-entity `sections` field (new this round) is folded into each entity type's own row rather than broken out — it roughly offsets the savings from simplifying the unfilled structure, so the total is essentially unchanged from the previous draft, just built on grounded data instead of invented inference. This also scales *inversely* with draft sparsity — an early-outline-stage project (mostly stubs, few sections written) loads even cheaper, which is exactly when frequent loads matter most.

---

## 8. Open Decisions (confirmed)

1. **Scene stub criterion** — **CONFIRMED:** `status=="planned"` OR no `dramatic_role` (either condition is sufficient — a planned scene is a stub even with a dramatic_role assigned; a scene in any status without a dramatic_role is also a stub). Characters do NOT affect classification but are included in stubs for context when assigned.
2. **Arc beat stub criterion** — **CONFIRMED:** `label` empty (unnamed skeleton). Sections existence is NOT a criterion. Replaces earlier `y`-based proposal.
3. **Section-only promotion** — **REJECTED.** Sections existence does NOT promote an entity to full form. Stub classification is based on frontmatter signal only (dramatic_role for scenes, label for arc beats). A planned scene with prose but no dramatic_role stays a stub.
4. **Empty sequences** — **CONFIRMED:** stay a full object with `"scenes": []`, not collapsed to a bare id.
5. **Scene `title` field** — **CONFIRMED:** kept for agent readability. ~600 token cost acceptable.
6. **Project title-page fields retrieval path** — **DEFERRED** to future `story_retrieve` expansion (§6).
7. **Memory retrieval path** — **DEFERRED** per your note (§5), backlog item only.
