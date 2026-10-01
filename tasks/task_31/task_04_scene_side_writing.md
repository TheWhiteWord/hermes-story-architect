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

- [ ] `plot_roles` in the scene schema; `computed: True` on the plot's five role fields
- [ ] `role` validated against `PLOT_ROLES`
- [ ] `plot_role_relations()` helper exists in `entity.py`, used by scene create
- [ ] Scene edit deletes `WHERE to_id=? AND kind LIKE 'plot_%'` then re-inserts
- [ ] Delete sweep removes a soft-deleted plot's `plot_*` rows (with the restore caveat commented)
- [ ] Missing plot / invalid role refused, message names the offender
- [ ] `story_export` rebuilds `plot_roles` onto the **scene** note; plot note no longer emits the 5 computed fields
- [ ] Export→import round-trip test added (silent-loss failure mode)
- [ ] Plot-side write path for the five fields gone; grep confirms
- [ ] 5 new tests written; two of them fail without the fix
- [ ] Existing tests that write the five fields updated to expect a read-only refusal
- [ ] Dashboard untouched and still correct
- [ ] `story_retrieve` can still read a plot's roles (verified, not assumed)
- [ ] Full suite green
- [ ] No compat shim, alias, or dual write path