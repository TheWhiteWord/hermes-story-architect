# Values view — real outputs (`story_load view='values'`)

Generated from the live handler against the `browser-verification-test`
project (post Phase 8 conversion: one value entity, `trust`). Each section is
one call and the exact JSON the tool returns.

The view has three shapes (design doc §5):

| Call | Returns |
| --- | --- |
| no arguments | Every value with its schema — the one command to see what exists |
| `scene=<id>` | Sequence/act `value_focus`; per plot the scene serves: its values with `last_left`/`next` — read before evaluating a scene |
| `plot=` / `sequence=` / `act=` (opt. `value=`) | The unit's `value_focus` (major/minor) + per value its turns in story order |

---

## 1. No arguments — every value with its schema

```json
{
  "view": "values",
  "values": [
    {
      "value": "trust",
      "id": "trust",
      "p": "self-trust",
      "c": "doubt",
      "cd": "suspicion",
      "nn": "self-deception",
      "note": "Whether Kael can trust their own read of the world."
    }
  ]
}
```

## 2. `scene=central-room-day` — before writing an early scene

The scene's sequence and act both count `trust` in 2 scenes. On the plot it
serves, `trust` has a `next` turn (where the value is headed) and no
`last_left` yet — this is the first scene of the story.

```json
{
  "view": "values",
  "scene": "central-room-day",
  "sequence": "seq-discovery",
  "act": "act-1",
  "sequence_focus": {"major": [{"value": "trust", "scenes": 2}], "minor": []},
  "act_focus": {"major": [{"value": "trust", "scenes": 2}], "minor": []},
  "plots": {
    "the-resistance": {
      "values": [
        {
          "value": "trust",
          "schema": {"id": "trust", "p": "self-trust", "c": "doubt", "cd": "suspicion", "nn": "self-deception", "note": "Whether Kael can trust their own read of the world."},
          "next": {"scene": "central-room-night", "from": "suspicion"}
        }
      ]
    },
    "the-scientists-last-stand": {"values": []}
  }
}
```

## 3. `scene=the-core-day` — the last scene

Same shape; `trust` now shows `last_left` (the-door-closes closed on
`self-trust`) and no `next` — nothing follows it.

```json
{
  "view": "values",
  "scene": "the-core-day",
  "sequence": "seq-confrontation",
  "act": "act-2",
  "sequence_focus": {"major": [{"value": "trust", "scenes": 4}], "minor": []},
  "act_focus": {"major": [{"value": "trust", "scenes": 4}], "minor": []},
  "plots": {
    "the-resistance": {
      "values": [
        {
          "value": "trust",
          "schema": {"id": "trust", "p": "self-trust", "c": "doubt", "cd": "suspicion", "nn": "self-deception", "note": "Whether Kael can trust their own read of the world."},
          "last_left": {"scene": "the-door-closes", "to": "self-trust"}
        }
      ]
    },
    "the-scientists-last-stand": {"values": []}
  }
}
```

## 4. `plot=the-resistance` — the full line, in story order

```json
{
  "view": "values",
  "unit": "plot",
  "plot": "the-resistance",
  "value_focus": {"major": [{"value": "trust", "scenes": 6}], "minor": []},
  "values": [
    {
      "value": "trust",
      "schema": {"id": "trust", "p": "self-trust", "c": "doubt", "cd": "suspicion", "nn": "self-deception", "note": "Whether Kael can trust their own read of the world."},
      "turns": [
        {"scene": "central-room-day", "plot": "the-resistance", "from": "self-trust", "to": "suspicion"},
        {"scene": "central-room-night", "plot": "the-resistance", "from": "suspicion", "to": "self-trust"},
        {"scene": "garden-day", "plot": "the-resistance", "from": "self-trust", "to": "self-trust"},
        {"scene": "garden-dream", "plot": "the-resistance", "from": "self-trust", "to": "doubt"},
        {"scene": "the-door-closes", "plot": "the-resistance", "from": "doubt", "to": "self-trust"},
        {"scene": "the-core-day", "plot": "the-resistance", "from": "self-trust", "to": "self-trust"}
      ]
    }
  ]
}
```

## 5. `sequence=seq-discovery` — one sequence's slice

```json
{
  "view": "values",
  "unit": "sequence",
  "sequence": "seq-discovery",
  "value_focus": {"major": [{"value": "trust", "scenes": 2}], "minor": []},
  "values": [
    {
      "value": "trust",
      "schema": {"id": "trust", "p": "self-trust", "c": "doubt", "cd": "suspicion", "nn": "self-deception", "note": "Whether Kael can trust their own read of the world."},
      "turns": [
        {"scene": "central-room-day", "plot": "the-resistance", "from": "self-trust", "to": "suspicion"},
        {"scene": "central-room-night", "plot": "the-resistance", "from": "suspicion", "to": "self-trust"}
      ]
    }
  ]
}
```

## 6. `act=act-2` — the act's sequences together

```json
{
  "view": "values",
  "unit": "act",
  "act": "act-2",
  "value_focus": {"major": [{"value": "trust", "scenes": 4}], "minor": []},
  "values": [
    {
      "value": "trust",
      "schema": {"id": "trust", "p": "self-trust", "c": "doubt", "cd": "suspicion", "nn": "self-deception", "note": "Whether Kael can trust their own read of the world."},
      "turns": [
        {"scene": "garden-day", "plot": "the-resistance", "from": "self-trust", "to": "self-trust"},
        {"scene": "garden-dream", "plot": "the-resistance", "from": "self-trust", "to": "doubt"},
        {"scene": "the-door-closes", "plot": "the-resistance", "from": "doubt", "to": "self-trust"},
        {"scene": "the-core-day", "plot": "the-resistance", "from": "self-trust", "to": "self-trust"}
      ]
    }
  ]
}
```

## 7. `plot=the-resistance&value=trust` — filtered to one value

Same as §4 here (one value total); the `value` filter narrows to that
value's turns when several exist.

```json
{
  "view": "values",
  "unit": "plot",
  "plot": "the-resistance",
  "value_focus": {"major": [{"value": "trust", "scenes": 6}], "minor": []},
  "values": [
    {
      "value": "trust",
      "schema": {"id": "trust", "p": "self-trust", "c": "doubt", "cd": "suspicion", "nn": "self-deception", "note": "Whether Kael can trust their own read of the world."},
      "turns": [
        {"scene": "central-room-day", "plot": "the-resistance", "from": "self-trust", "to": "suspicion"},
        {"scene": "central-room-night", "plot": "the-resistance", "from": "suspicion", "to": "self-trust"},
        {"scene": "garden-day", "plot": "the-resistance", "from": "self-trust", "to": "self-trust"},
        {"scene": "garden-dream", "plot": "the-resistance", "from": "self-trust", "to": "doubt"},
        {"scene": "the-door-closes", "plot": "the-resistance", "from": "doubt", "to": "self-trust"},
        {"scene": "the-core-day", "plot": "the-resistance", "from": "self-trust", "to": "self-trust"}
      ]
    }
  ]
}
```

## 8. `scene=nope` — the error shape

```json
{
  "view": "values",
  "scene": "nope",
  "error": "Scene not found: nope"
}
```

---

## Companion: `value_focus` via `story_retrieve`

The same major/minor counts are readable per unit with
`story_retrieve(fields=['value_focus'])` — the view above is the scene-facing
slice of the same computation:

| Entity | `value_focus` |
| --- | --- |
| plot `the-resistance` | major: trust × 6 scenes |
| act `act-2` | major: trust × 4 scenes |
| project `browser-verification-test` | major: trust × 6 scenes |
