# story_create

✅ **Finalized.** Source: `tools/story_create.py`. Tests: `tests/test_create_sections.py` (16).
Full suite 422 passed. No existing test needed changing.

Creates entities, and the whole project. The entry point for every write — `story_edit` sits
downstream of what this validates.

## Parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `entity_type` | enum(10) | yes | Rejected in-handler if unknown |
| `slug` | string | yes | Lowercase, hyphen-separated. For `project`, the folder name. |
| `project` | string | yes* | *not required for `entity_type: "project"`* |
| `frontmatter` | object | yes | Field values |
| `sections` | object | no | **New.** `{heading: prose}` |

## What was fixed

### 1. Prose passed at create time was silently dropped

The tool had no `sections` parameter. It created every standard section **empty** and ignored the
argument — so the most natural call, *"create this character and write who they are"*, lost the
prose and returned `{"success": true}`.

```json
{"entity_type": "character", "slug": "nova",
 "frontmatter": {"name": "Nova", "one_sentence": "X"},
 "sections": {"Identity": "A courier who talks too much.", "Notes": "Loves rain."}}
```

All standard sections are still created; the supplied ones are **filled**, not substituted — so
`story_load` shows a complete template. A heading that is *not* standard for the type is added as
written, because a scene may need one the schema has never heard of.

### 2. An unknown `entity_type` was inserted

The schema enum is advisory — an LLM can pass anything, and the handler never re-checked. A
`dragon` was happily inserted as a row and surfaced much later as a mystery.

```json
{"error": "Unknown entity_type: dragon",
 "valid_types": ["act", "arc_beat", "character", ...]}
```

### 3. The duplicate-id error named the wrong thing

Ids are global across types, but the check only compared ids, so creating a `world` with an id held
by a `character` said `"Entity already exists: world/shared"` — a claim that was simply false, and
would send the agent off inventing a different slug for no reason. The two cases now differ:

| Case | Response |
|---|---|
| Same type | `Entity already exists: character/kael` + *"use story_edit"* |
| Different type | `Id 'kael' is already used by a character.` + *"ids are unique across all types"* |

### 4. `ROLLBACK` in an autocommit connection

`get_db` sets `isolation_level=None`. The `except` handler called `conn.execute("ROLLBACK")`, which
in autocommit raises *"cannot rollback - no transaction is active"* — replacing the real error with
a confusing one. Now guarded, matching what `story_edit` already did.

Also: a bad `sections` value is rejected **before** the insert, so a rejected call cannot leave a
half-made entity behind.

## What a fresh entity actually contains

Verified for a `plot` created with only `{"name": "P1"}`:

- **Columns** — `name`, `one_sentence`, `status`
- **`extra` JSON** — every remaining field, defaulted
- **All 6 standard sections**, bodies `""`
- **Zero relation rows** — `setups`/`crisis`/`climax`/`payoffs` are `relations`, not columns, so
  nothing is stored until something links. `story_retrieve` synthesises them as `[]` on read.

### Defaults are not all `""` — some are UI placeholders

```
one_sentence: "Summary not set"
value_arc:    "Value arc not set"
```

Deliberate: the UI shows them so the user can see what still needs filling. The round trip is
lossless — export → wipe → re-import leaves `unfilled_fields` identical, so a placeholder never
decays into real content. They do appear in exported Markdown (`one_sentence: Summary not set`),
which is slightly odd in a published file but harmless.

**The rule that makes this safe:** a field is unfilled if it is *empty* **or** *still the default*.
See `unfilled_fields` in `core/entity.py` and `tests/test_unfilled_fields.py`.

Before that rule, clearing a field to `""` made the system think it was **filled** — the UI showed
a populated field with nothing in it. `status`, booleans and numbers are exempt (real values, not
absences), as are computed fields.

## Validation, all before insert

| Check | Behaviour |
|---|---|
| Slug | alphanumerics, hyphens, underscores only. Rejects `""`, `"a/b"`, `"../escape"`, spaces. |
| `arc_beat` parents | character and scene must exist |
| `scene.sequence_id` | must exist; `act_id` must match it |
| `plot.characters` | must reference existing entities |
| Duplicate id | see above |

## Ordering

Scenes and sequences auto-number within their parent when no `order` is given — the entity lands at
the end of its act/sequence rather than at 0.

## The response is thin, on purpose

```json
{"success": true, "message": "Created character: nova", "entity_id": "nova"}
```

No echo of what was written. To see it, `story_retrieve` — which also reports `unfilled_fields`,
the natural follow-up after a create. Keeping the response small is what makes the create →
retrieve → fill loop cheap in tokens.
