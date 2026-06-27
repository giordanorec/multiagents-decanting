# 11 — Critérios de Aceite

Esta é a especificação executável da v1.0. Cada item é um teste verificável que separa "implementação completa" de "implementação parcial".

## 11.1 Tier 1 (MVP — bloqueante para v1.0)

### Estrutura e setup

- [ ] **CA-001** `/multiagents-init` em diretório vazio cria todas as pastas e arquivos do layout (03.1) com templates corretos.
- [ ] **CA-002** Init conduz Discovery em **uma pergunta por vez** (não despeja múltiplas). Validar por inspeção de transcript.
- [ ] **CA-003** Init detecta versão do Claude Code e ajusta comportamento (SendMessage vs --resume).
- [ ] **CA-004** Init detecta plataforma (Win/Mac/Linux/WSL) e ajusta paths.
- [ ] **CA-005** Init cria `multiagents-decanting.toml` válido com defaults + override pelas respostas do Discovery.

### Memory e Decanting

- [ ] **CA-010** Spawn de agente cria `memory/<agente>/` com 7 arquivos (identity, dossier, decisions, handoff, state, lessons, trust.json) + pasta `playbooks/`.
- [ ] **CA-011** System prompt do agente referencia (não duplica) hierarquia 4-tier Anthropic Constitution.
- [ ] **CA-012** Drive de feature passa system prompt + protocolo de boot ao agente.
- [ ] **CA-013** Agente, em sessão fresca (modo frio), lê todos os arquivos de memory listados em §4.1 antes de executar.
- [ ] **CA-014** Ao fim da feature, agente decanta: handoff.md sobrescrito, decisions.md apendado, state.md atualizado, lessons.md apendado (se aplicável), trust.json atualizado.
- [ ] **CA-015** Report em `reports/<feature>/<agente>.md` segue template 5.11 (status, critérios marcados, evidências, pendências).
- [ ] **CA-016** Decanting forçado (`/multiagents-decant <agente>`) funciona via nova call do Agent tool lendo estado atual.
- [ ] **CA-017** Decanting de emergência (SIGTERM) escreve ao menos handoff.md dentro de 30s.

### Trust ladder

- [ ] **CA-020** Score default ao habilitar agente é 50.
- [ ] **CA-021** Após report aceito pelo Arquiteto, trust score sobe (+5).
- [ ] **CA-022** Após rework_major, trust score desce (-3).
- [ ] **CA-023** Score < 30: mediante teste, agente pede confirmação humana em ação reversível-médio. Score ≥ 70: não pede.
- [ ] **CA-024** `/multiagents-trust <agente>` mostra score + histórico + tendência.

### Guardrails

- [ ] **CA-030** Hook bloqueia `git push --force` em main sem confirmação explícita.
- [ ] **CA-031** Hook bloqueia `rm -rf` em path fora da raiz do projeto.
- [ ] **CA-032** Hook bloqueia commit de arquivo contendo padrão de secret (regex).
- [ ] **CA-033** Hook bloqueia Edit/Write em `memory/*/identity.md` sem flag `--allow-identity-change`.

### Resiliência

- [ ] **CA-040** Em chamada falha (rate limit, timeout), plugin faz retry com exponential backoff + jitter (3 tentativas).
- [ ] **CA-041** Após 3 falhas seguidas, circuit breaker ativa (pausa 5min antes de nova tentativa).
- [ ] **CA-042** Se Opus indisponível, fallback Sonnet → Haiku (configurável).
- [ ] **CA-043** Quando tokens consumidos atingem `max_tokens_per_session`, plugin encerra sessão com decanting forçado.
- [ ] **CA-044** Quando custo diário atinge `max_cost_per_day_usd`, plugin encerra todas as sessões com decanting forçado.

### Workflow patterns

