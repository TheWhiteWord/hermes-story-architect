# Issue A: One Source for Plot Roles and Story Milestones

Design document, Draft 1, October 10, 2026. Applies to the hermes-story-architect repository, dev branch. Scope: Issue A only.

## 1. Problem

The same structural facts are recorded in several places that can disagree. Three structural records exist today, and two of them duplicate facts:

1. **Per-plot roles.** Relations `plot_setup`, `plot_complication`, `plot_crisis`, `plot_climax`, `plot_resolution`, written through `scene.plot_roles`.
2. **Milestones.** Four scene flags (`is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`) plus pointer fields (`project.inciting_incident_scene_id`, `project.story_climax_scene_id`, `act.climax_scene_id`, `sequence.climax_scene_id`).
3. **`scene.dramatic_role`.** The scene's own role in the story. Scenes are where roles are defined, so this is a record to keep, not a duplicate (see section 4.1).

Evidence found in the code:

- **The test fixture contradicts itself.** In `tests/fixtures/save-the-children`, `project.md` names `central-room-day` as the inciting incident and the scene's own text says so, yet the scene has `is_inciting_incident: False`. The act-climax and story-climax flags disagree with their pointers in the same way.
- **Dead reads.** The `dramatic_elements` view in `tools/story_load.py` reads `is_setup`, `is_turning_point`, `is_crisis`, `is_climax`, `is_resolution` and `milestone` from scenes. None of these exist in `ENTITY_SCHEMAS`.
- **Lossy display.** `_milestone_marker` in `core/db.py` returns a single label per scene, so a scene that is both a sequence climax and the story climax shows only one.

## 2. Principles

These were agreed during design discussion and drive every decision below.

1. **Plan, execution and verification are separate.** The plan is what the user or assistant intends. Execution is what the written scenes actually do. Verification is the user's and assistant's reasoning about plan versus execution against the theory. Verification is not a schema feature, and no program judges whether the story obeys the theory. The theory lives in the skills.
2. **Each fact is stored once.** Duplicated facts drift, as the fixture shows.
3. **Only record what the theory does not already determine.** By McKee's definitions a sequence culminates in its climax and an act peaks in its climax, so the climax is the last scene of the unit. Recording it adds no information.
4. **The full set of story elements (inciting incident, complications, crisis, climax, resolution) is tracked at story and plot level.** The source file defines them at story level. Applying them inside sequences and acts is an inference, and resolution cannot exist inside a unit that ends at its climax.
5. **Setup is not the inciting incident.** Setup is the opening state before the balance is upset. The inciting incident is the first major turn that upsets it, and the protagonist must react to it.

## 3. Scope

**In scope:** where plot roles and story milestones are stored, how the story-level milestones are read, the sixth plot role, and one time script migration of existing fixture and live test project.

**Out of scope (later issues):** value propagation (B1), the P/C/CD/NN schema (B2), character arcs (B3).

## 4. Target model

### 4.1 Execution layer

