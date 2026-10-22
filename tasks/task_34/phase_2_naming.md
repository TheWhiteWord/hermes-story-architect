# Phase 2 — Naming and brittle coupling

**Goal.** Names that say what they mean, and no reader reaching into another
module's output as a string.

**State on entry.** Phase 1 is done: the tabs load and render. This phase is
consistency and robustness only — no behaviour change, no new surface.

**Status.** Complete. 2.1–2.4 landed; 2.5 verified (41 node checks, 25
headless-Chrome checks, full suite green).

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

- [x] Rename the JS field to `deepestRung` in `track-data.js` and update the one
      consumer in `character-journey-tab.js`.
- [x] Leave `core/track.py` alone — it is the LLM-facing contract and its name
      is documented there.
- [x] Add a one-line assertion in the node/JS check that `paths[0].deepestRung`
      is a number in `0..3`, so the index/word confusion cannot come back.

**Deviation, recorded.** The brief says "the node/JS check" as though one is in
the repo. There is none: Phase 1's 44 checks live in the scratch harness
`~/.hermes/cache/scratch/t34_harness.js`, and Phase 4.2 is what gives them a
permanent home. The assertion went into that harness — it already loads
`track-data.js` and `value-graph.js`, which is all `characterTrack` needs —
rather than into a file that does not exist. It now asserts `deepestRung` is
`null` or a number in `0..3` for **every** path, which is stronger than checking
`paths[0]`, and it fails on the word form. The harness's own pre-existing check
still asserted `tr.paths[0].deepest`; updated with it.

### 2.2 — `is-self` is emitted and never styled

`scene-beats-tab.js:91` adds `is-self` to the self-directed arrow. There is no
`.sb-link.is-self` rule anywhere — the class is dead, and the arrow reads as
inner conflict only because of its path shape.

Two honest options; pick one and delete the other:

- [x] Give it a rule (it is the one visual cue that a beat is inner conflict,
      which is a checkable fact in the design), **or**
- [ ] Delete the class and the `same` ternary, leaving the path shape to carry
      it.

**Choice: the rule.** Two reasons. `core/constants.py:313` already states the
fact as checkable — "the same character on both sides means inner conflict" —
so it is a real distinction the design wants visible, not decoration. And
`is-self` was already load-bearing: it is what made the arrow's head land
mid-path instead of on the answering bubble, which for a self-directed arrow is
not where the arrow ends. The path alone cannot carry that; deleting the class
would have put the head back on the wrong side.

**Rule landed** (`scene-beats.css`): `.sb-link.is-self` takes the actor's lane
colour at 78% and drops the dash — a closed loop in one colour is the one shape
in the tab that cannot be read as an exchange between two parties. `.sb-a`/`.sb-r`
were given the lane colour for their own arrows, so a beat is legible as
"from X to Y" and a self-directed one as "X alone".

**Fixed while here.** The arrowhead was positioned at `xb` unconditionally, which
for a self-directed arrow is a coordinate that does not exist on the path — the
path returns to `xa`, so the head was drawn at 94% of a curve whose last point is
at 50%. It is now `same ? xa + 44 : xb`, the turn the arrow actually comes back
from. Verified in the rendered SVG: `is-self` → `M 50 0 C 94 1 94 21 50 22`,
tip at 94; the two exchange arrows → `M 25 0 C 25 13 75 9 75 22` and back.

### 2.3 — The journey ribbon edits the value graph's SVG output

`character-journey-tab.js:132` calls `D.valueAxisSvg(view, geo)` and then
string-replaces `'>beats</text>'` with `'>plot</text>'`. It works today and
silently no-ops if that label is ever reworded — the axis would say "beats" on a
character's journey, with no error.

- [x] Give `D.valueAxisSvg` a `beatLabel` parameter (default `'beats'`) and use
      it at `value-graph.js:171` where `rowLabel('beats', 50)` is written.
- [x] Pass `'plot'` from the journey tab; delete the `.replace()` chain.
- [x] Check the value graph's own callers still pass nothing and get `'beats'`.

