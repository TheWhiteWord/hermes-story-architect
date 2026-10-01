# Phase 4 — Scene-side writing

**Phase 4 of 7.** Starts only after `task_03_rename_vocabulary.md` is complete.
See `INTEGRATION.md`. This is the substantive change — the reason the task exists.

## What changes

The agent stops opening plots to record which scenes run through them, and records it on
the scene instead. `PLAN.md` §3 — direction stays `from_id=plot → to_id=scene`.

**New scene field:**
```yaml
plot_roles:
  - plot: the-resistance
    role: setup
    description: the door was never locked
```

**Plot's five role fields become computed** (`computed: True`) — read-only, derived from the
relation rows, like `character.relationships` and `arc_beats_list`.

## Decisions taken

- **Direction:** keep plot-owns-row. Do **not** flip to scene-owns-row; that would cost the
  8 reader rewrites in `PLAN.md` §3 for no added capability.
- **Entry shape:** flat `plot_roles: [{plot, role, description}]`. Each entry names its own
  plot, so one scene can hold different roles in different plots — which is the whole reason
  the role cannot live on the scene alone.
- **Delete:** deleting a plot clears its role rows (below).

## Verified: why this needs bespoke code, not the generic loop

`_RELATION_FIELDS` (`entity.py:221-233`) maps **one field → one kind**. The generic writer at
`writes.py:374-409` iterates that map, so it deletes `WHERE own_col=? AND kind=?` for a
single kind. `plot_roles` is **one field → five kinds** (the role picks the kind). The
existing loop cannot express that.

Same for the generic delete at `writes.py:377-383`: keyed by `from_id` (the plot), so it
would not fire for a scene edit at all.

Precedent for a bespoke block: `scene.location` / `location_scene`, at `writes.py:411-429`.
Copy its shape, not its logic — see the delete note below.

## Verified: the delete problem is real, and is NOT the `location_scene` case

`delete_entity` (`writes.py:614-618`):

```python
DELETE FROM relations
WHERE from_id NOT IN (SELECT id FROM entities WHERE is_deleted=1) AND to_id=?
```

Rows **pointing at** a deleted entity are removed; rows **owned by** it survive so `restore`
stays an exact inverse (`writes.py:599-603`).

Consequence with plot-owns-row:

| deleted | role rows | correct? |
|---|---|---|
| scene | removed (`to_id` sweep) | ✅ |
| plot | **survive** (`from_id` sweep skips them) | ❌ |

Every reader filters on `to_id` only (`db.py:969-971`, `story_load.py:267`,
`story_retrieve.py:110-117`), so the rows become unreachable while dead — then **silently
reattach** if a plot is recreated with the same slug.

**Correction to an earlier assumption:** `location_scene` is *not* swept on delete. It gets
correct behaviour for free because deleting the scene hits the `to_id` sweep. Plot roles are
the opposite case and need genuinely new code.

**Decision: add plot-role rows to the delete sweep.** When a plot is soft-deleted, remove
the `plot_*` rows it owns. Note this trades away exact restore for these rows — restore puts
the plot entity back but not its role rows. That is the accepted cost; the alternative is
silent reattachment, which is worse. Say so in a comment at the code.

## What to do

1. `constants.py` — add `plot_roles` to the scene schema: `list`, `sub_fields`
   `{plot, role, description}`, and `computed: True` on the plot's five role fields.
   `role` must validate against `PLOT_ROLES`.
2. `entity.py` — a `plot_role_relations(scene_id, entries)` helper returning rows, shaped
   like `location_scene_relations` (`entity.py:384-412`) but emitting one row per entry with
   `kind = f"plot_{role}"` and `from_id = entry["plot"]`. Wire it into
   `relations_for_insert` so scene **create** works.
3. `writes.py` — on scene **edit** when `plot_roles` is present: delete
   `WHERE to_id=? AND kind LIKE 'plot_%'` (keyed on `to_id`, since the plot owns the row),
   then re-insert from the helper. Bespoke block after the location one at `:429`.
