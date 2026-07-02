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
  var SKIN_KEY = "multiagente.skin";
  var THEMES = ["auto", "dark", "light"];
  var THEME_GLYPH = { auto: "🌓", dark: "🌙", light: "☀" };

  // ---- skins (design systems) ----------------------------------------
  // Each skin => themes/<slug>.css scoped under html[data-skin="<slug>"].
  // 4 reference themes ship now; the other 16 are added later as files —
  // the loader tolerates a missing file (link.onerror) without breaking.
  var SKINS = [
    { slug: "visionos",     label: "visionOS" },
    { slug: "swiss",        label: "Swiss / Internacional" },
    { slug: "brutalism",    label: "Brutalismo" },
    { slug: "neobrutalism", label: "Neo-brutalismo" },
    { slug: "glass",        label: "Glassmorphism" },
    { slug: "neumorphism",  label: "Neumorfismo" },
    { slug: "material",     label: "Material 3" },
    { slug: "terminal",     label: "Terminal / TUI" },
    { slug: "editorial",    label: "Editorial / Revista" },
    { slug: "bauhaus",      label: "Bauhaus" },
    { slug: "memphis",      label: "Memphis 80s" },
    { slug: "cyberpunk",    label: "Cyberpunk / Synthwave" },
    { slug: "clay",         label: "Claymorphism" },
    { slug: "skeuomorphic", label: "Skeuomorfismo" },
    { slug: "darkpro",      label: "Dark Pro (IDE)" },
    { slug: "minimal",      label: "Minimalista / Notion" },
    { slug: "win98",        label: "Retro Windows 98" },
    { slug: "bloomberg",    label: "Denso / Bloomberg" },
    { slug: "duolingo",     label: "Lúdico / Gamificado" },
    { slug: "handdrawn",    label: "Desenhado à mão" },
  ];
  var DEFAULT_SKIN = "visionos";
  var FILTERS = ["all", "active", "no-sleeping"];
  var FILTER_LABEL = { all: "todos", active: "só working", "no-sleeping": "esconder sleeping" };

  var colors = {};          // agent -> hex color (from colors.json)
  var avatarCache = { char: {}, human: {}, icon: {} };  // style -> {agent -> markup}
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
  var AVATAR_STYLES = ["char", "human", "icon"];
  var avatarStyle = localStorage.getItem(AVATAR_STYLE_KEY);
  if (AVATAR_STYLES.indexOf(avatarStyle) === -1) avatarStyle = "char"; // default: personagens de pelúcia
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

  // ---- skins (design systems) ----------------------------------------
  function skinValid(slug) {
    for (var i = 0; i < SKINS.length; i++) if (SKINS[i].slug === slug) return true;
    return false;
  }
  // lazy-inject the <link> for a skin exactly once; tolerate missing file.
  function ensureSkinLink(slug) {
    var id = "skin-css-" + slug;
    if (document.getElementById(id)) return;
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.id = id;
    link.href = "/themes/" + slug + ".css";
    link.onerror = function () {
      // theme file not present yet — base style.css keeps the UI usable.
      // eslint-disable-next-line no-console
      if (window.console) console.info("[skin] '" + slug + "' ainda sem CSS — usando base.");
    };
    document.head.appendChild(link);
  }
  function applySkin(slug) {
    if (!skinValid(slug)) slug = DEFAULT_SKIN;
    ensureSkinLink(slug);
    document.documentElement.dataset.skin = slug;
    localStorage.setItem(SKIN_KEY, slug);
  }
  function initSkins() {
    var sel = document.getElementById("skin-select");
    var saved = localStorage.getItem(SKIN_KEY);
    if (!skinValid(saved)) saved = DEFAULT_SKIN;
    if (sel) {
      SKINS.forEach(function (s) {
        var opt = document.createElement("option");
        opt.value = s.slug;
        opt.textContent = s.label;
        sel.appendChild(opt);
      });
      sel.value = saved;
      sel.addEventListener("change", function () { applySkin(sel.value); });
    }
    // ensure link + attribute (the inline head loader may have run already)
    applySkin(saved);
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
      var i = AVATAR_STYLES.indexOf(avatarStyle);
      avatarStyle = AVATAR_STYLES[(i + 1) % AVATAR_STYLES.length];
      localStorage.setItem(AVATAR_STYLE_KEY, avatarStyle);
      avatarBtn.textContent = avatarLabel();
      if (lastSnapshot) renderTeam(lastSnapshot.agents || []);
    });

    bar.insertBefore(soundBtn, bar.firstChild);
    bar.insertBefore(filterBtn, bar.firstChild);
    bar.insertBefore(avatarBtn, bar.firstChild);
  }

  function avatarLabel() {
    if (avatarStyle === "char") return "🧸 pelúcia";
    if (avatarStyle === "human") return "🙂 personagens";
    return "⬡ ícones";
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
  // cadeia de fallback: char (PNG pelúcia) -> human (SVG mascote) -> icon (SVG frio)
  var AVATAR_FALLBACK = { char: "human", human: "icon", icon: null };

  function loadAvatar(agent, style) {
    if (AVATAR_STYLES.indexOf(style) === -1) style = "char";
    var cache = avatarCache[style] || (avatarCache[style] = {});
    if (cache[agent] !== undefined) return Promise.resolve(cache[agent]);

    var name = AVATARS.indexOf(agent) !== -1 ? agent : null;
    if (!name) { cache[agent] = null; return Promise.resolve(null); }

    var next = AVATAR_FALLBACK[style];
    function fallback() {
      if (!next) { cache[agent] = null; return Promise.resolve(null); }
      return loadAvatar(agent, next).then(function (m) { cache[agent] = m; return m; });
    }

    if (style === "char") {
      // PNG (fundo transparente) -> markup <img>. HEAD confirma existência.
      var src = "/assets/avatars-char/" + name + ".png";
      return fetch(src, { method: "HEAD" })
        .then(function (r) {
          if (!r.ok) return fallback();
          var markup = '<img class="avatar-img" src="' + src + '" alt="" draggable="false">';
          cache[agent] = markup; return markup;
        })
        .catch(fallback);
    }

    // human / icon -> SVG inline
    var dir = style === "human" ? "/assets/avatars-human/" : "/assets/avatars/";
    return fetch(dir + name + ".svg")
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (svg) {
        if (svg == null) return fallback();
        cache[agent] = svg; return svg;
      })
      .catch(fallback);
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
    var wf = snap.workflow || {};
    renderWorkflow(wf);
    renderParallel(wf.parallel);
    renderTeam(snap.agents || []);
    renderMetrics(snap.metrics || {});
    renderActivity(snap.activity || []);
    // keep the fullscreen view in sync while it's open
    if (fsOpenSlug) {
      var fa = agentBySlug(fsOpenSlug);
      if (fa) updateFullscreen(fa); else closeAgent();
    }
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
    if (!hero) return;

    // degrade com elegância: sem workflow válido -> esconde tudo
    var label = wf && (wf.phase_label || wf.phase);
    if (!label) {
      hero.hidden = true;
      renderWorkflowMap(wf || {});   // esconde o mapa também
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

    // --- mapa do workflow (jornada educativa) ---
    renderWorkflowMap(wf);
  }

  // ===================================================================
  //  MAPA DO WORKFLOW — jornada educativa: nós + arestas + ramificações
  //  + sub-loop de "Construindo" + painel explicador (hover/click/teclado)
  // ===================================================================
  var wfState = {
    sig: null,        // assinatura do estado; evita rebuild (preserva hover)
    phases: [],       // guide.phases atual
    curIdx: -1,       // índice da fase atual
    curId: null,      // id da fase atual
    pinnedId: null,   // nó fixado por clique (persiste entre snapshots)
    hoverId: null,    // nó em hover/foco (transiente, preview)
    wired: false,     // Escape/unpin já ligados?
  };

  // "ainda há itens → próximo item" -> "próximo item" (rótulo curto na aresta)
  function wfShorten(when) {
    if (!when) return "";
    var i = when.indexOf("→");
    if (i !== -1) return when.slice(i + 1).trim();
    return when.trim();
  }

  function subIndex(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return i;
    // "aprovacao_humano" não está no subloop de 5 — trate como o portão "Conferindo"
    if (id === "aprovacao_humano") {
      for (var j = 0; j < list.length; j++) if (list[j].id === "validando") return j;
    }
    return -1;
  }

  function renderWorkflowMap(wf) {
    var wrap = document.getElementById("wfmap-wrap");
    if (!wrap) return;
    if (!wfState.wired) initWorkflowMap();

    var guide = wf && wf.guide;
    var phases = guide && guide.phases;
    // degrade com elegância: sem guia -> esconde o mapa inteiro
    if (!phases || !phases.length) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;

    var curIdx = phaseIndex(phases, wf.phase);
    var sig = [
      wf.phase, wf.subphase, wf.phase_doing || "",
      phases.map(function (p) { return p.id; }).join(","),
    ].join("|");

    // sempre atualiza refs (barato) — o explicador depende delas
    wfState.phases = phases;
    wfState.curIdx = curIdx;
    wfState.curId = wf.phase;
    if (wfState.pinnedId && phaseIndex(phases, wfState.pinnedId) === -1) {
      wfState.pinnedId = null;
    }

    // só reconstrói o DOM quando o estado muda (preserva hover/interação)
    if (sig !== wfState.sig) {
      wfState.sig = sig;
      buildMap(wf, phases, curIdx);
      buildSubloop(wf, (guide.subloop || []));
    }
    updateExplainer();
  }

  function initWorkflowMap() {
    wfState.wired = true;
    var wrap = document.getElementById("wfmap-wrap");
    if (!wrap) return;
    // Escape solta o nó fixado
    wrap.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && wfState.pinnedId) {
        e.preventDefault();
        wfState.pinnedId = null;
        reflectPin();
        updateExplainer();
      }
    });
  }

  function buildMap(wf, phases, curIdx) {
    var map = document.getElementById("wfmap");
    if (!map) return;
    map.innerHTML = "";
    var lastIdx = phases.length - 1;
    phases.forEach(function (p, i) {
      map.appendChild(buildNode(wf, p, i, curIdx));
      if (i < lastIdx) {
        var nextId = phases[i + 1].id;
        var when = "";
        (p.goes_to || []).forEach(function (g) { if (g.to === nextId) when = g.when; });
        map.appendChild(buildEdge(wfShorten(when), i, curIdx));
      }
    });

    // trilho de retorno do ciclo (último nó volta a uma fase anterior)
    var ret = document.getElementById("wfreturn");
    if (ret) {
      ret.innerHTML = "";
      var last = phases[lastIdx];
      var retWhen = null, retTo = null;
      (last.goes_to || []).forEach(function (g) {
        var ti = phaseIndex(phases, g.to);
        if (ti !== -1 && ti < lastIdx) { retWhen = g.when; retTo = phases[ti].label; }
      });
      if (retWhen) {
        ret.hidden = false;
        ret.classList.toggle("is-active", curIdx === lastIdx);
        var arrow = el("span", "wfreturn-arrow", "⟲");
        arrow.setAttribute("aria-hidden", "true");
        ret.appendChild(arrow);
        var lbl = el("span", "wfreturn-label");
        lbl.appendChild(el("b", null, retWhen));
        if (retTo) lbl.appendChild(document.createTextNode(" — recomeça em “" + retTo + "”"));
        ret.appendChild(lbl);
      } else {
        ret.hidden = true;
      }
    }
  }

  function nodeState(i, curIdx) {
    if (curIdx === -1) return "future";
    if (i < curIdx) return "done";
    if (i === curIdx) return "current";
    return "future";
  }

  function buildNode(wf, p, i, curIdx) {
    var state = nodeState(i, curIdx);
    var node = el("div", "wfnode is-" + state);
    node.setAttribute("role", "listitem");
    node.dataset.id = p.id;
    if (wfState.pinnedId === p.id) node.classList.add("is-selected");

    var btn = el("button", "wfnode-btn");
    btn.type = "button";
    btn.setAttribute("aria-controls", "wf-explainer");
    btn.setAttribute("aria-expanded", wfState.pinnedId === p.id ? "true" : "false");
    btn.setAttribute("aria-label",
      (p.label || p.id) + (i === curIdx ? " — você está aqui." : ".") + " Ver detalhes desta fase.");

    var badge = el("span", "wfnode-badge");
    badge.setAttribute("aria-hidden", "true");
    var ic = el("span", "wfnode-icon", p.icon || "•");
    badge.appendChild(ic);
    if (state === "done") badge.appendChild(el("span", "wfnode-check", "✓"));
    btn.appendChild(badge);

    btn.appendChild(el("span", "wfnode-label", p.label || p.id));
    node.appendChild(btn);

    if (i === curIdx) {
      var here = el("span", "wfnode-here");
      here.appendChild(el("span", "wfnode-here-dot"));
      here.appendChild(document.createTextNode("você está aqui"));
      node.appendChild(here);
      var doing = wf.phase_doing || p.doing;
      if (doing) node.appendChild(el("span", "wfnode-doing", doing));
    }

    var branches = buildBranches(p, i, phases_of(), curIdx);
    if (branches) node.appendChild(branches);

    wireNode(btn, p.id);
    return node;
  }

  function phases_of() { return wfState.phases; }

  // ramificações que NÃO são a aresta linear pra frente nem o trilho de retorno
  function buildBranches(p, i, phases, curIdx) {
    var isLast = i === phases.length - 1;
    var nextId = !isLast ? phases[i + 1].id : null;
    var items = [];
    (p.goes_to || []).forEach(function (g) {
      if (g.to === nextId) return;               // aresta linear -> vira label da aresta
      var ti = phaseIndex(phases, g.to);
      if (isLast && ti !== -1 && ti < i) return; // volta do último -> trilho de retorno
      var arrow = (ti === i) ? "↻" : (ti !== -1 && ti < i ? "↩" : "↳");
      items.push({ arrow: arrow, txt: wfShorten(g.when) });
    });
    if (!items.length) return null;
    var box = el("div", "wfnode-branches");
    box.setAttribute("aria-hidden", "true"); // conteúdo repetido no explicador
    items.forEach(function (it) {
      var b = el("span", "wfnode-branch");
      b.appendChild(el("span", "wfbr-arrow", it.arrow));
      b.appendChild(document.createTextNode(" " + it.txt));
      box.appendChild(b);
    });
    return box;
  }

  function buildEdge(label, i, curIdx) {
    var state = nodeState(i, curIdx); // aresta i liga nó i -> i+1; herda o estado do nó i
    var e = el("div", "wfedge is-" + state);
    e.setAttribute("aria-hidden", "true");
    var line = el("div", "wfedge-line");
    e.appendChild(line);
    if (label) e.appendChild(el("span", "wfedge-label", label));
    return e;
  }

  function wireNode(btn, id) {
    btn.addEventListener("mouseenter", function () { wfState.hoverId = id; updateExplainer(); });
    btn.addEventListener("mouseleave", function () {
      if (wfState.hoverId === id) wfState.hoverId = null;
      updateExplainer();
    });
    btn.addEventListener("focus", function () { wfState.hoverId = id; updateExplainer(); });
    btn.addEventListener("blur", function () {
      if (wfState.hoverId === id) wfState.hoverId = null;
      updateExplainer();
    });
    btn.addEventListener("click", function () {
      wfState.pinnedId = (wfState.pinnedId === id) ? null : id;
      reflectPin();
      updateExplainer();
    });
  }

  function reflectPin() {
    var map = document.getElementById("wfmap");
    if (!map) return;
    Array.prototype.forEach.call(map.querySelectorAll(".wfnode"), function (n) {
      var sel = n.dataset.id === wfState.pinnedId;
      n.classList.toggle("is-selected", sel);
      var b = n.querySelector(".wfnode-btn");
      if (b) b.setAttribute("aria-expanded", sel ? "true" : "false");
    });
  }

  function updateExplainer() {
    var box = document.getElementById("wf-explainer");
    if (!box) return;
    var phases = wfState.phases;
    var showId = wfState.hoverId || wfState.pinnedId || wfState.curId;
    var idx = phaseIndex(phases, showId);
    if (idx === -1) { box.hidden = true; box.innerHTML = ""; return; }
    box.hidden = false;
    var p = phases[idx];
    var isCur = showId === wfState.curId;
    var pinned = wfState.pinnedId === showId;
    box.innerHTML = "";

    var head = el("div", "wfx-head");
    var ic = el("span", "wfx-icon", p.icon || "•");
    ic.setAttribute("aria-hidden", "true");
    head.appendChild(ic);
    head.appendChild(el("span", "wfx-title", p.label || p.id));
    if (isCur) {
      head.appendChild(el("span", "wfx-tag wfx-tag--here", "você está aqui"));
    } else {
      var pos = (wfState.curIdx !== -1 && idx < wfState.curIdx) ? "já passou" : "ainda vem";
      head.appendChild(el("span", "wfx-tag wfx-tag--muted", pos));
    }
    if (pinned) head.appendChild(el("span", "wfx-pin", "📌 fixado — Esc solta"));
    box.appendChild(head);

    if (p.detail) box.appendChild(el("p", "wfx-detail", p.detail));

    if (p.advance) {
      var adv = el("div", "wfx-row wfx-advance");
      adv.appendChild(el("b", "wfx-k", "O que faz avançar: "));
      adv.appendChild(document.createTextNode(p.advance));
      box.appendChild(adv);
    }

    if (p.goes_to && p.goes_to.length) {
      var g = el("div", "wfx-row wfx-goes");
      g.appendChild(el("b", "wfx-k", "Pra onde pode ir:"));
      var ul = el("ul", "wfx-list");
      p.goes_to.forEach(function (go) {
        var toIdx = phaseIndex(phases, go.to);
        var toLabel = toIdx !== -1 ? phases[toIdx].label : go.to;
        var li = el("li");
        li.appendChild(el("span", "wfx-when", go.when));
        li.appendChild(el("span", "wfx-to", "→ " + toLabel));
        ul.appendChild(li);
      });
      g.appendChild(ul);
      box.appendChild(g);
    }
  }

  function buildSubloop(wf, subloop) {
    var box = document.getElementById("wfsub");
    if (!box) return;
    if (wf.phase !== "LOOP_FEATURES" || !subloop.length) {
      box.hidden = true; box.innerHTML = "";
      return;
    }
    box.hidden = false;
    box.innerHTML = "";

    var head = el("div", "wfsub-head");
    var hIc = el("span", "wfsub-head-ic", "🔁");
    hIc.setAttribute("aria-hidden", "true");
    head.appendChild(hIc);
    head.appendChild(document.createTextNode("Dentro de "));
    head.appendChild(el("b", null, "Construindo"));
    head.appendChild(document.createTextNode(", cada item passa por:"));
    box.appendChild(head);

    var track = el("div", "wfsub-track");
    var curSubIdx = subIndex(subloop, wf.subphase);
    subloop.forEach(function (s, i) {
      var cls = "wfsub-step";
      if (curSubIdx !== -1) {
        if (i < curSubIdx) cls += " is-done";
        else if (i === curSubIdx) cls += " is-current";
        else cls += " is-future";
      }
      var step = el("div", cls);
      if (s.detail) step.title = s.detail;
      var ic = el("span", "wfsub-icon", s.icon || "•");
      ic.setAttribute("aria-hidden", "true");
      step.appendChild(ic);
      step.appendChild(el("span", "wfsub-label", s.label || s.id));
      track.appendChild(step);
      if (i < subloop.length - 1) {
        var ar = el("span", "wfsub-arrow", "→");
        ar.setAttribute("aria-hidden", "true");
        track.appendChild(ar);
      }
    });
    var loop = el("span", "wfsub-loop", "↺ repete por item");
    loop.setAttribute("aria-hidden", "true");
    track.appendChild(loop);
    box.appendChild(track);
  }

  // ===================================================================
  //  PARALELO — features rodando ao mesmo tempo (motor DAG)
  //  Só aparece quando workflow.parallel tem >1 item. Com 0/1, é o modo
  //  sequential de sempre e este bloco fica escondido (degrade gracioso).
  // ===================================================================
  function renderParallel(list) {
    var sec = document.getElementById("parallel");
    if (!sec) return;
    var grid = document.getElementById("parallel-grid");

    if (!Array.isArray(list) || list.length <= 1) {
      sec.hidden = true;
      if (grid) grid.innerHTML = "";
      return;
    }
    sec.hidden = false;

    var titleEl = document.getElementById("parallel-title");
    if (titleEl) titleEl.textContent = "Construindo " + list.length + " coisas ao mesmo tempo";

    if (!grid) return;
    grid.innerHTML = "";
    list.forEach(function (f, i) {
      if (!f) return;
      var slug = f.slug || f.id || "item";

      var card = el("div", "pfeat");
      card.setAttribute("role", "listitem");
      card.style.setProperty("--pfeat-i", String(i));
      if (f.agent) card.style.setProperty("--agent-color", colorFor(f.agent));

      var name = el("div", "pfeat-name");
      var dot = el("span", "pfeat-dot");
      dot.setAttribute("aria-hidden", "true");
      name.appendChild(dot);
      name.appendChild(el("span", "pfeat-slug", slug));
      card.appendChild(name);

      var doing = f.subphase_human || f.subphase;
      if (doing) card.appendChild(el("div", "pfeat-doing", doing));

      if (f.agent) {
        var who = el("div", "pfeat-agent");
        var wic = el("span", "pfeat-agent-ic", "🤖");
        wic.setAttribute("aria-hidden", "true");
        who.appendChild(wic);
        who.appendChild(el("span", "pfeat-agent-name", f.agent));
        card.appendChild(who);
      }

      grid.appendChild(card);
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
      card.setAttribute("tabindex", "0");
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", "abrir " + a.agente + " em tela cheia");

      var justDragged = false;   // supress the click that follows a drag

      // click / keyboard -> abre a visão em tela cheia do agente
      card.addEventListener("click", function (e) {
        if (justDragged) return;
        if (e.target && e.target.closest && e.target.closest(".agent-pin")) return;
        openAgent(a.agente, card);
      });
      card.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openAgent(a.agente, card);
        }
      });

      // drag-drop reorder
      card.addEventListener("dragstart", function (e) {
        dragSlug = a.agente; card.classList.add("dragging");
        try { e.dataTransfer.effectAllowed = "move"; } catch (x) {}
      });
      card.addEventListener("dragend", function () {
        card.classList.remove("dragging"); saveOrderFromDOM(root);
        justDragged = true; setTimeout(function () { justDragged = false; }, 80);
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

      var openHint = el("span", "agent-open-hint", "⤢ abrir");
      openHint.setAttribute("aria-hidden", "true");
      card.appendChild(openHint);

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

  // ---- fullscreen agent view (modal / tela cheia) --------------------
  var fsOpenSlug = null;
  var fsLastFocused = null;
  var fsEl = null;

  function clamp01(n) { return Math.max(0, Math.min(100, n)); }

  function agentBySlug(slug) {
    if (!lastSnapshot) return null;
    var list = lastSnapshot.agents || [];
    for (var i = 0; i < list.length; i++) if (list[i].agente === slug) return list[i];
    return null;
  }

  function renderFsTerminal(holder, stream) {
    var old = holder.firstChild;
    var nearBottom = true;
    if (old && old.scrollHeight) {
      nearBottom = (old.scrollHeight - old.scrollTop - old.clientHeight) < 28;
    }
    holder.innerHTML = "";
    if (Array.isArray(stream) && stream.length) {
      var term = buildTerminal(stream);
      term.classList.add("fs-term");
      holder.appendChild(term);
      if (nearBottom) requestAnimationFrame(function () { term.scrollTop = term.scrollHeight; });
    } else {
      holder.appendChild(el("div", "fs-term-empty", "sem stream ainda — o agente não emitiu linhas."));
    }
  }

  function buildFullscreenBody(a) {
    var frag = document.createDocumentFragment();
    var status = STATUS[a.status] ? a.status : "idle";
    var meta = STATUS[status];

    var closeBtn = el("button", "fs-close", "✕");
    closeBtn.type = "button";
    closeBtn.setAttribute("aria-label", "fechar tela cheia");
    closeBtn.addEventListener("click", closeAgent);
    frag.appendChild(closeBtn);

    var head = el("div", "fs-head");
    var avatar = el("div", "fs-avatar");
    avatar.setAttribute("aria-hidden", "true");
    var avInner = el("div", "fs-avatar-inner");
    avatar.appendChild(avInner);
    loadAvatar(a.agente, avatarStyle).then(function (svg) { avInner.innerHTML = svg || defaultAvatar(); });
    head.appendChild(avatar);

    var metaBox = el("div", "fs-meta");
    var name = el("h2", "fs-name", a.agente);
    name.id = "fs-name";
    metaBox.appendChild(name);

    var st = el("div", "fs-status");
    st.appendChild(el("span", "glyph", meta.glyph));
    st.appendChild(el("span", "fs-status-label", meta.label));
    metaBox.appendChild(st);

    var trust = (typeof a.trust === "number") ? a.trust : 50;
    var tw = el("div", "fs-trust");
    var thead = el("div", "fs-trust-head");
    thead.appendChild(el("span", null, "confiança"));
    thead.appendChild(el("b", "fs-trust-val", String(trust)));
    tw.appendChild(thead);
    var bar = el("div", "trust-bar");
    var fill = el("div", "trust-bar-fill");
    fill.style.width = clamp01(trust) + "%";
    bar.appendChild(fill);
    tw.appendChild(bar);
    metaBox.appendChild(tw);
    head.appendChild(metaBox);
    frag.appendChild(head);

    frag.appendChild(el("div", "fs-bubble", a.bubble || a.note || "—"));

    var wrap = el("div", "fs-term-wrap");
    var label = el("div", "fs-term-label");
    label.appendChild(el("span", null, "stream ao vivo"));
    label.appendChild(el("span", "live-dot"));
    wrap.appendChild(label);
    var holder = el("div", "fs-term-holder");
    wrap.appendChild(holder);
    renderFsTerminal(holder, a.stream);
    frag.appendChild(wrap);

    return frag;
  }

  function updateFullscreen(a) {
    if (!fsEl) return;
    var status = STATUS[a.status] ? a.status : "idle";
    var meta = STATUS[status];
    var panel = fsEl.querySelector(".fs-panel");
    if (panel) panel.style.setProperty("--agent-color", colorFor(a.agente));
    var glyph = fsEl.querySelector(".fs-status .glyph");
    if (glyph) glyph.textContent = meta.glyph;
    var slabel = fsEl.querySelector(".fs-status-label");
    if (slabel) slabel.textContent = meta.label;
    var trust = (typeof a.trust === "number") ? a.trust : 50;
    var tval = fsEl.querySelector(".fs-trust-val");
    if (tval) tval.textContent = String(trust);
    var fill = fsEl.querySelector(".fs-trust .trust-bar-fill");
    if (fill) fill.style.width = clamp01(trust) + "%";
    var bubble = fsEl.querySelector(".fs-bubble");
    if (bubble) bubble.textContent = a.bubble || a.note || "—";
    var holder = fsEl.querySelector(".fs-term-holder");
    if (holder) renderFsTerminal(holder, a.stream);
  }

  function onFsKeydown(e) {
    if (e.key === "Escape") { e.preventDefault(); closeAgent(); return; }
    if (e.key === "Tab" && fsEl) {
      var nodes = fsEl.querySelectorAll('button, [href], select, input, [tabindex]:not([tabindex="-1"])');
      var f = Array.prototype.filter.call(nodes, function (n) { return n.offsetParent !== null; });
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }

  function openAgent(slug, originEl) {
    var a = agentBySlug(slug);
    if (!a) return;
    if (fsEl) closeAgent();
    fsOpenSlug = slug;
    fsLastFocused = document.activeElement;

    var overlay = el("div", "fullscreen-agent");
    overlay.id = "fullscreen-agent";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "fs-name");

    if (originEl && originEl.getBoundingClientRect) {
      var r = originEl.getBoundingClientRect();
      var ox = ((r.left + r.width / 2) / (window.innerWidth || 1)) * 100;
      var oy = ((r.top + r.height / 2) / (window.innerHeight || 1)) * 100;
      overlay.style.setProperty("--fs-origin-x", ox.toFixed(1) + "%");
      overlay.style.setProperty("--fs-origin-y", oy.toFixed(1) + "%");
    }

    var backdrop = el("div", "fs-backdrop");
    backdrop.addEventListener("click", closeAgent);
    overlay.appendChild(backdrop);

    var panel = el("div", "fs-panel");
    panel.style.setProperty("--agent-color", colorFor(slug));
    panel.appendChild(buildFullscreenBody(a));
    overlay.appendChild(panel);

    overlay.addEventListener("keydown", onFsKeydown);
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
    fsEl = overlay;

    var closeBtn = overlay.querySelector(".fs-close");
    if (closeBtn) closeBtn.focus();
  }

  function closeAgent() {
    if (!fsEl) return;
    var overlay = fsEl;
    fsEl = null;
    fsOpenSlug = null;
    overlay.removeEventListener("keydown", onFsKeydown);
    overlay.classList.add("is-closing");
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var done = function () { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); };
    if (reduce) done(); else setTimeout(done, 190);
    document.body.style.overflow = "";
    if (fsLastFocused && fsLastFocused.focus) { try { fsLastFocused.focus(); } catch (e) {} }
    fsLastFocused = null;
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
    initSkins();
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
