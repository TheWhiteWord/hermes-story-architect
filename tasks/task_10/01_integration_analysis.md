# Task 10: UI Agent Response — Integration Analysis

> The UI agent delivered a full standalone HTML (3297 lines) based on an older dashboard version. Here's what to take from it and how to integrate it into the current `story-dashboard.html`.

---

## Problem

The UI agent produced `story-dashboard-script-stats.html` — a complete dashboard, not an incremental patch. It's based on an older version (sidebar starts with "graph" as default; current one starts with "story"). We need to extract ONLY the Script + Statistics code and fold it into the current file.

---

## What to Extract from the UI Agent's File

### 1. CSS (lines ~702–1064) — Add to current dashboard's `<style>` block

The current dashboard already has fountain CSS (lines 657–747) and entity panel CSS. The UI agent recreated his own — **ignore his, use ours**. Take only these **new** blocks:

| Lines | Block | What it is |
|-------|-------|------------|
| 702–849 | `#script-view`, `.screenplay-doc`, `.screenplay-title-page`, `.fountain-*` overrides, `.fountain-dual-dialogue`, `.script-empty` | Script view formatting |
| 850–1064 | `#stats-panel`, `.stats-header`, `.stats-tab`, `.stat-grid`, `.stat-block`, `.stat-summary`, `.duration-bar-*`, `.chart-container`, DataTables overrides | Statistics panel |

**Do NOT copy** lines 18–701 — those duplicate existing CSS (layout shell, sidebar, buttons, detail panel, entity cards, etc.) that the current dashboard already has, possibly with our recent improvements.

### 2. HTML (lines ~1150–1158 + 1256–1513) — Add to current dashboard's `<body>`

**In the sidebar** (after the Worlds button, before the separator):
```html
<button class="nav-btn" data-view="script" onclick="switchView('script', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
    <rect x="3" y="1.5" width="10" height="13" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
    <line x1="5.5" y1="5" x2="10.5" y2="5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="5.5" y1="7.5" x2="10.5" y2="7.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="5.5" y1="10" x2="8.5" y2="10" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
  </svg>
  <span class="nav-label">Script</span>
</button>
```

**In `<main id="main">`** (after Story view):
```html
<div class="view" id="script-view">
  <div class="view-header">
    <div class="view-title">Script</div>
    <div class="view-subtitle" id="script-subtitle">—</div>
    <div class="view-header-actions">
      <button class="btn btn-hermes" onclick="openStatsPanel()" id="script-stats-btn">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <rect x="1" y="7" width="2" height="4" rx="0.5" fill="currentColor"/>
          <rect x="5" y="4" width="2" height="7" rx="0.5" fill="currentColor"/>
          <rect x="9" y="1" width="2" height="10" rx="0.5" fill="currentColor"/>
        </svg>
        Statistics
      </button>
    </div>
  </div>
  <div class="view-body">
    <div id="screenplay-container">
      <div class="script-empty">...</div>
    </div>
  </div>
</div>
```

**After `</main>`** (the stats panel `<aside>`):
```html
<aside id="stats-panel">
  <!-- full structure from UI agent lines 1291–1499 -->
</aside>
```

### 3. JavaScript (lines ~2470–3296) — Add before `boot()` call

These are all **new functions** that don't exist in the current dashboard. Copy them wholesale:

| Lines | Function | Purpose |
|-------|----------|---------|
| 2474–2653 | `FOUNTAIN_RULES`, `tokeniseFountain()`, `getSceneLocationType()`, `getSceneTimeOfDay()` | Client-side fountain tokenizer |
| 2677–2686 | `wordToColor()` | Character/location color hashing |
| 2688–2704 | `fmtDuration()`, `fmtDurationShort()` | Duration formatting |
| 2706–2833 | `computeStats()` | Computes all statistics from tokens |
| 2835–2991 | `buildScriptView()`, `escHtml()` | Script view rendering |
| 2993–3026 | `openStatsPanel()`, `closeStatsPanel()`, `switchStatsGroup()` | Stats panel controls |
| 3028–3137 | `populateStats()`, `setText()`, `setBar()` | Populate stats into DOM |
| 3139–3253 | `renderDurationChart()`, `renderCharacterChart()`, `renderBarcodeChart()` | D3.js charts |
| 3255–3291 | `switchView()` wrapping, `_loadScreenplayThenBuildScript()` | Lazy-load integration |

**Do NOT copy** lines 1520–2469 — those recreate existing functions (`boot`, `normalise`, `initStory`, `buildGraphView`, `showCharacterPanel`, etc.) that the current dashboard already has with our improvements.

---

## Key Decision: Separate Stats Panel vs. Reuse Detail Panel

The UI agent created a **separate `#stats-panel`** instead of reusing `#detail-panel`. His reasoning (line 9 of response):

> "so entity panels remain fully functional while the stats panel is open. Sharing the panel would mean closing character/scene detail every time you switch back to the Script view."

This is a **deliberate architectural call**, not an oversight. The brief said "reuse the detail panel pattern" but he chose to create a parallel panel instead.

### Options:

| Approach | Pros | Cons |
|----------|------|------|
| **Separate `#stats-panel`** (his choice) | Entity panels stay open; stats panel is always one click from Script view | Two panel divs; takes more horizontal space; inconsistent with existing pattern |
| **Reuse `#detail-panel`** (brief's suggestion) | Consistent with entity panels; single panel | Closes entity detail when opening stats; going back to entity requires reopening |

### Recommendation

The UI agent's call is reasonable for the Script+Stats workflow (you're analyzing the screenplay, not browsing entities). But it does mean the stats panel and entity panel can't be open simultaneously, which is fine since they serve different purposes.

**If you want him to change it** — ask him to reuse `#detail-panel` instead. If you're happy with his call, keep it as-is.

---

## Integration Checklist

- [ ] Add UI agent's CSS (lines 702–1064) after existing `</style>` content
- [ ] Add Script sidebar button (after Worlds, before separator)
- [ ] Add `#script-view` div inside `<main>` (after Story view)
- [ ] Add `#stats-panel` aside after `</main>`
- [ ] Add all new JS functions before `boot()` call
- [ ] Verify: current dashboard's existing `switchView()` is replaced by the wrapped version (line 3258)
- [ ] Verify: `window.__SCREENPLAY_TEXT__` injection (from `story_dashboard.py`) still works — UI agent's code checks for it
- [ ] Verify: fountain CSS classes match between existing entity panel scene content and new script view rendering

---

## Open Questions for the UI Agent (If Needed)

1. **Separate panel vs. detail panel**: Do you want him to reuse `#detail-panel` or keep the separate `#stats-panel`?
2. **Dual dialogue rendering**: He flagged it as "v2" — do you want him to implement it now, or accept the simplified version?
3. **Readability/complexity scores**: He omitted these (correctly, per spec) — confirm this is acceptable for v1?

---

## Status: RESOLVED (pending user decision on panel architecture)

