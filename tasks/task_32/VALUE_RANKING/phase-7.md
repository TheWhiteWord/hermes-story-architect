# Phase 7 — Fix the value-pass skill section for the new model

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §6 step 7.
Depends on: **Phase 6** (the `values` view + `value_focus` exist). Documentation only — no code.

Two files teach the old value model and both get fixed: the standalone draft `tasks/task_30/VALUE_PASS_SKILL_SECTION.md` **and** the real skill reference `tasks/task_30/skill/references/craft/value-pass.md`.

## Scope (corrected)

The skill tree is **not built yet** — do not author `skills/hermes-story-architect/SKILL.md` or a craft table. The skill tree **exists in draft** at `tasks/task_30/skill/` (SKILL.md + `references/`), and two files in it teach the **old** value model. Both are in scope; rewrite both to the new model.

## Files to fix (both teach the old model — verified)

1. `tasks/task_30/VALUE_PASS_SKILL_SECTION.md` — the standalone draft (was the only one I'd found).
2. `tasks/task_30/skill/references/craft/value-pass.md` — the real skill reference file. **Nearly identical content to the draft**, same old-model teaching. This is the one that would ship; fix it.

Both name `value_schemas`, `value_lines`, inline `schema`, and roll-up-by-reasoning — all invalidated by the refactor. Fix them together; the draft is the review copy of the reference file, so keep the two in sync (or fix the reference and let the draft defer to it).

## Verification against code — the old→new map (done)

Every passage in both files is contradicted by the new design:

| Line (draft / reference) | Old teaching | New model |
| --- | --- | --- |
| 19-21 / 11-14 | retrieve `value_schemas` + `value_lines` before writing | `story_load view='values' scene=<id>`: sequence/act `value_focus` + per-plot `last_left`/`next` |
| 45-47 / 37-39 | define a value by adding inline `schema` to the first turn | **create a `value` entity** (four distinct words), then name it in the turn — no inline schema |
| 48-50 / 40-42 | a schema for an existing plot value is refused | a turn naming an **unknown value** is refused; message lists defined values + words + "create the value first" |
| 54 / 46 | `from` defaults to last `to` in `value_lines` | read `last_left` from the scene view |
| 58 / 66-72 | compare neighbour `from`/`to` in `value_lines` after moves | re-read the plot's turns via the values view |
| 91 / 99-101 | roll sequence/act/story up from `value_lines` by reasoning | read computed `value_focus` (major/minor); reasoning is now only for the prose summary |
| 102-107 / 110-115 | "what the store checks" lists inline schema + `value_lines` | value entity exists; `from`/`to` are words of that value entity's p/c/cd/nn; effects/protagonist/conflict-level checks unchanged |

- **Still correct, keep as-is (both files):** "separate step, never part of creating the scene" (14-31 / 6-23); reuse/near-match rules (41-44 / 32-36); opening-states rules (52-63 / 44-54) once `last_left` replaces `value_lines`; the positive-side / earned-vs-naive / deepening reasoning (74-88 / 66-80); irony out-of-scope pending B3 (103-104 / 94-96); "record the plan in sections" (92-96 / 82-87).
- **One genuine workflow change:** the old "define-on-first-turn" becomes **check existing values first; if none fits, create the value entity, then record the shift** (plan §7).

## Tasks

### T7.1 — Rewrite the value-recording passages (both files)
- [ ] **Before recording:** replace the `story_retrieve value_schemas/value_lines` instruction with `story_load view='values' scene=<id>`. Keep the reuse/near-match rules. Replace "define by adding inline `schema`" with: check existing values (`story_load view='values'` no-args lists them); if none fits, **create the value** (`story_draft` create `value`, four distinct words) in the same draft as the scene edit (creates apply before edits, `drafts.py:22`), then name it in the turn.
- [ ] **What the store checks:** rewrite the checks list — plot exists; the value names an existing value entity (else refused, message lists defined values + words + create-first); `from`/`to` are words of that value entity's four rungs; effects non-empty, one per protagonist, each with one valid conflict level; drop every mention of inline `schema`, `value_schemas`, `value_lines`.
- [ ] **Opening states:** "`from` defaults to the last recorded state" → read `last_left` from the scene view. Keep the "open elsewhere only when the scene shows it" rule and "say which in effect."
- [ ] **After inserting/moving/deleting:** replace "compare in `value_lines`" with re-reading the plot's turns through the values view.
- [ ] **Roll-up and irony:** replace "summaries read from `value_lines` by reasoning" with: read `value_focus` for major/minor at sequence/act/story; the entity's **sections** still hold the prose summary. Keep irony-out-of-scope.

### T7.2 — Add the new workflow beats the plan names (both files)
- [ ] **Before writing into a sequence or act:** read `value_focus` (`story_retrieve(fields=['value_focus'])`) to see which values are major/minor there and weigh the scene's shifts against them. Short "Planning" bullet.
- [ ] **Create-then-record** as the explicit rule.

### T7.3 — Consistency sweep
- [ ] Grep both files for `value_schemas`, `value_lines`, `view="story_value"`, `value_at_open/close/shift`, `y`, `schema` — every hit updated to the new model or confirmed as the untouched **character/arc_beat** B3 track.
- [ ] Keep the two files in sync (the draft is the review copy of `skill/references/craft/value-pass.md`); simplest is to fix the reference file and have the draft defer to it.
- [ ] The draft's "Placement" note (117-137) targets files not in the tree yet — leave as-is, it documents intent.

## Cleanup / legacy
- [ ] The draft's supersession list targets files that don't exist in the repo yet. Leave it — do not chase files that aren't there.

## Checklist
- [ ] both files (`VALUE_PASS_SKILL_SECTION.md` + `skill/references/craft/value-pass.md`) rewritten to the new model
- [ ] "what the store checks" matches the Phase 4 validator
- [ ] create-then-record rule + value_focus-before-write beat added
- [ ] both files grepped clean of old-model names (outside the B3 track) and in sync
- [ ] placement note intact; no skill-tree authoring

## Notes for the implementer
- **Depends on Phase 6** (the view/`value_focus` names it teaches must exist). Parallel-safe with Phase 8.
- This is the only skill artifact in scope. When the skill tree is eventually built, this file becomes `references/craft/value-pass.md` and its craft-table row is added then — not now.
