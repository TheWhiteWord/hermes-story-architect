
# Data Model Proposal: Scenes, Sequences, and Acts as First-Class Entities

## The Single Most Important Decision First

Before schemas: **the identity question determines everything else.**

The brief proposes slugging scenes from headings (`INT. HOUSE. NIGHT → house-night`). This is fragile for a different reason than the one you named — not just duplicate headings, but semantically meaningless headings. A scene's heading describes where it physically takes place, not what it *is*. Two scenes in the same kitchen are different story events that happen to share a location.

The right identity is **a user-assigned, human-readable slug that describes the scene's dramatic function**, not its physical location. `mara-discovers-files`, not `precinct-bathroom-day`. The heading is metadata. The slug is identity.

This has cascading consequences for the whole model, so I'm naming it first.

---

## 1. Vault Structure

```
projects/<project-slug>/
├── project.md
├── scenes/
│   ├── mara-discovers-files.md
│   ├── oak-lies-to-her-face.md
│   └── the-arrest.md
├── sequences/
│   ├── seq-inciting-discovery.md
│   └── seq-world-before.md
├── acts/
│   ├── act-1.md
│   ├── act-2.md
│   └── act-3.md
├── characters/
│   └── mara.md
└── plots/
    └── main-plot.md
```

**Why individual files per entity, not one-file-per-type:**
- Section-level retrieval requires one file per entity. A single `scenes.md` with 94 scenes means loading all 94 to retrieve one.
- `story_edit` operates on files. Individual files give you granular, targeted editing.
- The index summarizes everything anyway — the number of files doesn't bloat context.
- It matches the mental model users already have for characters and plots.

**Why acts/ and sequences/ as separate folders, not sections in project.md:**
The previous proposal put acts/sequences inside `## Structure` in `project.md`. That was acceptable for a skeleton, but once scenes are first-class files with their own notes, content, and arc annotations, acts and sequences need to be first-class too. A sequence with 12 scenes and production notes doesn't belong crammed into a parent's section.

---

## 2. Scene Entity

### Frontmatter

```yaml
# scenes/mara-discovers-files.md
id: mara-discovers-files          # stable slug (user-assigned, dramatic function)
type: scene
title: "Mara Discovers the Files"  # display name, can be edited freely
order: 22                          # position within parent sequence
status: planned | drafted | written | locked

# Physical location (for screenplay output only)
heading: "INT. PRECINCT BATHROOM - DAY"
location: precinct-bathroom        # slug → locations/precinct-bathroom.md
time_of_day: DAY | NIGHT | DUSK | DAWN | CONTINUOUS | LATER

# Containment (the parent chain)
sequence_id: seq-inciting-discovery
act_id: act-1

# Characters present
characters:
  - mara
  - detective-oak

# Plot threads this scene advances
plots:
  - main-plot

# --- Dramatic metadata (what the future arc/structure system reads) ---

# Value turn: the scene's story event
value: Trust                       # the value at stake in this scene
value_open: positive               # charge at scene opening
value_close: negative              # charge at scene closing
# null values = not yet analyzed; system never demands these

# Conflict levels engaged (McKee's three circles)
conflict_levels: [inner, personal] # inner | personal | extra-personal

# Scene's role in the containing sequence/act
dramatic_role: setup | complication | crisis | climax | resolution | transition
# null = not assigned; transition = valid (not every scene is a turning point)

# Flags for special structural positions
is_inciting_incident: false
is_sequence_climax: false
is_act_climax: false
is_story_climax: false
```

### Body Sections

```markdown
## Description

One paragraph. What happens in this scene — the physical action, not the dramatic interpretation.
Written early in planning. Should be draftable before content exists.

## Dramatic Function

What this scene *does* in the structure. Why it exists.
How it advances the value turn. What it sets up or pays off.
This is where the LLM writes analysis and the user writes intent.

## Notes

Free-form. Production notes, continuity concerns, open questions.
Not loaded by default in dramatic analysis queries.

## Content

The actual scene text (Fountain syntax or prose).
Loaded only when: editing, script view assembly, deep scene analysis.
This is the heaviest section — never loaded speculatively.
```

**Why this section split matters:** The retrieval strategy changes by query. "What happens in Act 2?" loads `## Description` from each scene. "Is this scene's dramatic function sound?" loads `## Dramatic Function`. "Show me the script" loads `## Content`. The index never needs to know what's in `## Content` to answer structural questions.

