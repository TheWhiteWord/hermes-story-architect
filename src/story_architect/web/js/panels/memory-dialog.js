window.DASH = window.DASH || {};

DASH.openMemoryDialog = function() {
  const modal = document.getElementById('memory-dialog');
  if (!modal) return;
  const memory = (DASH.story && DASH.story.story_memory) || {};
  const categories = memory.categories || {};
  const usage = memory.usage || '0/3000';
  const usageNumber = Number(usage.split('/')[0]) || 0;
  const usageLimit = Number(usage.split('/')[1]) || 3000;
  const labels = {
    decisions: 'Decisions',
    directions: 'Directions',
    open_questions: 'Open questions',
    continuity_warnings: 'Continuity warnings'
  };
  const escape = value => String(value).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
  const sections = ['decisions', 'directions', 'open_questions', 'continuity_warnings'].map(category => {
    const entries = categories[category] || [];
    const warningClass = category === 'continuity_warnings' ? ' memory-warning' : '';
    const body = entries.length
      ? `<ul class="memory-entries">${entries.map(entry => `<li>${escape(entry)}</li>`).join('')}</ul>`
      : '<div class="memory-empty">No entries.</div>';
    return `<section class="memory-category${warningClass}"><h3>${labels[category]} · ${entries.length}</h3>${body}</section>`;
  }).join('');
  const content = document.getElementById('memory-dialog-content');
  content.innerHTML = `<div class="memory-header"><h2>Story Memory</h2><button class="btn" id="memory-close" aria-label="Close">×</button></div><div class="memory-usage">${usage} characters used</div><div class="memory-progress"><span style="width:${Math.min(100, usageNumber / usageLimit * 100)}%"></span></div>${sections}<p class="memory-notice">Read-only view. Use story_memory to add, remove, or replace entries.</p>`;
  modal.classList.add('open');
  content.querySelector('#memory-close').onclick = DASH.closeMemoryDialog;
  modal.onclick = event => { if (event.target === modal) DASH.closeMemoryDialog(); };
};

DASH.closeMemoryDialog = function() {
  const modal = document.getElementById('memory-dialog');
  if (modal) modal.classList.remove('open');
};

DASH._memoryDialogBound = false;
DASH._bindMemoryDialog = function() {
  if (DASH._memoryDialogBound) return;
  DASH._memoryDialogBound = true;
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') DASH.closeMemoryDialog();
  });
};
DASH._bindMemoryDialog();
