# Phase 3 — The ribbon fills the panel

**Goal.** The journey ribbon uses the room the wide panel gives it.

**The finding.** Measured on the rendered page: with the panel at its wide
680px, the ribbon's SVG is 204px wide — **32% of the pane**. `.jr-scroll` is
`overflow-x: auto` but never overflows, so 443px sits empty to the right of the
chart.

**Cause.** `character-journey-tab.js:24,224`:

```js
const LABEL_W = 58, PAD_R = 8, MIN_SLOT = 12, MAX_SLOT = 46;
...
const slot = Math.min(MAX_SLOT, Math.max(MIN_SLOT, (W - LABEL_W - PAD_R) / Math.max(view.n, 1)));
```

`MAX_SLOT = 46` caps the per-scene column. For a 3-scene story the slot is
already 204px before the cap, so it clamps to 46 and `geo.W` lands at 204.

The value graph has no such cap — `value-graph.js:149` lets `slot` grow with the
width, which is why the two charts disagree about how much room they take.

## Tasks

### 3.1 — Choose the rule from real data, not from this fixture

Three scenes is the smallest case, and it is the one that looks worst. Before
changing a constant, measure a long story: the cap only earns its keep when the
per-scene column would otherwise be wide enough that a 4px marker and a 9px
label stop being readable.

- [x] Build (or reuse) a 30+ scene story and measure the per-scene slot at
      680px and at the default 320px panel width.
- [x] Decide: raise `MAX_SLOT`, remove it and let the ribbon fill like the value
      graph, or keep the cap and make the ribbon centre/scale within the pane.
      Record the choice and the measurement that drove it in this file.

**Measurement.** The rule was read out of the rendered HTML, not recomputed from
the source: `D.renderCharacterJourney(...)` at a given width, then the `width`
attribute of the `svg.jr-svg` it produced. Both panel widths, 1–48 scenes:

| pane | n | slot | ribbon | fill |
|---:|---:|---:|---:|---:|
| 680 | 3 | 204.7 | 680 | **100%** |
| 680 | 8 | 76.8 | 680 | 100% |
| 680 | 12 | 51.2 | 680 | 100% |
| 680 | 20 | 30.7 | 680 | 100% |
| 680 | 30 | 20.5 | 680 | 100% |
| 680 | 48 | 12.8 | 680 | 100% |
| 320 | 3 | 84.7 | 320 | 100% |
| 320 | 12 | 21.2 | 320 | 100% |
| 320 | 30 | 12.0 | 426 | 133% — scrolls |
| 320 | 48 | 12.0 | 642 | 201% — scrolls |

(the `slot`/`ribbon` columns above are the *post-fix* rule; the pre-fix column is
in the before/after pair under 3.2)

**What the 30-scene case shows.** The cap only binds while the uncapped slot
would still exceed 46px, i.e. while `n ≤ 12` at 680px and `n ≤ 7` at 320px. From
20 scenes up, the uncapped slot is already *below* the cap, so `MAX_SLOT` is
doing nothing there. It is not a readability guard that engages on long stories —
it is a constant that only ever bites short ones, exactly where the fill is
worst.

**The readability question, answered directly.** The widest mark the ribbon
draws per scene is the drives ring at 10.6px across (r 4.3 + a 2px stroke), then
the choice diamond at 10px; the lane rows are a fixed 15px tall, not per-scene.
So a *wide* column cannot make a marker unreadable — it makes it small relative
to its column. The cap protects nothing. `MIN_SLOT = 12` does real work (below it
the ring touches its neighbour); `MAX_SLOT` does none.

One tightness worth recording, not fixed here: at the floor the 10.6px ring has
0.7px to its neighbour, so a long story at the default panel reads as a nearly
solid band of marks. That is pre-existing behaviour (`MIN_SLOT = 12` predates
this phase and the brief did not ask for it), and at that density the marker rows
are a rhythm strip where touching reads fine. The ribbon scrolls, so the reader
is never stuck. Raising it would trade fill for gap; left alone deliberately.

**Decision: remove the cap.** The ribbon fills the pane: `slot` is whatever the
pane can give each scene, floored at `MIN_SLOT`, with no upper bound. When the
floor binds the ribbon exceeds the pane and `.jr-scroll`'s `overflow-x` scrolls
it — which is what that container is for, and what a 30-scene story at the
default panel needs. The act-focus chips remain the zoom for a short story.

Not chosen, and why: *raising* `MAX_SLOT` would still leave a constant that the
value graph does not have, so the two would still disagree, and it would still
clamp the 3-scene case to whatever the new number is. *Centring* would add CSS
and a second rule to keep in sync, and would leave the empty space — just
balanced instead of right-aligned.

### 3.2 — Apply it

- [x] Edit `character-journey-tab.js` per the decision in 3.1.
- [x] Confirm the ribbon is drawn at a readable slot in both the wide and the
      default panel: no clipping, no overflow, labels not overlapping.

The edit is two lines: `MAX_SLOT` leaves the constant list, and the slot
expression becomes `Math.max(MIN_SLOT, (W - LABEL_W - PAD_R) / Math.max(view.n, 1))`.
The `Math.max(280, …)` floor on `W` went with it — it was a second arbitrary
constant, and it never bound in practice (the pane is 647px at the wide panel
and 287px narrowed, both above 280).

Before/after, on the assembled page, driven by the dashboard's own JS
(`DASH.showCharacterPanel` → `DASH.panelTabs.activate('journey')`):