**On `dramatic_role`:** This is the field that prevents the most redesign later. McKee's hierarchy — scenes build sequences, sequences build acts — is expressed through the *cumulative pattern* of scene roles within each container. A sequence that has no `crisis` beat has a structural problem the LLM can flag without reading scene content. The role is assigned by the user or LLM, not derived.

**On `conflict_levels`:** This is the field character arcs will reference. An arc beat isn't just "something happens in scene 22" — it's specifically that inner conflict fires in scene 22. When the arc system asks "does this arc escalate through all three conflict levels?", it reads this field across the scene files in the arc beats, not the scene content.

**On null values:** Every dramatic metadata field is nullable. Planning-first workflow means scenes start with just `title`, `status: planned`, `sequence_id`, and `act_id`. The value turn analysis, conflict levels, and dramatic role fill in as the writer works. The system never blocks on incomplete data.

**On index placement:** The dramatic metadata fields above (`value`, `value_open`, `value_close`, `conflict_levels`, `dramatic_role`, `is_*_climax`) live in the scene file frontmatter but NOT in the main index. They're loaded on demand from `.story/structure-index.yaml` during structural analysis. This keeps the main index lean for navigation queries.

---

## 3. Sequence Entity

### Frontmatter

```yaml
# sequences/seq-inciting-discovery.md
id: seq-inciting-discovery
type: sequence
title: "The Inciting Discovery"
order: 2                           # position within parent act
status: planned | in-progress | complete
act_id: act-1

# The sequence's own value turn (McKee: moderate reversal)
value: Trust
value_open: positive
value_close: negative
# The sequence climax is the scene where this reversal lands:
climax_scene_id: mara-discovers-files

# Plot thread this sequence primarily advances (optional)
# Sequences usually serve one thread; subplots may have their own sequences
primary_plot: main-plot

# Dramatic purpose at the sequence level
purpose: null                      # free text: "Establish Oak's trustworthiness, then destroy it"
```

### Body Sections

```markdown
## Summary

What this sequence accomplishes dramatically. The arc of the sequence —
where it starts emotionally/narratively, how it builds, where it lands.
Written at planning stage. One or two paragraphs.

## Scene Order

The ordered list of scenes in this sequence, with one-line descriptions.
The LLM maintains this when scenes are added/removed/reordered.
This is a rendered view of the frontmatter `order` fields — kept here
for human readability, not as the authoritative source.
Authoritative order = scene frontmatter `order` field + `sequence_id`.

## Notes

Open questions, continuity flags, thematic notes.
```

**On `climax_scene_id`:** This is the most important field on the sequence. McKee's definition of a sequence is precisely this: a series of scenes that *culminates* in a scene of greater impact. The climax scene is the sequence's reason for existing. By naming it explicitly in the sequence's frontmatter, the index can expose `climax_scene_id` as a lightweight edge without loading sequence content. The arc system, when asking "what scene is the emotional peak of this sequence?", has a one-field answer.

**On `primary_plot`:** Sequences are usually in service of one plot thread — the main plot or a specific subplot. This field is optional but helps the structure system answer "which sequences advance the subplot?" without scanning every scene's `plots` array.

---

## 4. Act Entity

### Frontmatter

```yaml
# acts/act-1.md
id: act-1
type: act
title: "The Setup"
order: 1
status: planned | in-progress | complete

# The act's value turn (McKee: major reversal)
value: Trust
value_open: positive
value_close: negative
climax_scene_id: mara-discovers-files  # the act climax scene (may differ from seq climax)

# The spine field lives here — explained below
spine: null                        # at act level, spine = protagonist's desire THIS act
# Story-level spine lives in project.md
```

### Body Sections

```markdown
## Summary

The act's dramatic shape. Where it starts, what pressure builds, where the major
reversal lands and why it's more powerful than any preceding scene.
This is the section the LLM reads when asked "what's the arc of Act 1?"

## Thematic Function

How this act advances the controlling idea. What the act argues —
which side of the idea/counter-idea debate it embodies.
Optional. Useful for revision-stage analysis.

## Notes
```

---

## 5. Relationships: The Minimal Complete Set