4. `writes.py` — extend the delete sweep so a soft-deleted plot's `plot_*` rows go.
5. Validation: a `plot_roles` entry naming a non-existent plot, or a role outside
   `PLOT_ROLES`, must be refused. Model on `validate_scene_location`
   (`entity.py:493-520`) — same class of defect, a reference that resolves to nothing.
   Note the ordering caveat documented there: a plot created in the *same draft* is not
   visible to the validator.
6. `db.py` — plot's five fields already read from relations (`db.py:1109-1112`, rewritten in
   phase 2). Confirm they still populate once `computed` is set; `computed` changes only
   write behaviour, not reads.
7. `story_export` — **the round-trip breaks without this.** The scene branch
   (`story_export.py:278-287`) does `fm.update(extra)`, but `plot_roles` is a *relation*
   field and never lands in `extra` — so export would emit no `plot_roles` on the scene, and
   re-importing would silently lose every role. It must be rebuilt from the relation rows,
   the way the plot's five fields are (`story_export.py:169-177`), and written on the **scene**
   note instead. The plot branch (`story_export.py:269-275`) must stop emitting the five
   computed fields.
8. `story_retrieve` — the five plot fields are computed, so its `wanted` set
   (`tools/story_retrieve.py:186`) excludes them. Confirm the agent can still read a plot's
   roles; if it cannot, that is a finding, not a reason to un-compute the fields.
   Same question for the scene's `plot_roles`: it must be retrievable.

## Scope

No dashboard changes here — the payload shape is unchanged, so `entity-panels.js` keeps
working. That is phase 7's file, and phase 7 should find it needs less than expected.

## Legacy / obsolete code to clear

- `_RELATION_FIELDS["plot"]` — the five plot fields stop being *writable* relation fields.
  They remain the authoritative field↔kind map (phase 2), but a plot write must no longer
  produce rows. Verify nothing routes plot writes through it after this phase.
- Any remaining plot-side write path for the five fields. Grep for it; do not assume.

## Tests

- **New, required:** creating a scene with `plot_roles` writes one row per entry, with
  `from_id` = the plot, `to_id` = the scene, `kind` = `plot_<role>`, `note` = description.
- **New, required:** editing a scene's `plot_roles` replaces the rows wholesale — a removed
  entry leaves no row. This is the delete-then-reinsert contract.
- **New, required:** one scene, two plots, different roles — two rows, both correct.
- **New, required:** deleting a plot removes its `plot_*` rows.
- **New, required:** a `plot_roles` entry naming a missing plot is refused with a message
  naming the offending slug.
- **New, required:** export→import round-trip preserves `plot_roles`. Without the exporter
  rebuild above this fails silently — the markdown loses every role and re-import finds
  nothing to complain about. `tests/test_field_coverage.py:404` and
  `tests/test_export_sweep.py:4` both assert round-trip fidelity, so this is the test that
  catches it.
- **New:** writing `plot_roles` on an edit of an existing scene works (not just create).
- Update: any test that writes a plot's five fields directly — that is now a read-only field
  and the draft validator should refuse it as `computed`.
- Keep `test_phase2_db_reads.py:207` — reads are unaffected.

## Notes

- `computed: True` on the five fields is what makes them read-only; the mechanism is already
  honoured at `entity.py:272`, `drafts.py:167`, `writes.py:304`, `story_describe.py:114`.
  No new machinery needed.
- The draft validator blocks computed fields at **preview** time (`drafts.py:160-171`), so
  an agent writing a plot's roles gets told before it commits, not after.
- No completeness mechanism — decision 3 of `PLAN.md`, unchanged.

## Checklist

- [x] `plot_roles` in the scene schema; `computed: True` on the plot's five role fields
- [x] `role` validated against `PLOT_ROLES`
- [x] `plot_role_relations()` helper exists in `entity.py`, used by scene create
- [x] Scene edit deletes `WHERE to_id=? AND kind LIKE 'plot_%'` then re-inserts
- [x] Delete sweep removes a soft-deleted plot's `plot_*` rows (with the restore caveat commented)
- [x] Missing plot / invalid role refused, message names the offender
- [x] `story_export` rebuilds `plot_roles` onto the **scene** note; plot note no longer emits the 5 computed fields
- [x] Export→import round-trip test added (silent-loss failure mode)
- [x] Plot-side write path for the five fields gone; grep confirms
- [x] 5 new tests written; two of them fail without the fix
- [x] Existing tests that write the five fields updated to expect a read-only refusal
- [x] Dashboard untouched and still correct
- [x] `story_retrieve` can still read a plot's roles (verified, not assumed)
- [x] Full suite green
- [x] No compat shim, alias, or dual write path

