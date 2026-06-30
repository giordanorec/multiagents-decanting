---
description: "Migra um único agente do formato v0.2 (MEMORY.md) para o formato mad, sem migrar o projeto inteiro."
argument-hint: "<agente> (ex: pipeline-dev, dba)"
---

Migre **apenas** o agente `$ARGUMENTS` do formato v0.2 (`MEMORY.md` único) para o
formato de memória do mad, deixando os outros agentes como estão. Útil em times
grandes onde a migração precisa ser gradual. PT-BR com o usuário.

## Pré-checagem

1. Confirme que existe `memory/$ARGUMENTS/MEMORY.md` (formato v0.2). Se não existir, avise e aborte.
2. Se `memory/$ARGUMENTS/handoff.md` já existe, o agente provavelmente já foi migrado — confirme com o usuário antes de sobrescrever.

## Backup

Copie `memory/$ARGUMENTS/MEMORY.md` para `.backup-pre-migrate-<timestamp>/memory/$ARGUMENTS/MEMORY.md`. Confirme que o backup existe.

## Split heurístico

Leia o `MEMORY.md` antigo e divida o conteúdo (você, o LLM, classifica) nos arquivos do mad em `memory/$ARGUMENTS/`:

- `handoff.md` — sobrescrito: "onde parei" / últimas notas.
- `lessons.md` — append: aprendizados, gotchas, padrões.
- `decisions.md` — append: decisões explícitas (formato fixo do mad).
- `state.md` — snapshot (features feitas/andamento/débitos).
- `identity.md` — do template (papel, escopo, restrições inferidos).
- `dossier.md` — do template + contexto que houver.
- `trust.json` — score 50 default.

Crie a pasta `memory/$ARGUMENTS/playbooks/` vazia. Garanta que o agente está registrado em `.claude/agents/$ARGUMENTS.md` (se não estiver, registre via template do mad).

## Aviso e validação

- Adicione no topo do `handoff.md` uma nota: "memória migrada heuristicamente de MEMORY.md em <data>; pode ter misturado conteúdo — revisar."
- Confirme ao usuário: "$ARGUMENTS migrado. Revise `memory/$ARGUMENTS/` antes de descartar o backup. Os outros agentes seguem no formato anterior até serem migrados."
