# Tool notes — for the SKILL.md

Findings from the live test of `story_draft` / `story_admin` (2026-09-28).
Each one is a thing the **agent** must be told to do, discovered by running
the tools rather than by reading the code. Collected here while testing; to be
folded into `skills/hermes-story-architect/SKILL.md` when the skill is written.

Not a design doc. If a note here contradicts the code, the code wins and the
note is wrong.

---

## 1. Relay the whole `preview_md`, on every stage — not just the diff

**What happened.** A restage returned a full `preview_md` showing every entity
with its final field values, plus a `changes` block listing which ops moved.
The agent relayed the `changes` block and summarised the rest. The user could
not see the new Background sections or the changed `goals_short`, and said so.

**Why it matters.** The `changes` block answers *which ops differ from the
last stage*. It does not answer *what the draft now contains*. Only
`preview_md` answers that, and `preview_md` is what the user is approving.

**The rule.** After every `stage` — first stage, restage, edit, anything —
output the entire `preview_md` verbatim. The `changes` block may follow it as
a footnote; it never replaces it. Do not summarise, do not re-render, do not
pick out "the interesting" fields. The whole block is the artefact under
review.

**Corollary.** A `create` op has no prior state, so it renders no
`before → after` arrows even on a restage. That is correct, not a gap: the
user's question on a restaged create is "what does this draft contain now",
and the field table answers it. The `before → after` rendering is for `edit`
ops, where there genuinely is a prior value.

---

## 2. `ops` must be passed as a JSON string

**What happened.** Every `story_draft` call with `ops` as a native array
failed with `ops[0].op must be one of [...]; got None`. The same call with
`ops` as a JSON **string** succeeded first time. The objects inside the array
arrive with their keys stripped; a list value sent natively also came back
double-nested (`[["a","b"]]` instead of `["a","b"]`).

**Status.** This is a Hermes-layer defect in the tool-call bridge, not a
plugin bug — `core/drafts.py` receives correct args when called directly, and
the plugin's own tests pass native arrays. Still, the model will hit it every
time, so SKILL.md must state the workaround until the bridge is fixed.

**The rule.** Serialise `ops` to a JSON string and pass that. Do not attempt
a native array first.

---

## 3. `Want` is not a standard character section

**What happened.** Prose written to a `Want` section saved correctly, but the
standard set for a character is:

`Identity · Desires · Background · Contradictions · Psychology · Arc · Relationships · Voice · Notes`

**The rule.** Aim prose at the standard headings; `Want` is better placed in
`Desires`. Custom headings are accepted and are not an error, so a user who
asks for one is not blocked — just prefer the canonical name.

---

## 4. Field-count denominator excludes `computed` fields

**What happened.** A fully-populated character rendered `10 of 11 fields set`,
not `11 of 11` — the two `computed` fields (`relationships`, `arc_beats_list`)
are excluded from both numbers. The one short field was genuinely unset.

**The rule.** Do not read a count below the schema total as a bug. A type
where every settable field is filled still renders one short per `computed`
field, and those are read-only anyway.

---

## 5. An empty `purge` result is a real answer, not a failure

`purge` on a just-deleted entity returns `success: True` with `purged: []` —
correct, because the 30-day age floor kept it restorable. Report the empty
list to the user; do not read `success: True` alone as "purged". (From the
task 29 plan; to be re-verified when we reach the cleanup step of the live
test.)

---

## 7. Write `relationship.perspectives` as `{slug: {label, type}}`, not prose

**The rule.** On a `relationship`, every value inside `perspectives` must be a
**dict** with `label` and `type` keys — not a string:

```json
"perspectives": {
  "elias-kade": {"label": "She is the only person who has come up the rock.", "type": "ally"},
  "mara-venn":  {"label": "He files nothing and signs nothing.", "type": "liability"}
}
```

A bare string crashes `story_load` for the entire project — not just that
relationship. See `bugs.md` B7.

**Why this is worth knowing.** The schema says only *"Per-character
relationship view"* and gives no shape, so prose is the natural thing to write
and it is what the tool silently stores until something reads the project
back. `story_describe` will not warn you. Until the schema is fixed, write the
dict form deliberately.

**Symptom to recognise:** `story_load` returning
`{"error": "'str' object has no attribute 'get'"}` means some relationship on
the project has a string perspective. Check every one, not just the obvious
candidate.

## 7. Structured fields have a shape `story_describe` does not show you

`story_describe` reports `type` but drops `sub_fields`, so for these five
fields you must already know the shape. **This is a tool bug (B9), not a
schema one — the schema is correct.**

**`relationship.perspectives`** — one object per character, not a string:

