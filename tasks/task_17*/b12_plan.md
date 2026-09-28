# B12 — placeholder defaults: store nothing, render at the edge

**BUILT 2026-09-28.** 34 prose defaults → `""`, 10 false findings → 0, 892 pass.
**B12b (the title-page render) is deliberately NOT built** — see the note at the
foot. What the plan got right, what it missed, and the one measurement that
turned out to be load-bearing are recorded in `bugs.md` → B12.

**Three things this plan did not list, found by grepping the codebase:**

1. `db.py:396` — `extra.get("arc_type", "Arc type not set")` would have
   **injected** a placeholder for any row missing the key. Live, not dead.
2. `writes.py:_default_for` documented the placeholder as *deliberate*
   ("so the UI shows the gap"). The function is still correct — it is what keeps
   `screenplay_title` resetting to `'Default'` — but **a comment calling a
   placeholder intentional becomes a lie the moment the placeholder is gone.**
3. `plot_scope` is listed here as defaulting to `'main'`. **It does not exist**
   in the schema. Stale from an earlier revision; harmless, and the guard test
   now reads the schema instead of a list.

**One pre-existing dead check, found and left alone:** `entity.py:79` guards
`act.structure_type`, a field the `act` schema does not have. Confirmed present
before this change.

**On the plan's own prediction that the tests would pass unchanged** — they did
not, and that was worth knowing. 14 `TestUnfilledFields` cases fed the
placeholder *string* as input to `unfilled_fields`, which is the exact mechanism
this change removes. The plan's reasoning about `_is_empty` was right
(`len(value) == 0` is checked first) but it reasoned about the *default*, not
about what the tests *pass*. They now pass `""` and test the same property
through the surviving mechanism.

---

## Original plan (kept; the reasoning is sound)

**This is the better fix, and the measurements are stronger than the bug entry
assumed.** The entry framed it as "make `empty_ok` mean unset" — a one-line
tolerance for a bad default. Removing the placeholders instead deletes the
problem rather than accommodating it, and the data supports it completely.

---

## The proposal, and why it is better than the one-line fix

The bug entry's fix: teach `_validate_enum` that a value equal to the field's
own default means "unset". That keeps 25 prose strings in the data layer and
makes the validator aware of them.

**The proposal:** stop putting prose in the data. A default becomes `""` (or
`[]`, `0`, `{}` — whatever the type is), and the *placeholder text is a display
concern*, applied where a human reads it.

Three measured reasons this is right, not just tidier:

**1. No placeholder is real data.** Checked every `extra` value in both real
databases against all 25 placeholder strings:

```
save-the-children          0 stored placeholders
browser-verification-test  0 stored placeholders
```

**Not one.** They are defaults that get written on create and never edited.
There is no data to preserve and no migration — the deployment constraint does
the rest.

**2. The dashboard does not read them.** Grepped all of `src/dashboard/` for
each of the 25 strings: **zero hits**. The dashboard receives them only as
values it happens to render, and in practice never sees them, because it
filters on emptiness and length rather than on the string.

**3. They are already display strings leaking into storage.** `'Author N.A.'`,
`'Credit N.A.'`, `'Contact N.A.'`, `'Draft Date N.A.'` are *title-page
rendering* decisions — a screenplay's title page says "Written by", and that is
a formatting concern, not a fact about the story. Storing them means an export
to any other format inherits our phrasing.

## The display side: yes, map the labels from the schema (2026-09-28)

**The proposal:** since the dashboard already receives the data, and the schema
already knows what each field means, inject a field→label map rather than
hardcoding placeholder strings in JS. Confirmed as the right shape — and
measured, because the shape of the payload decides how big it is.

### What the payload looks like today

`get_dashboard_data` returns six keys; `story_data` is `{acts, arcs,
characters, locations, plots, project, relationships, scenes, sequences,
story_memory, worlds}`. A character node is 14 flat keys. Probed the serialized
payload for any label machinery:

```
'Goals not set'  present: False
'not set'        present: False
'N.A.'           present: False
'unfilled'       present: False
'placeholder'    present: False
'label'          present: False
```

**Nothing.** No field map, no label map, no placeholder concept. There are
already four injection slots (`__STORY_DATA__`, `__SECTIONS__`,
`__STRUCTURAL_STATS__`, `__SCREENPLAY_STATS__`), so adding a fifth is the
existing pattern, not a new mechanism.

### How much would need a label

Of the 31 prose placeholders across the schema, **21 sit on a field the
dashboard JS reads**; 10 are on fields it never mentions. But *reads* is not
*renders* — most of those 21 are read to decide whether to draw a row at all,
and an empty value already means "don't draw it". The honest count of fields
that would *want* a visible "not set" label is much smaller, and **deciding it
is a display choice, not a data one.**

