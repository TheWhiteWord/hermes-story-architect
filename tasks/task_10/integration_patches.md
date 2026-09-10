# Integration Patches — Script View + Statistics Panel

Each section has an exact anchor string to find in the file, and the text to insert.
No existing code is modified except where noted.

---

## 1. CDN LINKS — add to `<head>`, after the screenplay.css link (line 13)

Find:
```html
<!-- Better Fountain screenplay styling -->
<link rel="stylesheet" href="screenplay.css">
```

Insert AFTER:
```html
<!-- D3.js for statistics charts -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
```

---

## 2. CSS — add inside `<style>`, before the closing `</style>` tag (line 791)

Find:
```css
/* Narrow layout */
@media (max-width: 520px) {
  .search-bar { display: none; }
}
```

Insert AFTER (replacing that block with the block below — it already contains the media query):
```css
/* Narrow layout */
@media (max-width: 520px) {
  .search-bar { display: none; }
}

/* ─── Script View ──────────────────────────────────────────── */
#script-view .view-body {
  flex: 1;
  overflow-y: auto;
  background: var(--card);
}

/* Screenplay document wrapper — structural only, fountain classes come from screenplay.css */
.screenplay-doc {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 40px 60px;
}

/* Title page grid */
.screenplay-title-page {
  display: grid;
  grid-template-areas:
    "tl tc tr"
    ".  cc  ."
    "bl .  br";
  grid-template-columns: 1fr 1fr 1fr;
  min-height: 260px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
  padding: 24px 0 32px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
}
.title-tl { grid-area: tl; align-self: start; }
.title-tc { grid-area: tc; text-align: center; align-self: start; }
.title-tr { grid-area: tr; text-align: right; align-self: start; }
.title-cc { grid-area: cc; text-align: center; align-self: center; padding: 20px 0; }
.title-cc .tp-title { font-size: 15px; font-weight: bold; display: block; margin-bottom: 6px; color: var(--foreground); }
.title-cc .tp-credit { color: var(--muted-foreground); display: block; }
.title-bl { grid-area: bl; align-self: end; color: var(--muted-foreground); }
.title-br { grid-area: br; text-align: right; align-self: end; color: var(--muted-foreground); }

/* Soft page break between scenes */
.screenplay-page-break {
  border: none;
  border-top: 1px dashed var(--border);
  margin: 20px 0 6px;
  position: relative;
}
.screenplay-page-break::after {
  content: attr(data-page);
  position: absolute;
  right: 0;
  top: -8px;
  font-size: 9px;
  color: var(--muted-foreground);
  font-family: 'Courier New', Courier, monospace;
  background: var(--card);
  padding: 0 4px;
}

/* Scene number prefix inside scene heading */
.scene-num {
  opacity: 0.4;
  font-weight: normal;
  margin-right: 8px;
}

/* Clickable scene headings in the script view */
.screenplay-doc .fountain-scene_heading {
  cursor: pointer;
}
.screenplay-doc .fountain-scene_heading:hover {
  color: var(--accent);
}

/* Dual dialogue container */
.screenplay-dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  margin: 0;
}

/* Script empty state */
.script-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
  color: var(--muted-foreground);
  text-align: center;
  padding: 40px;
  font-size: var(--font-size-sm);
}
.script-empty svg { opacity: 0.25; margin-bottom: 4px; }

/* ─── Statistics Panel ─────────────────────────────────────── */
:root { --stats-panel-w: 360px; }

#stats-panel {
  width: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--panel-bg, #181818);
  transition: width 0.2s ease;
  position: relative;
  z-index: 1;
}
#stats-panel.open {
  width: var(--stats-panel-w);
  border-left: 1px solid var(--border);
}
@media (max-width: 699px) {
  #stats-panel {
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 0;
    z-index: 20;
  }
  #stats-panel.open {
    width: min(var(--stats-panel-w), calc(100vw - var(--sidebar-w)));
  }
}

.stats-header {
  padding: 12px 14px 0;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.stats-header-row {
  display: flex;
  align-items: center;
  padding-bottom: 10px;
}
.stats-title {
  font-size: var(--font-size-lg);
  font-weight: 500;
  color: var(--foreground);
  flex: 1;
}
.stats-close {
  background: none;
  border: none;
  color: var(--muted-foreground);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 2px;
}
.stats-close:hover { color: var(--foreground); }

.stats-subnav {
  display: flex;
}
.stats-tab {
  flex: 1;
  padding: 6px 4px;
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--muted-foreground);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font: inherit;
  transition: color 0.1s, border-color 0.1s;
}
.stats-tab:hover { color: var(--foreground); }
.stats-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.stats-body { flex: 1; overflow-y: auto; }
.stats-group { display: none; padding: 14px; flex-direction: column; gap: 14px; }
.stats-group.active { display: flex; }

.stats-section-label {
  font-size: var(--font-size-xs);
  color: var(--muted-foreground);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: -2px;
}

/* Stat number blocks */
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.stat-grid.cols-3 { grid-template-columns: 1fr 1fr 1fr; }
.stat-block {
  padding: 8px 10px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.stat-block-value {
  font-size: 18px;
  font-weight: 400;
  color: var(--foreground);
  line-height: 1;
  margin-bottom: 2px;
  font-variant-numeric: tabular-nums;
}
.stat-block-label {
  font-size: var(--font-size-xs);
  color: var(--muted-foreground);
}

/* Duration summary sentence */
.stat-summary {
  font-size: var(--font-size-xs);
  color: var(--muted-foreground);
  line-height: 1.6;
  padding: 8px 10px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-style: italic;
}

/* Horizontal fill bars (INT/EXT, time-of-day) */
.duration-bar-group { display: flex; flex-direction: column; gap: 4px; }
.duration-bar-row { display: flex; align-items: center; gap: 6px; font-size: var(--font-size-xs); }
.duration-bar-label { width: 56px; color: var(--muted-foreground); flex-shrink: 0; }
.duration-bar-track { flex: 1; height: 5px; background: var(--border); border-radius: 3px; overflow: hidden; }
.duration-bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
.duration-bar-value { width: 52px; text-align: right; color: var(--muted-foreground); flex-shrink: 0; }

/* D3 chart wrapper */
.chart-container {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  padding: 6px 4px 2px;
}
.chart-container svg text { font-family: inherit; }

/* Character color pip */
.char-pip {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
  flex-shrink: 0;
}

/* Sortable plain table (no DataTables dependency) */
.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-xs);
  color: var(--foreground);
}
.stats-table thead th {
  background: var(--card);
  color: var(--muted-foreground);
  border-bottom: 1px solid var(--border);
  padding: 5px 7px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}
.stats-table thead th:hover { color: var(--foreground); }
.stats-table thead th.sort-asc::after { content: ' ↑'; }
.stats-table thead th.sort-desc::after { content: ' ↓'; }
.stats-table tbody tr { border-bottom: 1px solid var(--border); }
.stats-table tbody tr:last-child { border-bottom: none; }
.stats-table tbody td { padding: 5px 7px; }
.stats-table tbody tr:hover td { background: var(--card); }

/* Barcode chart radio buttons */
.barcode-controls {
  display: flex;
  gap: 12px;
  font-size: var(--font-size-xs);
  color: var(--muted-foreground);
}
.barcode-controls label {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}
```

