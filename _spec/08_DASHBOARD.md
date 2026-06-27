# 08 — Dashboard

## 8.1 Visão

Dashboard local rodando em browser. Cada agente é um **personagem visual** com avatar, cor, status animado, e bubble de última ação. Layout "sala de equipe": todos os agentes visíveis simultaneamente. Theme dark/light, responsivo mobile, PWA installable.

Razões de design (consolidação da pesquisa):

- **Web, não tmux:** roda em qualquer SO; não depende de terminal específico.
- **Personagens em vez de logs crus:** tornar o sistema legível para leigos.
- **PWA installable:** usuário pode "instalar" como app no desktop ou mobile.
- **TUI Textual como fallback:** quando o usuário está em SSH sem browser.

## 8.2 Stack

- **Backend:** Python 3.9+, `http.server` (stdlib) + biblioteca `websockets` (única dep externa; ~1MB; instalada via pip no init).
- **Frontend:** HTML5 + CSS3 + JavaScript vanilla. **Zero frameworks** (sem React, Vue, Svelte). Build step = zero.
- **Avatars:** SVG inline; paleta de cores em `dashboard/assets/colors.json`.
- **Real-time:** WebSocket consumindo `logs/otel/<date>.jsonl` (spans OpenTelemetry GenAI emitidos pelos hooks do plugin) via tail + broadcast. Não há stream-json proprietário; OTel é a fonte única.
- **PWA:** manifest.json + service worker (~30 linhas).

## 8.3 Arquitetura

```
┌─ Browser ──────────────────────────────────────────┐
│  index.html                                         │
│   ├─ app.js (vanilla)                              │
│   │   ├─ WebSocket: ws://localhost:8765/ws         │
│   │   ├─ render: lista de personagens (App.render) │
│   │   └─ state: agentes[], métricas, theme         │
│   ├─ style.css (dark/light/responsivo)             │
│   ├─ manifest.json (PWA)                           │
│   └─ sw.js (service worker)                        │
└─────────────────────────────────────────────────────┘
                       ▲
                       │ WebSocket
                       ▼
┌─ Python: dashboard_server.py ─────────────────────┐
│  http.server (porta 8765)                           │
│   ├─ GET /         → serve index.html              │
│   ├─ GET /static/* → serve dashboard/assets/       │
│   └─ WebSocket /ws → broadcast em tempo real       │
│                                                      │
│  Background threads:                                 │
│   ├─ otel_tailer: tail -f logs/otel/<date>.jsonl    │
│   │   (deriva status dos agentes dos spans recentes)│
│   ├─ otel_aggregator: agrega métricas (tokens, $)   │
│   ├─ memory_watcher: monitora memory/*/handoff.md   │
│   │   pra mostrar última nota de cada agente        │
│   └─ broadcast_loop: empurra updates ao WS          │
└──────────────────────────────────────────────────────┘
                       ▲
                       │ filesystem reads
                       ▼
┌─ Filesystem ────────────────────────────────────────┐
│  logs/otel/<date>.jsonl    (fonte primária)          │
│  memory/<agente>/handoff.md (última nota)            │
│  memory/<agente>/trust.json (score)                  │
│  reports/<feature>/<agente>.md (entregas)            │
│  multiagents-decanting.toml (config, budget)         │
└──────────────────────────────────────────────────────┘
```

## 8.4 Layout do frontend

