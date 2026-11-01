# Specialist request -Editor

## Checklist

- [x] **Direct writes:** is a UI-initiated write acceptable given the README's "token-free and read-only" stance? The route would be protected only by the Host, Origin and custom-header checks.
- [x] **`edit_entity`:** does it accept `Content`, `heading`, `location`, `time_of_day` and `characters` together, and are `location` and `characters` refs validated?
- [x] **Change token:** is there an `updated_at` or version on sections or entities, or should I hash the content?
- [x] **Dashboard payload:** does it expose per-scene `Content`, `location` (slug), `time_of_day`, `plot_roles` and `location.world`? `scenes.js` reads `s.locations`, but the schema has a single `location`.
- [x] **Multiple locations:** can a scene ever have more than one?
- [x] **INT/EXT:** I'd keep it in the heading only, with no new field. Agree?
- [x] **Cue names:** should the cue be the character's display name uppercased, or is there an alias or short-name field (`OAK` versus `DETECTIVE OAK`)?
- [x] **Status:** should saving bump `planned` to `drafted`, and should `locked` scenes open read-only?
- [x] **Existing gaps logic:** is there a function behind the "characters unfilled" gap that I should reuse for the warnings?
- [x] **Undo:** is there any history for sections, or should save snapshot the previous content? `story_backup` exists.
- [x] **Router:** how does `navigation.js` handle hash routes, so the editor route fits in?

## Answers

### 1. Direct writes
Yes, with caveats. Transport already permits non-GET writes when Host is localhost, Origin is own/absent, and `X-Story-Architect: 1` is present (server.py middleware). The README's "token-free and read-only" describes the intended browser posture, not a hard gate; `/mcp` is the token-gated surface. So a UI write endpoint is acceptable **only** if it (a) goes through the same middleware, (b) stays on localhost, and (c) is documented as the one exception. Do not introduce a second auth model. Recommend documenting the exception in README; otherwise agents/users will assume writes are forbidden.


### 2. edit_entity
Yes. `Content` is a standard section for scene; `heading`, `location`, `time_of_day`, `characters` are schema fields/columns. edit_entity applies them in one transaction (column_updates + section_updates + relation rewrite). Validation: shape validation runs; `plot_roles` has its own validator; location/characters are **not** declared as `ref` on the scene schema, so `check_references` does not validate them. Location existence is not checked in edit_entity (column write only). If you need strict validation, add it before write; otherwise invalid slugs land silently.

### 3. Change token
No `updated_at`/version exists on entities or sections. Use a content hash (hash of the section body + relevant fields) as the change token.

### 4. Dashboard payload
Payload exposes single `location` slug; dashboard normalizes to `s.locations` array (core.js). `time_of_day`, `plot_roles` available. `location.world` is the location's `parent_id`. `Content` is a section; dashboard payload includes sections (normalize in core). Use normalized fields.

### 5. Multiple locations
No. Schema has single `location` slug per scene. Use one.

### 6. INT/EXT
Agree. Keep in heading only; no new field.

### 7. Cue names
No alias/short-name field. Use character display name uppercased.

### 8. Status
No auto bump. Saving should not change status. `locked` scenes should open read-only in UI (enforce client-side; backend doesn't gate).

### 9. Existing gaps logic
Reuse gap logic: `characters` unfilled when empty and `no_cast` false. Check no_cast handling.

### 10. Undo
No section history. `story_backup` creates timestamped DB copy. Snapshot previous content before save if undo needed.

### 11. Router
Hash routes like `#/p/<slug>`. Editor route fits as `#/p/<slug>/scene/<id>/edit` or similar.