### The one place the placeholders are load-bearing today

`tools/story_dashboard.py:210-241`, `_build_title_page`:

```python
credit = project_frontmatter.get("credit", "")
if credit:
    cc.append({"text": credit, "type": "credit"})
```

It gates on **truthiness, not on whether the value is a placeholder.** So
today it renders:

```
cc: title      'Default'
cc: credit     'Credit N.A.'
cc: author     'Author N.A.'
bl: draft_date 'Draft Date N.A.'
bl: draft      'N.A.'
br: contact    'Contact N.A.'
```

and with `''` defaults **only the title survives**. This is the one place where
removing the placeholders produces a **visible change to the rendered output**,
and it is not cosmetic — a typeset screenplay title page is the most
deliberately-designed surface in the app, and `'Credit N.A.'` printed as if it
were the credit line is a placeholder masquerading as content.

**This is the one decision the removal needs from the user, and it is a real
one:** should an unfilled title-page field show *nothing* (correct typesetting,
a visibly incomplete page) or show its label (a reminder)? Both are defensible;
they are not the same product.

### If labels are wanted, they come from the schema

The schema's `description` already carries the human phrasing — `"Title page:
credit line (e.g. 'Written by')"`. So a label map is not new text to write:

```python
# in get_dashboard_data, alongside story_data
"field_labels": {f"{et}.{f}": meta["description"]
                 for et, s in ENTITY_SCHEMAS.items()
                 for f, meta in s.items() if meta.get("optional")},
```

Injected as `window.__FIELD_LABELS__`. The dashboard then renders
`labels[etype + '.' + field]` for an empty optional field, and **no placeholder
string is ever stored or hardcoded in JS.**

**But this is a second piece of work, not part of the B12 fix.** B12's job is
"prose must not live in the data". Whether the UI then *chooses* to show
"Credit: not set" is a display decision that should be made on purpose, with
the title page settled first — not bundled into a data cleanup, where it would
be invisible in the diff and untestable as a display change.

### DECIDED (revised 2026-09-28): ONE voice — `<label>: N.A.`

The first pass proposed `label` + `unfilled_label` per field — a declared
reminder string for each of the 31 placeholders. **That is 31 strings to
maintain for one idea, and it is wrong.** One voice, one string:

```
Credit: N.A.
Goals: N.A.
```

**This deletes `unfilled_label` entirely.** The placeholder text is not moved,
it is *dropped* — `'Goals not set'`, `'Action not described'`,
`'Shift not recorded'` were 31 ways of saying one thing, and
`story_retrieve` already reports unfilled fields **by name**
(`unfilled_fields` → `["goals_short", "goals_long"]`), so the information was
never *in* the text to begin with. Nothing is lost.

`"N.A."` is already the house style: `project.draft`'s default is literally
`'N.A.'` today. This makes the whole schema consistent with it.

### The label: derived, with four declared exceptions

`field.replace("_", " ").title()` covers 27 of the 31 correctly, and **the
check that matters is collisions** — two fields of the same type rendering the
same reminder. Measured: **zero collisions across all 31.**

Four derive wrong, and get a declared `label`:

| field | derives as | declared as | why |
|---|---|---|---|
| `project.inciting_incident_scene_id` | `Inciting Incident Scene Id` | `Inciting Incident` | trailing `Id` is not English |
| `project.story_climax_scene_id` | `Story Climax Scene Id` | `Story Climax` | same |
| `plot.one_sentence` | `One Sentence` | `Summary` | it is a summary; the field name is an implementation detail |
| `act.act_objective` | `Act Objective` | `Objective` | redundant "Act" *inside* an act |

**Four declared labels, not 31 reminder strings.** That is the whole cost.

`description` was considered as the label source and rejected: it is prose
(*"Scene slug of the inciting incident"*), not a label, and rendering a
sentence as a field name is worse than a derived one.

### The final shape

```python
# BEFORE
"credit": {"type": "string", "default": "Credit N.A.", "optional": True, ...}
"goals_short": {"type": "string", "default": "Goals not set", "optional": True, ...}

# AFTER — no unfilled_label anywhere; label only where the name is not the phrase
"credit":     {"type": "string", "default": "", "optional": True, ...}
"goals_short":{"type": "string", "default": "", "optional": True, ...}
"one_sentence": {"type": "string", "default": "", "label": "Summary", "optional": True, ...}
```

**The reminder is one constant**, not a per-field string:

```python
UNFILLED = "N.A."      # core/constants.py, next to the other display defaults
```

