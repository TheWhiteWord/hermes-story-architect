window.DASH = window.DASH || {};

DASH._scriptBuilt = false;

DASH.buildScriptView = function() {
  const stats = window.__SCREENPLAY_STATS__;
  const container = document.getElementById('screenplay-container');
  if (!container) return;

  // No stats or no scriptHtml → empty state
  if (!stats || !stats.scriptHtml) {
    container.innerHTML = '<div class="script-empty"><div class="empty-state-title">No scenes with content yet</div><div class="empty-state-sub">Add content to your scenes to see the script view.</div></div>';
    DASH._scriptBuilt = true;
    return;
  }

  const doc = document.createElement('div');
  doc.className = 'screenplay-doc screenplay-content';

  // ── Title page ──
  if (stats.titlePage) {
    const tp = stats.titlePage;
    const hasContent = Object.values(tp).some(arr => Array.isArray(arr) ? arr.length > 0 : !!arr);
    if (hasContent) {
      // Find the title by its type, never by position. `screenplay_title` can be
      // empty, and a position-based split then renders the credit line as the
      // title — which is exactly the mistake a `type` field exists to prevent.
      // The type is `title` or `title_unfilled`, so match the prefix.
      const ccTokens = (tp.cc || []).map(t => (typeof t === 'string' ? { text: t } : t));
      const titleToken = ccTokens.find(t => (t.type || '').startsWith('title'))
                          || { text: '', unfilled: true };
      const creditTokens = ccTokens.filter(t => !(t.type || '').startsWith('title'));

      const tokenHtml = (arr) => (arr || []).map(t => {
        const text = typeof t === 'string' ? t : (t.text || '');
        const cls = (t && t.unfilled) ? 'tp-unfilled' : `tp-${(t && t.type) || 'x'}`;
        return `<span class="${cls}">${DASH.escapeHtml(text)}</span>`;
      }).join('<br>');

      const tl = tokenHtml(tp.tl);
      const tr = tokenHtml(tp.tr);
      const bl = tokenHtml(tp.bl);
      const br = tokenHtml(tp.br);
      const creditHtml = tokenHtml(creditTokens);

      const titleCls = titleToken.unfilled ? 'tp-unfilled' : 'tp-title';

      const tpEl = document.createElement('div');
      tpEl.className = 'screenplay-title-page';
      tpEl.innerHTML = `
        <div class="title-tl">${tl}</div>
        <div class="title-tc"></div>
        <div class="title-tr">${tr}</div>
        <div class="title-cc">
          <span class="${titleCls}">${DASH.escapeHtml(titleToken.text || '')}</span>
          ${creditHtml ? `<span class="tp-credit">${creditHtml}</span>` : ''}
        </div>
        <div class="title-bl">${bl}</div>
        <div class="title-br">${br}</div>
      `;
      doc.appendChild(tpEl);
    }
  }

  // ── Screenplay body (server-rendered HTML) ──
  const body = document.createElement('div');
  body.innerHTML = stats.scriptHtml;

  // Insert soft page breaks every ~8 scene headings
  let headingCount = 0;
  let pageNum = 1;
  body.querySelectorAll('.fountain-scene_heading').forEach(el => {
    headingCount++;
    if (headingCount > 1 && headingCount % 8 === 1) {
      pageNum++;
      const br = document.createElement('hr');
      br.className = 'screenplay-page-break';
      br.setAttribute('data-page', 'p. ' + pageNum);
      el.parentNode.insertBefore(br, el);
    }
  });

  doc.appendChild(body);

  // ── Wire scene heading clicks ──
  doc.querySelectorAll('.fountain-scene_heading').forEach((el, i) => {
    const sceneId = stats.sceneIds && stats.sceneIds[i];
    if (sceneId) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => {
        DASH.showScenePanel(sceneId);
      });
    }
  });

  // Subtitle
  const sceneCount = (DASH.story.scenes || []).length;
  const pages = stats.lengthStats && stats.lengthStats.pagesWhole || '?';
  DASH.setEl('script-subtitle', pages + ' p · ' + sceneCount + ' scenes');

  container.innerHTML = '';
  container.appendChild(doc);
  DASH._scriptBuilt = true;
};

DASH.boot();