```json
"perspectives": {
  "elias-kade": {"label": "The only witness", "feeling": "Grateful and exposed",
                 "type": "professional", "strength": 0.6, "secret": false},
  "mara-venn":  {"label": "A keeper who files nothing", "feeling": "Protective of a file she has falsified",
                 "type": "rival", "strength": -0.5, "secret": true}
}
```

A bare string **crashes `story_load` for the whole project**, not just that
relationship. Symptom: `{"error": "'str' object has no attribute 'get'"}`.

**`plot.setups` / `crisis` / `climax` / `payoffs`** — objects, not slug strings:

```json
"setups": [{"scene_id": "the-lamp-comes-back-on",
            "description": "Elias finds the lamp burning and says nothing."}]
```

A bare slug string is accepted, but **`description` is silently discarded** —
the relation is created with an empty `note`, the commit reports success, and
nothing warns you. The description is the point of the field; write it.

**When a structured field is unclear, check a real project before guessing.**
`browser-verification-test` has 6 correctly-shaped relationships and 2 plots
whose `relations.note` column shows exactly what a plot description should look
like. Reading the reference beats reading the code — see note 3.

---

## Verified working (2026-09-28)

Recorded so the skill does not hedge on what is solid.

- `story_admin(action="list_projects")` — enumerates without opening a database.
- `story_admin(action="create_project")` — creates folder + DB, persists every
  non-computed field. The empty `sections` rows a new project gets are
  `standard_sections()` placeholders, not a fault.
- `story_draft(action="stage")` — writes nothing. `entities` / `sections` /
  `relations` counts were identical before and after; only the `drafts` row
  appeared. Same on restage.
- `story_draft` restage diff — attributed per-op *and* per-field:
  `create character/elias-kade (frontmatter, sections)` vs
  `create character/mara-venn (sections)` when only Elias's frontmatter
  changed. Real granularity, not entity-level hashing.
- `story_draft(action="list")` and `action="discard"` — both fine.
- `story_draft(action="commit")` — the write path is sound; see note 6 for how
  it reports, and `bugs.md` B1 for the defect.

Defects found during testing are tracked separately in `bugs.md`.

---

## 6. Never pass a `commit` error straight through

**The rule.** After any `{"error": ...}` from `commit`, read the project back
(`story_load`, or `story_retrieve` on the affected entity) before telling the
user anything. Do not report the error as given.

**Why.** A commit has been observed to report `No open draft` for a write that
had in fact fully landed — see `bugs.md` B1. The error text is not reliable
evidence that nothing was written, and telling the user "that did not save"
about changes already in the database invites a retry that writes on top of
them. Confirm against the project, then report what is actually there.

---

## 8. Scene script has a format, and the tool will not tell you

`scene.Content` is **Fountain screenplay**, not prose. A cue is its own line,
ALL CAPS, dialogue indented beneath; a slugline is `INT./EXT. LOCATION - DAY`.
Writing `ELIAS: You could have telephoned.` on one line is not a style
preference — it renders as a wall of prose and the dashboard cannot parse it.

Nothing in the tool surface says this. `story_describe` does not mention that
`Content` is Fountain, and there is no format check on the write path
(**B11**: the existing `fountain_validator.py` is dead code *and* would pass
this text anyway). So the rules live only in
`skills/story-editor/references/screenplay-format.md`, and an agent that has
not read it writes valid-looking prose and never finds out.

**Read the format reference before staging scene script.** Re-read it when a
scene's dashboard rendering comes back as an undifferentiated block — that is
the symptom, and the block is nearly always inline cues or a missing slugline.
When the validator is wired up these become stage-time findings instead of a
rendering you have to diagnose visually.

**What is verified about the validator** (so this note is not over-confident):
no tool calls it, and `validate_screenplay()` returns `valid: True, 0 issues`
for all three malformed scenes in the live test — also for a pure-action scene,
and for inline-cue text. It detects line-level disagreement, not global
structure, and it classifies an inline cue as `action` because the line is not
`isupper()`. Treat it as unusable until fixed, not as a check that passed.

---

## Still to test

Nothing outstanding. All planned paths exercised on `lighthouse-test`
(created, edited, deleted+restored, reordered, purged, exported, and finally
`delete_project`-ed). Re-run against a new project if the plugin changes.

## Cleanup state

`lighthouse-test` was deleted at the end of the 2026-09-28 live test. Its
backup survives at
`/media/theww/AI/TWW/hermes-story-architect/backups/lighthouse-test_20260928_022215.db`
— kept deliberately, as the reference project for re-testing the Fountain
findings (B11, I1) without rebuilding the story from scratch.
`browser-verification-test` and `save-the-children` were not touched.
