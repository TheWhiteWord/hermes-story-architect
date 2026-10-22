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
- [x] **Skipped per user decision (Phase 8 kickoff).** Both conversions are single-plot, one/two values, no cross-plot merge — a hand-written `values.md` is the whole migration. The merge rule (identical → one; conflict → stop) is enforced on every write path (`validate_value`, `story_import._import_values`) and pinned by `test_values_export_import.py`, so a one-time script would duplicate live code and be deleted after use (this task's own cleanup rule). Not needed.
- [x] `id = slug(name)` — enforced by `validate_value` + `_import_values` ("id is the slug of its name" refusal).
- [x] Dry-run mode: `story_import dry_run` reported "nothing would be destroyed" before the confirm import (project rule: destructive imports dry-run first).
- [x] `value_turns` untouched — they resolve by name after Phase 4 (verified: all 6 live scenes' turns survived the re-import).

### T8.2 — Convert the fixture (`tests/fixtures/save-the-children/`)
- [x] **Done in Phase 4** (implementer note: never leave the branch red). `values.md` exists at the fixture root with `freedom` and `trust`; `value_schemas` stripped from `plots/The Resistance.md`.
- [x] Re-import clean: fixture imports succeed, 3 scenes' turns validate against the new entities (suite green, 1157 passed).
- [x] `expected_output.json` — it snapshots the **Fountain screenplay parser** output (`title_page`, `tokens`, `scriptHtml`, scene durations), not the story DB. Grepped: it contains zero `value`/`value_turns`/`value_schemas` keys. Nothing to regenerate.

### T8.3 — Convert the live project
- [x] `story_backup` first: `story_20261013_042708.db`.
- [x] Hand-wrote `values.md` (one value: `trust`) at the project root; stripped `value_schemas` from `plots/The Resistance.md` (kept `value_arc: Maturation`).
- [x] `story_import` dry-run ("nothing would be lost") then `confirm` — the DB now matches the converted markdown. **One surprise:** the first confirm import (run before the Hermes restart) still left the DB without the `trust` value entity — the running tool process held the pre-sync code in memory. After the restart, a second confirm import on the synced code imported the value correctly. Root cause: the tool modules were loaded at session start; the sync landed on disk mid-session. Fixed by re-running the import after restart, not by changing code.
- [x] Verified via the live tools: `story_retrieve value/trust` returns the full schema; `story_retrieve plot/value_focus` = major: trust×6 scenes, minor: []; act-2 = trust×4; project = trust×6; `story_load view='values'` (no args) lists `trust` with its four rungs; `view='values' scene=the-core-day` shows `last_left` (the-door-closes, self-trust) and no `next` (it is the last scene); all 6 scenes' turns survived intact.
- [x] Sanity confirmed at sequence level too: `scene=central-room-day` shows `sequence_focus`/`act_focus` = trust×2 with `next` = central-room-night.

### T8.4 — Tests + full verification
- [x] Full suite green: **1157 passed, 0 failed** (the 2 pre-existing ordering failures named in the task do not exist on this branch — the Phase 4 note records the same baseline: 1123 passed at Phase 4, now 1157 with the later phases' tests).
- [x] Round-trip on the fixture: export → import → export is stable — `TestIdempotence`/`TestRoundTrip` in `test_values_export_import.py` pass (files_removed == [] across three exports; fields/sections survive exactly).
- [x] Grepped `core/ tools/ src/ tests/` for `value_schemas`, `value_lines`, `compute_value_lines`, inline `schema` on turns — nothing left. The only remaining name is the new view's private helper `_value_schemas` (reads the value entities — the replacement, not a leftover).

## Cleanup / legacy
- [x] The migration script was never created (T8.1 skipped), so nothing to delete. Both data holders now live only in `values.md`; `plot.value_schemas`/`value_lines` exist in no live tree.
- [x] `tests/live_value_pass.py` deleted — it drove the old model (wrote `value_schemas` onto the plot note, read `value_lines` back). Its migration work is done (the live project now carries `values.md`), and a `__main__` harness testing removed behavior is not kept. `tests/value_pass_b1_b2.py` was already deleted in Phase 4.
- [x] Fixed a broken docstring left by the deletion sweep in `tools/story_load.py:436` (`_value_schemas` lost its opening line when an earlier patch removed the first sentence; restored as "Value name to schema, read from the value entities.").

## Checklist
- [x] migration script: **skipped** (user decision; merge rule already enforced on the write paths, one value per defining plot)
- [x] fixture converted (values.md + plot stripped); re-import clean; turns validate; expected_output.json needs no regeneration (Fountain-parser fixture, zero value keys)
- [x] live project backed up, converted (values.md + value_schemas stripped), re-imported (dry-run then confirm); value_focus + values view sane (verified through the live tools post-restart)
- [x] full suite green (1157 passed, 0 failed)
- [x] repo grepped clean of the three removed names outside history (only the new view's `_value_schemas` helper remains)
- [x] migration script never created (so nothing to delete); `tests/live_value_pass.py` deleted

## Notes for the implementer
- **Depends on every prior phase.** Run last. Not parallel. — satisfied: Phases 1-7 all landed before this phase.
- **Live DB guard:** `story_import` hard-refuses retired B1/B2 keys — the live tree carried none (grep clean of `value_at_open`/`value_at_close`/`shift`/`y`/`conflict_levels`/`story_value` on all notes). Backups taken twice (pre-conversion + the importer's own).
- **Mid-session tool staleness:** the plugin sync landed while the session's tool modules were already imported, so the first confirm import ran the old code (no `_import_values`). The fix was a re-run after restart, not a code change — worth remembering when verifying live conversions in the same session as a sync.

---

## Final brief (Phase 8 complete)

**What changed.** The live project is converted and the phase's cleanup is done. Two files touched in the repo (one deletion, one docstring fix); the live project's notes carry the conversion.

- **Live project** (`browser-verification-test`): `values.md` written with `trust` (p:self-trust / c:doubt / cd:suspicion / nn:self-deception + note); `value_schemas` stripped from `plots/The Resistance.md`. Backed up (`story_20261013_042708.db`), dry-run import clean, confirm import — the `trust` value entity now lives in the DB and every one of the 6 scenes' turns resolves against it by name.
- **Fixture**: already converted in Phase 4 (verified this phase: `values.md` with `freedom`/`trust` present, plot note clean, suite green).
- **Repo cleanup**: `tests/live_value_pass.py` deleted (old-model harness, its migration work done); a broken docstring on `_value_schemas` (`tools/story_load.py:436`) restored.

**Verified by running, not by reading.** Live tools post-restart: `story_retrieve value trust` → full schema; `plot.value_focus` → major trust×6; `act-2.value_focus` → trust×4; `project.value_focus` → trust×6; `story_load view='values'` → lists `trust` with all four rungs; `view='values' scene=the-core-day` → `last_left` (the-door-closes → self-trust), no `next` (last scene); `scene=central-room-day` → sequence/act focus trust×2, `next` = central-room-night. Suite: **1157 passed, 0 failed**. Grep for `value_schemas`/`value_lines`/`compute_value_lines` across `core/ tools/ src/ tests/` is clean — the only surviving name is the new view's private `_value_schemas` helper, which reads the value entities (the replacement, not a leftover).

**Skipped (with reason).** T8.1's migration script — both conversions are one defining plot each with no cross-plot merge, so a ~100-line script with a merge rule would be written, used once, and deleted per this phase's own cleanup rule. The merge/validation rules it would implement already run on every write and import path (`validate_value`, `_import_values`) and are pinned by `test_values_export_import.py`. If a future project has multiple plots defining the same value name with differing words, the conflict path is "refuse and let a human resolve" — already the live behavior. `expected_output.json` regeneration — the file snapshots the Fountain screenplay parser (`scriptHtml`, scene durations), not the story DB; it contains zero value keys.