---

## 3. HTML: Script nav button — insert in sidebar before the separator

Find this exact string in the HTML (line ~877):
```html
    <div class="nav-separator"></div>
```

Insert BEFORE it:
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

---

## 4. HTML: Script view + Stats panel — insert before `</main>` and before `#detail-panel`

Find:
```html
  </main>

  <!-- Detail Panel -->
  <aside id="detail-panel">
```

Replace with:
```html
    <!-- Script View -->
    <div class="view" id="script-view">
      <div class="view-header">
        <div class="view-title">Script</div>
        <div class="view-subtitle" id="script-subtitle">—</div>
        <div class="view-header-actions">
          <button class="btn btn-hermes" onclick="openStatsPanel()">
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
          <div class="script-empty">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect x="6" y="3" width="20" height="26" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <line x1="10" y1="10" x2="22" y2="10" stroke="currentColor" stroke-width="1.2"/>
              <line x1="10" y1="14" x2="22" y2="14" stroke="currentColor" stroke-width="1.2"/>
              <line x1="10" y1="18" x2="18" y2="18" stroke="currentColor" stroke-width="1.2"/>
            </svg>
            <div>No screenplay loaded</div>
            <div style="font-size:var(--font-size-xs);opacity:0.6">Ensure <code>window.__SCREENPLAY_TEXT__</code> is injected by the backend</div>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- Statistics Panel (separate aside — entity panels remain independent) -->
  <aside id="stats-panel">
    <div class="stats-header">
      <div class="stats-header-row">
        <span class="stats-title">Statistics</span>
        <button class="stats-close" onclick="closeStatsPanel()">✕</button>
      </div>
      <div class="stats-subnav">
        <button class="stats-tab active" data-group="overview"    onclick="switchStatsGroup('overview', this)">Overview</button>
        <button class="stats-tab"        data-group="characters"  onclick="switchStatsGroup('characters', this)">Characters</button>
        <button class="stats-tab"        data-group="scenes"      onclick="switchStatsGroup('scenes', this)">Scenes</button>
      </div>
    </div>

    <div class="stats-body">

      <!-- ── Overview ── -->
      <div class="stats-group active" id="stats-group-overview">

        <div class="stats-section-label">Length</div>
        <div class="stat-grid cols-3">
          <div class="stat-block"><div class="stat-block-value" id="lengthStats-pagesWhole">—</div><div class="stat-block-label">Pages</div></div>
          <div class="stat-block"><div class="stat-block-value" id="lengthStats-scenes">—</div><div class="stat-block-label">Scenes</div></div>
          <div class="stat-block"><div class="stat-block-value" id="lengthStats-words">—</div><div class="stat-block-label">Words</div></div>
        </div>
        <div class="stat-grid">
          <div class="stat-block"><div class="stat-block-value" id="lengthStats-lines">—</div><div class="stat-block-label">Lines</div></div>
          <div class="stat-block"><div class="stat-block-value" id="lengthStats-characters">—</div><div class="stat-block-label">Characters</div></div>
        </div>

        <div class="stats-section-label">Duration</div>
        <div class="stat-grid cols-3">
          <div class="stat-block"><div class="stat-block-value" id="durationStats-total">—</div><div class="stat-block-label">Total</div></div>
          <div class="stat-block"><div class="stat-block-value" id="durationStats-action">—</div><div class="stat-block-label">Action</div></div>
          <div class="stat-block"><div class="stat-block-value" id="durationStats-dialogue">—</div><div class="stat-block-label">Dialogue</div></div>
        </div>
        <div class="stat-summary" id="durationStats-summary">—</div>

        <div class="stats-section-label">Action vs. Dialogue</div>
        <div class="chart-container" id="durationStats-lengthchart" style="height:80px;"></div>

      </div>

      <!-- ── Characters ── -->
      <div class="stats-group" id="stats-group-characters">

        <div class="stat-grid">
          <div class="stat-block"><div class="stat-block-value" id="characterStats-count">—</div><div class="stat-block-label">Speaking characters</div></div>
          <div class="stat-block"><div class="stat-block-value" id="characterStats-monologues">—</div><div class="stat-block-label">Monologues (&gt;30s)</div></div>
        </div>

        <div class="stats-section-label">Speaking time</div>
        <div class="chart-container" id="characterStats-lengthchart" style="height:120px;"></div>

        <div class="stats-section-label">Character detail</div>
        <div style="overflow-x:auto;">
          <table class="stats-table" id="characterStats-table">
            <thead>
              <tr>
                <th onclick="sortTable('characterStats-table',0)">Name</th>
                <th onclick="sortTable('characterStats-table',1)" data-type="num">Duration</th>
                <th onclick="sortTable('characterStats-table',2)" data-type="num">Lines</th>
                <th onclick="sortTable('characterStats-table',3)" data-type="num">Words</th>
                <th onclick="sortTable('characterStats-table',4)" data-type="num">Mono</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>

        <button class="btn btn-hermes" data-hermes-send="Analyze the dialogue balance between characters in this screenplay. Which characters dominate, and are there any speaking-time imbalances worth addressing?">Ask Hermes about dialogue balance</button>

      </div>

      <!-- ── Scenes ── -->
      <div class="stats-group" id="stats-group-scenes">

        <div class="stat-grid">
          <div class="stat-block"><div class="stat-block-value" id="sceneStats-count">—</div><div class="stat-block-label">Scenes</div></div>
          <div class="stat-block"><div class="stat-block-value" id="locationStats-count">—</div><div class="stat-block-label">Locations</div></div>
        </div>

        <div class="stats-section-label">INT / EXT / Mixed</div>
        <div class="duration-bar-group">
          <div class="duration-bar-row">
            <span class="duration-bar-label">Interior</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-type_int_bar" style="background:#7b9cf0;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-type_int">—</span>
          </div>
          <div class="duration-bar-row">
            <span class="duration-bar-label">Exterior</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-type_ext_bar" style="background:#6bbfb0;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-type_ext">—</span>
          </div>
          <div class="duration-bar-row">
            <span class="duration-bar-label">Mixed</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-type_mixed_bar" style="background:#e0a86b;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-type_mixed">—</span>
          </div>
        </div>

        <div class="stats-section-label">Time of day</div>
        <div class="duration-bar-group">
          <div class="duration-bar-row">
            <span class="duration-bar-label">Day</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-time_day_bar"     style="background:#e0c96b;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-time_day">—</span>
          </div>
          <div class="duration-bar-row">
            <span class="duration-bar-label">Night</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-time_night_bar"   style="background:#7b9cf0;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-time_night">—</span>
          </div>
          <div class="duration-bar-row">
            <span class="duration-bar-label">Morning</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-time_morning_bar" style="background:#e07070;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-time_morning">—</span>
          </div>
          <div class="duration-bar-row">
            <span class="duration-bar-label">Evening</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-time_evening_bar" style="background:#b07be0;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-time_evening">—</span>
          </div>
          <div class="duration-bar-row">
            <span class="duration-bar-label">Dawn</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-time_dawn_bar"    style="background:#e06b9b;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-time_dawn">—</span>
          </div>
          <div class="duration-bar-row">
            <span class="duration-bar-label">Dusk</span>
            <div class="duration-bar-track"><div class="duration-bar-fill" id="sceneprop-time_dusk_bar"    style="background:#6bbfb0;width:0%"></div></div>
            <span class="duration-bar-value" id="sceneprop-time_dusk">—</span>
          </div>
        </div>

        <div class="stats-section-label">Scene barcode</div>
        <div class="chart-container" id="sceneStats-timechart" style="height:52px;padding:4px;"></div>
        <div class="barcode-controls">
          <label><input type="radio" name="barcode-mode" value="type" checked onchange="renderBarcodeChart(this.value)"> INT/EXT</label>
          <label><input type="radio" name="barcode-mode" value="time" onchange="renderBarcodeChart(this.value)"> Time of day</label>
        </div>

        <div class="stats-section-label">Locations</div>
        <div style="overflow-x:auto;">
          <table class="stats-table" id="locationStats-table">
            <thead>
              <tr>
                <th onclick="sortTable('locationStats-table',0)">Location</th>
                <th onclick="sortTable('locationStats-table',1)" data-type="num">Scenes</th>
                <th onclick="sortTable('locationStats-table',2)">Type</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>

        <button class="btn btn-hermes" data-hermes-send="Analyze the scene structure and pacing of this screenplay. Comment on the INT/EXT balance, time-of-day variety, and any pacing concerns.">Ask Hermes about pacing</button>

      </div>

    </div><!-- /.stats-body -->
  </aside>

  <!-- Detail Panel -->
  <aside id="detail-panel">
```

