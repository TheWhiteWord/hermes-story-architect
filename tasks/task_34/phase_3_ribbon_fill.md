# Phase 3 — The ribbon fills the panel

**Goal.** The journey ribbon uses the room the wide panel gives it.

**The finding.** Measured on the rendered page: with the panel at its wide
680px, the ribbon's SVG is 204px wide — **32% of the pane**. `.jr-scroll` is
`overflow-x: auto` but never overflows, so 476px sits empty to the right of the
chart.

**Cause.** `character-journey-tab.js:24,224`:

```js
const LABEL_W = 58, PAD_R = 8, MIN_SLOT = 12, MAX_SLOT = 46;
...
const slot = Math.min(MAX_SLOT, Math.max(MIN_SLOT, (W - LABEL_W - PAD_R) / Math.max(view.n, 1)));
```

`MAX_SLOT = 46` caps the per-scene column. For a 3-scene story the slot is
already 204px before the cap, so it clamps to 46 and `geo.W` lands at 204.

The value graph has no such cap — `value-graph.js:142` lets `slot` grow with the
width, which is why the two charts disagree about how much room they take.

## Tasks

### 3.1 — Choose the rule from real data, not from this fixture

Three scenes is the smallest case, and it is the one that looks worst. Before
changing a constant, measure a long story: the cap only earns its keep when the
per-scene column would otherwise be wide enough that a 4px marker and a 9px
label stop being readable.

- [ ] Build (or reuse) a 30+ scene story and measure the per-scene slot at
      680px and at the default 320px panel width.
- [ ] Decide: raise `MAX_SLOT`, remove it and let the ribbon fill like the value
      graph, or keep the cap and make the ribbon centre/scale within the pane.
      Record the choice and the measurement that drove it in this file.

### 3.2 — Apply it

- [ ] Edit `character-journey-tab.js` per the decision in 3.1.
- [ ] Confirm the ribbon is drawn at a readable slot in both the wide and the
      default panel: no clipping, no overflow, labels not overlapping.

### 3.3 — Confirm the two charts agree

The ribbon reuses the value graph's classes (`.vg-band`, `.vg-code`, `.vg-lane-line`)
deliberately, so the two read as one family. A per-scene width rule that differs
between them breaks that.

- [ ] State in this file what the two now share: the slot rule, the axis, or
      neither. If neither, say why that is acceptable.

### 3.4 — Verify

- [ ] Geometry probe: ribbon width as a share of the pane, reported for the
      3-scene and the 30-scene story.
- [ ] Headless Chrome: both tabs render, no clipping, no horizontal overflow.
- [ ] Full suite green.

## Parallel work

None. This phase edits `character-journey-tab.js`, so it runs after Phase 2.

## Checklist

- [ ] Slot rule decided from a 30+ scene measurement, recorded here
- [ ] `MAX_SLOT` changed (or removed) accordingly
- [ ] Ribbon readable at 680px and at 320px
- [ ] Shared-geometry statement written
- [ ] Geometry probe reports the fill share for both stories
- [ ] Headless Chrome green
- [ ] Full suite green
