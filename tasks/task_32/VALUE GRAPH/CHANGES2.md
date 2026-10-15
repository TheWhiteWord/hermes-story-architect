# Value graphs v2: refinements

Based on your integrated `value-graph.js` and `value-graph.css`. Your milestone row, sequence numbering, `DASH.escapeHtml` and `DASH.onViewOpened` are kept. **Apply by replacing the two files. No other edits.**

Tested with a synthetic story (130 and 260 scenes, 7 values, 3 plots) in headless Chromium. Not run against your real data.

## Bugs found in the integrated version

| Problem | Cause | Fix |
|---|---|---|
| Lane labels cut off at the left (`nfairness`, `miliation`, `atic love`) | Label column fixed at 50px | The width is computed from the longest label (58 to 118px) |
| Two legends overlapped on one row | Both were inline-flex siblings | One flowing row that wraps |
| Text shrank to about 7px in long stories | The SVG was scaled with `viewBox` whenever scenes did not fit | Charts are drawn at their real pixel size, so text never scales. Marks adapt instead. |
| Charts about 3% too wide | The width used the container including its padding | The padding is excluded |
| A redraw loop was possible | `ResizeObserver` redrew on every size change, and a redraw can add or remove a scrollbar | Redraws only when the width changed by 2px or more, once per frame |

## Long stories without a slider

- **Marks adapt to the room.** Below about 12px per scene, dots, spans and offsets shrink. Below about 10px a "same state" pill becomes a tick. Below about 4px the carried-on lines are dropped, and the slanted jump lines stay.
- **Act focus.** A control next to the tabs: `All | Act I | Act II | Act III`. It draws one act across the full width, which is a natural page, not an arbitrary one. Panels with no shifts in that act drop out. When the whole story is too dense to read (under about 7px per scene) a hint says so. It is hidden when the story has one act. To remove it, delete `renderActs` and the `#vg-acts` element.

## Interaction

- **One guide line across every panel** and **one card for the whole scene**: scene number, title, plot beat, and every shift in that scene with its effects. It replaces a native tooltip per panel, which was delayed, plain, and one panel at a time. In the plot view the card shows only that plot.
- **The whole chart area is clickable**, not just the marks. It opens the scene panel.
- Per-scene hover rectangles are gone, which is a lot fewer DOM nodes on long stories.

## Layout and CSS

- The axis is **sticky** and has no box border. Its three rows are labelled (`act`, `seq`, `beats`) in the empty left column.
- Panel heads and section titles no longer use `position: sticky; left: 0`, since nothing scrolls sideways.
- `.vg-content` no longer has `overflow: auto`. Check this one: sticky needs the scroll to happen in an ancestor such as your view body, and an `overflow: auto` parent would silently disable it.

## Not changed, your call

- The legend no longer explains the dotted (carried) and dashed slanted (jump) lines, since you removed those entries. A reader cannot tell what the dashed lines mean without it.
- Marks are coloured by plot. In a plot with two protagonists, colouring the level strip by character would show who is affected.

## Scroll zoom (added after the first v2)

- **Levels:** All, then the act under the pointer, then the sequence under the pointer. Scrolling in goes one level deeper at a time, scrolling out goes back one.
- **The ceiling is the chosen level.** If All is chosen, you can zoom out to All. If an act is chosen with the control, zooming out stops at that act. At the deepest level, scrolling in does nothing.
- **Which scroll counts:** Ctrl or Cmd plus scroll anywhere on the charts (a trackpad pinch does the same), and a plain scroll over the axis. A plain scroll over the charts is left alone, so the page still scrolls. To use a plain scroll everywhere, set `plainWheelOnCharts: true` in the `ZOOM` constants near the top of the zoom block, but then the page cannot be scrolled with the pointer over a chart.
- **One step per gesture:** deltas are accumulated and a step locks for 320ms, so a fast wheel flick or a trackpad swipe moves one level and not three.
- **Where you are:** a breadcrumb next to the act control (`All > Act II > S3`). Each step above the current level is clickable, down to the chosen level. A short fade (disabled under reduced motion) marks the change.
- The first hint line says how to zoom when the whole story is on screen.

Checked in headless Chromium by simulated wheel events: all, act, sequence, back out, the ceiling at All, the ceiling at a chosen act, plain scroll ignored on the charts and accepted on the axis. Not checked: a real trackpad pinch, or whether something else in your app already uses Ctrl plus scroll.
