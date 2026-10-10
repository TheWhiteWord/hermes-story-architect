# Task 2: Migration script — one-time dry-run + apply

## Goal

Write a one-time migration script that converts existing projects from the old
milestone flags/pointers to the new plot-role system. The script is NOT part of
the application — it runs once against the repo fixture and the live test
project.

## Work

### 2.1 Script location

`tools/migrate_issue_a.py` — a standalone script, not a tool handler. Run with
`python -m tools.migrate_issue_a --project <path> --dry-run` or `--apply`.

### 2.2 Dry-run report

For each project, report:

1. **Scenes with `is_inciting_incident: True`** → these need an
   `inciting_incident` role in the main plot (if the main plot lacks one).
2. **Scenes with `is_story_climax: True`** → these need a `climax` role in the
   main plot (if the main plot lacks one).
3. **Scenes with `is_act_climax: True` or `is_sequence_climax: True`** →
   these are NOT carried over (position follows from the theory). Report them
   as "not migrated" so the user knows.
4. **Flag/pointer disagreements** → if `is_inciting_incident` is True but
   `project.inciting_incident_scene_id` names a different scene (or vice
   versa), report the conflict. Do NOT guess which is right.
5. **Missing main plot** → if no plot has `plot_scope: main`, report that
   story-level milestones cannot be migrated.

### 2.3 Apply mode

After dry-run approval:

1. For each scene with `is_inciting_incident: True`: add an `inciting_incident`
   role to the main plot's `plot_roles` for that scene (if not already present).
2. For each scene with `is_story_climax: True`: add a `climax` role to the
   main plot's `plot_roles` for that scene (if not already present).
3. Strip the removed fields from `extra`:
   - Scene: `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`,
     `is_story_climax`
   - Project: `inciting_incident_scene_id`, `story_climax_scene_id`
   - Act: `act_climax_scene_id`
   - Sequence: `seq_climax_scene_id`
4. The act/sequence flags and pointers are NOT carried over — they are simply
   removed.

### 2.4 Idempotency

- Running the migration twice must be a no-op the second time.
- Importing old markdown files that still contain removed keys must be
  tolerated with a warning (verify in `tools/story_import.py`).

### 2.5 Tolerance in `story_import.py`

- In `_extra_for`, when building the `extra` dict, silently drop any of the
  removed keys (`is_inciting_incident`, `is_sequence_climax`, `is_act_climax`,
  `is_story_climax`, `inciting_incident_scene_id`, `story_climax_scene_id`,
  `act_climax_scene_id`, `seq_climax_scene_id`) with a warning printed to
  stderr. The import should not fail on old files.

## Checklist

- [x] Script created at `tools/migrate_issue_a.py`
- [x] Dry-run mode reports all five categories
- [x] Apply mode adds roles and strips fields
- [x] Idempotent (second run is no-op)
- [x] `story_import.py` tolerates old keys with warning
- [x] Script tested against `save-the-children` fixture
- [x] Full suite green (927/928 pass; 1 expected failure in `test_story_load_views.py::test_act_carries_its_own_climax_scene` — that test reads `act_climax_scene_id` from the `dramatic_elements` view, which is Task 3's scope to switch to the new plot-role readers)

## Completion summary

**`tools/migrate_issue_a.py`** — standalone migration script with `--dry-run` and `--apply` modes.

Dry-run reports five categories:
1. Scenes with `is_inciting_incident: True` → need `inciting_incident` role in main plot
2. Scenes with `is_story_climax: True` → need `climax` role in main plot
3. Scenes with `is_act_climax` or `is_sequence_climax` → reported as "not migrated"
4. Flag/pointer conflicts → reported without guessing which is right
5. Missing main plot → reported

Apply mode:
- Adds `plot_inciting_incident` / `plot_climax` relations to the main plot
- Strips all 8 removed fields from `extra` (scene flags, project pointers, act/sequence pointers)
- Idempotent: second run is a no-op

**`tools/story_import.py`** — `_extra_for` now silently drops the 8 removed keys with a stderr warning, so old markdown files import cleanly.

**Test results:**
- 927/928 tests pass
- 1 expected failure: `test_act_carries_its_own_climax_scene` reads `act_climax_scene_id` from the DB — that field is now stripped by the import tolerance. Switching the `dramatic_elements` view to read plot roles instead is Task 3's scope.
- Idempotency verified: second apply run reports "Nothing to migrate"
- Import tolerance verified: old keys dropped with warning, no import failure
