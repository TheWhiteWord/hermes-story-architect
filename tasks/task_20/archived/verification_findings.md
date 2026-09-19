# story_load Redesign Spec — Verification Notes

Verifying design ideas in `story_load_redesign_spec.md` against:
- Code: `tools/story_load.py`, `tools/story_retrieve.py`, `core/db.py`, `core/entity.py`, `core/constants.py`, `core/section_parser.py`
- Fixtures: `tests/fixtures/save-the-children/`

**Approach:** One design thread → verify → note → move on. Focus on *design ideas*, not fixture matching.

---

## Thread 1: No flat `relations` table — embed relations at endpoints

**Spec claim (§1.1):** Every relation embedded at one of its endpoints. Scene carries `chars`, plot carries scene-id arrays, character carries `rel`. Removes ~12.9k tokens. Reverse lookups ("what scenes is Kael in?") become a scan of the scene list.

### Verification

**Code state:** `db.py:84` `get_project_summary()` currently emits a flat `relations` table. The dashboard (`get_dashboard_data`, `db.py:204`) already does this denormalization in-process — it builds `scene_chars`, `character.scenes`, `plot.setups`, etc. from the same flat relation rows. So the *pattern* exists in the codebase; the spec is proposing to move it from consumer-time into the load payload itself.

**Design question:** The relations table encodes direction: `from_id → to_id`. Embedding means choosing *which* endpoint owns it. The spec proposes:
- `character_scene` relation → embedded at scene as `chars`
- `character_relationship` → embedded at character as `rel`
- `plot_setup/crisis/climax/payoff` → embedded at plot as `setups/crisis/climax/payoffs`
- `location_scene` → embedded at scene as `loc`

This is consistent with how the dashboard already denormalizes. **No design conflict.**

**One to verify:** The spec says plot carries `characters` as a direct array (§2, plot object). In the current code, `plot.characters` comes from `extra JSON` (frontmatter `characters:` list), NOT from a relation. The spec keeps this as frontmatter-sourced. **Consistent.**

**One to verify:** Character `rel` — spec says "id + label only, drop `feeling` text". Current code (`db.py:316`) stores `feeling` in the relation's `note` field as JSON `{"label": ..., "feeling": ...}`. The spec drops `feeling` to retrieve. **Consistent with the spec's stated goal** (structural map, not prose).

### Finding: ✅ Design is sound and consistent with existing denormalization patterns already in the codebase.

---

## Thread 2: Structure implied by nesting, not `parent_id`

**Spec claim (§1.2):** `act → sequences → scenes` expressed as literal JSON nesting. `sequence_id`, `act_id`, `parent_id` fields disappear.

### Verification

**Code state:** The DB schema (`db.py:7`) stores `parent_id` on entities. Scenes point to sequences (`parent_id`), sequences point to acts (`parent_id`). The dashboard (`db.py:477-546`) already builds this nesting in-process by scanning `parent_id` relationships.

**Design question:** Nesting means the load payload becomes a tree. This is a *shape* change, not an information change. The spec proposes the load builder does the tree assembly that the dashboard already does. **No information loss.**

**One to verify:** The spec drops `act_id` from scenes entirely. Current scenes have both `sequence_id` and `act_id` (denormalized). The spec says scenes nest inside sequences which nest inside acts, so `act_id` is implicit. **Correct** — but note: this means a consumer wanting "what act is this scene in?" walks up the tree. The spec considers this fine (and it is for a tree).

**One to verify:** `order` field dropped, array position implies order. Current scenes have an explicit `order` float (for insertions at non-integer positions). Array position works if the load builder sorts by `order_key` before emitting. **Must ensure the builder sorts sequences and scenes by `order_key` before nesting**, otherwise order is undefined. The dashboard does this (`db.py:481`, `db.py:513`). **Feasible, just needs to be specified in the builder.**

### Finding: ✅ Design is sound. One implementation note: builder MUST sort children by `order_key` before nesting into arrays, or order is lost.

---

## Thread 3: Order implied by array position, not `order` field

**Spec claim (§1.3):** Progression is real signal, array position carries it for free.

### Verification

This is the implementation note from Thread 2. The `order_key` column is a float (for insertions). As long as the builder sorts by `order_key` before emitting arrays, position encodes order. **No conflict.**

**Edge case:** What if two scenes have the same `order_key`? Current code allows it (no unique constraint). The spec doesn't address tie-breaking. **Minor gap** — could sort by `(order_key, id)` for stability.