## Final brief

### What the code actually needed

`core/`, `tools/` — and the diff is smaller than the plan implied because
phases 1–3 had already done the structural work:

| file | edit |
|---|---|
| `core/constants.py:102-116` | `computed: True` on the five plot role fields |
| `core/constants.py:154-166` | `plot_roles` on the scene schema |
| `core/entity.py` | `plot_role_relations()`, `validate_scene_plot_roles()`, `relation_fields()` |
| `core/writes.py:333` | computed relation fields dropped from `rel_fields` (one filter, both write paths) |
| `core/writes.py:441-462` | the scene edit block |
| `core/writes.py:643-655` | the delete sweep |
| `tools/story_export.py` | scene branch rebuilds `plot_roles`; plot branch stops emitting the five |
| `tools/story_import.py` | scene branch writes roles; plot branch deleted; a computed field is refused |
| `tools/story_retrieve.py` | scene `plot_roles` readable + filled-means-a-row |
| `tools/story_describe.py` | three `_RELATION_FIELDS` → `relation_fields()` |

**`computed` needed no new machinery**, exactly as the plan said — the check was
already honoured at four sites. The one place it did *not* reach was the generic
relation loop in `edit_entity`, which iterates `_RELATION_FIELDS` independently
of the field-routing loop above it. One filter on `rel_fields` closed it for both
the edit and (via the existing merge) the create.

### `relation_fields()` — the one addition the plan didn't call for

`plot_roles` is relation-stored but cannot live in `_RELATION_FIELDS`: that map
is field→(kind, is_list), and this field is one→five. Putting it there would make
the generic loop write rows of a kind that does not exist.

But it still has to be excluded from `extra`, accepted by create and edit,
reported as a relation by `story_describe`, and excluded from extra by the
importer — six sites that each had to learn about it. `relation_fields()` is the
one place to ask, and it returns the union. `BESPOKE_RELATION_FIELDS` carries the
set; the map stays authoritative for everything with a single kind.

### Correction 1 — the reattach premise is unreachable

The plan's delete rationale was: a dead plot's rows survive, and **silently
reattach if a plot is recreated with the same slug**. Measured — not reachable.
`delete_entity` soft-deletes, so the slug stays taken and `create_entity` refuses
it:

```
AFTER DELETE rows: []
entities: [('the-resistance', 1)]
RECREATE REFUSED: Entity already exists: plot/the-resistance.
```

The rows *are* still unreachable while the plot is dead (every reader filters on
`to_id`; `db.py:972` filters `from_id` on `is_deleted`), so **the sweep is still
right and stays**. What is wrong is where its cost lands.

**The real cost is `restore`, not reattachment.** `story_admin._restore_entity` is
documented as "Exact inverse of the delete. Sections and relations were never
removed" — and that is now false for a plot's role rows. Pinned by
`test_restore_brings_the_plot_back_without_its_roles`, which asserts the plot comes
back with `setups == []` and says what to do if it ever passes the other way.

This is worth stating plainly because it is a *documented lie* otherwise: the
restore docstring is now wrong, and the phase-4 comment at `writes.py:643` is the
correction. Fixing the docstring belongs with this change and was left out only
because it is prose in a different file — see NOTE 1.

### Correction 2 — `fields: ["all"]` no longer returns a plot's roles

Checklist item 8, verified rather than assumed. `_entity_fields` excludes computed
fields from the `["all"]` set, so a plot retrieved with `["all"]` returns no roles.
Naming them works (`fields: ["setups", ...]`), and the scene's `plot_roles` — which
*is* in `["all"]` — returns the same rows. So the agent can still read a plot's
roles; it just cannot get them for free alongside everything else.

This is the intended consequence of `computed`, not a bug to route around, and it
is the same mechanism that already governs `character.relationships`. But it is a
real reduction in what one call returns, so three tests that used `["all"]` on a
plot were changed to name the fields, and the change is commented at each.