---

## 5. JS — insert the entire block below immediately BEFORE the `// ─── Start` comment

Find (near line 2077):
```javascript
// ─── Start ─────────────────────────────────────────────────────────────────────
boot();
```

Insert BEFORE it:
```javascript
// ═══════════════════════════════════════════════════════════════════════════════
// SCRIPT VIEW & STATISTICS PANEL
// ═══════════════════════════════════════════════════════════════════════════════

// ─── Helpers ───────────────────────────────────────────────────────────────────
function fmtDurationShort(sec) {
  if (!sec || isNaN(sec)) return '0m';
  const m = Math.round(sec / 60);
  if (m < 60) return m + 'm';
  return Math.floor(m / 60) + 'h ' + (m % 60) + 'm';
}

function fmtDuration(sec) {
  sec = Math.round(sec || 0);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return h + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
  return m + ':' + String(s).padStart(2,'0');
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function setBar(baseId, count, total) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  setEl(baseId, count + ' (' + pct + '%)');
  const bar = document.getElementById(baseId + '_bar');
  if (bar) bar.style.width = pct + '%';
}

// ─── Sortable plain table ───────────────────────────────────────────────────────
// No DataTables dependency needed for 5-20 rows.
function sortTable(tableId, colIdx) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const th = table.querySelectorAll('thead th')[colIdx];
  const isNum = th.dataset.type === 'num';
  const wasDesc = th.classList.contains('sort-desc');
  // Reset all headers
  table.querySelectorAll('thead th').forEach(h => h.classList.remove('sort-asc','sort-desc'));
  th.classList.add(wasDesc ? 'sort-asc' : 'sort-desc');
  const asc = !wasDesc;

  const tbody = table.querySelector('tbody');
  const rows = [...tbody.querySelectorAll('tr')];
  rows.sort((a, b) => {
    const aText = a.cells[colIdx]?.textContent.trim() || '';
    const bText = b.cells[colIdx]?.textContent.trim() || '';
    if (isNum) {
      // extract leading number (handles "1:23" duration, plain integers, etc.)
      const aNum = parseFloat(a.cells[colIdx]?.dataset.sort || aText) || 0;
      const bNum = parseFloat(b.cells[colIdx]?.dataset.sort || bText) || 0;
      return asc ? aNum - bNum : bNum - aNum;
    }
    return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
  });
  rows.forEach(r => tbody.appendChild(r));
}

// ─── Script View ────────────────────────────────────────────────────────────────
let _scriptBuilt = false;

function buildScriptView() {
  const stats = window.__SCREENPLAY_STATS__;

  // Try pre-rendered HTML first (server-side: tokens_to_html())
  const preHtml = stats && stats.scriptHtml;
  // Fallback: raw text (for development without backend)
  const rawText = window.__SCREENPLAY_TEXT__;

  const container = document.getElementById('screenplay-container');
  if (!container) return;

  if (!preHtml && !rawText) {
    // empty state already in DOM
    _scriptBuilt = true;
    return;
  }

  const doc = document.createElement('div');
  doc.className = 'screenplay-doc screenplay-content';

  // ── Title page ──
  if (stats && stats.titlePage) {
    const tp = stats.titlePage;
    const hasContent = Object.values(tp).some(arr => Array.isArray(arr) ? arr.length > 0 : !!arr);
    if (hasContent) {
      const titleTokens = (tp.cc || []);
      const titleText = titleTokens.map(t => t.text || t).join('\n');
      const tl = (tp.tl || []).map(t => t.text || t).join('<br>');
      const tr = (tp.tr || []).map(t => t.text || t).join('<br>');
      const bl = (tp.bl || []).map(t => t.text || t).join('<br>');
      const br = (tp.br || []).map(t => t.text || t).join('<br>');

      // Split title page tokens into title + credit lines
      const titleLines = titleText.split('\n');
      const titleName = titleLines[0] || '';
      const creditLines = titleLines.slice(1).join('<br>');

      const tpEl = document.createElement('div');
      tpEl.className = 'screenplay-title-page';
      tpEl.innerHTML = `
        <div class="title-tl">${tl}</div>
        <div class="title-tc"></div>
        <div class="title-tr">${tr}</div>
        <div class="title-cc">
          <span class="tp-title">${escapeHtml(titleName)}</span>
          ${creditLines ? `<span class="tp-credit">${creditLines}</span>` : ''}
        </div>
        <div class="title-bl">${bl}</div>
        <div class="title-br">${br}</div>
      `;
      doc.appendChild(tpEl);
    }
  }

  // ── Screenplay body ──
  if (preHtml) {
    // Server pre-rendered: insert directly, then wire click handlers
    const body = document.createElement('div');
    body.innerHTML = preHtml;

    // Insert soft page breaks every ~52 scene headings
    let sceneCount = 0;
    let pageNum = 1;
    body.querySelectorAll('.fountain-scene_heading').forEach(el => {
      sceneCount++;
      if (sceneCount > 1 && sceneCount % 8 === 1) {
        // ~8 scenes/page for a rough page break
        pageNum++;
        const br = document.createElement('hr');
        br.className = 'screenplay-page-break';
        br.setAttribute('data-page', 'p. ' + pageNum);
        el.parentNode.insertBefore(br, el);
      }
    });

    doc.appendChild(body);
  } else {
    // Fallback: render raw Fountain text with simple line-type detection
    // (only used when backend hasn't injected scriptHtml)
    const lines = rawText.split('\n');
    let html = '';
    for (const line of lines) {
      const t = line.trim();
      if (!t) { html += '<div class="fountain-empty"> </div>'; continue; }
      if (/^(INT\.|EXT\.|INT\/EXT\.|I\/E\.)\s+/i.test(t)) {
        html += `<div class="fountain-scene_heading">${escapeHtml(t)}</div>`;
      } else if (/^[A-Z][A-Z0-9 '\-()]+$/.test(t) && t.length < 60) {
        html += `<div class="fountain-character">${escapeHtml(t)}</div>`;
      } else if (/^\(.*\)$/.test(t)) {
        html += `<div class="fountain-parenthetical">${escapeHtml(t)}</div>`;
      } else if (/^(FADE OUT|CUT TO|DISSOLVE TO|SMASH CUT|MATCH CUT|FADE IN):?$/i.test(t)) {
        html += `<div class="fountain-transition">${escapeHtml(t)}</div>`;
      } else if (/^>{1}[^<].*<$/.test(t)) {
        html += `<div class="fountain-centered">${escapeHtml(t.slice(1,-1).trim())}</div>`;
      } else {
        html += `<div class="fountain-action">${escapeHtml(t)}</div>`;
      }
    }
    doc.innerHTML += html;
  }

  // ── Wire scene heading clicks ──
  doc.querySelectorAll('.fountain-scene_heading').forEach(el => {
    const rawHeading = el.textContent.replace(/^\d+\.\s*/, '').toUpperCase().trim()
                                     .replace(/\s*\(.*\)\s*$/, '');
    const matched = (story && story.scenes || []).find(s => {
      const h = (s.heading || '').toUpperCase().trim().replace(/\s*\(.*\)\s*$/, '');
      return h === rawHeading;
    });
    if (matched) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => {
        // Switch to scenes view is NOT desirable here — open entity panel only
        showScenePanel(matched.id);
      });
    }
  });

  // Compute subtitle
  if (stats) {
    const pages = stats.lengthStats && stats.lengthStats.pagesWhole || '?';
    const scenes = stats.lengthStats && stats.lengthStats.scenes || '?';
    setEl('script-subtitle', pages + ' p · ' + scenes + ' scenes');
  } else if (rawText) {
    const lineCount = rawText.split('\n').length;
    const pages = Math.max(1, Math.floor(lineCount / 52));
    setEl('script-subtitle', '~' + pages + ' p (estimated)');
  }

  container.innerHTML = '';
  container.appendChild(doc);
  _scriptBuilt = true;
}

// ─── Statistics Panel ───────────────────────────────────────────────────────────
let _statsPopulated = false;
let _currentBarcodeMode = 'type';

function openStatsPanel() {
  if (!_scriptBuilt) buildScriptView();

  const stats = window.__SCREENPLAY_STATS__;
  if (!stats) {
    // No stats available — show panel with empty state message
    document.getElementById('stats-panel').classList.add('open');
    closePanel(); // close entity panel if open
    return;
  }

  if (!_statsPopulated) {
    populateStats(stats);
    _statsPopulated = true;
  }

  document.getElementById('stats-panel').classList.add('open');
  closePanel();

  // Re-render the active chart in case it was first rendered while hidden
  setTimeout(() => {
    const activeGroup = document.querySelector('.stats-group.active');
    if (activeGroup) {
      const id = activeGroup.id.replace('stats-group-', '');
      _renderChartsForGroup(id);
    }
  }, 50);
}

function closeStatsPanel() {
  document.getElementById('stats-panel').classList.remove('open');
}

function switchStatsGroup(group, btn) {
  document.querySelectorAll('.stats-group').forEach(g => g.classList.remove('active'));
  document.querySelectorAll('.stats-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('stats-group-' + group).classList.add('active');
  btn.classList.add('active');
  // Charts must be drawn into a visible container
  setTimeout(() => _renderChartsForGroup(group), 30);
}

function _renderChartsForGroup(group) {
  const stats = window.__SCREENPLAY_STATS__;
  if (!stats) return;
  if (group === 'overview')    renderDurationChart(stats);
  if (group === 'characters')  renderCharacterChart(stats);
  if (group === 'scenes')      renderBarcodeChart(_currentBarcodeMode);
}

// ─── Populate all stat elements ─────────────────────────────────────────────────
function populateStats(stats) {
  const ls = stats.lengthStats    || {};
  const ds = stats.durationStats  || {};
  const cs = stats.characterStats || {};
  const lo = stats.locationStats  || {};
  const ss = stats.sceneStats     || {};

  // ── Overview: Length ──
  setEl('lengthStats-pagesWhole', ls.pagesWhole  || '—');
  setEl('lengthStats-scenes',     ls.scenes      || '—');
  setEl('lengthStats-words',      (ls.words      || 0).toLocaleString());
  setEl('lengthStats-lines',      (ls.lines      || 0).toLocaleString());
  setEl('lengthStats-characters', (ls.characters || 0).toLocaleString());

  // ── Overview: Duration ──
  setEl('durationStats-total',    fmtDurationShort(ds.total));
  setEl('durationStats-action',   fmtDurationShort(ds.action));
  setEl('durationStats-dialogue', fmtDurationShort(ds.dialogue));

  const totalMin = Math.round((ds.total || 0) / 60);
  const actionPct = ds.total > 0 ? Math.round(((ds.action || 0) / ds.total) * 100) : 0;
  const lengthLabel = totalMin < 60 ? 'a short film' :
                      totalMin < 90 ? 'an hour-long film' :
                      totalMin < 120 ? 'a feature film' : 'an epic feature';
  const balanceLabel = actionPct > 65 ? 'action-heavy' :
                       actionPct < 35 ? 'dialogue-heavy' : 'balanced';
  setEl('durationStats-summary',
    `The screenplay is the length of ${lengthLabel}. It is ${balanceLabel} (${actionPct}% action).`);

  // ── Characters ──
  setEl('characterStats-count',      cs.characterCount || (cs.characters || []).length);
  setEl('characterStats-monologues', cs.monologues || 0);

  // Character table
  const chars = cs.characters || [];
  const cTbody = document.querySelector('#characterStats-table tbody');
  if (cTbody) {
    cTbody.innerHTML = chars.map(c => {
      const secs = c.secondsSpoken || 0;
      return `<tr>
        <td><span class="char-pip" style="background:${c.color || '#888'}"></span>${escapeHtml(c.name)}</td>
        <td data-sort="${secs}">${fmtDuration(secs)}</td>
        <td>${c.speakingParts || 0}</td>
        <td>${c.wordsSpoken || 0}</td>
        <td>${c.monologues || 0}</td>
      </tr>`;
    }).join('');
    // Default sort: duration desc
    sortTable('characterStats-table', 1);
  }

  // ── Scenes: counts ──
  const scenes = ss.scenes || [];
  setEl('sceneStats-count',    scenes.length || ls.scenes || 0);
  setEl('locationStats-count', lo.locationsCount || (lo.locations || []).length);

  // INT/EXT bars
  const tc = ss.typeCounts || {};
  const totalType = (tc.int || 0) + (tc.ext || 0) + (tc.mixed || 0);
  setBar('sceneprop-type_int',   tc.int   || 0, totalType);
  setBar('sceneprop-type_ext',   tc.ext   || 0, totalType);
  setBar('sceneprop-type_mixed', tc.mixed || 0, totalType);

  // Time-of-day bars
  const timec = ss.timeCounts || {};
  const totalTime = Object.values(timec).reduce((a, b) => a + b, 0);
  setBar('sceneprop-time_day',     timec.day     || 0, totalTime);
  setBar('sceneprop-time_night',   timec.night   || 0, totalTime);
  setBar('sceneprop-time_morning', timec.morning || 0, totalTime);
  setBar('sceneprop-time_evening', timec.evening || 0, totalTime);
  setBar('sceneprop-time_dawn',    timec.dawn    || 0, totalTime);
  setBar('sceneprop-time_dusk',    timec.dusk    || 0, totalTime);

  // Location table
  const locs = lo.locations || [];
  const lTbody = document.querySelector('#locationStats-table tbody');
  if (lTbody) {
    lTbody.innerHTML = locs.map(l => {
      const type = (l.interior_exterior || []).join('/').toUpperCase() || '—';
      return `<tr>
        <td><span class="char-pip" style="background:${l.color || '#888'}"></span>${escapeHtml(l.name)}</td>
        <td>${l.number_of_scenes || 0}</td>
        <td>${type}</td>
      </tr>`;
    }).join('');
    sortTable('locationStats-table', 1);
  }
}

// ─── D3 Charts ─────────────────────────────────────────────────────────────────
function renderDurationChart(stats) {
  const container = document.getElementById('durationStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const ds = stats.durationStats || {};
  const actionData    = ds.lengthchart_action   || [];
  const dialogueData  = ds.lengthchart_dialogue || [];
  if (!actionData.length && !dialogueData.length) return;

  // Pad to same length
  const len = Math.max(actionData.length, dialogueData.length);
  const aData = actionData.concat(Array(len - actionData.length).fill(0));
  const dData = dialogueData.concat(Array(len - dialogueData.length).fill(0));

  const W = container.clientWidth  || 320;
  const H = container.clientHeight || 72;
  const mg = { top: 6, right: 8, bottom: 16, left: 26 };
  const w = W - mg.left - mg.right;
  const h = H - mg.top  - mg.bottom;

  const svg = d3.select(container).append('svg').attr('width', W).attr('height', H);
  const g   = svg.append('g').attr('transform', `translate(${mg.left},${mg.top})`);

  const x    = d3.scaleLinear().domain([0, len - 1]).range([0, w]);
  const maxY = d3.max([...aData, ...dData]) || 1;
  const y    = d3.scaleLinear().domain([0, maxY]).range([h, 0]);

  const area = (data, fill) => d3.area()
    .x((d, i) => x(i)).y0(h).y1(d => y(d))
    .curve(d3.curveCatmullRom)(data);
  const line = (data) => d3.line()
    .x((d, i) => x(i)).y(d => y(d))
    .curve(d3.curveCatmullRom)(data);

  g.append('path').attr('d', area(aData)).attr('fill', 'rgba(123,156,240,0.12)');
  g.append('path').attr('d', area(dData)).attr('fill', 'rgba(107,191,176,0.12)');
  g.append('path').attr('d', line(aData)).attr('fill','none').attr('stroke','#7b9cf0').attr('stroke-width',1.5);
  g.append('path').attr('d', line(dData)).attr('fill','none').attr('stroke','#6bbfb0').attr('stroke-width',1.5);

  g.append('g').attr('transform',`translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(i => Math.round((i/(len-1||1))*100)+'%'))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.append('g')
    .call(d3.axisLeft(y).ticks(3).tickFormat(d => fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');

  // Legend
  const leg = svg.append('g').attr('transform', `translate(${mg.left + w - 86},${mg.top + 2})`);
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',5).attr('fill','#7b9cf0');
  leg.append('text').attr('x',12).attr('y',9).text('Action').style('font-size','8px').attr('fill','var(--muted-foreground)');
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',17).attr('fill','#6bbfb0');
  leg.append('text').attr('x',12).attr('y',21).text('Dialogue').style('font-size','8px').attr('fill','var(--muted-foreground)');
}

function renderCharacterChart(stats) {
  const container = document.getElementById('characterStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const chars = ((stats.characterStats || {}).characters || []).slice(0, 8);
  if (!chars.length) return;

  const W  = container.clientWidth  || 320;
  const H  = container.clientHeight || 110;
  const mg = { top: 6, right: 8, bottom: 18, left: 70 };
  const w  = W - mg.left - mg.right;
  const h  = H - mg.top  - mg.bottom;

  const svg = d3.select(container).append('svg').attr('width',W).attr('height',H);
  const g   = svg.append('g').attr('transform',`translate(${mg.left},${mg.top})`);

  const maxSec = d3.max(chars, c => c.secondsSpoken || 0) || 1;
  const x = d3.scaleLinear().domain([0, maxSec]).range([0, w]);
  const y = d3.scaleBand().domain(chars.map(c => c.name)).range([0, h]).padding(0.25);

  g.selectAll('rect').data(chars).enter().append('rect')
    .attr('x', 0)
    .attr('y', d => y(d.name))
    .attr('height', y.bandwidth())
    .attr('width', d => x(d.secondsSpoken || 0))
    .attr('fill', d => d.color || '#7b9cf0')
    .attr('rx', 2);

  g.append('g').call(d3.axisLeft(y).tickSize(0))
    .selectAll('text').style('font-size','9px').attr('dx','-3').attr('fill','var(--muted-foreground)');
  g.append('g').attr('transform',`translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(d => fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');
}

function renderBarcodeChart(mode) {
  _currentBarcodeMode = mode;
  const container = document.getElementById('sceneStats-timechart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const stats  = window.__SCREENPLAY_STATS__;
  const scenes = stats && stats.sceneStats && stats.sceneStats.scenes || [];
  if (!scenes.length) return;

  const TYPE_COL = { int:'#7b9cf0', ext:'#6bbfb0', mixed:'#e0a86b', other:'#555' };
  const TIME_COL = {
    dawn:'#e06b9b', morning:'#e07070', day:'#e0c96b',
    afternoon:'#e0c96b', evening:'#b07be0', dusk:'#6bbfb0',
    night:'#7b9cf0', continuous:'#555', later:'#555', unspecified:'#333'
  };

  const W   = container.clientWidth || 320;
  const H   = container.clientHeight || 44;
  const pad = 3;
  const bw  = Math.max(1.5, (W - pad * 2) / scenes.length);

  const svg = d3.select(container).append('svg').attr('width', W).attr('height', H);
  svg.selectAll('rect').data(scenes).enter().append('rect')
    .attr('x',      (d, i) => pad + i * bw)
    .attr('y',      0)
    .attr('width',  Math.max(1, bw - 0.5))
    .attr('height', H)
    .attr('fill',   d => mode === 'type'
      ? (TYPE_COL[d.locType] || TYPE_COL.other)
      : (TIME_COL[d.locTime] || TIME_COL.unspecified))
    .attr('rx', 1)
    .append('title').text(d => d.text || d.number);
}

// ─── switchView wrapper ────────────────────────────────────────────────────────
// Wraps the existing switchView to add script-tab lazy-build and stats panel cleanup.
// Must come AFTER the original switchView definition.
const _origSwitchView = switchView;
function switchView(view, btn) {
  _origSwitchView(view, btn);

  if (view === 'script') {
    if (!_scriptBuilt) buildScriptView();
  } else {
    closeStatsPanel();
  }
}
```