- [ ] **CA-050** Arquiteto identifica o pattern apropriado (chain/route/parallelize/orchestrator-worker/evaluator-optimizer) ao receber pedido.
- [ ] **CA-051** Arquiteto apresenta opções de paralelismo (sequencial / seletivo / agressivo) com estimativa de tokens.
- [ ] **CA-052** Decisão de pattern e paralelismo registrada em `docs/DECISOES.md`.

### Dashboard

- [ ] **CA-060** `/multiagents-dashboard` inicia servidor em porta 8765 (ou próxima livre) e abre browser.
- [ ] **CA-061** Dashboard mostra cada agente como personagem com avatar SVG, cor, status visual.
- [ ] **CA-062** Dashboard atualiza em tempo real via WebSocket (latência < 500ms para evento aparecer).
- [ ] **CA-063** Dashboard exibe métricas: tokens hoje, custo hoje, % budget, features completadas, tempo médio.
- [ ] **CA-064** Dashboard é PWA installable (manifest + service worker).
- [ ] **CA-065** Dashboard é responsivo (funciona em viewport mobile).
- [ ] **CA-066** Dashboard tem theme dark/light + auto.
- [ ] **CA-067** Dashboard só aceita conexões localhost por default.

### Observabilidade

- [ ] **CA-070** Plugin emite spans OTel GenAI (v1.41) para: agent.start, agent.boot, workflow.feature, model.call, tool.use, decanting.start, decanting.complete, agent.error, agent.end.
- [ ] **CA-071** Spans são gravados localmente em `logs/otel/<date>.jsonl`.
- [ ] **CA-072** Se `OTEL_EXPORTER_OTLP_ENDPOINT` definido, spans exportam via OTLP HTTP.
- [ ] **CA-073** Métricas: gen_ai.token.usage, gen_ai.cost.estimate, agent.feature.duration, agent.trust.score são emitidas.

### Multiplataforma

- [ ] **CA-080** Plugin instala e roda em Windows 11 sem WSL.
- [ ] **CA-081** Plugin instala e roda em macOS (Intel + Apple Silicon).
- [ ] **CA-082** Plugin instala e roda em Linux (Ubuntu 22.04+).
- [ ] **CA-083** Plugin usa `pathlib.Path` em 100% dos paths (sem string concat com `/`).
- [ ] **CA-084** Plugin abre I/O com `encoding="utf-8"` explícito.
- [ ] **CA-085** Wrappers shell (.bat, .ps1, bash) funcionam.
- [ ] **CA-086** Sem deps externas além de `websockets` (e opcional `textual`).

### CLI e comandos