### Finding: ✅ Sound. Add secondary sort by `id` for stable ordering.

---

## Thread 4: Hybrid full/stub representation

**Spec claim (§1.4):** Entities with no creative work collapse to bare id strings in the same array. Consumers branch on `typeof`.

### Verification

**Code state:** Currently all entities are full rows. No stub concept exists.

**Design question:** This is the most novel idea in the spec. The key insight: a stub is *visible in context* (it's a string in a parent's array) without needing a separate record. A scene that's just a planned title shows up as `"central-room-night"` inside its sequence's `scenes` array.

**One to verify:** The spec says stubs are "bare id strings". But the consumer needs to know *what* it is (scene? sequence?) to branch. The spec says "the consumer always knows the entity type it's reading" (§2, last paragraph). **This is true** — a sequence's `scenes` array contains scene stubs, a character's `arc` array contains arc stubs. The parent's type defines the children's type.

**One to verify:** The spec says the stub criterion for scenes is `status == "planned"` AND no `dramatic_role` AND no `chars` AND no sections. Looking at the fixture: `central-room-night` has `status: drafted`, `dramatic_role: climax`, `chars: [kael]` — so it's full. `the-core-day` has `status: written`, `dramatic_role: resolution`, `chars: [kael, mira]` — full. If a scene had `status: planned` and nothing else, it'd be a stub. **Consistent with the fixture.**

**One to verify:** Arc beat stub criterion — spec says `y` is unset. Current arc schema (`constants.py:164`) has `y` default `0.0`. So "unset" means `y == 0.0`. But `0.0` is also a valid value (neutral charge). **This is a real conflict** — `0.0` is the default AND a semantically meaningful value. The spec acknowledges this: "Flagged as a default — confirm this is the right stub boundary." **Open question, needs resolution.**

### Finding: ✅ Design is sound for scenes. ⚠️ Arc beat stub criterion has a semantic conflict: `y=0.0` is both default and meaningful value. Needs a different stub signal (maybe check if `label` is empty, or if `action`/`gap`/`choice` are all at default).

---

## Thread 5: Omitted field = unfilled

**Spec claim (§1.5):** Defaults/empties never emitted. Per-field unfilled detection is free.

### Verification

**Code state:** Current `get_project_summary` emits all columns + full `extra` JSON for every entity. The `unfilled` map is a separate computation.

**Design question:** This is a serialization discipline, not a structural change. The builder simply skips fields equal to their schema default. **Straightforward.**

**One to verify:** The spec says "Omit the key entirely when an entity has zero sections written (as with `mira`, `the-outsider`)." This applies to the `sections` field. Current code doesn't emit `sections` at all in the load payload — it's a new field the spec adds. **Consistent.**

