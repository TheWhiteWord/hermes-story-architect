# PHASE 2 - EDITOR UI

Phase 2 is done and packaged as `script-editor-phase2-ui.patch`. It applies on top of the phase-1 patch you already applied. I haven't seen the editor in a real browser, because there isn't one in my sandbox. Please open it once and check the styling against your mock.

## What was tested

- **Editor logic:** 43 checks run the dashboard's real JS in jsdom against a running server. They cover the keyboard flow, cue autocomplete, heading controls, cast and settings, save, conflict handling, paste, close and discard, a blank scene and a locked scene.
- **Integration edits:** the script-view click-through, the scene-panel card and the `boot()` fix run with the real modules.
- **Python suite:** 1100 pass. One fails, `test_no_hermes_imports`, which also fails without my changes (it flags "hermes" in `app/config.py`).
- **Not tested:** CSS and the visual layout, and a real browser. The paper margins, gutter labels and popup positions are the likeliest to need adjusting.

## What it does

- **Scene panel:** the content dump is replaced by your first mock's card: a 3-line preview, `N lines · N speaking parts`, a format badge ("Format OK" or "N critical"), and **Open script**.
- **Script view:** a click anywhere in a scene opens the editor on it, focused on the line you clicked. The scene panel is now reached from the editor's "Open scene" button. Say so if you'd rather keep a way to get there from the script view.
- **Editor:** it is an overlay inside `#main`, so the chat and the detail panel stay beside it. The URL is `#/p/<slug>/scene/<id>/edit`. Back, refresh and links work, and leaving with unsaved changes asks first.
- **Keyboard:**
  - Enter makes the next logical block.
  - Tab converts the current block.
  - Shift+Enter inserts a newline within a block.
  - `^1`–`^7` pick an element. I also accept Alt+digit, because browsers keep Ctrl+digit for tabs on some systems.
  - Ctrl/⌘ S saves and Esc closes.
- **Warnings:** they sit in a drawer under the page, as I suggested, with Go to and Ask Hermes buttons. They come from the server through a new `/check` endpoint, so there's no second copy of the rules in JS.

## Bugs the tests caught

- **Autocomplete took over Enter and Tab:** moving into an existing `MARA` cue and pressing Enter would have rewritten it to `MARA CHEN`. The list now opens on focus only for an empty cue, Enter never rewrites a name that already matches, and Tab always converts the block.
- **Chips lagged the controls:** the cast and settings chips waited about 450 ms for the debounced check. They now update immediately.
- **Missed external edits:** updates arriving within 6 seconds of your own save were ignored, so a Hermes edit in that window would be missed. It's now an exact hash comparison.
- **Dialogue click-through:** clicking a dialogue line passed `"MARAHi."` as the focus text, which matches nothing. It now uses the element clicked.

## Check these in a browser

1. **Re-reading data after a save.** Instead of reloading the page, `DASH.reloadData()` re-fetches the dashboard and calls `initStory` again, because a reload would discard anything else open. I tested the call, but it's the part most likely to misbehave against the real graph views. If something looks stale or doubled after a save, that's where to look.
2. **Autocomplete picking `Detective Oak` for `DET`.** Enter on a partial name accepts the top suggestion, as Final Draft does. The `Use “DET”` entry is one arrow-down away.
3. **Not in this phase:** an undo of the last save (the response already carries `previous_content`), highlighting from chat context, and dual dialogue, which stays as read-only raw Fountain.

Also, `script-view.js` calls `DASH.boot()` at the end, and `index.html` calls it again, so the project loads twice. That was already there. It's harmless, but worth removing.

I also added `tests/script_editor_harness.js` and `tests/script_editor_serve.py`. Like your existing JS harness, they run by hand. The usage is in the file headers, and they need `node` and `jsdom`.