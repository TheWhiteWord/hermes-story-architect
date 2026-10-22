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

## 2. `ops` and the JSON-string non-fix

Superseded. The `ops` array declared no per-op shape, so the model was guessing
and arriving with keys stripped. `story_draft`'s schema now declares all four
op kinds, built from the tables `validate_ops` enforces — pass `ops` as a native
array, always.

The "serialise to a JSON string" workaround never worked: `validate_ops`
rejects a string outright. It only appeared to, because the retry changed the
prompt the model was working from.

---

## 3. `Want` is not a standard character section

**What happened.** Prose written to a `Want` section appeared to save. The
standard set for a character is:

`Identity · Desires · Background · Contradictions · Psychology · Arc · Relationships · Voice · Notes`

**The rule.** Aim prose at the standard headings; `Want` belongs in `Desires`.

**Correction to the note above.** An earlier version of this file said custom
headings "are accepted and are not an error". That is wrong. Section names are a
**closed set**: `core/writes.py` rejects any edit key that is not a field, a
relation, or a standard section, so a custom heading fails the whole edit with
`Unrecognised character edit key(s): Want`. Verified against the live write
path, not read off it.

The list is not something to memorise or look up in a reference — `story_describe`
now reports it per entity type, and says it is closed. The original symptom
(prose landing where it was not expected) was a guessed section name, which the
tool surface gave no way to avoid.

---

## 4. Field-count denominator excludes `computed` fields

**What happened.** A fully-populated character rendered `10 of 11 fields set`,
not `11 of 11` — the two `computed` fields (`relationships`, `arc_beats_list`)
are excluded from both numbers. The one short field was genuinely unset.

**The rule.** Do not read a count below the schema total as a bug. A type
where every settable field is filled still renders one short per `computed`
field, and those are read-only anyway.

---

## 5. `purge` is gated three times, and the age floor is only one of them

**Rewritten 2026-09-29 — the original version of this note is wrong.**

It said: *"`purge` on a just-deleted entity returns `success: True` with
`purged: []` — correct, because the 30-day age floor kept it restorable."*

`purge` no longer returns that. Verified end to end:

1. **It refuses without a confirm string.** `purge_confirm` must contain
   `DELETE <project slug>`, exactly like `delete_project`. Without it:
   *"Purge refused. It is irreversible and must be the user's call."*
2. Given the string, **it only touches entities deleted more than thirty days
   ago.** With a backdated deletion and a recent one in the same project, it
   purged the 45-day-old character and left the recent one untouched and still
   restorable.
3. **It takes its own backup** first, and reports the path — the same courtesy
   `delete_project` extends.

So the empty-list case is still real, but it is reached *with* the confirm
string and past the age floor, not instead of it. The rule stands in a narrower
form: **`purged: []` means the age floor kept everything, not that the purge
failed** — and reporting it as "nothing was purged, everything is still
restorable" is the honest reading.

The practical guidance is stronger than the original: **there is almost never a
reason to purge.** `restore` covers the case people reach for purge to solve, and
it is exact.

Recorded in `skill/references/mechanics/project-lifecycle.md`.


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

## 6. Read a `commit` result; do not assume it from `success`

**The rule.** After any `{"error": ...}` from `commit`, read the project back
before telling the user anything. Report what the response says landed.

**The original reason no longer holds.** A commit reporting `No open draft` for a
write that had landed was `bugs.md` B1, and it is **fixed**: committing the same
draft twice now returns `success: true` with `already_committed: true` and writes
nothing. Verified 2026-09-29.

**The reason it still holds is a different one, and it is worse.** A commit is
**not all-or-nothing**. Verified with a two-op batch whose second op failed: the
first op was written, the response was `success: false`, and it named how many
landed. So `success: false` means "partly or not at all", never "nothing" — and
telling the user "that did not save" about a change that did land invites a
retry that writes on top of it.

The response is well-behaved: it reports the count, keeps the draft for a retry,
and says so. **The recovery is to re-stage the failed op alone, not to re-send
the batch.**

Recorded in `skill/references/mechanics/staging-changes.md`.

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

**What is verified about the existing validator** (so this note is not
over-confident): no tool calls it, and it is **not** the check you want. It was
built for script *import* — accepting a real human-written screenplay — and
permissive parsing is correct there, so it is not broken. Our case is the
opposite: an agent writing script that should be told where it departed. That
is a linter, and it does not exist yet (B11). Do not treat
`fountain_validator.py` as a passing check, and do not expect the write path
to catch malformed script — it currently catches nothing.

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