**One to verify:** What about `status`? The spec keeps `status` for scenes/sequences/acts. Current default for scene status is `"planned"` (`constants.py:111`). If a scene has `status: planned`, do we omit it (because it's the default) or keep it (because the spec says "keep")? The spec's field table says "keep" for status. **Conflict:** §1.5 says omit defaults, but §3 says keep status. **Needs resolution** — either status is always emitted (override §1.5) or omitted when at default.

### Finding: ⚠️ Conflict between §1.5 (omit defaults) and §3 (keep status). Status has a default value ("planned") that's also meaningful. Needs a rule: either "status is always emitted" or "status omitted when at default."

---

## Thread 6: `sections` field as notes-availability index

**Spec claim (§2, §"sections field"):** Per-entity string with one letter per section that has content. It's an availability index, not a quality judgment.

### Verification

**Code state:** `get_entity_sections()` (`db.py:170`) returns `{heading: body}`. The spec wants a compact encoding: `"PBA"` means Personality, Background, Arc sections exist.

**Design question:** The spec defines a legend per entity type (character: P/B/V/F/S/A/R/G, scene: D/F/N/C, etc.). This maps to `standard_sections()` in `entity.py:162`. **The data exists.** The builder needs to:
1. Get all section headings for an entity
2. Map each heading to its letter code
3. Concatenate into a string

**One to verify:** The spec says "Omit the key entirely when an entity has zero sections written." Current `get_entity_sections` returns `{}` for entities with no sections. **Easy to detect.**

**One to verify:** Section headings in the fixture use full names ("Personality", "Background"), not letters. The mapping from heading → letter must be defined. The spec's legend table does this. **Feasible.**

**One to verify:** The spec says letters are scoped per type only. Character's `S`=Secrets, arc's `S`=Shift. **True** — the consumer knows the entity type. No global uniqueness needed.

### Finding: ✅ Design is sound. The legend table is well-defined. Builder needs a heading→letter map per type.

---

## Thread 7: `unfilled` encoding

**Spec claim (§4):** Inverted transform of `unfilled_fields(entity)`. For each optional field at default, add entity id under field name. Restricted to non-stub entities.

### Verification

**Code state:** `unfilled_fields()` (`entity.py:151`) already exists and works. Current `get_project_summary` returns `unfilled` as `{entity_id: [field_names]}` (`db.py:142-163`). The spec wants to invert this to `{field_name: [entity_ids]}`.

**Design question:** Inversion is a simple transform. **Straightforward.**

**One to verify:** The spec says "runs across the full schema for each entity type (not just the fields kept in the load payload)". This means `unfilled` reports on ALL optional fields, including ones dropped from the load (like `goals_short`, `knowledge`). **This is intentional** — the spec wants proactive surfacing of what's missing, even if the field isn't in the load. **Consistent.**

**One to verify:** "Restricted to non-stub entities." A stub is already maximally unfilled. **Correct** — skip inversion for stubs.

**One to verify:** The spec's `unfilled` example only shows `goals_short`, `goals_long`, `knowledge`, `arc_value` — not `relationships`, `arc_type`, etc. This implies the fixture's characters have some fields filled. Looking at `kael.md`: no `arc_type`, no `arc_value`, no `goals_short`, no `goals_long`, no `knowledge` in frontmatter. So `unfilled_fields("character", extra)` would return all of those. **The spec's example is consistent with the fixture.**

### Finding: ✅ Design is sound. Inversion is mechanical. The "full schema" scope is intentional and correct.

---

## Thread 8: Scene `climax` single marker replacing 4 booleans

**Spec claim (§3, Scene):** `climax` is a single marker: `null | "inciting" | "seq" | "act" | "story"`. Replaces `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`.

### Verification

**Code state:** Current scene schema (`constants.py:123-126`) has 4 boolean fields. The fixture uses them (`is_sequence_climax: true` on `central-room-night`).

**Design question:** A single enum field is more compact than 4 booleans. **Clear win.**

**One to verify:** Can a scene be both inciting incident AND sequence climax? In the current model, yes (4 independent booleans). The spec's enum is exclusive (one value). Looking at the fixture: `central-room-day` has `is_inciting_incident: false` but the project's `inciting_incident_scene_id: central-room-day`. **Wait — the scene's boolean says false, but the project says it IS the inciting incident.** This is a data inconsistency in the fixture, but it reveals a design point: the spec's `climax` enum on the scene would be derived from the 4 booleans. If multiple are true, which wins? **The spec doesn't address priority.** Looking at the spec's example: `central-room-day` has `"climax": "inciting"`. The fixture has `is_inciting_incident: false` but project says it's inciting. **The spec's example seems to use the project's `inciting_incident_scene_id` as the source of truth, not the scene's boolean.**

**This is a real design question:** Should `climax` be derived from the scene's own booleans, or from the project's `inciting_incident_scene_id` + per-scene climax markers? The spec says "Replaces 4 booleans with 1 field" — implying it's derived from the booleans. But the fixture's booleans and project-level pointers disagree. **Needs resolution.**

### Finding: ⚠️ The 4 booleans can overlap (a scene could be both inciting and sequence climax). The spec's enum is exclusive. Priority rule needed. Also, fixture has inconsistency between scene booleans and project-level pointers — need to determine canonical source.

---

## Thread 9: Project title-page fields dropped

**Spec claim (§3, Project):** `screenplay_title`, `credit`, `author`, `contact`, `draft_date`, `draft` dropped. "Gap: none of the current retrieve sections map to these."

### Verification

**Code state:** `story_retrieve` sections for project are `["Synopsis", "Themes", "Structure", "Notes"]` (`entity.py:165`). Title-page fields are stored in `extra` JSON, not as sections. **Correct — no retrieve path exists.**

**Design question:** The spec says these are "title-page/export metadata, not story-understanding signal." **Reasonable.** But the spec also flags this as a gap needing a new mechanism. **Acknowledged in §6.**

**One to verify:** The spec drops these from load but doesn't propose a replacement until implementation. **This is fine** — the spec explicitly defers it.

### Finding: ✅ Design is sound. Gap acknowledged and deferred.

---

## Thread 10: Memory outline (deferred)

**Spec claim (§5):** Replace full-text memory with headers-only outline. `## ` titles + preview line.

### Verification

**Code state:** Current `story_load.py:91-94` reads the full `memory.md` file into the payload. The fixture's memory is nearly empty (`# Story Memory` only).

**Design question:** Headers-only is a regex/parse on `## ` headings. `section_parser.py` already does this. **Feasible.**

**One to verify:** The spec says "preview line" — first line after the heading? First N chars? **Undefined.** Needs a rule (e.g., first line, or first 100 chars).

### Finding: ✅ Design is sound. "Preview line" needs a concrete definition.

---

## Thread 11: Plot beat `setups/crisis/climax/payoffs` — ids only, drop description

**Spec claim (§3, Plot):** `setups`, `crisis`, `climax`, `payoffs` kept as scene-id arrays, drop description prose.

### Verification

**Code state:** Current plot relations store `note` with description text (`db.py:377-380`). The spec wants to drop the `note` and keep only `to_id`.

**Design question:** The spec says descriptions → `story_retrieve(plot, slug, sections=["Summary","Obstacles"])`. **But wait** — the per-beat descriptions ("Kael discovers the door isn't locked") are NOT the same as the plot's Summary/Obstacles sections. They're beat-level notes. **The spec's retrieve replacement doesn't actually cover this data.** The beat descriptions are stored in the relation `note` field, not in a section. `story_retrieve(plot, ...)` returns section bodies, not relation notes.

**This is a real gap:** Dropping beat descriptions from the load payload means they're only accessible via... what? The spec says `story_retrieve(plot, slug, sections=["Summary","Obstacles"])` — but that returns the plot's Summary and Obstacles sections, not the per-beat descriptions. **The beat descriptions would become inaccessible unless a new retrieve mechanism is added.**

### Finding: ⚠️ **Real gap.** Per-beat descriptions (relation `note` field) are NOT the same as plot section bodies. The spec's retrieve replacement (`story_retrieve(plot, ..., sections=["Summary","Obstacles"])`) does not retrieve beat descriptions. Either: (a) keep beat descriptions in the load payload, (b) add a new retrieve path for relation notes, or (c) accept the loss.

---

## Thread 12: Character `rel` — id + label only, drop `feeling`

**Spec claim (§3, Character):** `rel` keeps id + label, drops `feeling` text.

### Verification

**Code state:** Current `character_relationship` relations store `note` as `{"label": ..., "feeling": ...}` JSON (`entity.py:241-244`).

**Design question:** The spec drops `feeling` to retrieve. **But** `feeling` is stored in the relation `note`, not in a section. `story_retrieve(character, slug, sections=["Relationships"])` returns the Relationships section body (free text), NOT the structured `feeling` field. **Same issue as Thread 11** — the spec's retrieve replacement doesn't actually cover `feeling`.

**This is a real gap:** The `feeling` text is structured data in a relation note, not a section. Dropping it from load without a retrieve path means it's lost.

### Finding: ⚠️ **Real gap.** Character relationship `feeling` is stored in relation `note`, not in a section. `story_retrieve(character, ..., sections=["Relationships"])` returns the Relationships section body, not the structured feeling. Either: (a) keep `feeling` in the load payload, (b) add a retrieve path for relation notes, or (c) accept the loss.

---

## Thread 13: Sequence/Act `value`, `value_open`, `value_close` kept

**Spec claim (§3, Sequence/Act):** Keep `value`, `value_open`, `value_close` — "Cheap (~2-3 tokens each), gives sequence/act-level value-shift signal."

### Verification

**Code state:** Current sequence/act schemas have these fields (`constants.py:135-137`, `148-150`). They're stored in `extra` JSON.

**Design question:** The spec keeps them. **No conflict.**

**One to verify:** The spec's example sequence object doesn't show these fields. Looking at §2's example: the sequence object only shows `id`, `title`, `scenes`. **The example omits `value`/`value_open`/`value_close` even though the field table says "keep".** This is just an incomplete example, not a design conflict — but worth noting.

### Finding: ✅ Design is sound. Example is incomplete but the field table governs.

---

## Thread 14: Arc beat `label`, `scene`, `shift`, `y`, `is_crisis`, `is_climax` kept

**Spec claim (§3, Arc beat full form):** Keep these fields. Drop `action`, `gap`, `choice` (long prose → retrieve).

### Verification

**Code state:** Current arc schema has all these fields in `extra` JSON (`constants.py:154-167`).

**Design question:** The spec keeps structural fields, drops prose. **Consistent with the overall philosophy.**

**One to verify:** The spec says `action`, `gap`, `choice` → `story_retrieve(arc, slug, sections=["Action","Gap","Choice"])`. Current arc sections are `["Action", "Gap", "Choice", "Shift", "Development Log"]` (`entity.py:173`). **The retrieve path exists.** ✅

**One to verify:** The spec's example arc object shows `"shift": "positive→mixed"`. Current arc schema has `shift` default `"Shift not recorded"`. The fixture has `shift: positive → mixed`. **Consistent.**

### Finding: ✅ Design is sound. Retrieve path exists for dropped prose fields.

---

## Thread 15: Scene stub criterion — `status == "planned"` AND no `dramatic_role` AND no `chars` AND no sections

**Spec claim (§3, Scene stub):** Bare id string criterion.

### Verification

**Code state:** Current scene statuses: `planned`, `drafted`, `written`, `locked` (`constants.py:6`).

**Design question:** The spec uses a conjunction of conditions. A scene is a stub only if ALL of: status is planned, no dramatic_role, no chars, no sections. **This means a planned scene WITH a dramatic_role becomes full.** Is that intended? The spec says "an entity should be promoted to full form if it has *either* meaningful frontmatter *or* ≥1 section written" (§"sections field"). **So a planned scene with `dramatic_role: setup` would be full.** This seems reasonable — someone set the dramatic role, so work has been done.

**One to verify:** The spec says "no `chars`" — but `chars` is derived from the `character_scene` relation, not stored on the scene entity itself. The builder must compute `chars` from relations before applying the stub criterion. **Feasible** (the dashboard already does this).

### Finding: ✅ Design is sound. Builder must compute derived fields (chars, location) before applying stub criterion.

---

## Thread 16: Location/World — `rules` dropped

**Spec claim (§3, Location/World):** World `rules` dropped → `story_retrieve(world, slug, sections=["Description","History","Conflict"])`.

### Verification

**Code state:** World sections are `["Description", "History", "Conflict"]` (`entity.py:168`). `rules` is a frontmatter list field (`constants.py:69`), stored in `extra` JSON, NOT as a section.

**Design question:** The spec says `rules` → retrieve. But `rules` is frontmatter (structured list), not a section body. `story_retrieve(world, ...)` returns section bodies, not frontmatter fields. **Same issue as Threads 11 and 12** — the retrieve path doesn't cover frontmatter fields.

**This is a real gap:** World `rules` is a frontmatter list. It's not a section. Dropping it from load without a retrieve path means it's lost.

### Finding: ⚠️ **Real gap.** World `rules` is frontmatter, not a section. `story_retrieve(world, ...)` returns section bodies, not frontmatter. Either: (a) keep `rules` in load, (b) add a retrieve/fields path for frontmatter, or (c) accept the loss.

---

## Thread 17: Project `inciting_incident_scene_id`, `story_climax_scene_id` kept

**Spec claim (§3, Project):** Keep as "cross-reference anchors; redundant with per-scene `climax` marker but cheap enough."

### Verification

**Code state:** These are project frontmatter fields (`constants.py:101-102`), stored in `extra` JSON.

**Design question:** The spec keeps them. **No conflict.**

**One to verify:** The spec says they're "redundant with per-scene `climax` marker." If the scene's `climax` enum is derived from the project's pointers (as the spec's example suggests), then they're not just redundant — they're the *source*. **This reinforces the need to resolve Thread 8** (where does `climax` come from?).

