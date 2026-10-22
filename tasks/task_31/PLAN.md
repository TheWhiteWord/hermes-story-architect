# Task 31 — plot role: verification + implementation plan

Status: plan ready for implementation. Nothing implemented yet.
Source proposal: `PLOT-POSITION-PROPOSAL.md`.

**Decisions taken (this session):**
1. Plot roles are the 5 dramatic roles: `setup, complication, crisis, climax, resolution`.
   `transition` / `non-event` are never plot roles.
2. `payoffs` → `resolutions`; new `complications` role added. Plot vocabulary and
   `scene.dramatic_role` are now the same 5 values.
3. **No completeness mechanism.** Not computed, not a gap check, not a declared-role list.
   Whether a plot is finished is a judgement the agent (and user) makes and states. The
   schema records no opinion about it.
4. Terminology: a plot's slot is a **role** — the same word as `scene.dramatic_role` and the
   `"role"` key `story_load` already emits. "Beat" is story-level (`arc_beat`) and is not used
   for plot vocabulary anywhere in this change.

   Considered and rejected: **position**. The codebase already calls this a role in two
   places (`constants.py:140`, `story_load.py:271`, and the prose at `story_load.py:41` —
   "which plots run through a scene, and in what role"), so "position" would be a third word
   for one concept. It also fixes a live inconsistency: `story_load` emits `role` while the
   dashboard reads `beat` (`entity-panels.js:431`) — renaming to `role` makes the two agree.

---

## 1. Premises from the proposal, checked against the code

| # | Claim | Verdict |
|---|---|---|
| 1 | `plot.setups/crisis/climax/payoffs` are written on the plot | **True.** `core/entity.py:223-228` → `plot_setup/plot_crisis/plot_climax/plot_payoff` rows, `from_id=plot`, `to_id=scene`. |
| 2 | Membership must be a triple (scene, plot, role) | **True and already stored.** Role is the relation `kind`; PK is `(from_id,to_id,kind)` (`core/db.py:25-31`). A scene at two roles in one plot is two rows today. No schema change. |
| 3 | `dramatic_role` and plot roles are one vocabulary | **False in code** — 3-value overlap, `complication` has no slot, `resolution`≠`payoffs`. Fixed by decision 2. |
| 4 | `note` must be promoted or a column added | **Moot.** `relations.note TEXT` exists (`core/db.py:28`) and already carries the role's prose on `plot_setup`/`plot_payoff` rows. |
| 5 | Five plot fields become computed, read-only | Superseded by decision 3 — no completeness mechanism at all. |
| 6 | Writing happens scene-side | Adopted. See §3. |
| 7 | `is_*_climax` flags stay unconnected to plots | No code impact either way. |

## 2. Bug found while verifying — real, and fixed for free by this change

`relations_for_insert` (`entity.py:442`) special-cases the dict form for **only**
`plot_setup` and `plot_payoff`:

```python
if kind in ("plot_setup", "plot_payoff"):
    to_id = item.get("scene_id", ""); note = item.get("description", "")
else:
    to_id = str(item); note = ""
```

Executed against current code:

```
plot_setup  -> to_id='s1'                      ok
plot_crisis -> to_id="{'scene_id': 's2', …}"   dict stringified into to_id
plot_climax -> to_id="{'scene_id': 's3', …}"   dict stringified into to_id
plot_payoff -> to_id='s4'                      ok
```

Three write paths, three behaviours:

| path | crisis / climax / complication |
|---|---|
| create — `relations_for_insert` (`entity.py:428-459`) | **corrupt** — `to_id` is a dict repr, `note` lost |
| edit — `writes.py:388-400` | correct (handles every kind uniformly) |
| import — `story_import.py:505-515` | correct |

So a plot **create** writes garbage rows for three of five roles; the same fields via
edit or import are fine. Never caught because `tests/test_field_coverage.py:456` asserts
survival only through the edit path.

Fix: one dict→row function used by all three paths. Root-cause fix at the shared point.

## 3. Direction: keep `from_id=plot → to_id=scene`

Writing scene-side does **not** require flipping storage. The scene-side writer emits the
same rows. Editing a scene deletes `WHERE to_id=? AND kind LIKE 'plot_%'` — the exact
pattern `writes.py:417-425` already uses for `scene.location` / `location_scene`.

Reads that stay untouched: `db.py:996`, `db.py:1109-1112`, `story_load.py:263`,
`story_retrieve.py:103`, all dashboard JS.

Flipping direction would rewrite 8 read sites for zero added capability. Not doing it.

## 4. Dashboard compatibility — verified, and the rename's real cost