There's a temptation to add many cross-reference fields. Here's the discipline: **add a relationship only if removing it would require loading file content to reconstruct it.** If the information is derivable from existing fields at index time, it doesn't need to be a stored relationship.

### Relationships to store (can't be derived without content reads)

| From | To | Field | Reason it must be stored |
|---|---|---|---|
| Scene | Sequence | `sequence_id` | Containment — primary hierarchy |
| Scene | Act | `act_id` | Shortcut — avoids deriving act from sequence at every query |
| Scene | Characters | `characters[]` | Who's in the scene — can't derive without reading content |
| Scene | Plots | `plots[]` | Which threads fire here — not derivable from structure |
| Scene | Location | `location` | For screenplay assembly and location views |
| Sequence | Act | `act_id` | Containment |
| Sequence | Scene (climax) | `climax_scene_id` | The sequence's culminating scene — structurally significant |
| Act | Scene (climax) | `climax_scene_id` | The act's major reversal scene |

### Relationships to NOT store (derivable at index time)

| Relationship | Why not stored |
|---|---|
| Sequence → Scenes list | Derivable: all scenes where `sequence_id = this` |
| Act → Sequences list | Derivable: all sequences where `act_id = this` |
| Act → Scenes list | Derivable: all scenes where `act_id = this` |
| Scene → next/prev scene | Derivable: sort all scenes by `sequence_id + order` |
| Character → Scenes list | Derivable: all scenes where `characters contains this` |

The index regeneration (`story_index`) builds these derived lists once and caches them. Tools query the cache, not the raw files. No relationship needs to be stored twice.

### The arc-beat relationship (future, but design for it now)

Character arc beats will need to reference scenes. The reference lives **on the character file**, not on the scene file. Specifically: `character.md → ## Arc → arc beat → scene_id`. This means a scene doesn't need to know it's an arc beat for a character — the arc system reads the character's arc beats and follows the `scene_id` pointer to the scene. This is intentionally unidirectional. If you need the reverse ("which characters have arc beats in this scene?"), the index builds that at regeneration time.

One consequence: scenes get a **derived index field** `arc_beat_refs: [{character_id, beat_label}]` that the arc system can read without loading character files. This is the index doing its job.

---

## 6. Index Entries

The index is the only thing always in context. Each entity type gets a compact entry.

**Scene index entry (thin — navigation only, ~6 lines per scene, ~560 lines for 94 scenes):**

```yaml
- id: mara-discovers-files
  type: scene
  title: "Mara Discovers the Files"
  order: 22
  status: written
  sequence_id: seq-inciting-discovery
  act_id: act-1
  heading: "INT. PRECINCT BATHROOM - DAY"
  characters: [mara, detective-oak]
  plots: [main-plot]
  location: precinct-bathroom
  sections: [Description, Dramatic Function, Notes, Content]
```

This answers all navigation queries. Dramatic metadata (`value`, `conflict_levels`, `dramatic_role`, etc.) lives in the scene file frontmatter and is loaded on demand from `.story/structure-index.yaml` during structural analysis.

**Sequence index entry (full feature set — small number of entities):**

```yaml
- id: seq-inciting-discovery
  type: sequence
  title: "The Inciting Discovery"
  order: 2
  act_id: act-1
  status: in-progress
  scene_count: 8
  value: Trust
  value_open: positive
  value_close: negative
  climax_scene_id: mara-discovers-files
  primary_plot: main-plot
  sections: [Summary, Scene Order, Notes]
```

**Act index entry (full feature set — small number of entities):**

```yaml
- id: act-1
  type: act
  title: "The Setup"
  order: 1
  status: in-progress
  sequence_count: 2
  scene_count: 22
  value: Trust
  value_open: positive
  value_close: negative
  climax_scene_id: mara-discovers-files
  sections: [Summary, Thematic Function, Notes]
```

Total index overhead for a 3-act, 8-sequence, 94-scene story: approximately 3 act entries (~8 lines each) + 8 sequence entries (~12 lines each) + 94 scene entries (~6 lines each) = ~700 lines. Well within budget.

---

## 6a. Structure Index (Sidecar)

A derived file `.story/structure-index.yaml` holds scene-level dramatic metadata for pattern queries across the whole story. Loaded on demand during structural analysis, never part of the default context.

