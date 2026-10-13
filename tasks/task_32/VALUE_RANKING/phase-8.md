# Phase 8 — Migrate the fixture and the live project

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §6 step 8.
Depends on: **Phases 1-7 all landed** (schema off the plot; value entities exist and round-trip). This is the last phase — it converts the two data holders and makes the suite green end to end.

Move each plot's `value_schemas` into `values.md`, merging identical ones. No backward compatibility (project rule): after Phase 4, a plot note still carrying `value_schemas` is **refused on import** (unknown plot field), so the fixture and the live project must be converted or they cannot be imported at all.

## Verification against code — the two migration sources (done)

**Fixture — `tests/fixtures/save-the-children/`:**
- `plots/The Resistance.md` (main) carries `value_schemas` with **two** values: `freedom` (p:free/c:dependent/cd:imprisoned/nn:gilded cage) and `trust` (p:open/c:wary/cd:deceived/nn:exploited), each with a `note`.
- `plots/The Scientists Last Stand.md` (sub) has **no** `value_schemas` → nothing to migrate from it.
- Scenes `Central Room - Day.md`, `Central Room - Night.md`, `The Core - Day.md` carry `value_turns` naming `freedom` and `trust` on `the-resistance`, with `from`/`to` drawn from those schemas. **No inline `schema` on any fixture turn** (the two schemas are registered on the plot). So the fixture needs: 2 value entities + strip `value_schemas` from the plot note. The turns stay untouched — after Phase 4 they resolve against the new value entities by name.
- Merge check: only the main plot defines values, so no cross-plot merge is needed in the fixture. (The merge rule still applies generally — see the script.)

**Live project — `/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test/`:**
- Main plot `the-resistance` carries **one** schema: `trust` (p:self-trust/c:doubt/cd:suspicion/nn:self-deception, note "Whether Kael can trust their own read of the world.").
- Sub plot `the-scientists-last-stand` has **no** schemas.
- 6 scenes carry `trust` turns on `the-resistance`; **no inline `schema`** on any turn.
- After Phase 4 the live DB still holds `plot.value_schemas` in `extra`. Since the field is gone from the schema, it is inert on read — but a re-import from markdown (which no longer exports it) is the clean path. **`story_import` is destructive and hard-refuses retired B1/B2 keys** (memory), so confirm the live tree is free of them before importing.

## Tasks

### T8.1 — One-time migration script (`tools/migrate_values.py`, new)
- [ ] Reads each plot's `value_schemas` (from the DB, or from the plot note if run pre-import) and emits `value` entities into the project's `values.md`.
- [ ] **Merge rule:** two schemas naming the same value (case-insensitive) must be identical → one value entity; identical words but different `note` → keep one, and if notes differ, keep the first and emit a warning (do not silently pick). Differing words for the same value name → **stop and report** — that is a real conflict a human must resolve, never auto-merge.
- [ ] `id = slug(name)` (the Phase 2 invariant), four distinct words validated.
- [ ] Strips `value_schemas` from the plot notes it touches (fixture) — or, for the live project, relies on Phase 4 making it inert + a clean re-export.
- [ ] Dry-run mode: prints the values it would create and the plots it would strip, changes nothing. **Run dry-run first** (project rule: destructive imports dry-run first).
- [ ] Leaves `value_turns` on scenes untouched — they resolve by name after Phase 4.

### T8.2 — Convert the fixture (`tests/fixtures/save-the-children/`)
- [ ] Run the script (or hand-edit — it is two values) to create `values.md` at the fixture root with `freedom` and `trust`.
- [ ] Remove the `value_schemas` block from `plots/The Resistance.md`.
- [ ] Re-import the fixture; `story_import` must succeed (no unknown plot field). Confirm the 3 scenes' turns still validate against the new value entities.
- [ ] Update `tests/fixtures/save-the-children/expected_output.json` if it snapshots `value_schemas`/`value_lines` — regenerate from the real importer, do not hand-edit (project rule: ground truth from the real parser).

### T8.3 — Convert the live project
- [ ] `story_backup` the live project DB first.
- [ ] Run the script dry-run, then real: create `values.md` (one value: `trust`), strip nothing from notes needed beyond what re-export handles.
- [ ] Re-run `story_export` then `story_import` (dry-run, then `confirm`) so the DB matches the converted markdown. Confirm the 6 scenes' `trust` turns survive and validate.
- [ ] Sanity: `story_retrieve` the main plot / an act / the project with `fields=['value_focus']` returns sensible major/minor; `story_load view='values' scene=<id>` shows `last_left`/`next`.

### T8.4 — Tests + full verification
- [ ] Full suite green: **no failures** (the 2 pre-existing ordering failures — decide with the user whether they are in scope; if left, they must be the *only* failures and documented). The Phase 4 fixture-refusal red state is now resolved.
- [ ] Round-trip on the fixture: export → import → export is stable (idempotent).
- [ ] Grep the repo for `value_schemas`, `value_lines`, inline `schema` on turns — nothing left outside `tasks/` history and this VALUE_RANKING folder.

## Cleanup / legacy
- [ ] This phase **is** the legacy cleanup: the two data holders move to `values.md`. After it, `plot.value_schemas` exists in no live tree, and the migration script has served its purpose — delete `tools/migrate_values.py` once both conversions are done (it is a one-time tool, not a kept migration path; project rule: no backward-compat layers).
- [ ] `tests/live_value_pass.py` and `tests/value_pass_b1_b2.py`: if they drive the old inline-schema model, delete them (replacement, not refactor — the behavior they test is gone). Check first; keep any that only exercise effects/conflict-levels.

## Checklist
- [ ] migration script: merge rule (identical → one; conflict → stop), dry-run, id=slug(name)
- [ ] fixture converted (values.md + plot stripped); re-import clean; turns validate; expected_output.json regenerated from the real importer
- [ ] live project backed up, converted, re-imported (dry-run then confirm); value_focus + values view sane
- [ ] full suite green (only any agreed pre-existing failures)
- [ ] repo grepped clean of the three removed names outside history
- [ ] migration script deleted after use; obsolete live/value-pass test scripts removed if they test the old model

## Notes for the implementer
- **Depends on every prior phase.** Run last. Not parallel.
- **Live DB guard:** `story_import` hard-refuses retired B1/B2 keys — before importing the live project, confirm its tree carries none, or the import fails outright. Back up first regardless.
- The merge conflict case (same value name, different words across plots) is the one place a human decision is required; the script must **stop and print**, never guess. In both current data sets it does not arise (one defining plot each), but the script is written for the general case.
