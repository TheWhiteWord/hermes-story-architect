# 01 — `view='story_value'` — REVISED

Project: `browser-verification-test` · Raw: `01-story-value.json` · **1,415 bytes** (was 552)

## Shape

```
view: "story_value"
act: "all" | <act id>
story_value: str            # the project's value
value_at_open: str          # its charge at the start
value_at_close: str         # its charge at the end
acts: [{id, title, value, value_at_open, value_at_close, sequences[…]}]
        sequences: [{id, title, value, value_at_open, value_at_close, scenes[…]}]
                scenes: [{id, title, value, value_at_open, value_at_close}]
```

Four levels: project → act → sequence → scene. Every container titled.

## Changes made after review

**1. Sequences now carry `title`.** Previously `seq-discovery` and
`seq-confrontation` with no way to tell them apart without a second call. The
row was already being fetched for the value; the name came free.

**2. Scenes included under each sequence.** This was not cosmetic — it was
hiding a real divergence. Every scene in the project already carried
`value` / `value_at_open` / `value_at_close` in the schema; the view just never
read them. With scenes in, the project's actual value structure appears:

```
act-1 / seq-discovery      Trust    positive → negative
  central-room-day         Trust    positive → negative
  central-room-night       Trust    negative → positive   ← turns
  the-core-day             Trust    positive → positive

act-2 / seq-confrontation  (unset)
  garden-day               Hope     positive → mixed      ← a different value
  garden-dream             Hope     positive → negative
  the-door-closes          Freedom  negative → positive   ← a third value
```

The mainline is `Trust`. Act-2 carries no value of its own, and its three
scenes run `Hope`, `Hope`, `Freedom` — a thread the containers do not describe
at all. Before this change the view showed act-2 as four empty strings and the
`Hope`/`Freedom` thread was invisible in every value surface the plugin had.

Scenes are also where the value actually *moves*; a container's charge is a
summary of its scenes, not an independent fact. `central-room-night` is the only
place in the project where Trust flips negative→positive, and the view could not
show it.

## Read

**Good:**

- Answers exactly one question — "how does the value move?" — which is the point of a per-view call.
- `act` filter reaches all four levels, verified: `act=act-1` returns its one
  sequence and its three scenes.
- Project `value_at_close: "ironic"` against act-1 closing `negative` is
  correct, not a contradiction: the project closes where the **whole** story
  closes, act-1 where act-1 closes. Reading both, the model can tell "this act
  turns" from "the story turns".
- 1,415 bytes for a four-level value map across 6 scenes, 2 sequences, 2 acts.
  Still the cheapest view in the tool.

**Gaps:**

1. **Empty containers print four empty strings.** `act-2` and
   `seq-confrontation` return `value: ""`. That is a real "not written yet"
   state, and `view='unfilled'` owns that question — but here it is
   indistinguishable from a scene that legitimately has no shift. Omitting
   empty containers would lose the fact that act-2 exists at all, so this is a
   genuine trade-off rather than an oversight.
2. **The thread is visible but not summarised.** `Hope` and `Freedom` appear
   only as per-scene values; nothing says "this is a second value running
   parallel to the mainline". Deriving that means reading every scene. A
   `values: [...]` roll-up at the act level would make it one glance — but it
   is inference, not stored fact, and would need deciding what counts as
   distinct.

**Verdict:** the view now answers the question it exists to answer. 625 tests
pass, including one asserting every non-deleted scene in the DB appears here —
a scene silently missing from the value view is a value turn the reader cannot
see, which is the exact failure this view was hiding.