### Finding: ✅ Design is sound. Reinforces Thread 8 resolution.

---

## Thread 18: `confirmation` message format

**Spec claim (§2):** `"Loaded Save the Children — 3 scenes (1 developed), 1 sequence, 1 act, 6 characters, 2 locations, 2 plots."`

### Verification

**Code state:** Current `story_load.py:79-88` builds a confirmation from type counts. The spec's version adds "(1 developed)" — a count of non-stub scenes.

**Design question:** The builder needs to count stub vs. full scenes. **Feasible** — the stub classifier already makes this distinction.

**One to verify:** The spec's confirmation doesn't mention arc beats or worlds. Current confirmation includes arc beats. **Intentional omission** — the spec's confirmation is more curated. **Fine.**

### Finding: ✅ Design is sound. Builder needs stub/full counts for the confirmation.

---

## Thread 19: Token budget numbers

**Spec claim (§7):** Total ~47k → ~8k tokens.

### Verification

**Code state:** The spec's estimates are based on `data_model.md` token estimates. The actual token count depends on implementation. **Not verifiable without implementation**, but the *direction* is correct: removing relations table (-12.9k), simplifying arc beats (-10k), scene stubs (-7k), memory outline (-4.7k) are the big wins.

**One to verify:** The spec says "per-entity `sections` field is folded into each entity type's own row rather than broken out." This means the `sections` field adds ~1 token per entity (a short string). **Negligible.**