```
┌─────────────────────────────────────────────────────────────┐
│ multiagente-vivos · projeto: <nome>          [doctor] [⚙] [☀]│
├─────────────────────────────────────────────────────────────┤
│ ┌─ arquiteto ─┐ ┌─ pipeline-dev ┐ ┌─ qa-tester ─┐          │
│ │   [avatar]  │ │   [avatar]     │ │  [avatar]    │          │
│ │   verde     │ │   azul         │ │  roxo        │          │
│ │   ● idle    │ │   ◐ working    │ │  ✋ human    │          │
│ │             │ │                 │ │              │          │
│ │ "Lendo seu  │ │ "Editando      │ │ "Aguardando │          │
│ │  pedido..." │ │  src/parser.py"│ │  liberação"  │          │
│ │             │ │                 │ │              │          │
│ │ trust: 75   │ │ trust: 62      │ │ trust: 80    │          │
│ │ ▓▓▓▓▓▓▓░░░  │ │ ▓▓▓▓▓▓░░░░    │ │ ▓▓▓▓▓▓▓▓░░  │          │
│ └─────────────┘ └────────────────┘ └──────────────┘          │
│                                                                │
│ ┌─ dba (Tier 2) ─┐ ┌─ frontend-dev (Tier 2) ┐                │
│ │   [avatar]      │ │   [avatar]              │                │
│ │   z'z'z         │ │   z'z'z                 │                │
│ │   ○ sleeping    │ │   ○ sleeping            │                │
│ │   (não spawned) │ │   (não spawned)         │                │
│ └─────────────────┘ └─────────────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│ Métricas hoje:                                                │
│  Tokens: 123,456 / 500,000 (24.6%)  ▓▓░░░░░░░░               │
│  Custo:  $4.23 / $50.00 (8.5%)      ▓░░░░░░░░░               │
│  Features completadas: 3                                       │
│  Tempo médio por feature: 12 min                              │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Atividade em tempo real ─────────────────────────┐         │
│ │ 14:32:01 ▶ pipeline-dev usou tool Edit            │         │
│ │ 14:31:55 ▶ pipeline-dev leu src/parser.py         │         │
│ │ 14:31:48 ◆ pipeline-dev iniciou feature-007       │         │
│ │ 14:30:12 ✓ qa-tester decantou feature-006         │         │
│ │ ...                                                 │         │
│ └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 8.5 Estados visuais de cada agente

| Status | Animação | Cor de borda | Bubble |
|---|---|---|---|
| `idle` | pulsa lentamente | cor do agente, opacidade 80% | "aguardando" |
| `working` | rotação leve | cor sólida, opacidade 100% | última ação |
| `decanting` | "escrevendo" (linha animada) | dourado | "decantando aprendizado" |
| `human_driving` | mão estilizada | laranja | "controle humano" |
| `needs_recovery` | tremor sutil | vermelho | "precisa retomada" |
| `sleeping` | z's flutuantes | cinza claro | "descansando" |

## 8.6 Avatars

SVG inline em `dashboard/assets/avatars/`. Inspiração: personagens minimalistas estilo "Sims" ou "Stardew Valley" — silhueta + traço característico do papel.

| Agente | Avatar |
|---|---|
| arquiteto | Silhueta com chapéu de capitão / régua e compasso |
| pipeline-dev | Engrenagem estilizada |
| qa-tester | Lupa |
| dba | Cilindro de banco de dados |
| frontend-dev | Monitor com formas |
| devops-installer | Caixa de ferramentas / container |
| docs-writer | Pena / livro |
| llm-prompt | Cérebro estilizado |
| mobile-dev | Smartphone |
| asset-designer | Paleta de pintor |
| security-auditor | Escudo |

Paleta de cores em `dashboard/assets/colors.json`:

```json
{
  "arquiteto":         "#1e7a3a",
  "pipeline-dev":      "#1e5a7a",
  "qa-tester":         "#6a3a8a",
  "dba":               "#8a5a1e",
  "frontend-dev":      "#7a1e6a",
  "devops-installer":  "#5a5a5a",
  "docs-writer":       "#1e7a7a",
  "llm-prompt":        "#a55050",
  "mobile-dev":        "#3a8a8a",
  "asset-designer":    "#8a3a5a",
  "security-auditor":  "#7a1e1e"
}
```

Tons sóbrios pra dark theme, contraste OK pra light.

## 8.7 PWA

`dashboard/manifest.json`:

```json
{
  "name": "multiagente-vivos",
  "short_name": "multiagente",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#1e1e2e",
  "background_color": "#1e1e2e",
  "icons": [
    {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
  ]
}
```

Service worker mínimo (`sw.js`) que cacheia HTML/CSS/JS e funciona offline (mostra "dashboard sem conexão" se servidor morreu).

## 8.8 Comunicação WebSocket

Mensagens JSON do servidor → cliente:

```json
{"type": "agent_status", "agente": "pipeline-dev", "status": "working", "task": "feature-007"}
{"type": "agent_log", "agente": "pipeline-dev", "ts": "14:32:01", "event": "tool_use", "tool": "Edit", "summary": "Editando src/parser.py"}
{"type": "agent_decanting", "agente": "qa-tester", "feature": "feature-006", "files_written": [...]}
{"type": "metrics", "tokens_today": 123456, "cost_today_usd": 4.23, "features_completed": 3}
{"type": "trust_update", "agente": "pipeline-dev", "old_score": 60, "new_score": 62, "outcome": "rework_minor"}
{"type": "alert", "level": "warning", "message": "Budget em 80%"}
```

Cliente → servidor (raro; principalmente leitura):

```json
{"type": "request_dashboard_snapshot"}
{"type": "request_doctor"}
{"type": "set_theme", "theme": "dark"}
```

## 8.9 Métricas exibidas

| Métrica | Fonte | Atualização |
|---|---|---|
| Tokens hoje | aggregator OTel | tempo real |
| Custo estimado | OTel + tabela de preços por modelo | tempo real |
| % do budget | comparação com `multiagente.toml` | tempo real |
| Features completadas hoje | scan de `reports/` por data | a cada 60s |
| Tempo médio por feature | scan de `reports/` últimos 30 dias | a cada 60s |
| Trust score por agente | `memory/<agente>/trust.json` | a cada 5s |
| Tendência de trust | últimas 10 entradas | a cada 60s |

## 8.10 Modo TUI fallback (Textual)

Quando o usuário está em SSH sem browser, alternativa via Textual ([textualize.io](https://textual.textualize.io/)).

```
$ decanting.py dashboard --tui

┌─ multiagente-vivos ──────────────────── projeto: ML_AtivosJudiciais ──┐
│ arquiteto    ● idle      trust 75  ▓▓▓▓▓▓▓░░░                          │
│ pipeline-dev ◐ working   trust 62  ▓▓▓▓▓▓░░░░  editando src/parser.py  │
│ qa-tester    ✋ human    trust 80  ▓▓▓▓▓▓▓▓░░  aguardando liberação    │
│                                                                          │
│ Tokens hoje:  123456 / 500000 ▓▓░░░░░░░░ 24.6%                          │
│ Custo hoje:   $4.23 / $50.00  ▓░░░░░░░░░  8.5%                          │
│                                                                          │
│ ┌─ Atividade ──────────────────────────────────────────────────────┐   │
│ │ 14:32:01 ▶ pipeline-dev usou tool Edit                            │   │
│ │ 14:31:55 ▶ pipeline-dev leu src/parser.py                         │   │
│ │ 14:31:48 ◆ pipeline-dev iniciou feature-007                       │   │
│ └────────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ [q]uit  [d]octor  [t]heme  [r]efresh                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

Mesma engine de leitura (logs/otel/, memory/). Mesma frequência de update. Tudo o que HTML faz, TUI faz.

## 8.11 Performance e custo

- **Sem servidor remoto.** Tudo local.
- **WebSocket é eficiente.** Updates apenas em mudanças (não polling cliente).
- **Backend: ~30MB de RAM em uso normal.**
- **Frontend: < 200KB total (HTML+CSS+JS+SVG inline).**
- **Não envia dados para fora.** Privado por construção.
- **Sem deps NPM, zero build step.**

## 8.12 Customização pelo usuário

- Theme dark/light/auto (system).
- Reordenação de personagens (drag-and-drop).
- Pinar agentes principais no topo.
- Filtros (mostrar só working, esconder sleeping, etc).
- Densidade de log (verbose / normal / silent).
- Som on/off para notificações (roadmap V2).

## 8.13 Auto-start

`multiagente.toml`:

```toml
[dashboard]
auto_start_on_init = true
auto_open_browser = true
port = 8765  # se ocupada, tenta 8766, 8767, etc até 8775
```

## 8.14 Segurança

- Dashboard **só aceita conexões de localhost** por padrão (`bind 127.0.0.1`).
- Para acessar de outro dispositivo (ex: dashboard no desktop, ver no celular na mesma rede), usuário liga flag explícita `--bind 0.0.0.0` com warning visível.
- Roadmap V2: autenticação opcional via token simples.

## 8.15 Roadmap dashboard

- V1.0: HTML+WS+PWA, Textual TUI fallback, métricas core, theme, responsivo.
- V1.1: drag-and-drop reorder, filtros, sons.
- V1.2: replay de sessões antigas (timeline scrubable).
- V2.0: trust score evolution chart, gráficos de tendência, comparação entre projetos.
