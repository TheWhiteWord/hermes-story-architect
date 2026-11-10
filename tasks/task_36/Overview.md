# SCRIPT EDITOR

## The core idea

Keep the Fountain text in the scene's `Content` section as the single source of truth. The editor is a structured view over it, not a new format. The agent and the user then edit the same artifact. The editor holds a list of typed blocks (`action`, `character`, `parenthetical`, `dialogue`, `transition`, `note`) and serializes them to Fountain on save. Each block is an auto-growing `<textarea>`, not one big `contenteditable`. That is much more robust, and it has no browser quirks (your mock looks like Firefox).

Parsing stays server-side, so we don't port the lexer's Python-`regex` Unicode patterns to JS. Block types are explicit in the editor, so the lexer only runs when a scene is opened or when text is pasted.

The serializer has one catch. `classify_line` treats any line with no lowercase letters as a character cue. The serializer therefore has to emit `!` for all-caps action lines like `RAIN HAMMERS.` and `@` for cues like `McCOY`, or a save will silently reclassify blocks. I'll verify that the lexer honours both markers.

## Writing: a direct user write path

Today the browser is read-only, and writes go through agent drafts that the user approves. A human edit doesn't need approval. I'd add `PUT /api/projects/{slug}/scenes/{scene}/script` calling `core.writes.edit_entity` once, so the content and the scene fields change in one transaction. The existing middleware already requires the `x-story-architect` header on writes.

The request carries a `base_hash` of the content as loaded. If Hermes committed in the meantime, the server returns 409. Your SSE `update` event already tells the UI when that happens. If the editor is dirty, it shows a banner offering "Review" or "Keep mine".

## Heading, location and time of day

The heading block is generated, not typed. It's three inline controls: INT/EXT, a location picker, and a time-of-day select. They produce `INT. KITCHEN - NIGHT`, and `Content`'s first line and `scene.heading` are written from that one value. That also satisfies your linter's "first line must be a heading" rule.

- **Location set:** the registered location's name fills the heading.
- **Heading typed or imported first:** I'd reuse `extract_location` and `match_location` from `screenplay.py` and suggest "Matches *Kitchen*, link it?". It would never link silently.
- **No match:** the heading keeps the free text, `scene.location` stays empty, and a critical warning appears.
- **Custom heading:** forced headings like `.SNIPER SCOPE POV` get a "custom heading" toggle that disables the controls.
- **Where to set the location (your open question):** the heading's location control is the primary place, and the Settings chip's "+" opens the same picker. The schema has a single `location`, so "+" really means "set or change" and "−" means clear. The world tag is derived from `location.world`, and a chip with no world is styled as a critical warning.

## Unregistered characters, with no new scene field

The script is the persistence. On open and on save, the cast is derived from the character cues:

1. Normalize each cue (strip `(V.O.)`, `(CONT'D)`, case).
2. Resolve it with `match_character`, so `OAK` still matches `Detective Oak`.
3. Registered characters appear as role-coloured chips. Unresolved ones appear as dashed neutral chips with a warning. Nothing is stored for them.

The element picker's list is the registered cast, then other registered characters, then ad-hoc names already used in this scene. Names used in other scenes' scripts can be included too, since the dashboard already loads all the script text. The last entry is "Use 'DET' (unregistered)". Each ad-hoc chip gets an "Ask Hermes to create this character" action through your existing `data-hermes-send` hook.

`scene.characters` on save equals the registered characters found in the script plus any added manually with "+". Cast "−" should be disabled with a reason ("speaks in 3 cues") while cues still exist. Otherwise the next save would quietly re-add the character.

## Warnings

One server function, `scene_script_findings(...)`, returns `{level, code, message, anchor}`. The anchor is a block index or a field name, so a click jumps to the problem. Unregistered cues also get an inline dotted underline.

- **Critical:**
  - unregistered characters
  - unregistered location
  - location with no world
  - missing or invalid heading (reusing `check_scene_content`)
  - `order == 0`
  - empty `time_of_day`
  - no `plot_roles` while `dramatic_role` isn't `transition` or `non-event`
- **Others:** optional fields such as objective and one-sentence summary.

The field warnings can't be fixed in the editor, so each one gets a "Fix with Hermes" button, which is also how reordering a scene (`order`) gets done.

## Entry points and integration

- **Scene panel:** the content preview is replaced by your first mock, a card with a 2-line clamp, stats, a format badge and "Open script".
- **Script view:** clicking a scene opens the editor on that scene, near the clicked line. Today `sceneIds[i]` is matched to headings by index, so a scene with no heading shifts every later click. The editor fixes this.
- **Overlay:** it covers the content area but leaves the chat panel visible, as in your mock, so entities can still be referenced in chat.
- **Routing:** I'd use a hash route like `#/p/demo/script/<scene>`, so back, deep links and refresh work. The unsaved-changes guard covers navigation too.
- **Files:** `web/js/script-editor/{model,ui,warnings}.js`, `web/css/script-editor.css` (reusing `screenplay.css`'s `.fountain-*` classes so the page matches the script view), `app/routes/scripts.py`, and `core/scene_script.py` with the cast resolution, findings and serializer. It follows your `DASH.*` globals and needs no build step.

## Mock feedback

- Move the warnings box out of the page. It overlaps the paper and is cut off. A collapsible footer drawer next to "Show warnings" with badge counts (●3 · ○5) would work better.
- "Scene heading" shouldn't be in the element list, since the heading is generated. The list becomes a type switcher for the current block.
- Show the scene as `07 · The Kitchen` with an "unordered" badge when `order` is 0.
- "Format OK" in the card should reflect the warnings, e.g. "Format OK · 2 critical".
- "42 lines" next to such a short script needs a definition. Is it text lines, dialogue lines, or pages? "Speaking parts" should mean distinct speakers.
- The mock has "Critcal" as a typo in the warnings box.