### Finding: ✅ Directionally correct. Actual numbers need implementation to verify.

---

## Thread 20: Open decisions (§8)

The spec lists 6 open decisions. Let me verify each against the code:

1. **Scene stub criterion** — verified in Thread 15. ✅
2. **Arc beat stub criterion** — verified in Thread 4. ⚠️ `y=0.0` conflict.
3. **Section-only promotion** — verified in Thread 15. ✅
4. **Empty sequences** — spec proposes `"scenes": []`. Current code: a sequence with no scenes would still be emitted as a full object. **Consistent.** ✅
5. **Scene `title` field** — spec keeps it. Current scenes have `title` in the `name` column. **Consistent.** ✅
6. **Project title-page fields retrieval path** — deferred. ✅
7. **Memory retrieval path** — deferred. ✅

### Finding: All open decisions are well-flagged. Thread 2 (arc stub) is the most urgent to resolve.

---

## Summary of Findings

### ✅ Sound design ideas (no conflicts):
1. No flat relations table — embed at endpoints
2. Structure by nesting, not `parent_id`
3. Order by array position (with `order_key` sort)
4. Hybrid full/stub representation (scene stubs)
5. Omitted field = unfilled
6. `sections` field as availability index
7. `unfilled` inverted encoding
8. Project title-page fields dropped (gap deferred)
9. Memory outline (deferred)
10. Arc beat prose → retrieve (path exists)
11. Sequence/Act value fields kept
12. Confirmation message format
13. Token budget direction