**Landed.** Signature is `valueAxisSvg(model, geo, plotId, beatLabel)`;
`rowLabel(beatLabel || 'beats', 50)`. The journey tab passes `'plot'` and the two
`.replace()` calls that stripped the SVG wrapper remain, since the ribbon needs
the inner markup only. Verified in node: the story and plot graphs still emit
`>beats</text>`, and the journey ribbon emits `>plot</text>` with no `beats`
anywhere — asserted on the real `renderCharacterJourney` output, not on a hand
built string.

### 2.4 — Hard-coded entity colours in `entityRef`

`track-data.js:43,45` hard-code `#6bbfb0` (location) and `#e0a86b` (world). Those
are the same values as `--role-supporting` and `--role-rival`, and the character
branch already goes through `D.roleColor`.

- [x] Replace the two literals with the tokens. Confirm the rendered chips match
      the plot chips for the same entity in a screenshot or DOM assertion.
      *(The role tokens turned out to be the wrong target — see the deviation
      below. Landed as one colour table read by `entityRef` and the two views.)*

**Deviation, recorded — the brief's own fix would break its own goal.** The task
says "replace the literals with the tokens" and, in the same breath, "confirm
the chips match the plot chips". They cannot both hold, because the entity views
do not use those tokens for these kinds:

| reader | what it emits for a location | what it emits for a world |
|---|---|---|
| `views/locations.js:24` | hard-coded `#6bbfb0` | — |
| `views/worlds.js:23` | — | hard-coded `#e0a86b` |
| `components.css` `.tag-location` | `#6bbfb0` | `#e0a86b` (`.tag-variant`) |
| `colors.js` `REL_TYPE_COLORS.ally` | `#6bbfb0` | — |
| `colors.js` `REL_TYPE_COLORS.professional` | — | `#e0a86b` |

So `--role-supporting` is **not** "the token for a location" — it is the token
for the *supporting* role, and `roleColor('supporting')` returns `#6bbfb0`. A
location chip in that colour is indistinguishable from a supporting character,
and an ally relationship chip is the same teal again. The token would have
silently merged three kinds into one colour, which is the exact class of defect
this phase exists to remove.

**Landed instead.** One table, `DASH.ENTITY_KIND_COLORS` in `colors.js` — the
JS colour map, which `JS_ORDER` loads first, so `track-data.js` and the views can
both read it. The two `entityRef` literals, and the two hard-coded pips in
`views/locations.js` and `views/worlds.js` that the brief's "confirm they match"
was really about, now all read it. Four copies became one, and the chips and the
cards are the same colour by construction rather than by coincidence.

**Confirmed by DOM assertion, not screenshot.** `entityRef` on the real payload:
`the-office` → `#6bbfb0` (matches `views/locations.js`), `the-institute` →
`#e0a86b` (matches `views/worlds.js`), characters still through `roleColor`
(`kael` → `#7b9cf0`, `admin` → `#e07070`, `mira` → `#6bbfb0`).

### 2.5 — Verify

- [x] Re-run the node harness (44 checks) and the headless-Chrome harness.
- [x] Full suite green.

Node harness: 41 checks, all green, plus the 3 source-level checks Phase 1 ran
= the 44. Headless Chrome: 25/25, from the assembled page, both tabs. Full suite:
green.

## Parallel work

None inside this phase. **Phase 3 also edits `character-journey-tab.js`**, so it
waits for this phase to land.

## Checklist

- [x] `deepestRung` renamed; `core/track.py` untouched
- [x] `is-self` resolved one way, not left dangling
- [x] `valueAxisSvg` takes a label parameter; the `.replace()` chain is gone
- [x] `entityRef` reads one colour table, not its own hex literals
- [x] Node and Chrome harnesses green
- [x] Full suite green

## What Phase 3 inherits

`character-journey-tab.js` is now safe to edit: it reads `deepestRung`, and the
axis label is a parameter it passes rather than a string it rewrites. Nothing in
this phase changed how the ribbon is sized, which is Phase 3's whole subject —
`MAX_SLOT` and the geometry are untouched.
