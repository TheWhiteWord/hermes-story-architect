# Values visualization in graph

## Four-lane timeline
FILE: `docs/html_ui_dashboard/value_lane_timeline_mockup.html`

- **Four-lane timeline.** Y is four labeled lanes instead of a numeric scale. Each scene is a point in a lane, and the shift is the line or arrow between points. Order the lanes as above. Make the negation-of-negation lane look different, with a hatched fill or its own hue, so it reads as "corrupted positive" and not just "more negative." Label the Y axis "distance from the ideal" or "intensity of negation," not good/bad, so you avoid the growth/decay connotation. A scene usually moves several values at once, so use one lane chart per value (small multiples) with an optional overlay, instead of cramming everything into one.


How to read it

- Lanes: top to bottom they go Positive, Contradictory, Contrary, Negation of negation. The axis means "distance from the ideal", so up is not "good" and down is not "bad".
- Dots: each dot is where the value sits in that scene. The negation-of-negation lane has a hatched background, and its dots are hollow rings. This shows it as a corrupted version of the positive, not just "more negative".
- Lines: the line between two dots is the shift. A thicker line means a bigger jump. A dashed gray line means the value stayed in the same state, which is a real state and not "nothing happened".


## Square
FILE: `docs/html_ui_dashboard/value_square_linked_timeline.html`

- **The square itself as a map.** Draw the square and plot each scene as a point inside it, joined by a path. This shows the nuance best, since you can see a story orbiting the corrupted corner. It loses the time axis, but you can fix that by numbering the points or fading the color by scene order. It works well as a linked second view next to the timeline.

### How the square works

- Corners: Positive is top left and Contrary is top right. Contradictory is bottom left and Negation of negation is bottom right, shown with the same hatched patch as in the timeline.
- Path: each scene is a numbered dot, joined in order. The solid line is the story so far and the faint dashed line is what's still ahead.
- Revisits: a state that appears several times, like Love in scenes 1, 2 and 8, gets several dots spread in a small ring around that corner so none of them overlap. Dots get darker as the story goes on.

### What the square shows that the timeline doesn't

The path crossing the square, for example from Hate (top right) down to the corrupted corner (bottom right), is a different movement from sliding down a ladder.
Scenes that cluster in one corner mean the story is stuck in one region. Scenes that sweep across the square mean the value is being tested from several angles.
The text under the chart translates each shift into both views: how many rungs it moved on the ladder, and which corners it connects on the square.
