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
          <span class="tp-title">${DASH.escapeHtml(titleName)}</span>
          ${creditLines ? `<span class="tp-credit">${creditLines}</span>` : ''}
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
