# `story_load` Redesign — Consolidated Specification

Target: reduce feature-scale load payload from ~47,000 tokens to ~8,000–8,500 tokens while preserving structural navigability and proactive gap-awareness. Worked against the `save-the-children` fixture throughout.

---

## 1. Core Principles

1. **No flat `relations` table.** Every relation is an attribute of one of its two endpoints and gets embedded there (scene carries `chars`, plot carries scene-id arrays, character carries `rel`). This removes ~12.9k tokens with no loss of navigability, since reverse lookups ("what scenes is Kael in?") become a scan of the already-present scene list rather than a join.
2. **Structure is implied by nesting, not by `parent_id`.** `act → sequences → scenes` is expressed as literal JSON nesting. `sequence_id`, `act_id`, and `parent_id` fields disappear entirely — containment *is* the pointer.
3. **Order is implied by array position, not an `order` field.** Progression (scene order, arc-beat order) is real signal worth keeping, but position in an array carries it for free.
4. **Hybrid full/stub representation for scenes and arc beats.** Entities with no creative work done yet collapse to a bare id string inside the same ordered array as fully-detailed entities. Consumers branch on `typeof`. This is the same classifier used for unfilled-field surfacing (§4), so it's one mechanism serving two purposes, not two systems.
5. **Omitted field = unfilled.** Defaults/empties are never emitted. This makes per-field unfilled-detection close to free rather than a parallel bookkeeping structure.
6. **Every kept field earns its place on session-start signal value, not on where it happens to be stored** (column vs. extra JSON) — per the brief's original design philosophy.

---

## 2. Full Payload Schema (worked example)

```json
{
  "loaded": true,
  "confirmation": "Loaded Save the Children — 3 scenes (1 developed), 1 sequence, 1 act, 6 characters, 2 locations, 2 plots.",

  "project": {
    "name": "Save the Children",
    "logline": "In a world where humanity survives only as consciousness inside a machine, a young person fights to escape an oppressive system — unaware that the rebellion itself, the system, and every feeling of purpose they have ever known are the inherited memories of the last scientists who built the world that imprisoned them.",
    "genre": "Sci-fi drama",
    "setting": "The Institute — a decaying research facility, 400 years apart",
    "status": "active",
    "spine": "A young person discovers the truth about their world and chooses to escape",
    "controlling_idea": "Freedom requires sacrifice",
    "value": "Trust",
    "value_at_open": "positive",
    "value_at_close": "negative",
    "structure_type": "Classical",
    "act_count": 3,
    "inciting_incident_scene_id": "central-room-day",
    "story_climax_scene_id": "central-room-night"
  },

  "acts": [
    {
      "id": "act-1",
      "title": "Act I",
      "status": "planned",
      "sequences": [
        {
          "id": "seq-discovery",
          "title": "Sequence A",
          "scenes": [
            {
              "id": "central-room-day",
              "title": "Central Room - Day",
              "status": "drafted",
              "dramatic_role": "setup",
              "chars": ["kael", "mira"],
              "loc": "the-central-room",
              "climax": "inciting",
              "sections": "DC"
            },
            "central-room-night",
            "the-core-day"
          ]
        }
      ]
    }
  ],

  "characters": {
    "kael": {
      "name": "Kael",
      "one_sentence": "A young person inside The I who begins to feel the system is wrong.",
      "story_role": "Protagonist",
      "arc_type": "positive",
      "arc_complete": false,
      "rel": [
        {"id": "mira", "label": "closest friend"},
        {"id": "the-administrator", "label": "antagonist"}
      ],
      "sections": "PBA",
      "arc": [
        {"label": "First Doubt", "scene": "central-room-day", "shift": "positive→mixed", "y": 0.8, "sections": "AGC"},
        "kael-2",
        "kael-3"
      ]
    },
    "mira": {
      "name": "Mira", "one_sentence": "...", "story_role": "Supporting",
      "arc_type": "positive", "arc_complete": false
    },
    "the-administrator": {
      "name": "The Administrator", "one_sentence": "...", "story_role": "Antagonist",
      "sections": "P",
      "arc": ["the-administrator-1", "the-administrator-2", "the-administrator-3"]
    },
    "the-outsider": { "name": "The Outsider", "one_sentence": "...", "story_role": "Supporting" },
    "dr-elena-voss": {
      "name": "Dr. Elena Voss", "one_sentence": "...", "story_role": "Supporting",
      "arc": ["dr-elena-voss-1", "dr-elena-voss-2", "dr-elena-voss-3"]
    },
    "marcus-chen": {
      "name": "Marcus Chen", "one_sentence": "...", "story_role": "Supporting",
      "arc": ["marcus-chen-1", "marcus-chen-2"]
    }
  },

  "plots": {
    "the-resistance": {
      "name": "The Resistance", "one_sentence": "The core plot...", "status": "active",
      "plot_type": "Complicating", "plot_scope": "main", "value_arc": "Maturation",
      "characters": ["kael", "mira"],
      "setups": ["central-room-day"],
      "crisis": ["central-room-night"],
      "climax": [], "payoffs": [],
      "sections": "S"
    },
    "the-scientists-last-stand": {
      "name": "The Scientist's Last Stand", "one_sentence": "...", "status": "active",
      "plot_type": "Contradictory", "plot_scope": "main", "value_arc": "Education",
      "setups": ["central-room-day"], "payoffs": ["the-core-day"]
    }
  },

  "locations": {
    "the-central-room": { "name": "The Central Room", "one_sentence": "..." },
    "the-garden": { "name": "The Garden", "one_sentence": "..." }
  },

  "worlds": {
    "the-real-world": { "name": "The Real World", "one_sentence": "..." },
    "the-i": { "name": "The I", "one_sentence": "..." }
  },

  "unfilled": {
    "goals_short": ["kael", "mira", "the-administrator", "the-outsider", "dr-elena-voss", "marcus-chen"],
    "goals_long": ["kael", "mira", "the-administrator", "the-outsider", "dr-elena-voss", "marcus-chen"],
    "knowledge": ["kael", "mira", "the-outsider"],
    "arc_value": ["kael", "mira", "the-administrator", "the-outsider", "dr-elena-voss", "marcus-chen"]
  },

  "memory_outline": {
    "status": "placeholder — design deferred, see §5",
    "sections": [
      {"heading": "Continuity notes", "preview": "..."},
      {"heading": "Character knowledge", "preview": "..."},
      {"heading": "World events", "preview": "..."},
      {"heading": "Open questions", "preview": "..."}
    ]
  }
}
```