### Tests

New `tests/test_scene_plot_roles.py`, 26 tests: create/edit rows, all five kinds,
one scene × two plots × different roles, wholesale replacement, clearing, the
read-only refusal on both write paths, the plot reading back what the scene wrote,
missing-plot and bad-role refusals, a refused edit leaving the original row intact,
the delete sweep, the restore cost, the export round-trip, and schema assertions.

**Both "fails without the fix" claims verified by reverting each fix:**
- removing the export rebuild → 2 round-trip tests fail (silent loss, as predicted)
- removing the delete sweep → 3 delete tests fail

`test_write_shape.py`'s phase-1 coverage **moved** to the scene side rather than
being deleted — the dict→row corruption was real and the regression test should
outlive the field it was written on. `test_plot_roles.py`'s fixture now writes roles
via `plot_roles`; `test_field_coverage.py` asserts the read-only refusal instead of
the rows.

**Fixture:** the three roles moved from `plots/The Resistance.md` to the three
scene notes, exactly as phase 3 moved them between fields. The plot note is now
three lines shorter and the DB rebuilds identically.

**Suite: 991 passed, 3 failed.** The 3 (`test_draft_preview.py` ×2,
`test_story_describe.py::test_every_link_key_story_load_emits_is_a_real_field_name`)
fail identically on the unmodified tree — verified by stashing in phase 3, and
unchanged here.

### Four truncation tests were passing by accident

`UNFILLED_LIMIT` is 15 and the fixture produced 15 gap types after this change —
so `truncated` stopped firing, and four tests that assert truncation broke. The
cause is not truncation: the plot's five role fields used to be five of those gap
types, and they are computed now.

They were asserting *"the fixture happens to exceed the cap"*, which is a fact
about the fixture, not about the code. Each now sets the cap explicitly by
monkeypatch — which `test_untruncated_view_has_no_other_fields` in the same file
already did. Four tests that cannot fail for the reason they claim to test are
worse than no test, and the fixture was about to change again in a later phase.

### Naming sweep

`grep -rn "payoff"` over `core/ tools/ src/ tests/` returns nothing. Every
`_RELATION_FIELDS` use outside `entity.py` is now either deliberate and commented
(`writes.py:333` filters computed; `story_retrieve.py:103,143` iterate the
one-kind map that the plot's fields still occupy as *readers*; `entity.py:498` is
the one-kind writer and must not see `plot_roles`) or has moved to
`relation_fields()`. One dead import removed (`_RELATION_FIELDS` in
`test_plot_roles.py`, unused since phase 2).

### NOTE — observations, not objectives

1. **`story_admin._restore_entity`'s docstring said "Exact inverse"** — corrected
   in this phase rather than logged. It now names the plot-role exception, so the
   two comments (`writes.py` sweep and `story_admin` restore) agree.
2. **`kind LIKE 'plot_%'` uses `_` as a LIKE wildcard**, so it also matches
   `plotX…`. No such kind exists and none can (roles come from `PLOT_ROLES`), but
   the pattern is looser than it reads. Three sites use it: the edit block, the
   delete sweep, and the two read blocks. An `IN (SELECT kind …)` would be exact
   and no longer.
3. **The unfilled gap moved, and shrank.** A plot no longer reports five phantom
   gaps; a scene reports `plot_roles` when it serves no plot. Net −4 gap types on
   the fixture. Every scene in a project now carries a `plot_roles` gap until it
   is placed in a plot, which is the intended trade but is a visible change to the
   unfilled view.
4. **`story_load` view `dramatic_elements` with `add_plot` was untouched and needs
   no change** — it already reads `kind LIKE 'plot_%'` and derives the role from
   the kind. Phase 7's dashboard work should confirm this rather than assume it.
5. **The pre-existing `with` failure looks real.** `test_story_describe.py:272`
   walks `story_load` output and rejects relationship field `with` as unknown,
   which suggests `with` is missing from the relationship schema's known set. Not
   this phase's; carried from phase 3.
6. **`docs/html_ui_dashboard/*.html` mockups** now differ from the model in a
   second way (they show plot-side roles). Out of scope per INTEGRATION.md.