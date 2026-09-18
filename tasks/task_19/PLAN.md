# Re-Alignment Plan: `sqlite-migration` → `dev` Storage Contract

## Purpose
Fix the regressions introduced by the SQLite migration so that the new implementation
matches the storage contract defined by the `dev` branch (the working original).

## Rules (apply to every task)
1. READ the task file section, the relevant spec section, and the actual code it touches.
2. VERIFY against code before editing. If code contradicts task or spec, STOP and flag.
3. IMPLEMENT the task.
4. CHECK-MARK the task file and append a one-line completion note.
5. After all tasks in a phase are done, append a brief phase summary.
6. If a blocker is encountered that cannot be resolved simply and is non-blocking, 
   make a note in `### Deferred Issues` and move on.

## Good Practice
- **Naming:** after a rename/refactor, the name describes what the code IS NOW.
  No `old_`, `_legacy`, `_bak`, `_deprecated` in names.
- **No historical-reference comments** that contradict the new code.
- **No legacy code, unused imports, dead functions** — remove them as part of the 
  task that makes them dead.
- **No compatibility guards.** App is pre-publication.

---

## Phase 0: Data Integrity (foundational — derived fields depend on clean data)
- [ ] **Task 1**: Fix `relationships` round-trip corruption
  - Store label+feeling as JSON in relation note, parse on denormalize, reconstruct on export
- [ ] **Task 2**: Fix `arc_beats_list` shape (lean objects, not bloated entity dicts)
  - Emit `{id, label, scene, shift, y, order, is_crisis, is_climax}` — exactly what old dashboard reads
- [ ] **Task 3**: Fix character/location `scenes` shape
  - `{id, title, heading}` objects, not `[to_id, note]` dicts

## Phase 1: Missing Derived Fields (dashboard structure panels)
- [ ] **Task 4**: Add `scene.arc_beats` (reverse from arc entities)
  - `{character, beat_id, label, y, is_crisis, is_climax}` per beat
- [ ] **Task 5**: Add `sequence.scenes_list`, `scene_count`, `plots`
  - `scenes_list[]`: scene IDs where parent_id = seq.id, sorted by order
  - `plots[]`: aggregated from scene.plots with beat flags
- [ ] **Task 6**: Add `act.sequences_list`, `scenes_list`, `sequence_count`, `scene_count`, `plots`
  - Same patterns as sequence, applied to acts
- [ ] **Task 7**: Fix `scene.plots` — include beat info
  - Change from `[plot_id_strings]` to `[{id, beat}]` objects

## Phase 2: Project Counts & Stats
- [ ] **Task 8**: Add project count fields (scene_count through arc_count)
- [ ] **Task 9**: Fix `structural_stats.plotCoverage` (currently empty array)
  - Compute per-plot scene coverage stats
- [ ] **Task 10**: Fix `project.act_count` (max of declared vs actual)

## Phase 3: Performance & Cleanup
- [ ] **Task 11**: Fix scene.characters reverse lookup performance
  - O(n) scan → build reverse lookup once from rel_rows
- [ ] **Task 12**: Fix `unfilled_fields` to check status column for scene/sequence/plot

## Phase 4: Arc ID Format (breaking change — DISCUSS WITH USER)
- [ ] **Task 13**: Decide arc ID format (composite `kael-1` vs simple `1`)
  - Dashboard works either way; affects external references and migration

---

## Files Touched Summary
| File | Tasks |
|------|-------|
| `core/db.py` | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 |
| `core/entity.py` | 1 |
| `tools/story_export.py` | 1 |
| `tools/story_import.py` | 10, 13 |

## Verification Strategy
After each phase, run the dashboard and compare against `git show dev:src/dashboard/story-dashboard.html`
to verify the JSON injection shapes match the old contract.
