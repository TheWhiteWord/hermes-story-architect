# Task 28 — Chat preview

**Not implementation.** A mock of the intended chat interaction, built from the
real field names in `ENTITY_SCHEMAS` and the real standard sections in
`core.entity.standard_sections`. Use it to settle the *presentation* before any
code is written — that is the part hardest to change later.

The agent's prose is written by the model, not by the plugin. The plugin
contributes exactly one thing per turn: the **preview block**, which is
`preview_md` from the tool result, relayed verbatim.

---

## Turn 1 — the user asks for a scene

> **user:** add a scene where Mira finally tells Kael about the reservoir, and
> it goes badly

The agent reads the structure, drafts the scene, and stages it rather than
committing. Tool call:

```
story_draft(action="stage", project="save-the-children", summary="Mira tells Kael — goes badly", ops=[
  {"op":"create","type":"scene","slug":"mira-tells-kael",
   "frontmatter":{"title":"The Telling","sequence_id":"act-one","act_id":"act-one",
                  "status":"drafted","time_of_day":"DUSK","location":"central-room",
                  "characters":["mira","kael"],"value_at_open":"hope",
                  "value_at_close":"doubt","shift":"honesty costs her the only leverage she had",
                  "dramatic_role":"crisis","is_sequence_climax":true},
   "sections":{"Objective":"Mira confesses the reservoir is already failing.",
               "Conflict":"Kael trusts the plan more than he trusts her.",
               "Notes":"She has never told anyone. He reads it as manipulation."},
   "summary":"New scene: The Telling"},
  {"op":"edit","entity_type":"location","entity_id":"central-room",
   "data":{"mood":"claustrophobic warmth"},
   "summary":"The room tightens once Mira speaks"},
  {"op":"reorder","entity_type":"sequence","entity_id":"act-one",
   "ordered_ids":["arrival","mira-tells-kael","the-fall"],
   "summary":"The Telling lands mid-sequence"}
])
```

The agent's reply — the preview block is the whole message:

> I've drafted this rather than saving it. Nothing is in the database yet.
>
> ---
>
> ### 📝 Draft `d-4c1f` — *Mira tells Kael — goes badly*
> **save-the-children** · 3 changes · staged just now
>
> ---
>
> **＋ NEW SCENE** · `scene/mira-tells-kael`
>
> | field | value |
> |---|---|
> | title | The Telling |
> | status | drafted |
> | sequence · act | act-one · act-one |
> | time / location | DUSK · central-room |
> | characters | mira, kael |
> | value | hope → **doubt** |
> | shift | honesty costs her the only leverage she had |
> | dramatic role | **crisis** · sequence climax |
>
> **Objective** — Mira confesses the reservoir is already failing.
> **Conflict** — Kael trusts the plan more than he trusts her.
> *Notes* — She has never told anyone. He reads it as manipulation.
>
> ---
>
> **✏ EDIT** · `location/central-room`
> `mood`: ~~neutral institutional~~ → **claustrophobic warmth**
>
> **↕ REORDER** · `sequence/act-one`
> `arrival` → **`mira-tells-kael`** → `the-fall`
>
> ---
>
> ⚠️ **Not yet checked:** Kael's `character_value_at_close` in the next scene
> still assumes he trusts her. This draft will leave that un-updated.
>
> ---
>
> Say **save it** to write all three, or tell me what to change and I'll
> restage. Nothing is written until you do.

**Design questions this raises:**

1. Should the warning block be in the preview at all, given stage-time
   validation is shape-only? Here it flags a *cross-entity* inconsistency,
   which the design says can't be checked at stage time. Either it comes from
   the agent's own reasoning (fine — it's prose, not plugin output) or the
   design is wrong. **Decide which.**
2. Is `mood: neutral institutional → claustrophobic warmth` the right density
   for an edit, or should edits get the same table treatment as creates?
3. The unfilled fields are invisible. A scene with 6 of 22 fields set reads as
   complete here. **Should the preview show what is still empty?**

---

## Turn 2 — the user revises

> **user:** the shift is too neat. and don't resequence, it's fine where it is

> Understood. Restaging `d-4c1f` with the resequence dropped and the shift
> rewritten.
>
> ---
>
> ### 📝 Draft `d-4c1f` — *Mira tells Kael — goes badly* — **updated**
> **save-the-children** · 2 changes · restaged just now
>
> ---
>
> **＋ NEW SCENE** · `scene/mira-tells-kael`
>
> | field | value |
> |---|---|
> | title | The Telling |
> | status | drafted |
> | sequence · act | act-one · act-one |
> | time / location | DUSK · central-room |
> | characters | mira, kael |
> | value | hope → **doubt** |
> | shift | she trades the only leverage she has for being believed, and isn't |
> | dramatic role | **crisis** · sequence climax |
>
> **Objective** — Mira confesses the reservoir is already failing.
> **Conflict** — Kael trusts the plan more than he trusts her.
> *Notes* — She has never told anyone. He reads it as manipulation.
>
> ---
>
> **✏ EDIT** · `location/central-room`
> `mood`: ~~neutral institutional~~ → **claustrophobic warmth**
>
> ---
>
> *(reorder dropped)*
>
> Say **save it** to write both, or tell me what to change.

