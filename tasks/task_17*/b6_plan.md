# B6 — `REQUIRED_FIELDS` disagrees with the schema

**Status: BUILT AND VERIFIED 2026-09-28.** Kept as the record of what was
decided and why. The outcome is in `bugs.md` → B6.

**Built:** `core/constants.py` — the 12-line dict deleted, `REQUIRED_FIELDS`
derived from `ENTITY_SCHEMAS` after it, with `WRITE_PATH_SUPPLIED` as the
literal `{id, type, order, status}` (a literal, not an import of
`FIELDS_TO_SKIP`, because `entity.py` imports `constants.py` and the reverse
would be circular). `tests/test_arcs.py` — the two tests below, plus the one
existing assertion that defended the bug changed from `order` to `label`.

**Suite: 889 → 891.** Both new tests verified to fail against the old
hand-written list before the fix was kept.

---

**Plan as written, before building.** Bug entry: `bugs.md` → B6. Baseline
**889 tests pass**; this must leave that number at 889 or higher.

**Scope: B6 only.** B12 (the enum check rejecting the schema's own placeholder
defaults) is a separate defect in a separate function and is **not** in this
plan. Two of the findings below will still appear after this fix — that is
expected and is what B12 is for.

---

## The defect, in one line

`REQUIRED_FIELDS` in `core/constants.py:23-34` is a hand-maintained duplicate
of what `ENTITY_SCHEMAS` already declares as `optional: False`, and it has
drifted. The write path supplies four of those fields itself, so the correct
list is *"non-optional, minus what the write path fills in"* — and the
hand-written list does not match that for three of ten types.

---

## What to change

One dict becomes a comprehension. `core/constants.py:23-34`:

```python
# The write path supplies these four itself: `id` and `type` are in
# FIELDS_TO_SKIP, `order` is auto-numbered, `status` defaults to a valid
# value. So a field is required only if the schema says it is not optional
# AND the write path does not already fill it in.
WRITE_PATH_SUPPLIED = FIELDS_TO_SKIP | {"order", "status"}

REQUIRED_FIELDS = {
    entity_type: [f for f, meta in schema.items()
                  if not meta.get("optional", True) and f not in WRITE_PATH_SUPPLIED]
    for entity_type, schema in ENTITY_SCHEMAS.items()
}
```

`FIELDS_TO_SKIP` lives in `core/entity.py:161` and `ENTITY_SCHEMAS` is defined
*below* `REQUIRED_FIELDS` in `constants.py`, so **the comprehension has to move
below `ENTITY_SCHEMAS`** (i.e. to the end of the file) or import `FIELDS_TO_SKIP`
— pick the former, it avoids a circular import for no benefit.

The 12-line hand-written dict is deleted. That is the whole fix.

---

## Why it is safe — measured, not assumed

**1. The fix only ever REMOVES requirements.** Checked every type: the derived
list is a subset of the current one for all ten, so nothing that passes today
starts failing. The dangerous direction cannot occur.

**2. Of the 9 fields it drops, exactly 3 could ever have fired.** The other 6
have truthy placeholder defaults, so they were never reported:

| dropped field | default | ever fired? |
|---|---|---|
| `arc_beat.id` | `''` | **yes, on every create** |
| `arc_beat.order` | `0` | **yes, on every create** |
| `arc_beat.y` | `0.0` | **yes, on every create** |
| `arc_beat.action` / `gap` / `choice` / `shift` | prose placeholders | no |
| `plot.status` | `'active'` | no |
| `project.logline` | `'logline not set'` | no |

So the fix removes **three** false findings per arc-beat draft and changes
nothing else. That matches the B6 entry's re-measurement.

**3. The falsy check is safe for the derived list.** `drafts.py:179` tests
`if not merged.get(field)`, which would misread a legitimate `0` as missing —
but **no field in the derived list is `type: number`**. Every one is a string or
a list, where a falsy value genuinely does mean absent. Verified by inspecting
the derived list against the schema types. (The bug in `y` was never the falsy
check; it was `y` being in the list at all.)

**4. Nothing pins the current values.** No test asserts `REQUIRED_FIELDS`
contents, so the wrong list is not load-bearing for the suite.

---

## Expected result

A minimal valid arc beat — `character`, `scene`, `label`, the only three
non-optional fields — currently reports:

```
Missing required field: id
Missing required field: y
Missing required field: order
```

and after the fix reports **none of the three**. The two enum findings that
remain (`Invalid character_value_at_open: Not set`) are **B12**, untouched here.

Types confirmed unchanged: `character`, `location`, `world`, `scene`,
`sequence`, `act`, `relationship` — the derived list equals the current one.

---

## The check

One test, in the existing style, added to `tests/test_arcs.py`:

```python
def test_minimal_arc_beat_reports_no_missing_field(self):
    """The schema's non-optional fields are the only ones that can be required.

    `id` is unsatisfiable (the write path builds it), and `order`/`y` default to
    0 — a falsy default is a missing value only if the field is required, and
    none of these three is.
    """
    findings = validate_shape([{
        "op": "create", "type": "arc_beat", "slug": "kael-1",
        "frontmatter": {"character": "kael", "scene": "s1", "label": "First Doubt"},
    }])
    assert not [f for f in findings if "Missing required field" in f]
```

Plus a guard that the derivation stays honest, because the whole point is that
there is now no second copy to drift:

```python
def test_required_fields_is_derived_from_the_schema(self):
    for et, schema in ENTITY_SCHEMAS.items():
        expected = {f for f, m in schema.items()
                    if not m.get("optional", True) and f not in WRITE_PATH_SUPPLIED}
        assert set(REQUIRED_FIELDS[et]) == expected
```

**A test that fails without the fix:** the first one reports 3 findings today,
the second reports 7 dropped fields across 3 types.

---

## One existing test encodes the bug

`tests/test_arcs.py:36-40`:

```python
def test_validate_arc_missing_required(self):
    warnings = validate_entity("arc_beat", {"id": "beat-1"})
    assert any("character" in w for w in warnings)
    assert any("scene" in w for w in warnings)
    assert any("order" in w for w in warnings)      # <-- this line
```

`order` is **not** required under the fix, so this assertion will fail. The
first two assertions stay correct and still have value. **Delete the third
line** — it asserts the behaviour B6 exists to remove, and keeping it would
mean the test suite actively protects the bug.

The other 8 `validate_entity` call sites in `test_arcs.py` and all of
`test_core.py`'s pass `id` in the frontmatter explicitly, so they are unaffected
either way.

---

## Risk

**Low, and the failure mode is loud.** The only consumer that could notice is
`drafts.validate_shape` reporting *fewer* findings, and `entity.validate_entity`
reporting fewer `Missing required field` warnings. Neither can start rejecting
something that used to pass — verified by the subset check above.

**The one thing to watch:** a caller outside `core/` that imports
`REQUIRED_FIELDS` would now see three shorter lists. Grepped — only
`core/drafts.py:135` and `core/entity.py:6` import it, both already read.

---

## Not in this plan

- **B12** — the two remaining enum findings on an arc beat, and the 1–3 on
  every `character`, `plot` and `project` create. Same root shape (the schema
  knows, a hand-maintained assumption does not), different function
  (`_validate_enum`), different blast radius. Its own plan.
- **D5 step 4** — which may make `id` a non-issue entirely by generating it.
  Doing B6 first means that is *verified* rather than assumed.
- **Making the derived list available to D5.** D5 step 4 declares `id` on all
  ten types; this comprehension will pick that up automatically, which is
  correct — a generated id is supplied by the write path, so it should be in
  `WRITE_PATH_SUPPLIED` or optional. Not decided here.