### ⚠️ Conflicts needing resolution:

| # | Issue | Severity | Resolution options |
|---|-------|----------|-------------------|
| A | **Arc beat stub criterion**: `y=0.0` is both default and meaningful | Medium | Use different signal: `label == ""` or `action/gap/choice` all at default |
| B | **§1.5 vs §3 status conflict**: Omit defaults vs keep status | Low | Decide: status always emitted, or omitted at default |
| C | **Scene `climax` enum**: exclusive enum from non-exclusive booleans. Fixture has inconsistency between scene booleans and project pointers | High | Determine canonical source; define priority if multiple booleans true |
| D | **Per-beat plot descriptions**: dropped from load, but NOT covered by `story_retrieve(plot, sections=["Summary","Obstacles"])` — they're relation notes, not sections | High | Keep in load, or add relation-note retrieve path, or accept loss |
| E | **Character relationship `feeling`**: dropped from load, but NOT covered by `story_retrieve(character, sections=["Relationships"])` — it's relation note, not section | High | Keep in load, or add relation-note retrieve path, or accept loss |
| F | **World `rules`**: dropped from load, but NOT covered by `story_retrieve(world, sections=[...])` — it's frontmatter, not section | Medium | Keep in load, or add frontmatter retrieve path, or accept loss |

### 📝 Implementation notes:
- Builder MUST sort children by `order_key` (then `id` for stability) before nesting
- Builder MUST compute derived fields (chars, location) before applying stub criterion
- "Preview line" in memory outline needs concrete definition (first line? first N chars?)

---

## Key Design Threads to Discuss

The **high-severity** items (C, D, E) all stem from the same root cause: **the spec assumes `story_retrieve(entity, sections=[...])` can replace dropped fields, but some dropped fields are stored as relation notes or frontmatter — not as sections.** The retrieve tool only returns section bodies.

This is the central design tension to resolve: either (a) the load payload keeps these fields, or (b) the retrieve tool expands to cover relation notes and frontmatter, or (c) the data is accepted as lost on load (retrievable only via direct DB query or new tools).

The spec's philosophy ("every kept field earns its place on session-start signal value") suggests (a) for fields with high signal, (b) for fields that can be cleanly retrieved. The current retrieve tool's section-only scope is the blocker.
