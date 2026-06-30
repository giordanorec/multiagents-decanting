# Changelog — mad (MultiAgent Decanting)

Formato: [Keep a Changelog](https://keepachangelog.com/). Versionamento semântico.

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
