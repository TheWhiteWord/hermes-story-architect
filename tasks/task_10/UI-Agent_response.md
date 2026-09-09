Script tab

A new #script-view renders the full screenplay as a formatted scrollable document — Courier New, proper Fountain element styling (bold scene headings, indented dialogue, right-aligned transitions). Scene headings are clickable and cross-link to the existing showScenePanel() for the matching scene. Soft page breaks are inserted automatically every ~52 lines when a scene heading is encountered (so breaks fall at clean points, not mid-dialogue). A title page grid is rendered at the top if the Fountain file has title page keys.

Data loading — The script checks window.__SCREENPLAY_TEXT__ first (your backend injection), then tries screenplay.fountain, then screenplay.md. Building is deferred until the user first clicks the Script tab, so it doesn't slow the initial load.

Statistics panel

A separate #stats-panel aside — not reusing #detail-panel — so entity panels remain fully functional while the stats panel is open. This was a deliberate structural call: sharing the panel would mean closing character/scene detail every time you switch back to the Script view, which breaks the workflow.

The panel has three sub-groups (Overview / Characters / Scenes) with tab navigation, matching BF's layout. D3.js powers three charts: an action-vs-dialogue area line chart, a horizontal bar chart of character speaking time, and the scene barcode (colored bars per scene, togglable between INT/EXT and time-of-day coloring). DataTables handles the character and location tables (sortable, paginated, filterable).

Client-side Fountain tokeniser

A ~200-line JS port of the afterwriting-parser logic, covering: title page, scene headings (with INT./EXT./EST./I/E prefix detection, location type, time-of-day extraction), character cues, dialogue (with per-word duration estimate at 100 wpm), parentheticals, action (200 wpm duration), transitions, sections/synopsis, notes, page breaks, and boneyard comments. Dual-dialogue flagging is captured in tokens but simplified in rendering (full dual-column layout is marked as a v2 item — it requires look-ahead pairing that would roughly double the renderer complexity for an edge case).

switchView wrapping — The existing switchView function is wrapped (not replaced) so the Script tab's lazy-load logic slots in cleanly without touching any of the existing view logic.

Stats not included per spec scope: readability/complexity scores, PDF page map, real page count (uses the 52-lines-per-page estimate). All noted as out of scope in the brief.