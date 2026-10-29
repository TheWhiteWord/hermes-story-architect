window.DASH = window.DASH || {};

DASH._currentBarcodeMode = 'type';
DASH._chartObservers = {};


DASH._ensureChartRendered = function(containerId, renderFn) {
  const container = document.getElementById(containerId);
  if (!container) return;
  // Clean up previous observer for this container
  if (DASH._chartObservers[containerId]) {
    DASH._chartObservers[containerId].disconnect();
    delete DASH._chartObservers[containerId];
  }
  // Render immediately
  renderFn();
  // Observe resize — re-render when container reaches final size (after CSS transition)
  const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
      if (entry.contentRect.width > 0) {
        renderFn();
      }
    }
  });
  ro.observe(container);
  DASH._chartObservers[containerId] = ro;
}

DASH.renderDurationChart = function(stats) {
  DASH._ensureChartRendered('durationStats-lengthchart', () => {
    DASH._renderDurationChart(stats);
  });
}

DASH._renderDurationChart = function(stats) {
  const container = document.getElementById('durationStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const ds = stats.durationStats || {};
  const actionData = ds.lengthchart_action   || [];
  const dialogueData = ds.lengthchart_dialogue || [];
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
  const g = svg.append('g').attr('transform', `translate(${mg.left},${mg.top})`);

  const x = d3.scaleLinear().domain([0, len - 1]).range([0, w]);
  const maxY = d3.max([...aData, ...dData]) || 1;
  const y = d3.scaleLinear().domain([0, maxY]).range([h, 0]);

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
    .call(d3.axisLeft(y).ticks(3).tickFormat(d => DASH.fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');

  // Legend
  const leg = svg.append('g').attr('transform', `translate(${mg.left + w - 86},${mg.top + 2})`);
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',5).attr('fill','#7b9cf0');
  leg.append('text').attr('x',12).attr('y',9).text('Action').style('font-size','8px').attr('fill','var(--muted-foreground)');
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',17).attr('fill','#6bbfb0');
  leg.append('text').attr('x',12).attr('y',21).text('Dialogue').style('font-size','8px').attr('fill','var(--muted-foreground)');
}

DASH.renderCharacterChart = function(stats) {
  const container = document.getElementById('characterStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const chars = ((stats.characterStats || {}).characters || []).slice(0, 8);
  if (!chars.length) return;

  const W = container.clientWidth  || 320;
  const H = container.clientHeight || 110;
  const mg = { top: 6, right: 8, bottom: 18, left: 70 };
  const w = W - mg.left - mg.right;
  const h = H - mg.top  - mg.bottom;

  const svg = d3.select(container).append('svg').attr('width',W).attr('height',H);
  const g = svg.append('g').attr('transform',`translate(${mg.left},${mg.top})`);

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
    .call(d3.axisBottom(x).ticks(4).tickFormat(d => DASH.fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');
}

DASH.renderBarcodeChart = function(mode) {
  DASH._currentBarcodeMode = mode;
  const container = document.getElementById('sceneStats-timechart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const stats = window.__SCREENPLAY_STATS__;
  const scenes = stats && stats.sceneStats && stats.sceneStats.scenes || [];
  if (!scenes.length) return;

  const TYPE_COL = { int:'#7b9cf0', ext:'#6bbfb0', mixed:'#e0a86b', other:'#555' };
  const TIME_COL = {
    dawn:'#e06b9b', morning:'#e07070', day:'#e0c96b',
    afternoon:'#e0c96b', evening:'#b07be0', dusk:'#6bbfb0',
    night:'#7b9cf0', continuous:'#555', later:'#555', unspecified:'#333'
  };

  const W = container.clientWidth || 320;
  const H = container.clientHeight || 44;
  const pad = 3;
  const bw = Math.max(1.5, (W - pad * 2) / scenes.length);

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