**Design question:** restaging replaced a 3-op list with a 2-op list. The user
never said "discard the reorder" as a separate act — the agent inferred it from
"don't resequence". That inference is invisible unless the preview marks what
changed since last stage. **Should the restage diff against the previous
version?** It is the single most confusing thing in this exchange.

---

## Turn 3 — the user commits

> **user:** save it

> ```
> story_draft(action="commit", project="save-the-children", draft_id="d-4c1f")
> ```

> Saved. Both changes are in `save-the-children`.
>
> ---
>
> ### ✅ Draft `d-4c1f` committed
>
> | | |
> |---|---|
> | **＋ scene/mira-tells-kael** | created · order 2 in act-one |
> | **✏ location/central-room** | `mood` → claustrophobic warmth |
>
> Still true, and still unaddressed: Kael's `character_value_at_close`
> downstream assumes he trusts her. Want to stage that next?

**Design question:** the commit response is much terser than the stage preview.
Is that right — the user has already read the detail — or should commit
re-show the diff for the record?

---

## Turn 4 — what a failure looks like

Not a mock of a *desired* interaction, but of the response the design's
partial-failure guarantee produces:

> ```
> story_draft(action="commit", project="save-the-children", draft_id="d-9a7e")
> → {"success": false, "committed": [0], "failed": 1,
>    "error": "Sequence not found: act-two",
>    "message": "1 of 2 changes was written. Draft d-9a7e kept so you can retry."}
> ```

> ⚠️ **Partly saved.** 1 of 2 changes wrote, then it stopped.
>
> | | |
> |---|---|
> | ✅ **scene/mira-tells-kael** | created |
> | ❌ **reorder/act-two** | failed — no such sequence |
>
> The draft is still open, so nothing is lost. The scene above is now in the
> database. Want me to fix the sequence id and commit just that part?

**Design question, and it's the important one:** the user is now looking at a
project where one thing from the draft is saved and the rest is not. The draft
row makes it recoverable, but nothing in the *chat* says "you are in a mixed
state" except this message. Is one clear warning enough, or should commit
offer to re-stage the remainder as a fresh draft automatically?

---

## Turn 5 — listing after a `/new`

> **user:** what were we working on?

> ```
> story_draft(action="list", project="save-the-children")
> ```

> You have one open draft in **save-the-children**:
>
> | draft | summary | staged |
> |---|---|---|
> | `d-2b8e` | Rewrite the ending — Kael walks | 2 days ago |
>
> Want to see it before deciding anything?

**Design question:** `d-2b8e` is 2 days old and names entities the project may
have moved past. Should `list` say anything about staleness, or is age
information enough for the agent to ask the right question?

---

## Presentation decisions

Settled against the mock in `chat-preview.md`. The plugin contributes exactly
one thing per turn — the **preview block**, relayed verbatim from `preview_md`.
Everything around it is the agent's prose, and stays that way.

**1. Unfilled fields: a count, not a list.** The preview header carries
`6 of 22 fields set`. A draft is *expected* to be incomplete, so the count is
the informative part; enumerating sixteen empty fields buries the six that
matter. `story_load(view="unfilled")` already exists for the full list — the
preview only has to make the user aware there is one. One line, no per-field
markers.

**2. Edits: one line per field, `before → after`.** A table is for a whole
entity; an edit is a delta. Two changed fields get two lines, not a five-row
table with one populated row. Strike-through for the old value, bold for the
new, which is what the mock already does and what reads well in the Hermes
chat.

**3. Restage diffs against the previous version. This is the load-bearing
one.** When a draft is re-staged, the preview marks what changed since the last
stage: ops added, ops dropped, values changed. Without it, "don't resequence"
produces a preview that silently omits a queued change and the user has no way
to know it was dropped rather than never proposed. Store the previous op list
in the drafts row (`prev_ops`) at restage; the diff is computed once, at stage.
Everything else here is cosmetic; this is the one interaction where the user
could hold a wrong belief about the state of their work.

**4. Commit confirmation is terse.** A one-line outcome per op. The user read
the full detail moments earlier in the same conversation; repeating it is noise.
The exception is partial failure, which gets the full treatment.

**5. Partial failure does not auto re-stage.** Commit reports what landed, what
failed and why, and asks. Auto re-staging would mint a second draft id for the
remainder, and two ids for one conversation is harder to reason about than one
id plus a question. The agent re-stages when the user answers.

**6. `list` reports id, summary, age and op count. No staleness verdict.** The
plugin cannot know whether a two-day-old draft is still relevant — that depends
on what happened in the project since, which it does not model. Age plus op
count is enough for the agent to ask a sensible question. A computed "probably
stale" would be a guess dressed as a signal.

**7. The cross-entity warning is the agent's prose, not plugin output.** The
design's stage-time validation stays shape-only, because
`validate_plot_characters` / `validate_scene_act_id` / `validate_arc_parents`
each open their own connection and read committed state — a staged create's slug
is not there yet, so a plugin-emitted cross-entity warning would be wrong more
often than right. The agent *can* notice the inconsistency by reasoning over
what `story_load` returned, and saying so in prose is honest about where it
came from. The plugin's `validation` field in the stage result carries shape
findings only.