**Implementation note — heterogeneous arrays:** `scenes` and `arc` arrays mix objects (full) and bare strings (stubs). Any code consuming this payload needs a `typeof x === "string"` branch at both points. Document this once at the top of the schema definition rather than re-explaining per field.

### `sections` field — what it is and isn't

Every entity type has a fixed, known set of prose sections a user/agent can write into (already enumerated in `data_model.md`'s retrieve table). `sections` is a per-entity string with one letter per section that currently has content — **it is a notes-availability index, not a completeness or quality judgment.** It tells the agent what's there to pull via `story_retrieve` before it guesses a section name; it says nothing about whether that content is "enough." Omit the key entirely when an entity has zero sections written (as with `mira`, `the-outsider`, etc. above).

| Type | Legend |
|---|---|
| character | P=Personality, B=Background, V=Voice, F=Greatest Fear, S=Secrets, A=Arc, R=Relationships, G=Goals |
| scene | D=Description, F=Dramatic Function, N=Notes, C=Content |
| plot | S=Summary, O=Obstacles, K=Stakes |
| arc | A=Action, G=Gap, C=Choice, S=Shift, L=Development Log |
| project | S=Synopsis, T=Themes, X=Structure, N=Notes |
| location / world | D=Description, H=History, C=Conflict |
| sequence / act | S=Summary, F=Thematic Function, N=Notes |

Letters are scoped per type only — no need for global uniqueness (e.g. character's `S`=Secrets and arc's `S`=Shift don't collide since the consumer always knows the entity type it's reading).

**Interaction with full/stub tiering:** an entity should be promoted to full form if it has *either* meaningful frontmatter (per the criteria in §3) *or* ≥1 section written, even if frontmatter is still empty — a scene with real prose but no `dramatic_role` yet is not "nothing has happened here," and collapsing it to a bare id would hide real authored work. See open item in §8.

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
| rel (id + label only) | keep | Relationship *map* is structural; drop `feeling` text |
| arc_value, arc_value_at_open/close | **drop** | → `story_retrieve(character, slug, sections=["Arc"])` |
| goals_short, goals_long | **drop** | → `story_retrieve(character, slug, sections=["Goals"])` |
| knowledge | **drop** | → `story_retrieve(character, slug, sections=["Background"])` |
| relationship `feeling` | **drop** | → `story_retrieve(character, slug, sections=["Relationships"])` |

### Scene (full form)

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| id, title, status | keep | Identity, readability without a retrieve round-trip |
| dramatic_role | keep | Reveals whether structure is functional (brief's own example) |
| chars, loc | keep | Structural cross-reference, replaces `character_scene`/`location_scene` relations |
| climax (single marker: `null\|"inciting"\|"seq"\|"act"\|"story"`) | keep | Replaces 4 booleans with 1 field |
| order, sequence_id, act_id, parent_id | **drop** | Implicit via nesting + array position |
| heading, time_of_day | **drop** | Screenplay-formatting detail → `story_retrieve(scene, slug, sections=["Content"])` |
| value, value_open, value_close | **drop** | → `story_retrieve(scene, slug, sections=["Description"])` |
| conflict_levels | **drop** | → same retrieve call as above |

### Scene (stub form)
Bare id string. Criterion: `status == "planned"` AND no `dramatic_role` AND no `chars` AND no `sections` written. A stub scene is visible directly in the nested tree as a plain string — no separate record is needed to know it's undeveloped; that's what makes it a stub.

### Sequence / Act

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| id, title, status | keep | Identity |
| value, value_open, value_close | keep | Cheap (~2-3 tokens each), gives sequence/act-level value-shift signal |
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
Bare id string. Criterion: `y` is unset (no shape data assigned yet). **Flagged as a default — confirm this is the right stub boundary before implementation**, since arc beats weren't as explicitly discussed as scenes.

### Plot

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| name, one_sentence, status | keep | Identity |
| plot_type, plot_scope, value_arc | keep | Cheap, gives "what kind of plot, how central" signal |
| characters | keep | Structural cross-reference |
| setups, crisis, climax, payoffs (scene-id arrays) | keep, **but ids only** | Replaces relation rows; drop the description prose per beat |
| beat description text | **drop** | → `story_retrieve(plot, slug, sections=["Summary","Obstacles"])` |

### Location / World

| Field | Keep? | Why / Retrieve replacement |
|---|---|---|
| id, name, one_sentence | keep | Already minimal, cheap |
| rules (world) | **drop** | → `story_retrieve(world, slug, sections=["Description","History","Conflict"])` |

---

## 4. Unfilled Field Encoding

**Naming note:** the earlier draft of this spec called this structure `gaps`, which collided with "gap" already being a specific arc-beat field name (`action`/`gap`/`choice`) and also implied a category of story-terminology "gap" this data has nothing to do with. Renamed to `unfilled`, matching the term the brief and the existing `unfilled_fields()` function already use. It's about incomplete data (optional fields still at their schema default), nothing else.

An earlier version of this spec also introduced a `structural` tier (things like "Act II has no scenes") and a `section`-presence tier as parts of this structure. Both are dropped here — not because the underlying observations are wrong, but because they don't need new inference logic. Once the nested full/stub tree (§2, §3) and the per-entity `sections` field (§2) exist, both are already directly visible in the payload: an act with `"sequences": []` or a sequence whose `scenes` array is all bare strings *is* the "undeveloped" signal, and a missing letter in an entity's `sections` string *is* the "no notes written yet" signal. No separate computed record is needed to restate what the structure already shows.

**What `unfilled` actually is:** a direct, inverted transform of the existing `unfilled_fields(entity)` function (`core/entity.py`) — for each optional schema field still equal to its default (`""`, `[]`, `False`, "not set", etc.), the entity id is added under that field name:

```json
"unfilled": {
  "goals_short": ["kael", "mira", "the-administrator", "the-outsider", "dr-elena-voss", "marcus-chen"],
  "knowledge": ["kael", "mira", "the-outsider"]
}
```

reads as: `goals_short` is unset for all six characters; `knowledge` is unset for three of them. This runs across the **full schema for each entity type** (not just the fields kept in the load payload), since the point is proactive surfacing of what an author hasn't written yet, regardless of whether that field would ever appear in load.

**Restricted to non-stub entities.** A stub (bare id string) is already maximally "unfilled" by definition — running `unfilled_fields()` against it and reporting the result would just restate its stub-ness in a different place. Skip it.

Estimated cost at feature scale: ~150–250 tokens, down from ~800.

---

## 5. Memory — Deferred, Placeholder Design

Per your note: `.story/memory.md` is not yet fully fleshed out and its final shape is still open, so this section is intentionally minimal rather than fully designed.

For now: replace full-text inclusion with a **headers-only outline** — `## ` section titles plus a short preview line each (see `memory_outline` in §2). This keeps the load payload honest about what continuity topics exist without paying for the bodies.

**Open gap to flag for backlog, not to solve now:** none of the three sibling tools currently expose a clean way to fetch memory *sections* specifically (`story_retrieve` is entity-scoped; `story_search` is unclear whether it indexes `memory.md` at all). If the outline stays, something like `story_retrieve(entity_type="memory", sections=[...])` will eventually be needed, or the outline becomes a dead end with no way to drill in. Not a blocker for this redesign, but worth a ticket.

---

## 6. Migration Strategy

**Changes to `get_project_summary()` (or equivalent load-building function):**
1. Replace the flat entity query + relation join with three passes: (a) build nested act→sequence→scene tree, (b) build character/plot/location/world dicts, (c) embed cross-references (chars, rel, plot scene-arrays) directly rather than joining a relations table.
2. Add a `sections` computation per entity (which prose sections are non-empty), sourced from whatever already backs `story_retrieve`'s section lookup — no new content store needed, just a presence check per section per entity.
3. Add a classifier pass marking each scene/arc-beat as full or stub per the criteria in §3 (frontmatter signal **or** ≥1 `sections` letter → full), and emit accordingly (object vs. bare id).
4. Add the `unfilled` computation pass by calling the existing `unfilled_fields()` and inverting its output (`entity → [fields]` becomes `field → [entities]`), skipping stub entities.
5. Add `memory_outline` extraction (regex/parse on `## ` headers).
6. Drop all fields marked "drop" above from the load query entirely — don't fetch what you won't emit.

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
| World rules | `story_retrieve("world", slug, sections=["Description","History","Conflict"])` |
| Project title-page fields | **no current retrieve path — needs a new mechanism** (e.g. a `fields=[...]` param alongside `sections=[...]`, since these are flat metadata, not prose sections) |
| Memory detail | **no current retrieve path — flagged in §5, backlog item** |

**Known spec gaps to resolve during implementation**, not before: the project title-page retrieval path and the memory section retrieval path. Everything else in this spec has a working retrieve replacement already.

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

## 8. Open Decisions (defaults proposed, confirm before/during implementation)

1. **Scene stub criterion** — proposed: `status=="planned"` AND no `dramatic_role` AND no `chars` AND no sections written. Confirm this matches intent.
2. **Arc beat stub criterion** — proposed: `y` unset AND no sections written. Not previously discussed in depth — confirm.
7. **Section-only promotion edge case** — an entity with real prose in a section but no frontmatter signal yet (rare, but possible — e.g. someone writes a scene's Description before setting `dramatic_role`) is promoted to full form per §2's rule. Confirm this is desired rather than a third tier, since it means a "full" entity can sometimes carry almost no fields besides `id` and `sections`.
3. **Empty sequences** (zero scenes) — proposed: stay a full object with `"scenes": []`, not collapsed to a bare id, to keep sequence-level shape consistent. Not yet explicitly confirmed.
4. **Scene `title` field** — kept in the final schema (§2) for agent readability in conversation, though an earlier working example dropped it. Flagging this explicitly since it's a slight walk-back — confirm you're fine with the small token cost (~5/scene, ~600 total) for the readability win.
5. **Project title-page fields retrieval path** — needs a new mechanism (§6), not currently solvable via existing `story_retrieve`.
6. **Memory retrieval path** — explicitly deferred per your note (§5), backlog item only.