```yaml
# .story/structure-index.yaml — regenerated by story_index
scenes:
  - id: mara-discovers-files
    value: Trust
    value_open: positive
    value_close: negative
    conflict_levels: [inner, personal]
    dramatic_role: climax
    is_sequence_climax: true
    is_act_climax: false
    arc_beat_refs: [{char: mara, label: "First Doubt"}]

  - id: oak-lies-to-her-face
    value: Trust
    value_open: mixed
    value_close: negative
    conflict_levels: [personal]
    dramatic_role: complication
    ...

sequences:
  - id: seq-inciting-discovery
    value: Trust
    value_open: positive
    value_close: negative
    climax_scene_id: mara-discovers-files

acts:
  - id: act-1
    value: Trust
    value_open: positive
    value_close: negative
    climax_scene_id: mara-discovers-files
```

**Operational rule:** Scene feature fields are authoritative in scene file frontmatter. The structure-index is a read-optimized cache. The LLM never writes to it directly — it writes to scene files and `story_index` rebuilds the cache. To prevent staleness, `story_structural edit` on a scene triggers a lightweight structure-index update for that scene's entry specifically, without a full rebuild.

**Query routing:**

| Query | Load |
|-------|------|
| "What's the value arc of Act 2?" | Main index (act entry has value fields) |
| "Which sequence is structurally weakest?" | structure-index.yaml |
| "Which scenes turn Trust negative?" | structure-index.yaml |
| "Does this arc escalate through conflict levels?" | structure-index.yaml |
| "What scenes are in sequence 3?" | Main index (navigation) |
| "What's the dramatic role of scene-22?" | structure-index.yaml or scene file |
| "Is this scene's function sound?" | Scene file (## Dramatic Function) |

---

## 7. What's Missing from What You Described

### The Story Level Entity

McKee's hierarchy is: Beat → Scene → Sequence → Act → **Story**. You have scenes, sequences, and acts. You don't have an explicit Story entity above the act. Currently `project.md` plays this role — it holds the logline, genre, status.

You need to either formally promote `project.md` to be the story entity, or accept that story-level structural fields (spine, controlling idea, inciting incident, climax scene, value at open/close for the whole story) live in `project.md` frontmatter as a peer of logline and genre. I recommend the latter. `project.md` *is* the story entity. It just needs the right fields added:

```yaml
# project.md additions
spine: "A detective discovers her partner's corruption and must choose between loyalty and truth"
controlling_idea: "Justice triumphs when we sacrifice what we love most for what we believe"
value: Trust
value_at_open: positive
value_at_close: ironic
inciting_incident_scene_id: oak-lies-first-time
story_climax_scene_id: she-turns-him-in
structure_type: Classical | Miniplot | Antiplot
```

No new entity. No new folder. But these fields must be there, because the arc system needs the story-level value arc (the whole sweep from open to close) to evaluate whether individual character arcs are building toward the right destination.

### Subplots and Their Relationship to Sequences

McKee identifies four subplot types: Contradictory, Resonant, Setup, Complicating. Your existing `plots/` entity handles plot threads. The gap is: **a subplot's scenes need to be traceable through the act/sequence structure, not just through their plot array.**

Right now a subplot scene would have `plots: [romance-subplot]` and `sequence_id: seq-5`. But which scenes in seq-5 are subplot scenes and which are main-plot scenes? This matters when the structure system asks "does this sequence interweave the subplot effectively?"

The minimal solution: a sequence gets an optional `subplot_role` field on its `plots[]` entries, or alternatively each scene's `plots[]` array is treated as ordered (first entry = primary thread for this scene). Either is fine. The key constraint is that this doesn't require a new entity type — it's a metadata field on existing relationships.

### The `dramatic_role` Enum Needs a `non-event` Value

McKee explicitly says some scenes don't turn — they're exposition, transition, or setup with no value shift. These are valid (sometimes necessary) but structurally weak. The system needs to be able to represent them without forcing a fake value turn. Add `non-event` to the `dramatic_role` enum, and leave `value_open` and `value_close` as null for those scenes. The future structure system can flag them ("this sequence has three non-events in a row") without the data model breaking.

---

## 8. Accommodating Structure Types

Classical, Miniplot, and Antiplot have different structural expectations, but the data model doesn't need to branch for them. The model is neutral. What changes is **what the LLM enforces** based on `project.structure_type`.

A few fields need to be nullable rather than required precisely because of this:

- `value_close` on a scene can be `null` for Antiplot (no causal value progression expected)
- `climax_scene_id` on an act can be `null` for Antiplot (no clear act climax required)
- `spine` in `project.md` can be `null` for Miniplot with a passive protagonist
- `is_inciting_incident` may fire on multiple scenes in Miniplot (diffuse inciting events)

The model accommodates all three by being nullable. The structure system, not the data model, knows that a `null` act climax is a problem in Classical but acceptable in Antiplot.

---

## 9. Where the Spine Lives

McKee defines the spine as "the energy of the protagonist's desire" — it's a story-level concept, not an act-level one. It belongs in `project.md`.

However, each act has a version of the spine question: "what is the protagonist *trying to do* in this act?" That's different from the story-level desire. Acts can have an `act_objective` field — the protagonist's immediate goal for the duration of the act — which is an aspect of the global spine, not a separate concept. This maps exactly to McKee's "scene-objective is an aspect of the super-objective."

```yaml
# act-1.md frontmatter
act_objective: "Prove herself in the new precinct — be a good cop who trusts her partner"
# This is a *manifestation* of the story spine, not a separate spine.
# Story spine lives in project.md.
```

No `spine` field on sequences or scenes. At the sequence level, `purpose` covers it. At the scene level, `## Dramatic Function` covers it in prose.

---

## 10. Tool Surface

You proposed a single `story_structural` tool with a `type` parameter. That's right. Here's the exact surface:

```
story_structural
  action: create | retrieve | edit | reorder | delete
  type: scene | sequence | act
  id: <slug>
  sections: [Description, Dramatic Function, ...]   # for retrieve
  data: {...}                                        # for create/edit
```

No new tool for index regeneration — `story_index` already handles that and should be extended to walk `scenes/`, `sequences/`, `acts/`. No new tool for screenplay assembly — that's a `story_dashboard` concern (Script view assembles scenes in order, reads `## Content` sections).

The one tool call that doesn't fit cleanly is **reordering** — moving scene-003 to position 7 within a sequence. This requires updating `order` fields on multiple files. `story_structural` with `action: reorder` handles this as a batch edit: the tool accepts the new ordered list of scene ids within a sequence and updates all their `order` fields atomically.

---

## 11. Trade-offs and What's Left Open

**Chosen: heading is metadata, slug is identity.** This means the slug is set once and changing it is a refactoring operation (update all references). The display `title` field is what users see and can change freely. The slug is what the system uses internally. If you choose to auto-generate slugs from headings for convenience, treat them as initial suggestions the user must confirm, not final identities.

**Chosen: `act_id` on scenes as a shortcut.** Strictly, act membership is derivable from sequence membership. Storing `act_id` directly on scenes is denormalization. The reason to accept it: many queries filter by act, and forcing a join through sequence at query time means loading all sequences first. One extra field per scene buys O(1) act filtering.

**Chosen: content in `## Content` section, not a separate file.** An alternative is `scene-slug.fountain` as a sibling file. The separate-file approach is cleaner for Fountain tooling but breaks the section-level retrieval pattern. Keeping content in a body section means one tool (`story_structural retrieve`) handles everything, and the index tracks section availability uniformly.

**Left open: scene ordering authority.** Two valid options: (a) `order` field in frontmatter is authoritative, rendered into `## Scene Order` in the sequence file for readability; or (b) `## Scene Order` in the sequence file is authoritative, parsed by `story_index` to populate `order` fields. Option (a) is more robust for programmatic reordering. Option (b) is more natural for a user editing the sequence file directly. This depends on how much you trust users to edit frontmatter vs. body prose.

**Left open: scene status granularity.** `planned | drafted | written | locked` is a starting point. "Drafted" and "written" may be the same thing depending on your workflow. If the screenplay import sets status on import, you may want `imported` as a distinct status that means "content came from fountain, not typed here." This is a workflow question, not a model question.

**Left open: location as entity vs. string.** Scenes reference `location: precinct-bathroom` — a slug into `locations/`. If a scene is planned and the location doesn't exist yet, does the slug still work? You probably want `location` to be a nullable free string for planned scenes that becomes a slug once the location entity exists. Or always a slug, with a convention that the location file gets created on demand. Either is fine; just decide before building the index parser.