- [ ] **CA-090** `decanting init` (= /multiagents-init) funcional (= //multiagents-init).
- [ ] **CA-091** `/multiagents-enable <agente>` habilita especialista adicional (cria memory/ e registra subagent_type, sem spawnar processo).
- [ ] **CA-092** Despacho de trabalho é feito pelo Arquiteto via `Agent` tool nativo (não há comando `drive` próprio do plugin).
- [ ] **CA-092b** Quando Claude Code ≥ 2.1.77 com `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, plugin usa `SendMessage` para continuidade multi-turn. Quando não, usa nova call do Agent tool com boot lendo handoff. Ambos casos: fluência preservada dentro da feature.
- [ ] **CA-093** `/multiagents-inspect <agente>` mostra estado completo.
- [ ] **CA-094** `/multiagents-dashboard` inicia dashboard.
- [ ] **CA-095** `/multiagents-decant <agente>` força decanting via nova Agent call.
- [ ] **CA-096** `/multiagents-doctor` retorna verde/amarelo/vermelho com detalhes.
- [ ] **CA-097** `/multiagents-trust <agente>` mostra trust.
- [ ] **CA-098** `/multiagents-upgrade` atualiza sem tocar memory/docs/specs/reports.
- [ ] **CA-099** `/multiagents-explain <conceito>` retorna explicação clara em PT-BR.

### i18n e leigos

- [ ] **CA-100** Mensagens do plugin disponíveis em PT-BR e EN.
- [ ] **CA-101** Discovery roda em PT-BR por padrão.
- [ ] **CA-102** Comando `/multiagents-tutorial` executa walkthrough guiado completo.
- [ ] **CA-103** Templates por tipo de projeto (ML, web, CLI, jogo, documento, outro) disponíveis no init.

## 11.2 Tier 2 (v1.1 — melhorias)

- [ ] **CA-200** Tier 2 agent types disponíveis (dba, frontend-dev, devops-installer, docs-writer).
- [ ] **CA-201** Dashboard: drag-and-drop reorder de personagens.
- [ ] **CA-202** Dashboard: filtros (mostrar só working, esconder sleeping).
- [ ] **CA-203** Dashboard: pinar agentes principais.
- [ ] **CA-204** Notificações sonoras opcionais.
- [ ] **CA-205** `/multiagents-migrate-from-v02` funcional.
- [ ] **CA-206** `/multiagents-migrate-agent <agente>` funcional.
- [ ] **CA-207** Extended thinking adaptive (Opus 4.7+) configurável por tipo de decisão do Arquiteto.

## 11.3 Tier 3 (v1.2 — diferenciação)

- [ ] **CA-300** Voice input via Whisper local (Faster-Whisper INT8): `/multiagents-voice` aceita áudio do mic.
- [ ] **CA-301** Voice output (TTS opcional): notificações faladas opt-in.
- [ ] **CA-302** Integração Telegram: bot opt-in que notifica conclusão de feature ou pede aprovação.
- [ ] **CA-303** Integração WhatsApp Business API (opt-in).
- [ ] **CA-304** Integração Slack (opt-in).
- [ ] **CA-305** Ollama fallback: agente pode rodar contra LLM local via OpenAI-compatible API.
- [ ] **CA-306** Docker image oficial: `giordanorec/multiagents-decanting:latest`.
- [ ] **CA-307** A2A protocol compatibility: agentes do plugin podem expor Agent Card.
- [ ] **CA-308** Sandboxing opcional (Docker/E2B/Firecracker) para execução de código não-confiável.
- [ ] **CA-309** Eval contínuo opcional via DeepEval ou Promptfoo, alimentando trust.json.
- [ ] **CA-310** Tier 3 agent types (llm-prompt, mobile-dev, asset-designer, security-auditor).

## 11.4 Critérios qualitativos

Difíceis de testar automaticamente, mas tão críticos quanto:

- [ ] **CQ-001** Leigo sem experiência em IA generativa consegue completar tutorial e iniciar primeiro projeto em < 20 min.
- [ ] **CQ-002** Documentação tem exemplos para cada tipo de projeto (ML, web, CLI, jogo, doc).
- [ ] **CQ-003** Mensagens de erro são acionáveis (dizem o que fazer, não só o que aconteceu).
- [ ] **CQ-004** README é claro o suficiente para alguém decidir "vale a pena" em < 3 min.
- [ ] **CQ-005** Resposta a `/multiagents-explain decanting` é compreensível por advogado/médico/professor.

## 11.5 Não-bloqueantes (nice-to-have)

- [ ] **NB-001** Plugin tem website com docs (GitHub Pages OK).
- [ ] **NB-002** Plugin tem vídeo de demo curto (< 3 min).
- [ ] **NB-003** Plugin aparece em "Awesome Claude Code" list.
- [ ] **NB-004** Plugin tem ao menos 5 contribuições externas no primeiro semestre.

## 11.6 Definição de "Pronto para release"

**v1.0 release:** todos os critérios Tier 1 (CA-001 a CA-103) e critérios qualitativos CQ-001 a CQ-005 marcados.

**v1.1 release:** todos Tier 1 + Tier 2.

**v1.2 release:** todos Tier 1 + Tier 2 + Tier 3.
