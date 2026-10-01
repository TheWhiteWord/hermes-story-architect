# Phase 2 — One source for the role vocabulary

**Phase 2 of 7.** Starts only after `task_01_fix_dict_to_row.md` is complete.
No parallel work. See `INTEGRATION.md`.

## What this phase is for

`PLAN.md` §4 found the same role list hand-written in **six** places. Adding a role means
editing all six, and missing one is a silent dashboard bug rather than an error. This phase
removes the duplication so phase 3's rename and phase 4's new role are one-line changes.

No user-visible behaviour change. No rename yet — that is phase 3.

## Verified: the six sites

| # | site | shape |
|---|---|---|
| 1 | `core/db.py:707-714` | `if kind == "plot_setup": … elif …` — unfilled map |
| 2 | `core/db.py:996-998` | `kind in (...)` then `kind.replace("plot_","")` — scene→plot reverse lookup |
| 3 | `core/db.py:1109-1112` | four `_normalize_beats(rel_map…)` calls |
| 4 | `core/entity.py:223-228` | `_RELATION_FIELDS["plot"]` — the authoritative field→kind map |
| 5 | `tools/story_import.py:505` | field/kind tuple pair |
| 6 | `tools/story_export.py:170-171` | field/kind tuple pair |

Plus the JS renderers, `entity-panels.js:27-30` and `529-532` (`has_*` flags).

## Wrong assumption found while verifying this phase

`INTEGRATION.md` proposed deriving everything from a single `PLOT_ROLES` list. **That does
not work.** Field names are not the plural of role names:

```
setup       -> setups          ok
complication-> complications  ok
crisis      -> crisiss         WRONG (field is `crisis`)
climax      -> climaxs         WRONG (field is `climax`)
resolution  -> resolutions     ok
```

`crisis` and `climax` are singular field names. A naive `role + "s"` produces keys that
exist nowhere, and the reads silently return empty. Low impact, resolved here.

**Resolution: the field↔role mapping stays explicit; only the *iteration* is derived.**
`_RELATION_FIELDS["plot"]` (`entity.py:223-228`) already *is* that mapping — field name to
`(kind, is_list)`. It is the one place the vocabulary is written by hand. Everything else
must derive from it rather than restate it.

## What to do

1. In `core/constants.py` add `PLOT_ROLES` — **the 4 roles that exist at this phase**
   (`setup, crisis, climax, payoff`), declared as a literal list, plus a **test** asserting
   it matches `_RELATION_FIELDS["plot"]` exactly. The test is what prevents drift; a comment
   would not.

   It cannot be derived: `constants` cannot import `entity` (entity imports constants), so
   the import would be circular. Hence literal + test.

   Phase 3 adds `complication`/`resolution` to this same list. That phase owns the list
   growing to 5 — do not pre-add roles here, they do not exist yet.
2. `db.py:707-714` — replace the four-branch `elif` chain with a loop over the
   field/kind mapping. The unfilled map keys on the **field** name, so this one iterates
   `_RELATION_FIELDS`, not `PLOT_ROLES`.
3. `db.py:996-998` — already derives the role via `kind.replace("plot_","")`; keep that, but
   take the kind set from the mapping instead of the inline tuple.
4. `db.py:1109-1112` — replace four near-identical assignments with a loop over the mapping.
5. `db.py:1259-1271` and `1299-1310` — the `has_*` flags. Currently four hardcoded keys
   initialised `False` plus four `elif beat == …` assignments, duplicated verbatim for
   sequence and act. Derive: `{f"has_{role}": False for role in PLOT_ROLES}` and
   `seq_plots[pid][f"has_{beat}"] = True` inside one loop. **This is the substantive win** —
   it is the duplication that makes a new role cost 4 edits.
6. `story_import.py:505` / `story_export.py:170-171` — derive the `(field, kind)` pairs from
   the mapping instead of restating the tuple. Both are already loops; only the tuple is
   duplicated.
7. JS `entity-panels.js:27-30` and `529-532` — these read `has_*` off the payload, so they
   keep working untouched. Only if the payload key shape changes would they need editing;
   it does not. **Verify, do not assume** — if `has_*` naming is unchanged, leave the JS
   alone (that is phase 7's file, not this phase's).

## Legacy / obsolete code to clear

- The inline kind tuples at `db.py:996`, `story_import.py:505`, `story_export.py:170-171` —
  replaced by iteration, not kept as a default.
- Nothing is deprecated here; this phase only removes restatements.

## Tests

- **New, required:** `PLOT_ROLES` equals the roles derived from `_RELATION_FIELDS["plot"]`,
  as a set, and has **4** entries at this phase. This is the drift guard — phase 3 updates
  both sides and the count to 5.
- **Extend:** assert a plot with roles in **all four** fields produces all four `has_*`
  flags on both its sequence and its act rows. Written before the refactor it will fail on
  the hardcoded four-flag version — which is the point.
- `tests/test_phase2_db_reads.py:207` (`test_plot_has_setups`) keeps working; do not touch.

## Notes

- Direction unchanged (`PLAN.md` §3). This phase touches readers only, no writer, no schema.
- If deriving a loop turns out to need a per-role special case, that is a signal the mapping
  is wrong — stop and raise it rather than adding the branch.

## Checklist

- [ ] `PLOT_ROLES` declared in `constants.py`, 4 entries (phase 3 grows it to 5)
- [ ] Drift test asserts `PLOT_ROLES` == roles in `_RELATION_FIELDS["plot"]`
- [ ] `db.py:707-714` unfilled map is a loop, not four `elif`s
- [ ] `db.py:1109-1112` is a loop, not four assignments
- [ ] `has_*` flags derived from `PLOT_ROLES` at **both** `db.py:1259` and `db.py:1299`
- [ ] `story_import.py:505` and `story_export.py:170` derive their pairs from the mapping
- [ ] No inline `plot_setup`/`plot_crisis`/`plot_climax`/`plot_payoff` tuple left outside `_RELATION_FIELDS`
- [ ] Four-role `has_*` test added (fails before the refactor); phase 3 extends it to five
- [ ] JS confirmed unaffected; left untouched if so
- [ ] Full suite green
- [ ] No compat shim or alias