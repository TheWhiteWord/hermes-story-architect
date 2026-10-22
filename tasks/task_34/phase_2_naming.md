# Phase 2 — Naming and brittle coupling

**Goal.** Names that say what they mean, and no reader reaching into another
module's output as a string.

**State on entry.** Phase 1 is done: the tabs load and render. This phase is
consistency and robustness only — no behaviour change, no new surface.

## Tasks

### 2.1 — `deepest` means two different things

- `core/track.py:227` builds `deepest` as the **word** of the deepest rung
  visited (`"imprisoned"`).
- `track-data.js` builds `paths[].deepest` as the **index** of that rung (`2`),
  and `character-journey-tab.js:124` renders it through
  `RUNG[p.deepest]` → `"CD"`.

Same field name, two types, two consumers. The LLM-facing `story_load` view says
one thing and the dashboard says another, which is exactly the shape of the key
renames this codebase has already been bitten by (`beat` → `role`, `BEAT` →
`CLIMAX`).

- [ ] Rename the JS field to `deepestRung` in `track-data.js` and update the one
      consumer in `character-journey-tab.js`.
- [ ] Leave `core/track.py` alone — it is the LLM-facing contract and its name
      is documented there.
- [ ] Add a one-line assertion in the node/JS check that `paths[0].deepestRung`
      is a number in `0..3`, so the index/word confusion cannot come back.

### 2.2 — `is-self` is emitted and never styled

`scene-beats-tab.js:91` adds `is-self` to the self-directed arrow. There is no
`.sb-link.is-self` rule anywhere — the class is dead, and the arrow reads as
inner conflict only because of its path shape.

Two honest options; pick one and delete the other:

- [ ] Give it a rule (it is the one visual cue that a beat is inner conflict,
      which is a checkable fact in the design), **or**
- [ ] Delete the class and the `same` ternary, leaving the path shape to carry
      it.

Do not leave it emitted and unstyled.

### 2.3 — The journey ribbon edits the value graph's SVG output

`character-journey-tab.js:132` calls `D.valueAxisSvg(view, geo)` and then
string-replaces `'>beats</text>'` with `'>plot</text>'`. It works today and
silently no-ops if that label is ever reworded — the axis would say "beats" on a
character's journey, with no error.

- [ ] Give `D.valueAxisSvg` a `beatLabel` parameter (default `'beats'`) and use
      it at `value-graph.js:171` where `rowLabel('beats', 50)` is written.
- [ ] Pass `'plot'` from the journey tab; delete the `.replace()` chain.
- [ ] Check the value graph's own callers still pass nothing and get `'beats'`.

### 2.4 — Hard-coded entity colours in `entityRef`

`track-data.js:43,45` hard-code `#6bbfb0` (location) and `#e0a86b` (world). Those
are the same values as `--role-supporting` and `--role-rival`, and the character
branch already goes through `D.roleColor`.

- [ ] Replace the two literals with the tokens. Confirm the rendered chips match
      the plot chips for the same entity in a screenshot or DOM assertion.

### 2.5 — Verify

- [ ] Re-run the node harness (44 checks) and the headless-Chrome harness.
- [ ] Full suite green.

## Parallel work

None inside this phase. **Phase 3 also edits `character-journey-tab.js`**, so it
waits for this phase to land.

## Checklist

- [ ] `deepestRung` renamed; `core/track.py` untouched
- [ ] `is-self` resolved one way, not left dangling
- [ ] `valueAxisSvg` takes a label parameter; the `.replace()` chain is gone
- [ ] `entityRef` reads tokens, not hex literals
- [ ] Node and Chrome harnesses green
- [ ] Full suite green