and the render is `f"{label or derived}: {UNFILLED}"` — the same expression
for every field on every surface. A surface that wants no reminder passes
`None`; one that wants a different word passes a string. **The default is one
constant, and overriding it is a display decision made at the call site.**

### The one default that must not move

`project.screenplay_title` → `'Default'`. Unchanged from the previous pass: it
is a **real value**, not a placeholder — a project with no title set should
still typeset something, and an empty title page is worse than a generic one.
Verified as the only string default in the schema that is neither empty, nor a
legal enum member, nor a placeholder pattern. A test asserts it, because
converting it would silently change the rendered title page.

### The render

```python
if credit:
    cc.append({"text": credit, "type": "credit"})
else:
    cc.append({"text": f"Credit: {UNFILLED}", "type": "credit_unfilled"})
```

`type` is what the dashboard styles on, so a reminder is visually distinct from
typeset content — otherwise a filled page and an empty one are structurally
identical and the reader cannot tell which slots are open.

**Separate commit from B12.** B12 makes the data clean; B12b makes the surface
honest. Bundled, a title-page change would be invisible in a diff about
placeholder defaults.

### Revised scope

| | in scope | out |
|---|---|---|
| **B12** | prose `default` → `""`, text **deleted** (not moved); `label` on 4 fields; `UNFILLED` constant; `_is_empty` and `_validate_enum` unaffected; `arc_type`'s legal `'absent'` already handled | any rendering |
| **B12b** | `unfilled_label(f)` helper deriving the label; `_build_title_page` renders `<label>: N.A.` for empty slots with a `credit_unfilled` token type | applying reminders to the other 27 fields — each surface decides separately |

---

## What it costs, measured

**`unfilled_fields` is built on comparing against the default.**
`core/entity.py:180-193`:

```python
def _is_empty(value, default) -> bool:
    if value is None: return True
    if isinstance(value, (str, list, dict)) and len(value) == 0: return True
    return value == default          # ← the placeholder comparison
```

Its docstring says so outright: *"which for some fields is a UI placeholder
string like 'Summary not set' rather than an empty value."*

**Good news: it already handles the empty case.** `len(value) == 0` is checked
*before* the default comparison, so switching a default to `""` makes
`_is_empty` return `True` on the first branch. **`unfilled_fields` keeps
working unchanged** — the `value == default` branch becomes redundant for
strings but stays correct for `0`/`False`/`[]` defaults.

Verified by reading the three call sites: `core/db.py:743`,
`tools/story_retrieve.py:140`, and the `sub_fields` path at `entity.py:226`.

**`_validate_enum` gets simpler, not more complex.** With `""` defaults, the
existing `empty_ok and val == ""` branch fires and the bug is gone — because
there is no longer a prose value to misread. **B12's one-line fix and this fix
converge on the same code; this one removes the cause.**

**The special cases you predicted exist, and are small.** One enum-guarded
field has a *legal* value that means "no arc":

- `arc_type` includes `'absent'` in `ARC_TYPES` — a real choice, not "unset".
- `statistics.js:225` already filters `c.arc_type !== 'absent'`
- `network.js:134` already does `char.arc_type || 'absent'`

**So the dashboard already distinguishes a real "absent" from unset, by
comparing to a sentinel.** Switching the default from `'Arc type not set'` to
`""` works with code that is already written: `""` is falsy, so
`char.arc_type || 'absent'` renders `absent`, and `c.arc_type &&` excludes it
from the arc count. **No dashboard change is needed for this case** — which is
the answer to "do we need rules for the special cases": the rule already exists
and is already correct.

Every *other* enum-guarded field already defaults to `""` — `plot_type`,
`plot_scope`, `time_of_day`, `dramatic_role`, `value_at_open`/`_close` on scene,
sequence and act. **They are the control group: they have never produced a
false finding, precisely because they default to `""`.** That is the strongest
evidence available that the fix works, short of doing it.

---

## The change

The change is a pass over `ENTITY_SCHEMAS`, replacing prose defaults with `""`
and **deleting the text**. **Not a hand edit of 31 lines** — a rule, so a
placeholder added later is converted the same way. Plus `label` on the four
fields whose name is not the human phrase.

| current `default` | becomes | type |
|---|---|---|
| `'Goals not set'`, `'Not set'`, `'Summary not set'`, … | `""` | string |
| `'Credit N.A.'`, `'Author N.A.'`, `'Contact N.A.'`, `'Draft Date N.A.'` | `""` | string |
| `'N.A.'` (`project.draft`) | `""` | string |
| `[]` | unchanged | list |
| `0`, `0.0`, `False` | unchanged | number/bool |
| `'active'`, `'planned'`, **`'Default'`** — **real values** | **unchanged** | see below |

