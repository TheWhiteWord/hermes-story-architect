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

- [x] `PLOT_ROLES` declared in `constants.py`, 4 entries (phase 3 grows it to 5)
- [x] Drift test asserts `PLOT_ROLES` == roles in `_RELATION_FIELDS["plot"]`
- [x] `db.py:707-714` unfilled map is a loop, not four `elif`s
- [x] `db.py:1109-1112` is a loop, not four assignments
- [x] `has_*` flags derived from `PLOT_ROLES` at **both** `db.py:1259` and `db.py:1299`
- [x] `story_import.py:505` and `story_export.py:170` derive their pairs from the mapping
- [x] No inline `plot_setup`/`plot_crisis`/`plot_climax`/`plot_payoff` tuple left outside `_RELATION_FIELDS`
- [x] Four-role `has_*` test added (fails before the refactor); phase 3 extends it to five
- [x] JS confirmed unaffected; left untouched if so
- [x] Full suite green
- [x] No compat shim or alias

---

## Final brief

**Done.** The role vocabulary now lives in exactly two places: `PLOT_ROLES`
(`core/constants.py:16`) and `_RELATION_FIELDS["plot"]` (`core/entity.py:241`).
Everything else derives from them.

### What changed

| site | before | after |
|---|---|---|
| `core/entity.py` | — | `PLOT_BEAT_FIELDS` added, derived from `_RELATION_FIELDS["plot"]` |
| `core/db.py:707` | 4-branch `elif` chain | `elif kind in PLOT_FIELD_BY_KIND` + one lookup |
| `core/db.py:996` | inline 4-tuple | `elif kind in PLOT_FIELD_BY_KIND` |
| `core/db.py:1109` | 4 assignments | loop over `PLOT_BEAT_FIELDS` |
| `core/db.py:1259`, `:1299` | 4 hardcoded `False` + 4 `elif` per site | `{f"has_{r}": False for r in PLOT_ROLES}` + one `if beat in PLOT_ROLES` |
| `tools/story_import.py:503`, `story_export.py:170` | inline tuples | loop over `PLOT_BEAT_FIELDS` |
| `tools/story_import.py:469` | skip-set naming the 4 fields | `{"name","one_sentence","status","id"} | set(PLOT_BEAT_FIELDS)` |

`PLOT_FIELD_BY_KIND` in `db.py` is the one added derived view — the two
lookups there key on the relation *kind*, not the field, so it is not a rename
of the existing dict but a genuine second direction. Nothing else needed it.

**Not changed, deliberately:** `tools/story_load.py:259` already derives the
role from the kind via SQL (`kind LIKE 'plot_%'` + `replace`), so it never
restated the list. Left alone.

### Tests

New `tests/test_plot_roles.py`, 6 tests:
- **drift guard** — `PLOT_ROLES` == roles derived from `_RELATION_FIELDS["plot"]`,
  plus a count of 4 at this phase. Phase 3 changes both to 5.
- a test stating the field-name constraint (`crisis`/`climax` stay singular),
  so the reason the map is explicit survives the next reader.
- **four-role `has_*`**, parametrised over sequence *and* act, plus a test that
  the flag set is exactly `{has_<role>}` — no stale hardcoded flag survives.

Verified as a real guard, not a tautology: simulated phase 3 by adding
`complications`/`plot_complication` to the map and `complication` to
`PLOT_ROLES` — the flag tests fail (`act row missing has_complication`), and
pass again once reverted. Baseline 959 → **965 passed**.

JS: verified, not assumed. Extracted every `has_*` the JS reads and compared to
what the backend emits — identical set, and each `p.has_X` is paired with a
label `X` in both blocks. Payload key shape unchanged, so
`entity-panels.js` is **untouched**. (Phase 7 owns it.)

### Notes for the next phase

1. **`zip`-ing the two lists is a trap I hit while testing.** My first fixture
   paired fields to roles positionally; adding `complication` in the middle
   silently mispaired every scene. Now the pairing is derived from the kind.
   Phase 3 should do the same — never assume `PLOT_ROLES` and
   `PLOT_BEAT_FIELDS` are in the same order.
2. **Phase 3 checklist delta beyond the task file:** `story_import.py:469`
   (the skip-set) is now derived, so INTEGRATION.md's warning about it is
   already handled — do not re-derive it there. `PLOT_ROLES` becomes 5 and
   `test_four_roles_at_this_phase` becomes 5; that test is the intended tripwire.
3. **`db.py` now imports `entity` at module level** (it only ever imported
   `unfilled_fields` lazily inside a function). No cycle — `entity` imports
   `db` only inside functions — verified by import and by the suite. Worth
   remembering if `entity` ever grows a module-level `db` import.
4. **Unverified, pre-existing, out of scope:** `test_field_coverage.py:445-457`
   and `test_write_shape.py:107-112` hardcode kind strings. They are test
   fixtures for specific roles, not restatements of the vocabulary, and phase 3
   will have to touch them anyway for the rename. Left as-is.
5. `PLOT_ROLES` in `constants.py` sits between `PLOT_SCOPES` and `VALUE_ARCS`
   with a comment explaining why it cannot be derived. If phase 3 finds a way to
   derive it after all, delete the comment with it.