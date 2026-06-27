/* multiagente dashboard — vanilla JS client. Zero deps. */
(function () {
  "use strict";

  // ---- config / state -------------------------------------------------
  var THEME_KEY = "multiagente.theme";
  var THEMES = ["auto", "dark", "light"];
  var THEME_GLYPH = { auto: "🌓", dark: "🌙", light: "☀" };

  var colors = {};          // agent -> hex color (from colors.json)
  var avatarCache = {};     // agent -> svg markup
  var ws = null;
  var reconnectDelay = 1000;
  var reconnectTimer = null;
  var lastSnapshot = null;

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

  // map agent slug -> avatar file (fallback to slug itself)
  var AVATARS = [
    "arquiteto", "pipeline-dev", "qa-tester", "dba", "frontend-dev",
    "devops-installer", "docs-writer", "llm-prompt", "mobile-dev",
    "asset-designer", "security-auditor",
  ];

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

  // ---- assets ---------------------------------------------------------
  function loadColors() {
    return fetch("/assets/colors.json")
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (j) { colors = j || {}; })
      .catch(function () { colors = {}; });
  }
  function loadAvatar(agent) {
    if (avatarCache[agent] !== undefined) return Promise.resolve(avatarCache[agent]);
    var name = AVATARS.indexOf(agent) !== -1 ? agent : null;
    if (!name) { avatarCache[agent] = null; return Promise.resolve(null); }
    return fetch("/assets/avatars/" + name + ".svg")
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (svg) { avatarCache[agent] = svg; return svg; })
      .catch(function () { avatarCache[agent] = null; return null; });
  }
  function colorFor(agent) { return colors[agent] || "var(--accent)"; }

  // ---- connection indicator ------------------------------------------
  function setConn(state) {
    var el = document.getElementById("conn");
    if (!el) return;
    el.className = "conn conn--" + state;
    var label = { online: "ao vivo", connecting: "conectando…", offline: "reconectando…" }[state];
    el.querySelector(".conn-label").textContent = label;
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

    ws.onopen = function () {
      reconnectDelay = 1000;
      setConn("online");
    };
    ws.onmessage = function (ev) {
      var msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (msg && msg.type === "snapshot") {
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
    reconnectTimer = setTimeout(function () {
      reconnectTimer = null;
      connect();
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 1.6, 15000);
  }

  // ---- render ---------------------------------------------------------
  function render(snap) {
    renderTitle(snap.project);
    renderTeam(snap.agents || []);
    renderMetrics(snap.metrics || {});
    renderActivity(snap.activity || []);
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

  function renderTeam(agents) {
    var root = document.getElementById("team");
    if (!agents.length) {
      root.innerHTML = '<div class="team-empty" id="team-empty">aguardando agentes…</div>';
      return;
    }
    root.innerHTML = "";
    agents.forEach(function (a) {
      var status = STATUS[a.status] ? a.status : "idle";
      var meta = STATUS[status];
      var c = colorFor(a.agente);

      var card = el("div", "agent agent--" + status);
      card.style.setProperty("--agent-color", c);

      if (status === "sleeping") card.appendChild(el("span", "zzz", "z z z"));

      var avatar = el("div", "agent-avatar");
      avatar.setAttribute("aria-hidden", "true");
      card.appendChild(avatar);
      loadAvatar(a.agente).then(function (svg) {
        avatar.innerHTML = svg || defaultAvatar();
      });

      card.appendChild(el("div", "agent-name", a.agente));

      var st = el("div", "agent-status");
      st.appendChild(el("span", "glyph", meta.glyph));
      st.appendChild(el("span", null, meta.label));
      card.appendChild(st);

      var bubbleText = a.bubble || a.note || "—";
      card.appendChild(el("div", "agent-bubble", bubbleText));

      var trust = (typeof a.trust === "number") ? a.trust : 50;
      var tw = el("div", "agent-trust");
      var head = el("div", "agent-trust-head");
      head.appendChild(el("span", null, "trust"));
      head.appendChild(el("span", null, String(trust)));
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

  function defaultAvatar() {
    return '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3">' +
      '<circle cx="32" cy="24" r="11"/><path d="M14 52 a18 14 0 0 1 36 0" stroke-linecap="round"/></svg>';
  }

  function fmtInt(n) {
    return (n || 0).toLocaleString("pt-BR");
  }
  function pct(used, max) {
    if (!max || max <= 0) return null;
    return Math.min(100, (used / max) * 100);
  }
  function barClass(p) {
    if (p == null) return "";
    if (p >= 90) return "is-danger";
    if (p >= 80) return "is-warn";
    return "";
  }

  function renderMetrics(m) {
    var tokens = m.tokens_today || 0;
    document.getElementById("m-tokens").textContent = fmtInt(tokens);
    // no token budget in contract; show tokens with no bar reference
    var tFill = document.getElementById("m-tokens-bar");
    tFill.style.width = tokens > 0 ? "100%" : "0";
    tFill.className = "bar-fill";
    document.getElementById("m-tokens-sub").textContent = fmtInt(tokens) + " tokens hoje";

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

    document.getElementById("m-features").textContent = String(m.features_completed || 0);
  }

  function renderActivity(items) {
    var ul = document.getElementById("activity-list");
    if (!items.length) {
      ul.innerHTML = '<li class="activity-empty">sem atividade recente</li>';
      return;
    }
    ul.innerHTML = "";
    items.forEach(function (it) {
      var li = el("li");
      li.appendChild(el("span", "act-ts", it.ts || ""));
      var ic = el("span", "act-icon", it.icon || "·");
      ic.setAttribute("data-i", it.icon || "·");
      li.appendChild(ic);
      li.appendChild(el("span", "act-text", it.text || ""));
      ul.appendChild(li);
    });
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
    registerSW();
    loadColors().then(connect);
    // re-render on system theme change while in auto mode (CSS handles it,
    // but update the toggle glyph stays accurate — nothing else needed).
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
