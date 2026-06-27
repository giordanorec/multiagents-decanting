/* ====================================================================
   Ideation Dashboard — main controller
   Vanilla JS. Polls ./state/status.json and ./state/events.jsonl.
   ==================================================================== */

(() => {
  'use strict';

  // ===================== Config =====================
  const CONFIG = {
    statusPath:     '../state/status.json',
    eventsPath:     '../state/events.jsonl',
    ideasPath:      '../state/ideas.jsonl',
    archivePath:    '../state/archive.json',
    embeddingsPath: '../state/embeddings.jsonl',
    statusInterval: 1500,
    eventsInterval: 800,
    animSpacingMs:  250,
    decayAfterSec:  60,
    decayMinAlpha:  0.25,
  };

  // ===================== State =====================
  const S = {
    status: null,
    lastStatus: null,
    events: [],
    eventOffset: 0,
    eventQueue: [],
    animBusy: false,
    nodes: new Map(),        // id -> node object
    links: [],               // {source, target, kind}
    linkIndex: new Set(),    // source|target|kind
    ideaCache: new Map(),    // id -> idea record (essence/rationale)
    embeddings: [],          // raw 384-dim vectors
    embeddingOffset: 0,
    phases: [],              // {phase, t0, t1}
    rounds: [],              // {round, t0, t1}
    archiveCache: null,
    firstStatusSeen: false,
    drawers: { umap:false, parallel:false, coverage:false, lineage:false },
    lineageFocus: null,
  };

  // ===================== DOM =====================
  const $ = id => document.getElementById(id);

  // ===================== Charts =====================
  let graph = null;
  let coverageGauge = null;
  let timelineChart = null;
  let umapChart = null;
  let parallelChart = null;
  let coverageHeatmap = null;
  let lineageChart = null;

  // ====================================================
  //                  INITIALIZATION
  // ====================================================
  function init() {
    initGraph();
    initCoverageGauge();
    initTimeline();
    initDrawers();
    initThemeToggle();

    // Start polling loops
    pollStatus(); setInterval(pollStatus, CONFIG.statusInterval);
    pollEvents(); setInterval(pollEvents, CONFIG.eventsInterval);

    // Animation queue tick
    setInterval(processAnimQueue, CONFIG.animSpacingMs);

    // Decay refresh ticker — force graph redraw every 600ms
    setInterval(() => { if (graph) graph.nodeRelSize(graph.nodeRelSize()); }, 600);

    window.addEventListener('resize', () => {
      coverageGauge && coverageGauge.resize();
      timelineChart && timelineChart.resize();
      umapChart && umapChart.resize();
      parallelChart && parallelChart.resize();
      coverageHeatmap && coverageHeatmap.resize();
      lineageChart && lineageChart.resize();
      if (graph) {
        const el = $('graphCanvas');
        graph.width(el.clientWidth).height(el.clientHeight);
      }
    });
  }

  // ====================================================
  //                  FORCE GRAPH
  // ====================================================
  function initGraph() {
    const el = $('graphCanvas');
    graph = ForceGraph()(el)
      .width(el.clientWidth)
      .height(el.clientHeight)
      .backgroundColor('rgba(0,0,0,0)')
      .nodeId('id')
      .nodeRelSize(4)
      .nodeAutoColorBy('cluster')
      .cooldownTime(Infinity)
      .d3AlphaDecay(0.01)
      .d3VelocityDecay(0.35)
      .linkColor(l => l.kind === 'centroid' ? 'rgba(120,130,150,0.15)' : 'rgba(180,160,120,0.35)')
      .linkWidth(l => l.kind === 'centroid' ? 0.5 : 1)
      .linkDirectionalParticles(l => l._active ? 4 : 0)
      .linkDirectionalParticleSpeed(0.012)
      .linkDirectionalParticleWidth(2)
      .nodeCanvasObject(drawNode)
      .nodePointerAreaPaint(nodePointerArea)
      .onNodeClick(node => focusLineage(node.id))
      .onNodeHover(node => { document.body.style.cursor = node ? 'pointer' : 'default'; });

    // Tooltip-like via title (force-graph builds DOM label automatically)
    graph.nodeLabel(n => `${n.id} — ${(n.essence||'').slice(0,80)}`);
  }

  function drawNode(node, ctx, scale) {
    const now = Date.now() / 1000;
    const lastRef = node.last_referenced_at || node._created || now;
    const ageSec = now - lastRef;
    let alpha = 1.0;
    if (ageSec > CONFIG.decayAfterSec) {
      const over = ageSec - CONFIG.decayAfterSec;
      alpha = Math.max(CONFIG.decayMinAlpha, 1 - over / 180);
    }

    // Animation alpha overrides
    if (node._spawnT) {
      const dt = (Date.now() - node._spawnT) / 300;
      if (dt < 1) {
        const ease = Math.min(1, dt);
        node._size = (node._targetSize || 5) * ease;
        const haloR = 18 * (1 - ease) + 4;
        ctx.beginPath();
        ctx.arc(node.x, node.y, haloR, 0, 2*Math.PI);
        ctx.fillStyle = `rgba(255,255,255,${0.5 * (1-ease)})`;
        ctx.fill();
      } else { node._spawnT = null; node._size = node._targetSize; }
    }
    if (node._goldenT) {
      const dt = (Date.now() - node._goldenT) / 1000;
      if (dt < 1) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, (node._size||5) + 10*(1-dt), 0, 2*Math.PI);
        ctx.fillStyle = `rgba(232,196,109,${0.45 * (1-dt)})`;
        ctx.fill();
      } else { node._goldenT = null; }
    }
    if (node._critT) {
      const dt = (Date.now() - node._critT) / 1200;
      if (dt < 1) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, (node._size||5) + 6 + 8*Math.sin(dt*Math.PI*2), 0, 2*Math.PI);
        ctx.strokeStyle = node._critColor || 'rgba(217,122,108,0.7)';
        ctx.lineWidth = 1.6;
        ctx.stroke();
      } else { node._critT = null; }
    }
    if (node._burstT) {
      const dt = (Date.now() - node._burstT) / 500;
      if (dt < 1) {
        for (let i = 0; i < 6; i++) {
          const a = i * Math.PI / 3;
          const r = 25 * dt;
          ctx.beginPath();
          ctx.arc(node.x + Math.cos(a)*r, node.y + Math.sin(a)*r, 2*(1-dt), 0, 2*Math.PI);
          ctx.fillStyle = `rgba(212,165,116,${0.7*(1-dt)})`;
          ctx.fill();
        }
      } else { node._burstT = null; }
    }
    if (node._ghost) { alpha *= 0.4; }
    if (node._winnerT) {
      const dt = (Date.now() - node._winnerT) / 600;
      if (dt < 1) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, (node._size||5) + 6*Math.sin(dt*Math.PI), 0, 2*Math.PI);
        ctx.strokeStyle = `rgba(126,200,178,${0.6*(1-dt)})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      } else { node._winnerT = null; }
    }

    // Node body
    const r = node._size || 5;
    const c = node.color || '#d4a574';
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2*Math.PI);
    ctx.fillStyle = c;
    ctx.fill();
    ctx.lineWidth = 0.8;
    ctx.strokeStyle = 'rgba(0,0,0,0.4)';
    ctx.stroke();

    // Promoted ring
    if (node.promoted) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 2.5, 0, 2*Math.PI);
      ctx.strokeStyle = 'rgba(232,196,109,0.9)';
      ctx.lineWidth = 1.4;
      ctx.stroke();
    }

    // Label for big nodes
    if (scale > 1.5 && r > 5) {
      const lbl = (node.essence || node.id).slice(0, 18);
      ctx.font = `${Math.max(8, 10/scale*1.2)}px ui-monospace, monospace`;
      ctx.fillStyle = 'rgba(230,232,236,0.65)';
      ctx.textAlign = 'center';
      ctx.fillText(lbl, node.x, node.y + r + 8);
    }
    ctx.globalAlpha = 1;
  }

  function nodePointerArea(node, color, ctx) {
    const r = (node._size || 5) + 4;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2*Math.PI);
    ctx.fillStyle = color; ctx.fill();
  }

  function ensureNode(id, init={}) {
    if (S.nodes.has(id)) return S.nodes.get(id);
    const n = {
      id, _size: 5, _targetSize: 5, _created: Date.now()/1000,
      last_referenced_at: Date.now()/1000,
      cluster: init.cluster || 'unassigned',
      essence: init.essence || '',
      promoted: false,
      ...init,
    };
    S.nodes.set(id, n);
    return n;
  }

  function addLink(source, target, kind='lineage') {
    const key = `${source}|${target}|${kind}`;
    if (S.linkIndex.has(key)) return;
    S.linkIndex.add(key);
    S.links.push({ source, target, kind });
  }

  function refreshGraphData() {
    if (!graph) return;
    const data = { nodes: Array.from(S.nodes.values()), links: S.links };
    graph.graphData(data);
    if (S.nodes.size > 0) {
      $('emptyState').classList.add('hidden');
    }
  }

  function touchNode(id) {
    const n = S.nodes.get(id);
    if (n) n.last_referenced_at = Date.now()/1000;
  }

  // ====================================================
  //                  STATUS POLLING
  // ====================================================
  async function pollStatus() {
    try {
      const r = await fetch(CONFIG.statusPath, { cache: 'no-store' });
      if (!r.ok) return;
      const status = await r.json();
      S.lastStatus = S.status;
      S.status = status;
      S.firstStatusSeen = true;
      applyStatus(status);
    } catch (e) {
      // silent — file may not yet exist
    }
  }

  function applyStatus(st) {
    $('topicLabel').textContent = st.topic || '—';
    $('runIdLabel').textContent = (st.run_id || '—').slice(0, 14);
    $('tierLabel').textContent  = st.tier || '—';

    setMaybePulse('phaseLabel', st.phase || '—');
    setMaybePulse('roundLabel', `${st.round ?? '-'}/${st.max_rounds ?? '-'}`);

    $('elapsedLabel').textContent = formatElapsed(st.elapsed_seconds || 0);
    $('ideasCountLabel').textContent = st.ideas_count ?? 0;

    // Coverage gauge
    if (coverageGauge) {
      const cov = (st.coverage_pct || 0) * 100;
      coverageGauge.setOption({ series: [{ data: [{ value: cov.toFixed(1), name: 'cov' }] }] });
    }

    renderAgents(st.agents || []);
    renderTopIdeas(st.top_ideas || []);
    renderGaps(st.structural_gaps || []);

    // Hydrate top ideas into graph nodes (essence/elo/promoted) for nicer rendering
    (st.top_ideas || []).forEach(ti => {
      const n = ensureNode(ti.id, { essence: ti.essence, cluster: ti.cluster, elo: ti.elo });
      n.essence = ti.essence; n.cluster = ti.cluster; n.elo = ti.elo;
      n._targetSize = Math.max(5, Math.min(14, 5 + (ti.elo - 1500) / 40));
    });
    refreshGraphData();
  }

  function setMaybePulse(id, val) {
    const el = $(id);
    if (el.textContent !== String(val)) {
      el.textContent = val;
      el.classList.remove('flash'); void el.offsetWidth;
      el.classList.add('flash');
    }
  }

  function formatElapsed(s) {
    s = Math.floor(s);
    const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), ss = s%60;
    if (h) return `${h}h ${m}m`;
    if (m) return `${m}m ${ss}s`;
    return `${ss}s`;
  }

  // ====================================================
  //                  SIDE PANELS
  // ====================================================
  function renderAgents(agents) {
    $('agentsCount').textContent = agents.length;
    const html = agents.map(a => `
      <div class="agent-row ${a.status || 'idle'}">
        <div class="agent-dot"></div>
        <div class="agent-info">
          <div class="agent-name">${escape(a.name)}</div>
          <div class="agent-task">${escape(a.task || '—')}</div>
          <div class="agent-persona">${escape((a.persona || '').slice(0, 60))}</div>
        </div>
      </div>
    `).join('');
    $('agentsList').innerHTML = html || '<div class="empty-msg" style="padding:12px;color:var(--text-faint)">No agents reporting</div>';
  }

  function renderTopIdeas(ideas) {
    const html = ideas.slice(0, 5).map(i => `
      <div class="idea-row" data-id="${i.id}">
        <div class="idea-essence">${escape(i.essence || '—')}</div>
        <div class="idea-meta">
          <span>${escape(i.cluster || 'unassigned')}</span>
          <span class="idea-elo">${i.elo ?? '—'}</span>
        </div>
      </div>
    `).join('');
    $('topIdeasList').innerHTML = html || '<div class="empty-msg" style="padding:12px;color:var(--text-faint)">No ideas yet</div>';
    $('topIdeasList').querySelectorAll('.idea-row').forEach(el => {
      el.addEventListener('click', () => focusLineage(el.dataset.id));
    });
  }

  function renderGaps(gaps) {
    $('gapsCount').textContent = gaps.length;
    const html = gaps.slice(0, 8).map(g => {
      const axes = g.axes ? Object.entries(g.axes).map(([k,v]) => `${k}=${v}`).join(', ') : '';
      const cell = g.cell ? `[${g.cell.join(',')}]` : '';
      return `<div class="gap-row"><span class="gap-cell">${cell}</span> missing: ${escape(axes)}</div>`;
    }).join('');
    $('gapsList').innerHTML = html || '<div class="empty-msg" style="padding:12px;color:var(--text-faint)">No gaps identified</div>';
  }

  function escape(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ====================================================
  //                  EVENTS POLLING (byte-offset tail)
  // ====================================================
  async function pollEvents() {
    try {
      let res;
      try {
        res = await fetch(CONFIG.eventsPath, {
          cache: 'no-store',
          headers: { 'Range': `bytes=${S.eventOffset}-` },
        });
      } catch (e) { return; }

      if (res.status === 416) return; // requested range not satisfiable, no new bytes

      if (res.status === 206) {
        const text = await res.text();
        const cl = res.headers.get('Content-Length');
        if (cl) S.eventOffset += parseInt(cl, 10);
        else    S.eventOffset += text.length;
        ingestEventText(text);
        return;
      }

      if (res.ok) {
        // Fallback: server doesn't support Range — re-fetch full and parse newer lines
        const text = await res.text();
        // If we already saw bytes, only take suffix
        if (S.eventOffset > 0 && text.length >= S.eventOffset) {
          ingestEventText(text.slice(S.eventOffset));
        } else {
          ingestEventText(text);
        }
        S.eventOffset = text.length;
      }
    } catch (e) {
      // silent
    }
  }

  function ingestEventText(text) {
    if (!text) return;
    const lines = text.split('\n');
    for (const line of lines) {
      const t = line.trim();
      if (!t) continue;
      try {
        const ev = JSON.parse(t);
        console.log('[event]', ev.type, ev.id || ev.to || ev.from || ev.agent || '');
        S.events.push(ev);
        S.eventQueue.push(ev);
      } catch (e) {
        console.warn('bad event line', t.slice(0, 80));
      }
    }
  }

  // ====================================================
  //                  ANIMATION QUEUE
  // ====================================================
  function processAnimQueue() {
    if (S.eventQueue.length === 0) return;
    const ev = S.eventQueue.shift();
    handleEvent(ev);
  }

  function handleEvent(ev) {
    switch (ev.type) {
      case 'idea_created':       onIdeaCreated(ev); break;
      case 'idea_merged':        onIdeaMerged(ev); break;
      case 'idea_bifurcated':    onIdeaBifurcated(ev); break;
      case 'idea_promoted':      onIdeaPromoted(ev); break;
      case 'idea_critiqued':     onIdeaCritiqued(ev); break;
      case 'axes_transformed':   onAxesTransformed(ev); break;
      case 'tournament_result':  onTournament(ev); break;
      case 'phase_transition':   onPhaseTransition(ev); break;
      case 'round_started':      onRoundStarted(ev); break;
      case 'round_completed':    onRoundCompleted(ev); break;
      case 'agent_started':      /* feed will refresh via status */ break;
      case 'agent_completed':    break;
      case 'clusters_updated':   onClustersUpdated(ev); break;
      case 'pareto_extracted':   showToast(`Pareto front: ${ev.count} ideas`); break;
      case 'final_report':       showToast('Final report ready'); break;
    }
    refreshGraphData();
  }

  function onIdeaCreated(ev) {
    const n = ensureNode(ev.id, { essence: '', cluster: ev.cell ? `c${ev.cell[0]}` : 'new' });
    n._spawnT = Date.now();
    n._size = 0;
    n._targetSize = 6;
    n._created = Date.now()/1000;
    (ev.parents || []).forEach(p => {
      ensureNode(p);
      addLink(p, ev.id, 'lineage');
      // Activate the link briefly for particles
      const link = S.links.find(l => (l.source === p || (l.source && l.source.id === p)) && (l.target === ev.id || (l.target && l.target.id === ev.id)));
      if (link) { link._active = true; setTimeout(() => { link._active = false; }, 1500); }
      touchNode(p);
    });
  }

  function onIdeaMerged(ev) {
    const n = ensureNode(ev.to, { cluster: 'merged' });
    n._spawnT = Date.now();
    n._targetSize = 7;
    (ev.from || []).forEach(p => {
      ensureNode(p);
      addLink(p, ev.to, 'lineage');
      const link = S.links.find(l => link2id(l.source) === p && link2id(l.target) === ev.to);
      if (link) { link._active = true; setTimeout(() => { link._active = false; }, 2000); }
      const pn = S.nodes.get(p);
      if (pn) { setTimeout(() => { pn._ghost = true; }, 1500); }
    });
  }

  function onIdeaBifurcated(ev) {
    const src = ensureNode(ev.from);
    src._burstT = Date.now();
    (ev.to || []).forEach(c => {
      const cn = ensureNode(c);
      cn._spawnT = Date.now();
      cn._targetSize = 6;
      addLink(ev.from, c, 'lineage');
      const link = S.links.find(l => link2id(l.source) === ev.from && link2id(l.target) === c);
      if (link) { link._active = true; setTimeout(() => { link._active = false; }, 1500); }
    });
  }

  function onIdeaPromoted(ev) {
    const n = ensureNode(ev.id);
    n.promoted = true;
    n._goldenT = Date.now();
    n._targetSize = (n._targetSize || 6) * 1.2;
    touchNode(ev.id);
  }

  function onIdeaCritiqued(ev) {
    const n = ensureNode(ev.id);
    n._critT = Date.now();
    n._critColor = ev.critic === 'minority' ? 'rgba(108,199,181,0.85)' :
                   ev.critic === 'black-hat' ? 'rgba(217,122,108,0.85)' :
                   'rgba(200,200,200,0.7)';
    touchNode(ev.id);
  }

  function onAxesTransformed(ev) {
    // Full graph shimmer: dim every node briefly
    S.nodes.forEach(n => {
      const orig = n._ghost;
      n._ghost = true;
      setTimeout(() => { n._ghost = orig || false; }, 800);
    });
    showToast('Axes transformed');
  }

  function onTournament(ev) {
    const w = ensureNode(ev.winner);
    w._winnerT = Date.now();
    if (typeof ev.elo_delta === 'number') {
      w.elo = (w.elo || 1500) + ev.elo_delta;
    }
    const l = ensureNode(ev.loser);
    l._targetSize = Math.max(3, (l._targetSize || 5) - 0.4);
    if (typeof ev.elo_delta === 'number') {
      l.elo = (l.elo || 1500) - ev.elo_delta;
    }
  }

  function onPhaseTransition(ev) {
    showToast(`Entering: ${ev.to}`);
    const nowT = Date.now();
    if (S.phases.length) S.phases[S.phases.length-1].t1 = nowT;
    S.phases.push({ phase: ev.to, t0: nowT, t1: null });
    refreshTimeline();
  }

  function onRoundStarted(ev) {
    setMaybePulse('roundLabel', `${ev.round}/${S.status?.max_rounds ?? '-'}`);
    const nowT = Date.now();
    if (S.rounds.length) S.rounds[S.rounds.length-1].t1 = nowT;
    S.rounds.push({ round: ev.round, t0: nowT, t1: null });
    refreshTimeline();
  }

  function onRoundCompleted(ev) {
    const r = S.rounds.find(x => x.round === ev.round);
    if (r) r.t1 = Date.now();
    refreshTimeline();
  }

  function onClustersUpdated(ev) {
    // Color refresh handled by nodeAutoColorBy on next graphData
    showToast(`Clusters: ${ev.count}`);
  }

  function link2id(x) { return typeof x === 'object' ? x.id : x; }

  // ====================================================
  //                  TOASTS
  // ====================================================
  function showToast(msg) {
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    $('toastStack').appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  // ====================================================
  //                  COVERAGE GAUGE
  // ====================================================
  function initCoverageGauge() {
    coverageGauge = echarts.init($('coverageGauge'), null, { renderer: 'canvas' });
    coverageGauge.setOption({
      series: [{
        type: 'gauge',
        startAngle: 200, endAngle: -20,
        min: 0, max: 100,
        radius: '95%',
        center: ['50%', '70%'],
        progress: { show: true, width: 6, itemStyle: { color: '#d4a574' } },
        axisLine: { lineStyle: { width: 6, color: [[1, '#2a313c']] } },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        title: { show: false },
        detail: {
          valueAnimation: true,
          formatter: '{value}%',
          fontSize: 13,
          color: '#e6e8ec',
          offsetCenter: [0, '-10%'],
          fontFamily: 'ui-monospace, monospace',
        },
        data: [{ value: 0, name: 'cov' }],
      }],
    });
  }

  // ====================================================
  //                  TIMELINE
  // ====================================================
  function initTimeline() {
    timelineChart = echarts.init($('timeline'), null, { renderer: 'canvas' });
    refreshTimeline();
  }

  function refreshTimeline() {
    if (!timelineChart) return;
    const phaseBars = S.phases.map((p, i) => ({
      name: p.phase, value: [i, p.t0, p.t1 || Date.now(), p.phase],
      itemStyle: { color: '#7ec8b2' },
    }));
    const roundBars = S.rounds.map((r, i) => ({
      name: `r${r.round}`, value: [i, r.t0, r.t1 || Date.now(), `round ${r.round}`],
      itemStyle: { color: '#d4a574' },
    }));

    timelineChart.setOption({
      grid: { left: 60, right: 16, top: 8, bottom: 18 },
      tooltip: {
        formatter: p => `${p.value[3]}<br>${new Date(p.value[1]).toLocaleTimeString()} → ${new Date(p.value[2]).toLocaleTimeString()}`,
      },
      xAxis: {
        type: 'time',
        axisLabel: { color: '#98a0ad', fontSize: 9 },
        axisLine: { lineStyle: { color: '#2a313c' } },
      },
      yAxis: {
        type: 'category', data: ['phase', 'round'],
        axisLabel: { color: '#98a0ad', fontSize: 10 },
        axisLine: { lineStyle: { color: '#2a313c' } },
      },
      series: [{
        type: 'custom',
        renderItem: (params, api) => {
          const yCat = api.value(0) === undefined ? 0 : api.value(0);
          const cat = params.dataIndex < phaseBars.length ? 0 : 1;
          const start = api.coord([api.value(1), cat]);
          const end   = api.coord([api.value(2), cat]);
          const height = 14;
          return {
            type: 'rect',
            shape: { x: start[0], y: start[1] - height/2, width: Math.max(2, end[0]-start[0]), height },
            style: api.style({ opacity: 0.85 }),
          };
        },
        encode: { x: [1, 2], y: 0 },
        data: phaseBars.map(b => ({ ...b, value: [0, b.value[1], b.value[2], b.value[3]], itemStyle: b.itemStyle }))
                       .concat(roundBars.map(b => ({ ...b, value: [1, b.value[1], b.value[2], b.value[3]], itemStyle: b.itemStyle }))),
      }],
    });
  }

  // ====================================================
  //                  DRAWERS
  // ====================================================
  function initDrawers() {
    document.querySelectorAll('.drawer-btn').forEach(btn => {
      btn.addEventListener('click', () => openDrawer(btn.dataset.drawer));
    });
    document.querySelectorAll('.drawer-close').forEach(btn => {
      btn.addEventListener('click', () => closeDrawer(btn.dataset.close));
    });
    $('drawerScrim').addEventListener('click', closeAllDrawers);
  }

  function openDrawer(name) {
    closeAllDrawers();
    const dr = $(`drawer-${name}`);
    if (!dr) return;
    dr.classList.add('open');
    $('drawerScrim').classList.add('open');
    S.drawers[name] = true;
    setTimeout(() => populateDrawer(name), 200);
  }

  function closeDrawer(name) {
    const dr = $(`drawer-${name}`);
    if (dr) dr.classList.remove('open');
    S.drawers[name] = false;
    if (!Object.values(S.drawers).some(v => v)) $('drawerScrim').classList.remove('open');
  }

  function closeAllDrawers() {
    Object.keys(S.drawers).forEach(closeDrawer);
  }

  async function populateDrawer(name) {
    if (name === 'umap')      await populateUMAP();
    if (name === 'parallel')  populateParallel();
    if (name === 'coverage')  await populateCoverage();
    if (name === 'lineage')   populateLineage();
  }

  // ---- UMAP ----
  async function populateUMAP() {
    if (!umapChart) umapChart = echarts.init($('umapChart'), null, { renderer: 'canvas' });
    umapChart.showLoading({ text: 'Loading embeddings...', color: '#d4a574',
      textColor: '#e6e8ec', maskColor: 'rgba(20,23,28,0.7)' });

    try {
      const r = await fetch(CONFIG.embeddingsPath, { cache: 'no-store' });
      if (!r.ok) { umapChart.hideLoading();
        umapChart.setOption({ title: { text: 'embeddings unavailable', left: 'center', top: 'center', textStyle: { color: '#98a0ad' } } });
        return;
      }
      const text = await r.text();
      const entries = text.split('\n').filter(Boolean).map(l => JSON.parse(l));
      const vectors = entries.map(e => e.vector || e.embedding || e.v);
      const ids = entries.map(e => e.id || '');
      if (vectors.length < 3 || !window.UMAP) {
        umapChart.hideLoading();
        umapChart.setOption({ title: { text: 'not enough data for UMAP', left: 'center', top: 'center', textStyle: { color: '#98a0ad' } } });
        return;
      }
      const umap = new UMAP.UMAP({ nComponents: 2, nNeighbors: Math.min(15, vectors.length - 1) });
      const proj = umap.fit(vectors);
      const data = proj.map((p, i) => {
        const node = S.nodes.get(ids[i]);
        return { value: [p[0], p[1]], name: ids[i], itemStyle: { color: node?.color || '#d4a574' } };
      });
      umapChart.hideLoading();
      umapChart.setOption({
        tooltip: { formatter: p => `${p.name}` },
        xAxis: { type: 'value', axisLabel: { color: '#98a0ad' } },
        yAxis: { type: 'value', axisLabel: { color: '#98a0ad' } },
        series: [{ type: 'scatter', data, symbolSize: 8 }],
      });
    } catch (e) {
      umapChart.hideLoading();
      umapChart.setOption({ title: { text: 'embeddings unavailable', left: 'center', top: 'center', textStyle: { color: '#98a0ad' } } });
    }
  }

  // ---- Parallel ----
  function populateParallel() {
    if (!parallelChart) parallelChart = echarts.init($('parallelChart'), null, { renderer: 'canvas' });
    const ideas = S.status?.top_ideas || [];
    if (!ideas.length) {
      parallelChart.setOption({ title: { text: 'no ideas yet', left: 'center', top: 'center', textStyle: { color: '#98a0ad' } } });
      return;
    }
    // Synthesize axes from idea attributes if present, else fallback to elo/cluster
    const data = ideas.map(i => [i.elo || 1500, i.cluster ? i.cluster.length : 0, (i.essence || '').length]);
    parallelChart.setOption({
      parallelAxis: [
        { dim: 0, name: 'elo' },
        { dim: 1, name: 'cluster_len' },
        { dim: 2, name: 'essence_len' },
      ],
      parallel: { left: 60, right: 60, top: 40, bottom: 40,
        parallelAxisDefault: { axisLine: { lineStyle: { color: '#98a0ad' } }, nameTextStyle: { color: '#e6e8ec' } } },
      series: [{ type: 'parallel', lineStyle: { color: '#d4a574', width: 1, opacity: 0.6 }, data }],
    });
  }

  // ---- Coverage Heatmap ----
  async function populateCoverage() {
    if (!coverageHeatmap) coverageHeatmap = echarts.init($('coverageHeatmap'), null, { renderer: 'canvas' });
    try {
      const r = await fetch(CONFIG.archivePath, { cache: 'no-store' });
      if (!r.ok) throw new Error('no archive');
      const arch = await r.json();
      S.archiveCache = arch;

      const cells = arch.cells || arch.archive || [];
      // Project to first 2 dimensions; average scores within (d0,d1) bins
      const map = new Map();
      let maxD0 = 0, maxD1 = 0;
      cells.forEach(c => {
        const idx = c.cell || c.coords || [0, 0];
        const d0 = idx[0] ?? 0, d1 = idx[1] ?? 0;
        const score = c.score ?? c.elite_score ?? 0;
        const key = `${d0}|${d1}`;
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(score);
        if (d0 > maxD0) maxD0 = d0;
        if (d1 > maxD1) maxD1 = d1;
      });
      const data = [];
      for (const [k, vs] of map.entries()) {
        const [d0, d1] = k.split('|').map(Number);
        const avg = vs.reduce((a,b) => a+b, 0) / vs.length;
        data.push([d0, d1, avg]);
      }
      coverageHeatmap.setOption({
        tooltip: { position: 'top' },
        xAxis: { type: 'category', data: range(maxD0+1).map(String), axisLabel: { color: '#98a0ad' } },
        yAxis: { type: 'category', data: range(maxD1+1).map(String), axisLabel: { color: '#98a0ad' } },
        visualMap: { min: 0, max: 1, calculable: true, orient: 'horizontal',
          left: 'center', bottom: 0, textStyle: { color: '#e6e8ec' },
          inRange: { color: ['#1a1e25', '#7ec8b2', '#d4a574', '#e8c46d'] } },
        series: [{ type: 'heatmap', data,
          label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: '#fff' } } }],
      });
    } catch (e) {
      coverageHeatmap.setOption({ title: { text: 'archive unavailable', left: 'center', top: 'center', textStyle: { color: '#98a0ad' } } });
    }
  }

  function range(n) { return Array.from({ length: n }, (_, i) => i); }

  // ---- Lineage ----
  function focusLineage(id) {
    S.lineageFocus = id;
    $('lineageFocus').textContent = `(${id})`;
    openDrawer('lineage');
  }

  function populateLineage() {
    if (!lineageChart) lineageChart = echarts.init($('lineageTree'), null, { renderer: 'canvas' });
    if (!S.lineageFocus) {
      lineageChart.setOption({ title: { text: 'click a node to focus', left: 'center', top: 'center', textStyle: { color: '#98a0ad' } } });
      return;
    }

    // Build ancestor + descendant tree via BFS over S.links
    const root = S.lineageFocus;
    const upward = buildTree(root, 'up');
    lineageChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'tree',
        data: [upward],
        top: '5%', left: '12%', right: '12%', bottom: '5%',
        symbol: 'circle', symbolSize: 14,
        orient: 'TB',
        label: { position: 'top', rotate: 0, color: '#e6e8ec', fontFamily: 'ui-monospace, monospace', fontSize: 11 },
        leaves: { label: { position: 'bottom' } },
        emphasis: { focus: 'descendant' },
        expandAndCollapse: true,
        animationDuration: 500,
      }],
    });
  }

  function buildTree(id, dir) {
    const visited = new Set();
    function build(nid, depth) {
      if (visited.has(nid) || depth > 6) return { name: nid };
      visited.add(nid);
      const node = S.nodes.get(nid);
      const label = node?.essence ? node.essence.slice(0, 24) : nid;
      const children = [];
      for (const l of S.links) {
        const src = link2id(l.source), tgt = link2id(l.target);
        if (dir === 'up' && tgt === nid) children.push(build(src, depth+1));
        if (dir === 'down' && src === nid) children.push(build(tgt, depth+1));
      }
      return { name: label, id: nid, children };
    }
    return build(id, 0);
  }

  // ====================================================
  //                  THEME TOGGLE
  // ====================================================
  function initThemeToggle() {
    const saved = localStorage.getItem('idea-theme');
    if (saved) document.body.dataset.theme = saved;
    $('themeToggle').addEventListener('click', () => {
      const cur = document.body.dataset.theme || 'dark';
      const next = cur === 'dark' ? 'light' : 'dark';
      document.body.dataset.theme = next;
      localStorage.setItem('idea-theme', next);
    });
  }

  // ====================================================
  //                  BOOT
  // ====================================================
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