- **Scenes are where structural roles are defined.** A role can only be recorded once a scene exists, because the theory's elements happen in scenes. `scene.dramatic_role` records the scene's own role in the story, and `scene.plot_roles` records its role in each plot (one scene can hold different roles in different plots, so a plot's role cannot live on the scene alone).
- **Plots read their roles back from scenes.** The plot's role fields (`setups`, `complications`, `crisis`, `climax`, `resolutions`, and the new `inciting_incident`) are computed and read-only. They organize what happened in each plot and are never written on the plot. This is already how the repository works.
- **There are six roles:** `setup`, `inciting_incident`, `complication`, `crisis`, `climax`, `resolution`. The new one is `inciting_incident`.
- **Story-level milestones are the main plot's roles.** The main plot is the plot with `plot_scope = main`. The story's inciting incident, crisis and climax are whatever scenes hold those roles in the main plot. Nothing separate is stored at project level.
- **Act and sequence climaxes are not stored.** Position follows from the theory.

### 4.2 Plan layer (existing entity sections)

Planning already has a home: the free-text sections every entity carries (the `sections` table, a heading and a body). They hold the plan for any element: what a plot is about and how it should evolve, the intended reversal of an act or sequence, and so on. A plan can be written before any scene exists, and it evolves with the writing. It never names a scene, because where an element happens is only known once the scene is written. No new schema fields are added for planning. The `story-theory` skill instructs the assistant to record any planning discussion for an element in that element's sections when creating it.

### 4.3 Verification layer

Nothing in the schema. The `story-theory` skill states the expectations (escalation, position of climaxes, plan versus execution), and the findings go in the existing memory categories: `decisions`, `open_questions`, `continuity_warnings`.

## 5. Field changes

| Field | Change |
| --- | --- |
| `scene.is_inciting_incident` | Remove |
| `scene.is_story_climax` | Remove |
| `scene.is_act_climax` | Remove |
| `scene.is_sequence_climax` | Remove |
| `project.inciting_incident_scene_id` | Remove |
| `project.story_climax_scene_id` | Remove |
| `act.climax_scene_id` | Remove |
| `sequence.climax_scene_id` | Remove |
| Plot role `inciting_incident` | Add (field `inciting_incident`, relation `plot_inciting_incident`) |
| `scene.plot_roles` | Keep, with the role list extended to six |
| `scene.dramatic_role` | Keep (scenes are where roles are defined) |
| Plan fields | None added (planning lives in entity sections) |

## 6. Reading the story-level milestones

A read-side presentation, not a verdict:

- Report the scenes holding the inciting-incident, crisis and climax roles in the main plot and for each sub_plot.
- If several scenes hold the same role, list them all in story order and do not choose between them.
- If there is no main plot, say so (it appears under `unfilled`).
- Replace the `dramatic_elements` view's dead reads with this presentation.
- `_milestone_marker` returns every milestone a scene holds, not one.

The dashboard reads the flags and pointers in three places: `scenes.js` (lines 42 to 45), `entity-panels.js` (lines 436 to 439) and `story.js` (lines 49 to 56). These must read the presented milestones instead.

## 7. Migration of existing projects

One time script not to be part of the application (app has not been deployed yet, so only repo fixture, and live test project are affected). Run as a dry run first, after `story_backup`.

1. A scene with `is_story_climax` gets a `climax` role in the main plot, if it lacks one.
2. A scene with `is_inciting_incident` gets an `inciting_incident` role in the main plot, if it lacks one.
3. The act and sequence flags and pointers are not carried over. 
4. The dry run also reports any flag that disagrees with its project pointer. It does not guess which one is right.
5. After approval, strip the removed fields from `extra`.

The migration must be idempotent. Importing old markdown files that still contain removed keys should be tolerated with a warning (to be verified in `tools/story_import.py`).

## 8. Work plan

Each step leaves the test suite green.

| Step | Work |
| --- | --- |
| 0 | Install pytest, run the suite on dev, record the baseline. |
| 1 | Add the sixth role: `PLOT_ROLES` in `core/constants.py`, `_RELATION_FIELDS["plot"]` and the scene role validator in `core/entity.py`, `DASH.PLOT_ROLES` in `src/dashboard/js/colors.js`, and the pins in `tests/test_plot_roles.py`. |
| 2 | Write the migration as a dry-run report plus an apply mode. |
| 3 | Switch the readers: `core/db.py`, the `dramatic_elements` view, and the three dashboard locations. |
| 4 | Remove the stored fields from `ENTITY_SCHEMAS` and the write paths. Update fixtures and tests. |
| 5 | Update the `story-theory` skill with the theory guidance from section 4.3 and the instruction to record planning in entity sections when creating elements. |

## 9. Open decisions

1. **`scene.dramatic_role` and `scene.plot_roles`.** Both record roles at scene level, and plots currently read only the `plot_roles` entries. Confirm that this stays, or whether a plot should also read a scene's `dramatic_role` when the scene has no `plot_roles` entry for it.
2. **Several scenes holding one role in the main plot and su_plots.** Presentation lists them all (section 6). inciting_incident should be limited to one.
3. **Dashboard tags for sequence and act climax.** They are no longer stored.
4. **No main plot.** Confirm that the story-level milestones are then simply empty.

## 10. Files and tests affected

**Code:** `core/constants.py`, `core/entity.py`, `core/db.py`, `tools/story_load.py`, `tools/story_import.py`, `tools/story_export.py`, `src/dashboard/js/colors.js`, `src/dashboard/js/views/scenes.js`, `src/dashboard/js/panels/entity-panels.js`, `src/dashboard/js/views/story.js`, `skills/story-theory`.

**Tests:** `test_plot_roles.py` (pins the five-role list and the JS copy), `test_scene_plot_roles.py`, `test_story_describe.py` (line 186), `test_field_coverage.py`, `test_unfilled_fields.py`, `test_story_load_views.py`, `test_phase2_db_reads.py`, `test_draft_preview.py`, `test_write_shape.py`, `test_round_trip.py`, `test_core.py` (the `climax_scene_id` checks near line 919).

**Fixtures:** the `save-the-children` fixture. 

These lists come from searching the code for the relevant names. The exact failures need the step 0 baseline.

## 11. Risks

- Existing projects carry the old flags. The migration must report conflicts instead of resolving them silently.
- `DASH.PLOT_ROLES` is a hand-written copy of the role list and a test pins it, so both must change together. differentiation must be made between min and sub plots.
- Markdown export and import round-trip every schema field, so removed fields affect old exported files.
