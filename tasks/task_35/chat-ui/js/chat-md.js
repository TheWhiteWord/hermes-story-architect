/* Story Architect chat: tiny safe markdown renderer.
   Input is escaped FIRST, then a small subset is turned into HTML:
   paragraphs, headings, bold/italic, inline + fenced code, lists, quotes, rules, http(s) links. */
(function () {
  const SA = (window.SAChat = window.SAChat || {});
  const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  function inline(raw) {
    return esc(raw).split(/(`[^`\n]+`)/).map((seg, i) => {
      if (i % 2) return '<code>' + seg.slice(1, -1) + '</code>';
      return seg
        .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<em>$2</em>')
        .replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    }).join('');
  }

  function md(src) {
    const lines = String(src == null ? '' : src).replace(/\r\n?/g, '\n').split('\n');
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (/^\s*$/.test(line)) { i++; continue; }
      const fence = line.match(/^\s*```/);
      if (fence) {
        const code = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) code.push(lines[i++]);
        i++; // closing fence (or end of stream)
        out.push('<pre><code>' + esc(code.join('\n')) + '</code></pre>');
        continue;
      }
      const h = line.match(/^\s{0,3}#{1,6}\s+(.*)$/);
      if (h) { out.push('<div class="sa-h">' + inline(h[1]) + '</div>'); i++; continue; }
      if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) { out.push('<hr>'); i++; continue; }
      if (/^\s*>/.test(line)) {
        const q = [];
        while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ''));
        out.push('<blockquote>' + inline(q.join(' ')) + '</blockquote>');
        continue;
      }
      const ul = /^\s*[-*+]\s+/, ol = /^\s*\d+[.)]\s+/;
      if (ul.test(line) || ol.test(line)) {
        const re = ul.test(line) ? ul : ol, tag = re === ul ? 'ul' : 'ol', items = [];
        while (i < lines.length && re.test(lines[i])) items.push('<li>' + inline(lines[i++].replace(re, '')) + '</li>');
        out.push('<' + tag + '>' + items.join('') + '</' + tag + '>');
        continue;
      }
      const para = [];
      while (i < lines.length && !/^\s*$/.test(lines[i]) && !/^\s*(```|>|#{1,6}\s|[-*+]\s|\d+[.)]\s)/.test(lines[i])) para.push(lines[i++]);
      if (!para.length) para.push(lines[i++]);
      out.push('<p>' + para.map(inline).join('<br>') + '</p>');
    }
    return out.join('');
  }

  SA.esc = esc;
  SA.md = md;
})();
