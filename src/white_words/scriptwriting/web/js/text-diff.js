window.DASH = window.DASH || {};

// A line diff for the compare screens: `lines` gives every line tagged eq / del / add,
// `collapse` folds long unchanged runs so a one-line edit in a long scene stays readable.
(function (D) {
  const MAX_CELLS = 160000;

  const parts = (s) => (s == null || s === '' ? [] : String(s).split('\n'));

  // Two arrays, each item compared through `key`. `wrap` shapes the output rows.
  function diffSeq(x, y, key, wrap) {
    const same = (i, j) => key(x[i]) === key(y[j]);
    let head = 0;
    while (head < x.length && head < y.length && same(head, head)) head++;
    let tx = x.length;
    let ty = y.length;
    while (tx > head && ty > head && same(tx - 1, ty - 1)) { tx--; ty--; }
    const out = [];
    for (let i = 0; i < head; i++) out.push(wrap('eq', x[i]));
    const mx = tx - head;
    const my = ty - head;
    if (!mx || !my || mx * my > MAX_CELLS) {
      for (let i = head; i < tx; i++) out.push(wrap('del', x[i]));
      for (let j = head; j < ty; j++) out.push(wrap('add', y[j]));
    } else {
      const w = my + 1;
      const t = new Uint32Array((mx + 1) * w);
      for (let i = mx - 1; i >= 0; i--) {
        for (let j = my - 1; j >= 0; j--) {
          t[i * w + j] = same(head + i, head + j) ? t[(i + 1) * w + j + 1] + 1 : Math.max(t[(i + 1) * w + j], t[i * w + j + 1]);
        }
      }
      let i = 0;
      let j = 0;
      while (i < mx && j < my) {
        if (same(head + i, head + j)) { out.push(wrap('eq', x[head + i])); i++; j++; }
        else if (t[(i + 1) * w + j] >= t[i * w + j + 1]) out.push(wrap('del', x[head + i++]));
        else out.push(wrap('add', y[head + j++]));
      }
      while (i < mx) out.push(wrap('del', x[head + i++]));
      while (j < my) out.push(wrap('add', y[head + j++]));
    }
    for (let i = tx; i < x.length; i++) out.push(wrap('eq', x[i]));
    return out;
  }

  const lines = (a, b) => diffSeq(parts(a), parts(b), (l) => l, (op, text) => ({ op, text }));

  // Screenplay blocks ({type, text}); a block is the same only if both are.
  const blocks = (a, b) => diffSeq(a || [], b || [], (k) => k.type + '\u0000' + k.text, (op, block) => ({ op, block }));

  // Keep `context` unchanged lines around each change; a longer run becomes one gap row.
  // `pinFirst` keeps the opening row whatever happens around it (a scene's heading).
  function collapse(ops, context, pinFirst) {
    const keep = ops.map((o, i) => !!pinFirst && i === 0);
    ops.forEach((o, i) => {
      if (o.op === 'eq') return;
      for (let k = Math.max(0, i - context); k <= Math.min(ops.length - 1, i + context); k++) keep[k] = true;
    });
    const out = [];
    let skipped = 0;
    ops.forEach((o, i) => {
      if (keep[i]) {
        if (skipped) { out.push({ op: 'gap', skipped }); skipped = 0; }
        out.push(o);
      } else skipped++;
    });
    if (skipped) out.push({ op: 'gap', skipped });
    return out;
  }

  D.textDiff = { lines, blocks, collapse };
})(window.DASH);