```
                    BEFORE                    AFTER
default   pane 647  ribbon 204  32%           ribbon 647  100%
narrow    pane 287  ribbon 204  71%           ribbon 287  100%
                    slot 46   (capped)        slot 193.8 / 86.0
```

Both after-rows report `scroll client == scroll` (no overflow), 3 hit columns,
3 timeline rows, and 0 labels past the ribbon's right edge. The 32% in the
before-column is the phase's own finding, reproduced rather than assumed.

### 3.3 — Confirm the two charts agree

The ribbon reuses the value graph's classes (`.vg-band`, `.vg-code`, `.vg-lane-line`)
deliberately, so the two read as one family. A per-scene width rule that differs
between them breaks that.

- [x] State in this file what the two now share: the slot rule, the axis, or
      neither. If neither, say why that is acceptable.

**They share the axis, and the *shape* of the slot rule, but not the slot
constant — and that difference is the container's, not the chart's.**

What is now identical:

- the axis. The ribbon already draws `D.valueAxisSvg(view, geo, null, 'plot')`;
  it has no axis code of its own.
- the *form* of the rule. Both are `slot = max(floor, (W - labelW - padR) / n)`.
  Both fill their container and scroll when the floor binds. Neither has an
  upper cap.
- the label column's meaning. `LABEL_W = 58` is `GEO.minLabelW` in
  `value-graph.js:19`, and the ribbon's longest lane label is `extra-pers.` at
  11 chars — which is exactly the string that constant was chosen for. The
  ribbon's own labels (`in scene`, `in beats`, `drives`, `choice`, `change`)
  never need more.

What differs, and why that is acceptable:

| | value graph | ribbon |
|---|---|---|
| slot floor | 1.5px | 12px |
| `W` floor | 360px | none |
| `labelW` | `valueLabelWidth(model)`, 58–118px | 58px fixed |

The floors differ because the containers differ. The value graph draws into the
main view, which is hundreds of pixels wide, so it can afford a per-chart floor
and must not shrink below it. The ribbon draws into a 287–647px detail pane; a
360px floor there would make a 3-scene story at the *default* panel 360px wide
and overflow it — the clipping 3.2 exists to prevent. And `labelW` differs
because the ribbon does not draw the schema lane words the graph draws: it draws
`P`/`C`/`CD`/`NN`, so it takes the graph's own minimum rather than a width
computed for labels it never renders.

The one thing that would have been a genuine disagreement — one chart capped,
one not — is gone.

### 3.4 — Verify

- [x] Geometry probe: ribbon width as a share of the pane, reported for the
      3-scene and the 30-scene story.
- [x] Headless Chrome: both tabs render, no clipping, no horizontal overflow.
- [x] Full suite green.

**Geometry probe** (`~/.hermes/cache/scratch/ribbon_geom.js`, node; reads the
landed modules and reports the width the panel itself rendered):

```
3-scene   680px  slot 204.7  ribbon 680  100%      320px  slot 84.7  ribbon 320  100%
30-scene  680px  slot 20.5   ribbon 680  100%      320px  slot 12.0  ribbon 426  133% (scrolls)
```

**Headless Chrome** (`~/.hermes/cache/scratch/ribbon_chrome_check.py`, three
drives of the assembled page):

```
ok  journey @ default  pane=647 svgW=647 hits=3 labels=27
ok  journey @ narrow   pane=287 svgW=287 hits=3 labels=27
ok  beats   @ default  pane=647 rows=drew
ALL OK
```

Each journey row is checked for: no horizontal overflow (`scrollWidth ==
clientWidth`), every hit column inside the scroll box, no label past the
ribbon's right edge, and no two labels sharing space. The Beats tab is in the
same run to confirm the change did not disturb it.

**Full suite:** `1179 passed`.

## Phase 3 brief

**Landed.** `MAX_SLOT` and the `280` floor are gone from
`character-journey-tab.js`; the ribbon fills its pane and scrolls when the
`MIN_SLOT` floor binds. Two constants removed, one expression simplified, no
behaviour added.

**The decision was made from a 30-scene measurement, as 3.1 asked, and it
discharged the phase's premise.** The brief offered "raise `MAX_SLOT`" as one of
three options; the measurement shows the cap only ever binds on stories of
12 scenes or fewer, and from 20 scenes up it is inert. It was not a readability
guard. The 3-scene case is the one the cap hurts, not the one it helps.

**Corrected from the brief.** The cause was cited as `value-graph.js:142`. The
slot rule is at `value-graph.js:149` (`valueGeometry`); line 142 is inside
`valueLabelWidth`. The finding itself is right and reproduced.

**Verification is DOM assertions, not screenshots** — the vision tool was down,
and the assertions are stronger: the probe drives the dashboard's own JS and
reads the width the panel actually rendered, and the overlap check is computed
from the built DOM.

**Left for Phase 4.** The two probes are still scratch files. Phase 4.2 is what
gives them permanent homes; the assertions worth carrying over are the
`svg.jr-svg` width-vs-pane fill share and the four journey DOM invariants.

## Parallel work

None. This phase edits `character-journey-tab.js`, so it runs after Phase 2.

## Checklist

- [x] Slot rule decided from a 30+ scene measurement, recorded here
- [x] `MAX_SLOT` changed (or removed) accordingly
- [x] Ribbon readable at 680px and at 320px
- [x] Shared-geometry statement written
- [x] Geometry probe reports the fill share for both stories
- [x] Headless Chrome green
- [x] Full suite green
