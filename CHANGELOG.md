# Changelog — mad (MultiAgent Decanting)

Formato: [Keep a Changelog](https://keepachangelog.com/). Versionamento semântico.

## [1.3.1] — 2026-06-30

### Adicionado
- **Auto-spawn de especialistas na adoção** (`/mad-init` cascata, passo adopt): ao
  adotar um projeto com trabalho prévio, o mad detecta o backlog (docs/BACKLOG_V1.md,
  docs_projeto/tecnico/06_backlog_v1.md, etc.), **habilita automaticamente** os
  especialistas mencionados (campo `**Especialista:**`) e **avança a fase** conforme
  o que já está pronto — podendo ir direto pra LOOP_FEATURES com a 1ª feature ativa,
  sem exigir `/mad-enable` manual. Especialista inexistente → aviso, sem falhar;
  arquiteto sempre habilitado; idempotente.

## [1.3.0] — 2026-06-30 (Workflow State Machine)

> ⚠️ **MUDANÇA SIGNIFICATIVA NO WORKFLOW.** O processo do projeto deixa de ser
> prosa (sugestão) e vira uma **state machine hardcoded imposta por hooks**. O
> Arquiteto NÃO consegue mais pular fases. Corrige o buraco estrutural da v1.2.

### Adicionado
- **State machine** (`scripts/workflow.py`): 7 fases (BOOTSTRAP→…→PILOTO) +
  sub-máquina por feature, com gates puros e testáveis.
- **Hooks de enforcement**: `session-start-inject-state.py` (injeta o estado no
  contexto a cada sessão), `pre-workflow-gate.py` (BLOQUEIA tool call fora de
  estado — fail-closed), `post-decanting-update-state.py` (avança sub-fase ao
  decantar).
- **Comandos** `/mad-phase status|next|next-phase|approve-spec|approve-merge|
  rework|rollback|emergency-bypass` — única forma legítima de avançar.
- **`/mad-init` em cascata** (`scripts/mad_init.py`): idempotente e context-aware —
  RETOMA / MIGRA (v1.2) / ADOTA (trabalho prévio) / CRIA do zero.
- **Migração** `scripts/migrate_v1_3.py` + `/mad-migrate-to-v1_3` (backup + infere
  fase + instala hooks, preserva memória).
- **Logs de auditoria** `logs/workflow.jsonl` (sanitizado, append-only).
- Dashboard: banner de fase; doctor: seção de integridade do workflow.

### Mudado (breaking)
- Skill `mad-workflow` **reescrita** como state machine.
- `agents/arquiteto.md`: bloco de aviso da state machine no topo.

### Migração
Rode `/mad-init` — ele detecta e migra/adota automaticamente. Ver
`docs/MIGRATING_TO_V1_3.md`.

## [1.2.0] — 2026-06-30 (Tier 3)

### Adicionado
- **4 agentes Tier 3**: `llm-prompt` (design/tuning de prompts, regressão),
  `mobile-dev` (PWA/responsivo/Capacitor), `asset-designer` (sprites/ícones/paletas),
  `security-auditor` (OWASP, secrets, supply chain — opus, revisor não-implementador).
- **Notificações** (`/mad-notify`, `scripts/notify.py`): Telegram + Slack via stdlib,
  opt-in por `[notify]`/env vars.
- **A2A Agent Card** (`/mad-a2a`, `scripts/a2a.py`): gera card compatível com A2A a
  partir do `identity.md`.
- **Voz local** (`/mad-voice`, `scripts/voice.py`): transcrição via faster-whisper
  (opt-in, 100% local).
- **Docker** (`Dockerfile`, `.dockerignore`) + **devcontainer** para Codespaces.
- Config: `[thinking]`, `[notify]`, `[voice]`, `[models]` (Ollama roadmap) no toml.

### Dashboard polish (Tier 2)
- Drag-drop reorder, filtros (todos/só working/esconder sleeping), pin no topo,
  sons WebAudio em eventos. Tudo persistido, zero deps.

## [1.1.0] — 2026-06-30 (Tier 2)

### Adicionado
- **4 agentes Tier 2**: `dba` (schema/migrations/índices/backup), `frontend-dev`
  (UI/UX, acessibilidade, testa no dev server), `devops-installer` (instalação/CI/
  deploy — único instalador), `docs-writer` (README/USO/CHANGELOG, tom direto).
- **Migração do v0.2**: `/mad-migrate-from-v02` (backup obrigatório + split
  heurístico do `MEMORY.md` nos arquivos de memória do mad) e `/mad-migrate-agent`
  (migração gradual, um agente por vez).
- Discovery profundo (`mad-discovery`) ganhou a guarda "explore antes de perguntar"
  (self-serve) e "não adivinhe o propósito pelo nome da pasta".

### Mudado
- Distribuição via hub único `giordanorec/ai-coding-tools` (catálogo de todos os
  plugins do Giordano), em vez de marketplace solo.

## [1.0.0] — 2026-06-27 (Tier 1)

### Adicionado
- Orquestração multi-agente em **modo decanting nativo** (Agent tool, sem `claude -p`).
- 3 agentes: `arquiteto`, `pipeline-dev`, `qa-tester`.
- Skill `mad-discovery` (postura + rigor) e `mad-workflow`.
- 10 slash commands `/mad-*`; trust ladder; guardrails por blast radius.
- Budget enforced + circuit breaker; dashboard HTML+WS+PWA; OpenTelemetry GenAI.
- CLI Python cross-platform (dep única `websockets`); 54 testes.
