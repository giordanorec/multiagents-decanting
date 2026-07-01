/* multiagente dashboard — vanilla JS client. Zero deps. */
(function () {
  "use strict";

  // ---- config / state -------------------------------------------------
  var THEME_KEY = "multiagente.theme";
  var ORDER_KEY = "multiagente.order";
  var PINNED_KEY = "multiagente.pinned";
  var FILTER_KEY = "multiagente.filter";
  var SOUND_KEY = "multiagente.sound";
  var AVATAR_STYLE_KEY = "multiagente.avatarStyle";
  var THEMES = ["auto", "dark", "light"];
  var THEME_GLYPH = { auto: "🌓", dark: "🌙", light: "☀" };
  var FILTERS = ["all", "active", "no-sleeping"];
  var FILTER_LABEL = { all: "todos", active: "só working", "no-sleeping": "esconder sleeping" };

  var colors = {};          // agent -> hex color (from colors.json)
  var avatarCache = { human: {}, icon: {} };  // style -> {agent -> svg markup}
  var ws = null;
  var reconnectDelay = 1000;
  var reconnectTimer = null;
  var lastSnapshot = null;
  var prevSnapshot = null;  // para detectar eventos (sons)

  var order = loadJSON(ORDER_KEY, []);        // ordem custom (slugs)
  var pinned = loadJSON(PINNED_KEY, []);      // slugs pinados (topo)
  var filterMode = localStorage.getItem(FILTER_KEY) || "all";
  if (FILTERS.indexOf(filterMode) === -1) filterMode = "all";
  var soundOn = localStorage.getItem(SOUND_KEY) === "1";
  var avatarStyle = localStorage.getItem(AVATAR_STYLE_KEY);
  if (avatarStyle !== "icon" && avatarStyle !== "human") avatarStyle = "human"; // default: personagens
  var dragSlug = null;

  // stream kinds válidos (espelham o contrato do server / _stream_pretty do v0.2)
  var STREAM_KINDS = {
    read: 1, write: 1, edit: 1, bash: 1, grep: 1, web: 1, agent: 1,
    think: 1, decant: 1, ok: 1, error: 1, start: 1, say: 1, dim: 1, tool: 1,
  };

  // status -> {glyph, label}
  var STATUS = {
    idle:          { glyph: "●", label: "idle" },
    working:       { glyph: "◐", label: "working" },
    decanting:     { glyph: "✎", label: "decantando" },
    human_driving: { glyph: "✋", label: "controle humano" },
    error:         { glyph: "⚠", label: "precisa retomada" },
    needs_recovery:{ glyph: "⚠", label: "precisa retomada" },
    sleeping:      { glyph: "○", label: "sleeping" },
  };

  var AVATARS = [
    "arquiteto", "pipeline-dev", "qa-tester", "dba", "frontend-dev",
    "devops-installer", "docs-writer", "llm-prompt", "mobile-dev",
    "asset-designer", "security-auditor",
  ];

  // ---- storage helpers ------------------------------------------------
  function loadJSON(key, def) {
    try { var v = JSON.parse(localStorage.getItem(key)); return v == null ? def : v; }
    catch (e) { return def; }
  }
  function saveJSON(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }

  // ---- theme ----------------------------------------------------------
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.querySelector(".theme-glyph").textContent = THEME_GLYPH[t] || "☀";
  }
  function initTheme() {
    var saved = localStorage.getItem(THEME_KEY);
    if (THEMES.indexOf(saved) === -1) saved = "auto";
    applyTheme(saved);
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.addEventListener("click", function () {
      var cur = document.documentElement.getAttribute("data-theme") || "auto";
      var next = THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length];
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }

  // ---- controls (filtro + som) — injetados na topbar ------------------
  function initControls() {
    var bar = document.querySelector(".topbar-actions") || document.querySelector(".topbar") || document.body;

    var filterBtn = el("button", "ctrl-btn", FILTER_LABEL[filterMode]);
    filterBtn.id = "filter-toggle";
    filterBtn.title = "filtrar agentes";
    filterBtn.setAttribute("aria-label", "filtrar agentes");
    filterBtn.addEventListener("click", function () {
      filterMode = FILTERS[(FILTERS.indexOf(filterMode) + 1) % FILTERS.length];
      localStorage.setItem(FILTER_KEY, filterMode);
      filterBtn.textContent = FILTER_LABEL[filterMode];
      if (lastSnapshot) renderTeam(lastSnapshot.agents || []);
    });

    var soundBtn = el("button", "ctrl-btn", soundOn ? "🔔" : "🔕");
    soundBtn.id = "sound-toggle";
    soundBtn.title = "sons de notificação";
    soundBtn.setAttribute("aria-label", "alternar sons");
    soundBtn.addEventListener("click", function () {
      soundOn = !soundOn;
      localStorage.setItem(SOUND_KEY, soundOn ? "1" : "0");
      soundBtn.textContent = soundOn ? "🔔" : "🔕";
      if (soundOn) beep(660, 0.06); // feedback
    });

    var avatarBtn = el("button", "ctrl-btn", avatarLabel());
    avatarBtn.id = "avatar-toggle";
    avatarBtn.title = "estilo dos avatares";
    avatarBtn.setAttribute("aria-label", "alternar estilo dos avatares");
    avatarBtn.addEventListener("click", function () {
      avatarStyle = (avatarStyle === "human") ? "icon" : "human";
      localStorage.setItem(AVATAR_STYLE_KEY, avatarStyle);
      avatarBtn.textContent = avatarLabel();
      if (lastSnapshot) renderTeam(lastSnapshot.agents || []);
    });

    bar.insertBefore(soundBtn, bar.firstChild);
    bar.insertBefore(filterBtn, bar.firstChild);
    bar.insertBefore(avatarBtn, bar.firstChild);
  }

  function avatarLabel() {
    return avatarStyle === "human" ? "🙂 personagens" : "⬡ ícones";
  }

  // ---- sound (WebAudio, sem assets) -----------------------------------
  var audioCtx = null;
  function beep(freq, dur) {
    if (!soundOn) return;
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      var o = audioCtx.createOscillator();
      var g = audioCtx.createGain();
      o.type = "sine"; o.frequency.value = freq;
      g.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.15, audioCtx.currentTime + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + (dur || 0.12));
      o.connect(g); g.connect(audioCtx.destination);
      o.start(); o.stop(audioCtx.currentTime + (dur || 0.12));
    } catch (e) {}
  }

  function detectEvents(snap) {
    if (!prevSnapshot) return;
    // feature concluída -> tom de sucesso (sobe)
    var nf = (snap.metrics || {}).features_completed || 0;
    var of = (prevSnapshot.metrics || {}).features_completed || 0;
    if (nf > of) { beep(880, 0.12); }
    // agente entrou em erro -> tom de alerta (desce, duplo)
    var prevStatus = {};
    (prevSnapshot.agents || []).forEach(function (a) { prevStatus[a.agente] = a.status; });
    (snap.agents || []).forEach(function (a) {
      if (a.status === "error" && prevStatus[a.agente] !== "error") {
        beep(330, 0.1); setTimeout(function () { beep(247, 0.14); }, 110);
      }
    });
    // budget cruzou 80% -> aviso
    var m = snap.metrics || {}, pm = prevSnapshot.metrics || {};
    var np = pct(m.cost_today_usd, m.max_cost_per_day_usd);
    var pp = pct(pm.cost_today_usd, pm.max_cost_per_day_usd);
    if (np != null && np >= 80 && (pp == null || pp < 80)) { beep(550, 0.18); }
  }

  // ---- assets ---------------------------------------------------------
  function loadColors() {
    return fetch("/assets/colors.json")
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (j) { colors = j || {}; })
      .catch(function () { colors = {}; });
  }
  function loadAvatar(agent, style) {
    style = (style === "icon") ? "icon" : "human";
    var cache = avatarCache[style] || (avatarCache[style] = {});
    if (cache[agent] !== undefined) return Promise.resolve(cache[agent]);
    var name = AVATARS.indexOf(agent) !== -1 ? agent : null;
    if (!name) { cache[agent] = null; return Promise.resolve(null); }
    var dir = style === "human" ? "/assets/avatars-human/" : "/assets/avatars/";
    return fetch(dir + name + ".svg")
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (svg) {
        // sem SVG humano -> cai no ícone frio
        if (svg == null && style === "human") {
          return loadAvatar(agent, "icon").then(function (ic) { cache[agent] = ic; return ic; });
        }
        cache[agent] = svg; return svg;
      })
      .catch(function () {
        if (style === "human") {
          return loadAvatar(agent, "icon").then(function (ic) { cache[agent] = ic; return ic; });
        }
        cache[agent] = null; return null;
      });
  }
  function colorFor(agent) { return colors[agent] || "var(--accent)"; }

  // ---- connection indicator ------------------------------------------
  function setConn(state) {
    var el2 = document.getElementById("conn");
    if (!el2) return;
    el2.className = "conn conn--" + state;
    var label = { online: "ao vivo", connecting: "conectando…", offline: "reconectando…" }[state];
    el2.querySelector(".conn-label").textContent = label;
    var banner = document.getElementById("offline-banner");
    if (banner) banner.hidden = (state === "online");
  }

  // ---- websocket ------------------------------------------------------
  function wsUrl() {
    var loc = window.location;
    var httpPort = parseInt(loc.port, 10);
    if (!httpPort) httpPort = (loc.protocol === "https:") ? 443 : 8765;
    var wsPort = httpPort + 1000;
    var proto = (loc.protocol === "https:") ? "wss:" : "ws:";
    return proto + "//" + loc.hostname + ":" + wsPort;
  }

  function connect() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    setConn(lastSnapshot ? "offline" : "connecting");
    var url;
    try { url = wsUrl(); } catch (e) { scheduleReconnect(); return; }
    try { ws = new WebSocket(url); } catch (e) { scheduleReconnect(); return; }

    ws.onopen = function () { reconnectDelay = 1000; setConn("online"); };
    ws.onmessage = function (ev) {
      var msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (msg && msg.type === "snapshot") {
        detectEvents(msg);
        prevSnapshot = lastSnapshot;
        lastSnapshot = msg;
        render(msg);
        setConn("online");
      }
    };
    ws.onclose = function () { scheduleReconnect(); };
    ws.onerror = function () { try { ws.close(); } catch (e) {} };
  }

  function scheduleReconnect() {
    setConn("offline");
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(function () { reconnectTimer = null; connect(); }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 1.6, 15000);
  }

  // ---- render ---------------------------------------------------------
  function render(snap) {
    renderTitle(snap.project);
    renderWorkflow(snap.workflow || {});
    renderTeam(snap.agents || []);
    renderMetrics(snap.metrics || {});
    renderActivity(snap.activity || []);
  }

  // helper: index de fase por id (phases agora é lista de {id,label})
  function phaseIndex(phases, id) {
    for (var i = 0; i < phases.length; i++) {
      if (phases[i] && phases[i].id === id) return i;
    }
    return -1;
  }

  function renderWorkflow(wf) {
    var hero = document.getElementById("hero");
    var stepWrap = document.getElementById("stepper-wrap");
    if (!hero || !stepWrap) return;

    // degrade com elegância: sem workflow válido -> esconde tudo
    var label = wf && (wf.phase_label || wf.phase);
    if (!label) {
      hero.hidden = true;
      stepWrap.hidden = true;
      return;
    }
    hero.hidden = false;

    // --- título humano + o que está fazendo ---
    var title = document.getElementById("hero-title");
    title.textContent = wf.phase_label || wf.phase;
    // fase técnica só num tooltip discreto
    title.title = wf.phase ? "fase: " + wf.phase : "";
    var doing = document.getElementById("hero-doing");
    doing.textContent = wf.phase_doing || "";
    doing.style.display = wf.phase_doing ? "" : "none";

    // --- item atual ---
    var item = document.getElementById("hero-item");
    if (wf.feature) {
      item.hidden = false;
      item.innerHTML = "";
      item.appendChild(el("span", "hi-badge", wf.feature));
      var txt = el("span", "hi-text");
      var slug = wf.feature_slug || wf.feature;
      txt.appendChild(el("span", "hi-slug", "Construindo: " + slug));
      var sub = wf.subphase_human || wf.subphase;
      if (sub) {
        txt.appendChild(document.createTextNode(" "));
        txt.appendChild(el("span", "hi-sub", "— " + sub));
      }
      item.appendChild(txt);
    } else {
      item.hidden = true;
      item.innerHTML = "";
    }

    // --- flags: warnings / bypasses ---
    var flags = document.getElementById("hero-flags");
    flags.innerHTML = "";
    if (wf.bypasses > 0) {
      flags.appendChild(el("span", "flag flag--bypass", "⚠ " + wf.bypasses + " bypass" + (wf.bypasses > 1 ? "es" : "")));
    }
    var warnOnly = (wf.warnings || 0) - (wf.bypasses || 0);
    if (warnOnly > 0) {
      flags.appendChild(el("span", "flag flag--warn", "▲ " + warnOnly + " aviso" + (warnOnly > 1 ? "s" : "")));
    }

    // --- próximo passo ---
    var next = document.getElementById("hero-next");
    if (wf.next) {
      next.hidden = false;
      next.innerHTML = "";
      next.appendChild(el("b", null, "A seguir: "));
      next.appendChild(document.createTextNode(wf.next));
    } else {
      next.hidden = true;
    }

    // --- stepper (trilha de etapas) ---
    var phases = wf.phases || [];
    if (!phases.length) {
      stepWrap.hidden = true;
      return;
    }
    stepWrap.hidden = false;
    var ol = document.getElementById("stepper");
    ol.innerHTML = "";
    var curIdx = phaseIndex(phases, wf.phase);
    phases.forEach(function (p, i) {
      var cls = "step";
      if (curIdx !== -1) {
        if (i < curIdx) cls += " is-done";
        else if (i === curIdx) cls += " is-current";
      }
      var li = el("li", cls);
      li.appendChild(el("span", "step-dot"));
      li.appendChild(el("span", "step-label", p.label || p.id || ""));
      ol.appendChild(li);
    });
  }

  function renderTitle(project) {
    var t = "multiagente" + (project ? " · " + project : "");
    document.getElementById("title").textContent = t;
    document.title = t;
  }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }

  // pinados primeiro, depois ordem custom, depois default
  function arrangeAgents(agents) {
    var bySlug = {};
    agents.forEach(function (a) { bySlug[a.agente] = a; });
    var slugs = agents.map(function (a) { return a.agente; });
    slugs.sort(function (x, y) {
      var px = pinned.indexOf(x) !== -1, py = pinned.indexOf(y) !== -1;
      if (px !== py) return px ? -1 : 1;
      var ox = order.indexOf(x), oy = order.indexOf(y);
      if (ox === -1) ox = 1e6; if (oy === -1) oy = 1e6;
      if (ox !== oy) return ox - oy;
      return x.localeCompare(y);
    });
    return slugs.map(function (s) { return bySlug[s]; });
  }

  function passesFilter(a) {
    if (filterMode === "active") return a.status === "working" || a.status === "decanting";
    if (filterMode === "no-sleeping") return a.status !== "sleeping";
    return true;
  }

  function saveOrderFromDOM(root) {
    var ord = [];
    Array.prototype.forEach.call(root.querySelectorAll(".agent"), function (c) {
      if (c.dataset.slug) ord.push(c.dataset.slug);
    });
    order = ord; saveJSON(ORDER_KEY, order);
  }

  function renderTeam(agents) {
    var root = document.getElementById("team");
    updateTeamCount(agents);
    var arranged = arrangeAgents(agents).filter(passesFilter);
    if (!arranged.length) {
      root.innerHTML = '<div class="team-empty" id="team-empty">' +
        (agents.length ? "nenhum agente no filtro atual" : "aguardando agentes…") + "</div>";
      return;
    }
    root.innerHTML = "";
    arranged.forEach(function (a) {
      var status = STATUS[a.status] ? a.status : "idle";
      var meta = STATUS[status];
      var c = colorFor(a.agente);
      var isPinned = pinned.indexOf(a.agente) !== -1;

      var card = el("div", "agent agent--" + status + (isPinned ? " agent--pinned" : ""));
      card.style.setProperty("--agent-color", c);
      card.dataset.slug = a.agente;
      card.setAttribute("draggable", "true");

      // drag-drop reorder
      card.addEventListener("dragstart", function (e) {
        dragSlug = a.agente; card.classList.add("dragging");
        try { e.dataTransfer.effectAllowed = "move"; } catch (x) {}
      });
      card.addEventListener("dragend", function () {
        card.classList.remove("dragging"); saveOrderFromDOM(root);
      });
      card.addEventListener("dragover", function (e) {
        e.preventDefault();
        var dragging = root.querySelector(".dragging");
        if (!dragging || dragging === card) return;
        var rect = card.getBoundingClientRect();
        var after = (e.clientY - rect.top) > rect.height / 2;
        root.insertBefore(dragging, after ? card.nextSibling : card);
      });

      // pin
      var pin = el("button", "agent-pin", isPinned ? "📌" : "📍");
      pin.title = isPinned ? "desafixar" : "fixar no topo";
      pin.setAttribute("aria-label", pin.title);
      pin.addEventListener("click", function (e) {
        e.stopPropagation();
        var i = pinned.indexOf(a.agente);
        if (i === -1) pinned.push(a.agente); else pinned.splice(i, 1);
        saveJSON(PINNED_KEY, pinned);
        if (lastSnapshot) renderTeam(lastSnapshot.agents || []);
      });
      card.appendChild(pin);

      if (status === "sleeping") card.appendChild(el("span", "zzz", "z z z"));

      var avatar = el("div", "agent-avatar");
      avatar.setAttribute("aria-hidden", "true");
      var avInner = el("div", "agent-avatar-inner");
      avatar.appendChild(avInner);
      card.appendChild(avatar);
      loadAvatar(a.agente, avatarStyle).then(function (svg) { avInner.innerHTML = svg || defaultAvatar(); });

      card.appendChild(el("div", "agent-name", a.agente));

      var st = el("div", "agent-status");
      st.appendChild(el("span", "glyph", meta.glyph));
      st.appendChild(el("span", null, meta.label));
      card.appendChild(st);

      card.appendChild(el("div", "agent-bubble", a.bubble || a.note || "—"));

      // mini-terminal ao vivo (estilo tmux) — só se houver stream
      if (Array.isArray(a.stream) && a.stream.length) {
        var term = buildTerminal(a.stream);
        card.appendChild(term);
        // auto-scroll pro fim quando chega linha nova
        requestAnimationFrame(function () { term.scrollTop = term.scrollHeight; });
      }

      var trust = (typeof a.trust === "number") ? a.trust : 50;
      var tw = el("div", "agent-trust");
      var head = el("div", "agent-trust-head");
      head.appendChild(el("span", null, "confiança"));
      head.appendChild(el("b", null, String(trust)));
      tw.appendChild(head);
      var bar = el("div", "trust-bar");
      var fill = el("div", "trust-bar-fill");
      fill.style.width = Math.max(0, Math.min(100, trust)) + "%";
      bar.appendChild(fill);
      tw.appendChild(bar);
      card.appendChild(tw);

      root.appendChild(card);
    });
  }

  function updateTeamCount(agents) {
    var badge = document.getElementById("team-count");
    if (!badge) return;
    var total = agents.length;
    var active = 0;
    agents.forEach(function (a) {
      if (a.status === "working" || a.status === "decanting") active++;
    });
    badge.textContent = total ? (active + " ativo" + (active === 1 ? "" : "s") + " · " + total + " no time") : "";
  }

  function defaultAvatar() {
    return '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3">' +
      '<circle cx="32" cy="24" r="11"/><path d="M14 52 a18 14 0 0 1 36 0" stroke-linecap="round"/></svg>';
  }

  // ---- mini-terminal por agente (stream ao vivo) ---------------------
  function buildTerminal(stream) {
    var term = el("div", "agent-term");
    term.setAttribute("role", "log");
    term.setAttribute("aria-label", "stream ao vivo do agente");
    stream.forEach(function (ln) {
      if (!ln) return;
      var kind = STREAM_KINDS[ln.kind] ? ln.kind : "tool";
      var row = el("div", "term-line term--" + kind);
      if (ln.ts) row.appendChild(el("span", "term-ts", ln.ts));
      row.appendChild(el("span", "term-ic", ln.icon || "·"));
      var tx = el("span", "term-tx");
      if (kind === "edit") appendEditText(tx, ln.text || "");
      else tx.textContent = ln.text || "";
      row.appendChild(tx);
      term.appendChild(row);
    });
    return term;
  }

  // destaca as adições ("+ …") em verde nas linhas de edição
  function appendEditText(node, text) {
    var i = text.indexOf("+ ");
    if (i === -1) { node.textContent = text; return; }
    if (i > 0) node.appendChild(document.createTextNode(text.slice(0, i)));
    node.appendChild(el("span", "term-add", text.slice(i)));
  }

  function fmtInt(n) { return (n || 0).toLocaleString("pt-BR"); }
  function pct(used, max) { if (!max || max <= 0) return null; return Math.min(100, (used / max) * 100); }
  function barClass(p) { if (p == null) return ""; if (p >= 90) return "is-danger"; if (p >= 80) return "is-warn"; return ""; }

  function renderMetrics(m) {
    // modo: "subscription" (padrão, Claude Max — SEM custo em $) ou "paid_api"
    var paid = m.mode === "paid_api";
    var tokens = m.tokens_today || 0;

    document.getElementById("m-tokens").textContent = fmtInt(tokens);
    var tLabel = document.getElementById("m-tokens-label");
    var tBarWrap = document.getElementById("m-tokens-barwrap");
    var tFill = document.getElementById("m-tokens-bar");
    var tSub = document.getElementById("m-tokens-sub");
    var costMetric = document.getElementById("metric-cost");

    if (paid) {
      // API paga: mostra $ e barra de budget
      tLabel.textContent = "Tokens";
      if (tBarWrap) tBarWrap.hidden = false;
      tFill.style.width = tokens > 0 ? "100%" : "0";
      tFill.className = "bar-fill";
      tSub.textContent = fmtInt(tokens) + " tokens hoje";

      if (costMetric) costMetric.hidden = false;
      var cost = m.cost_today_usd || 0;
      var maxCost = m.max_cost_per_day_usd || 0;
      document.getElementById("m-cost").textContent = "$" + cost.toFixed(2) +
        (maxCost ? " / $" + maxCost.toFixed(2) : "");
      var p = pct(cost, maxCost);
      var cFill = document.getElementById("m-cost-bar");
      cFill.style.width = (p == null ? 0 : p) + "%";
      cFill.className = "bar-fill bar-fill--cost " + barClass(p);
      document.getElementById("m-cost-sub").textContent =
        p == null ? "sem budget definido" : p.toFixed(1) + "% do budget diário";
    } else {
      // assinatura (padrão): uso informativo, sem $ nem budget
      tLabel.textContent = "Uso hoje";
      if (tBarWrap) tBarWrap.hidden = true;   // não é budget, esconde a barra
      tSub.textContent = fmtInt(tokens) + " tokens usados · informativo (assinatura, sem custo em $)";
      if (costMetric) costMetric.hidden = true;
    }

    document.getElementById("m-features").textContent = String(m.features_completed || 0);
  }

  var seenActivity = {};   // key -> true, para animar só o que é novo
  function renderActivity(items) {
    var ul = document.getElementById("activity-list");
    if (!items.length) { ul.innerHTML = '<li class="activity-empty">sem atividade recente</li>'; return; }
    var firstRender = Object.keys(seenActivity).length === 0;
    var nextSeen = {};
    ul.innerHTML = "";
    items.forEach(function (it) {
      var key = (it.ts || "") + "|" + (it.text || "");
      nextSeen[key] = true;
      var isNew = !firstRender && !seenActivity[key];
      var li = el("li", isNew ? "act-new" : null);
      li.appendChild(el("span", "act-ts", it.ts || ""));
      var ic = el("span", "act-icon", it.icon || "·");
      ic.setAttribute("data-i", it.icon || "·");
      li.appendChild(ic);
      var text = el("span", "act-text", it.text || "");
      text.title = it.text || "";
      li.appendChild(text);
      ul.appendChild(li);
    });
    seenActivity = nextSeen;
  }

  // ---- service worker -------------------------------------------------
  function registerSW() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    }
  }

  // ---- boot -----------------------------------------------------------
  function boot() {
    initTheme();
    initControls();
    registerSW();
    // hook de dev/teste: permite injetar um snapshot manualmente sem WS
    window.__madRender = function (s) { lastSnapshot = s; render(s); };
    loadColors().then(connect);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
