# PHASE 1 - EDITOR BACKEND

Phase 1 (the backend) is done and ready to apply with `git apply script-editor-phase1-backend.patch`. It applies cleanly to a fresh clone of `dev`.

The full suite gives 1096 passed and 1 failed. The failure is `test_no_hermes_imports`, which flags the word "hermes" in `app/config.py`. It fails the same without my changes, so I left it alone. The 65 new tests cover the pure model, the DB layer, and the HTTP routes including the middleware.

## Code organisation (your note on manual vs agent writes)

It does matter, and the split is cheap to make now:

- **`core/scene_script.py`** is pure logic with no DB: parse and serialize blocks, heading parts, cast resolution, findings, and stats.
- **`core/manual_edits.py`** holds writes authored by a person in the UI. It validates what a UI can get wrong, then calls the same `core.writes.edit_entity` that agent commits use, so an edit means one thing in one place. Manual entity creation can later be added here as another function that validates and then calls `core.writes`.
- **`app/routes/scripts.py`** is a thin HTTP layer: `GET` and `PUT /api/projects/{slug}/scenes/{scene}/script`, plus `POST …/script/parse` for pasted text.

The README now documents this as the one browser write exception, as you suggested.

## Behaviours worth checking

- **One save writes everything.** `Content`, `heading`, `location`, `time_of_day` and `characters` go in one `edit_entity` call. The heading line in the script and the scene's fields can't drift apart. It never touches `status`.
- **Stale saves are refused.** Each load returns a hash, and a save must present it. If Hermes committed in between, the save returns 409 with the current hash and nothing is written. The save response includes `previous_content`, so the UI can offer an in-session undo.
- **Round-tripping is verified, not assumed.** A scene whose Fountain the editor can't round-trip without losing words loads as `locked: true` (`not_roundtrippable`), and the editor will open it read-only. The serializer adds `!` or `@` only where plain text would be misread. A fixture test checks the blocks against the lexer on your real scene content.
- **Cue matching is strict.** It matches the full name, the slug, or whole words that identify exactly one character, so `OAK` resolves to `Detective Oak`. It deliberately does not match prefixes or fuzzy names: `DET` stays unregistered, as in your mock. If two characters share a word, the cue resolves to nothing and the warning lists the candidates. I didn't reuse `screenplay.match_character`, because its substring and fuzzy rules would silently link `DET` and `MA`.
- **Backend checks for the gaps you flagged.** The backend refuses a `location` or an `extra_cast` slug that doesn't exist, since `edit_entity` doesn't check them. It also refuses `locked` scenes. You said locked is client-side only; I added the server check because it's one line and the UI can be bypassed. Say so if you'd rather drop it.
- **Order 0 is hard to reach.** `create_entity` appends an undecided order at the end, so a new scene never sits at 0. The "order unset" warning therefore only fires for scenes someone deliberately un-placed, or imported at 0. That fits your edge-case description, but check it against how scenes really end up at 0.
- **Stats.** `lines` counts non-blank text lines, as you described. `speaking_parts` counts distinct speakers. I also return `words`. Pages would be the more useful figure than `lines`, but it needs a convention of your choosing, so I left it out.

## Not yet done

The editor UI and the entry points are phases 2 and 3: the scene-panel card, the script-view click-through, and the `#/p/<slug>/scene/<id>/edit` route. Before starting phase 2 I'd like to read how `navigation.js` handles hash routes and how the overlay should sit next to the chat panel. I haven't verified either yet.

Shall I go ahead with phase 2, the editor overlay (block editing, the element switcher, the heading controls, the cast and settings chips, and the warnings drawer)?