The dashboard reads plot roles in **three** shapes. All must be updated.

**(a) Plot panel — role blocks.** `entity-panels.js:272-309` reads
`plot.setups/crisis/climax/payoffs`, plus panel headings. Rename `payoffs`→`resolutions`,
add `complications`. `renderBeats` (`:253-269`) is role-agnostic — no change.

**(b) Sequence/act plot rows — `has_*` flags.** `db.py:1259-1271` and `1299-1310` build
`has_setup/has_crisis/has_climax/has_payoff`; `entity-panels.js:27-30` and `529-532` render
them. Hand-written per-role code, duplicated twice in Python and twice in JS. Adding a
role means 4 edits. → **derive the flags from the role name in a loop**, so the
vocabulary has one home.

**(c) Scene panel — `scene.plots[].beat`.** `db.py:998` emits `{id, beat}`; read at
`entity-panels.js:431`. Rename the key `beat`→`role` per decision 4 — this is the
story-level word leaking into a plot context, exactly what decision 4 removes.
`core.js:64` (`s.plots = s.plots || []`) needs no change.

CSS classes `.beat-row/.beat-scene/.beat-desc` (`views.css:229-248`) are used by
`statistics.js:214` and the sequence/act panels for **non-plot** rows. They are generic
row/scene/description styling, so **leave the class names alone** — renaming them is churn
across files for no gain.

Mock data `data-load.js:62-63` has `payoffs` — update for the rename.

## 5. Data reality

> **SUPERSEDED — see `INTEGRATION.md` §"Correction to PLAN.md §5".** The original claim
> below was wrong: the live project *does* hold plot role rows, so a standalone rename
> script is needed. Corrected figures:
>
> | database | plot role rows |
> |---|---|
> | fixture `save-the-children` | `plot_setup` 2, `plot_payoff` 1 |
> | live `browser-verification-test` | `plot_setup` 2, `plot_crisis` 2, `plot_climax` 2, `plot_payoff` 2 |
>
> The script is needed for the **live project only** — phase 3 regenerates the fixture from
> its edited markdown. No migration code ships in the plugin.

Original (incorrect) text retained only to show what changed:

Only fixtures carry plot role rows:
- `tests/fixtures/save-the-children/.story/story.db` — 2 plots, 2 `plot_setup`, 1 `plot_payoff`
- `~/.story/story.db` — no `relations` table

No production data. **No migration.** Rename kinds in the fixture; no compat layer.

## 6. Implementation steps

1. **`core/constants.py`** — plot schema: `payoffs`→`resolutions`, add `complications`;
   descriptions say *role*. Add `PLOT_ROLES` beside `SCENE_DRAMATIC_ROLES` so one list
   drives validation, the `has_*` loop and the docs. (Introduced in phase 2 with the 4 roles
   that exist then; phase 3 grows it to 5 — see `INTEGRATION.md`.)
2. **`core/entity.py`** — `_RELATION_FIELDS` entries for all 5 roles (not two); **one**
   dict→row function replacing the `entity.py:442` special-case; scene-side role field.
   Validate that a named scene exists (same class of defect as `scene.location`, already
   guarded at `entity.py:493`).
3. **`core/writes.py`** — scene-side delete+rewrite. Modelled on the bespoke block at
   `:411-429`, **not** on `location_scene`'s delete behaviour: that one is swept free by the
   `to_id` delete, plot roles are not (the plot owns the row). See `INTEGRATION.md` phase 4.
4. **`core/db.py`** — `has_*` flags derived in a loop from the role name;
   `scene.plots[].beat`→`role`; `_normalize_beats` renamed off "beat"; computed read for
   the 5 fields. **No completeness check** (decision 3).
5. **`tools/story_import.py`** / **`tools/story_export.py`** — round-trip; share the one
   dict→row function instead of a third copy.
6. **Dashboard** — `entity-panels.js` role blocks + `data-load.js` mock;
   `scene.plots[].beat`→`role`. Verified by a headless-Chrome render, not a string check.
7. **Tests** — 9 files reference roles. Add one regression test for §2 (create must not
   stringify a dict).
8. ~~**Skill**~~ — **OUT OF SCOPE by decision.** The skill docs describe the old model and
   are not updated by this task. Known consequence, accepted: they will describe the
   pre-change model afterwards. See `task_07_dashboard_and_docs.md`.

## 7. Explicitly skipped

- Completeness / declared-role tracking — decision 3.
- `transition`/`non-event` as plot roles — decision 1.
- Direction flip — §3.
- CSS class rename — §4.
- Migration — §5.