**The exclusion that matters.** A default that is already a *legal value* of
its enum, or a real fallback, must not become `""` — the field would then
report as unfilled when it holds a real default:

- `project.status` → `'active'` (in `VALID_STATUSES`)
- `project.plot_scope` → `'main'`
- **`project.screenplay_title` → `'Default'`** — the subtle one. It is not an
  enum member and not a placeholder pattern, but it is a **real value**: a
  project with no title set should still typeset something, and an empty title
  page is worse than a generic one. Verified as the only string default in the
  schema that is neither empty, nor a legal enum member, nor a placeholder.
  **Leave it.** A test asserts the distinction, because converting it would
  silently change the rendered title page — the exact regression B12b exists to
  make visible.

So the rule is: **prose placeholders become `""`; real values and legal enum
members are left alone.**

---

## The checks

1. **Every enum-guarded field's default is either `""` or a legal enum value.**
   The one that fails today is the bug; the test is its regression guard.
2. **`unfilled_fields` still reports the same fields.** Reuse the existing
   `TestUnfilledFields` cases — they pass today *because* `len(value) == 0` is
   checked first, so they should pass unchanged. **If any needs its input
   rewritten, that is a signal the reasoning is wrong — stop and re-read.**
3. **A minimal `character` create reports no enum finding.** The B12 symptom,
   as a direct test.
4. **The dashboard arc summary still counts the same characters.** A
   `statistics.js:225`-shaped assertion: a character with `arc_type: ""` is
   excluded, one with `'absent'` is excluded, one with `'negative'` is counted.
5. **No placeholder prose survives as a `default`.** Walk every schema entry:
   any `default` that is prose must now be `""`. This is the test that fails
   today on 31 fields.
6. **The labels are unique per type.** No two fields of the same entity type
   derive or declare the same label — the collision check that makes the
   derived-label shortcut safe. Measured zero today; the test keeps it that way
   if a field is ever added.
7. **B12b's render** — a filled credit renders its value with `type: "credit"`;
   an empty one renders `Credit: N.A.` with `type: "credit_unfilled"`. And
   `screenplay_title` still renders `'Default'` — the case that would regress
   silently if the exclusion were got wrong.

---

## Not in this plan

- **The placeholder *text*.** **Deleted, not moved.** One voice — `N.A.` — and
  `unfilled_fields` already reports *which* fields are unfilled by name, so the
  prose was never carrying information. The 31 strings go, and a single
  `UNFILLED` constant in `core/constants.py` replaces them. A surface that
  wants a different word passes it at the call site; one that wants no reminder
  passes `None`.
- **The `value == default` branch in `_is_empty`.** It becomes redundant for
  strings once defaults are `""`, but it is still load-bearing for `0`, `False`
  and `[]` defaults. **Leave it.**
- **B6.** Separate plan, runs first.

---

## B12b — BUILT 2026-09-28 (the decision was made, then the plan's assumption failed)

**The user chose the labelled reminder** (`Credit: N.A.`) over an empty page.
The decision was already recorded below; what was not known is that **the plan's
styling hook does not exist.** It said `type` is "what the dashboard styles on" —
`script-view.js` joined every token's `.text` into one string and discarded
`type`. Real JS was required, not the ~10 lines of Python budgeted.

**A bug the green tick could not see.** `_slot()` returned `None` for an empty
title; `screenplay_title` is empty in the fixture; so `cc[0]` was the credit
line and the position-based split typeset **`Credit: N.A.` as the title**. The
unit tests passed. Reading the rendered DOM is what caught it.

**The fix is a shape, not a patch: a token that can be absent invites its
consumer to index by position, and position is not an identity.** `_slot()` now
always returns a token; the dashboard finds the title by `type`.

**896 pass.**

---

## B12b as originally planned (kept; the render shape was right)

**The title page is the one place in the plugin where B12 changed output.**
`_build_title_page` gates on truthiness, so an unfilled project rendered
`'Credit N.A.'` and `'Author N.A.'` where the credit line belongs, and now
renders **only the title**.

**Both states are defensible and they are not the same product:** an empty
title page is correct typesetting and visibly incomplete; a labelled page is a
reminder. The decision is recorded in `bugs.md` → B12b and belongs in its own
commit, where it is visible in a diff. Bundled into a data cleanup it would be
invisible and untestable as a display change.

`UNFILLED` and the four declared `label`s are in place for it. Nothing consumes
them yet, which is deliberate — an unused constant that a later commit needs is
cheaper than a display change smuggled into a data fix.
