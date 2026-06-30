---
description: "Migra um projeto do plugin antigo multiagentes-giordano (v0.2) para o mad (decanting)."
---

Você vai migrar um projeto que usa o plugin antigo **multiagentes-giordano v0.2**
(sessões persistentes via `claude -p`, dashboard tmux, `MEMORY.md` único) para o
**mad** (decanting nativo). Toda comunicação com o usuário em **PT-BR**.

Esta migração é **destrutiva no layout** (reorganiza pastas) mas **preserva o
conteúdo**. Por isso o backup é obrigatório e o usuário revisa antes de descartar.

## Convenção da CLI

Descubra a raiz do plugin mad (o projeto-alvo ainda não tem `scripts/` do mad):

```bash
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
if [ -z "$PLUGIN_ROOT" ] || [ ! -f "$PLUGIN_ROOT/scripts/mad.py" ]; then
  PLUGIN_ROOT=$(find "$HOME/.claude/plugins" -maxdepth 6 -type f -path "*/mad/*/scripts/mad.py" 2>/dev/null | head -1 | xargs -r dirname | xargs -r dirname)
fi
PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
```

## Passo 1 — Detectar e confirmar

1. Confirme que é um projeto v0.2: procure sinais — `sessions.json`, `scripts/spawn.sh`/`drive.sh`, `scripts/open_dashboard.sh`, `memory/<agente>/MEMORY.md`, `status/<agente>.json`. Se NÃO achar nenhum, avise que não parece ser um projeto v0.2 e pergunte se deve seguir mesmo assim.
2. Se já existe `multiagents-decanting.toml`, o projeto já foi migrado — **aborte** e sugira `/mad-doctor`.
3. Liste ao usuário o que encontrou (agentes, arquivos v0.2) e **peça confirmação** antes de mexer.

## Passo 2 — Backup obrigatório

Crie `.backup-pre-migrate-<timestamp>/` e **copie para lá** (não mova ainda): `sessions.json`, `status/`, `logs/`, `scripts/` antigos, e todos os `memory/<agente>/MEMORY.md`. Confirme que o backup existe e tem conteúdo antes de prosseguir.

## Passo 3 — Preservar sem tocar

NÃO altere: `docs/` (espec viva), `specs/`, `reports/`, `.claude/agents/`, `CLAUDE.md`. Eles seguem válidos no mad (formato Markdown não muda).

## Passo 4 — Scaffold do mad

Rode o init do mad (cria estrutura nova, copia scripts/dashboard/hooks, wira hooks, gera o toml). Use os agentes que já existiam no projeto v0.2 como lista:

```
"$PY" "$PLUGIN_ROOT/scripts/mad.py" init --name "<nome-do-projeto>" --agents "<agentes-existentes>" --budget "<valor>"
```

Se o init recusar por já existir estrutura parcial, crie o `multiagents-decanting.toml` e as pastas que faltam manualmente a partir dos templates do plugin.

## Passo 5 — Migrar a memória (split heurístico de MEMORY.md)

Para CADA agente, leia o `memory/<agente>/MEMORY.md` antigo e **divida** o conteúdo nos arquivos novos (este split é heurístico — você, o LLM, faz a leitura e classifica):

- `handoff.md` — sobrescreva com as últimas notas / estado "onde paramos".
- `lessons.md` — append: aprendizados explícitos (gotchas, padrões que funcionaram).
- `decisions.md` — append: decisões explícitas encontradas (com o formato fixo do mad; o que não tiver "alternativas/por quê" registre o que der).
- `state.md` — snapshot atual (features feitas/em andamento/débitos).
- `identity.md` — crie do template (papel, escopo, restrições) inferindo do agente.
- `dossier.md` — crie com placeholder + o contexto de projeto que houver.
- `trust.json` — crie com score 50 default.

O conteúdo bruto original continua no backup — então **não precisa ser perfeito**; marque com um aviso no `handoff.md` que veio de migração heurística e pode ter misturado coisas.

## Passo 6 — Descartar / arquivar o legado v0.2

- `sessions.json` → descarte (o mad não usa session_ids manuais; o Claude Code gerencia subagents). Já está no backup.
- `status/` antigo → recrie do zero (vazio); o status no mad emerge dos spans OTel.
- `logs/` antigo → já está no backup; pode limpar o `logs/` para o mad usar `logs/otel/`.
- Scripts antigos (`spawn.sh`, `drive.sh`, `open_dashboard.sh`, `_tail_color.sh`, `_status_summary.sh`, `_stream_pretty.py`) → remova (substituídos pelos scripts do mad). Estão no backup.

## Passo 7 — Validar e apresentar o diff

1. Rode o dashboard: `"$PY" scripts/mad.py dashboard --background`.
2. Rode `"$PY" scripts/mad.py doctor`.
3. Apresente ao usuário um **resumo do diff**: o que mudou, o que ficou preservado, e **o que precisa de revisão manual** (especialmente o split de cada `MEMORY.md`). Diga onde está o backup.
4. Avise: "revise o split da memória de cada agente antes de descartar o backup `.backup-pre-migrate-*/`."

## Mensagem final

"Migração concluída (heurística). Projeto agora roda em modo decanting (mad).
- Dashboard: http://localhost:8765
- Backup do estado v0.2: `.backup-pre-migrate-<timestamp>/`
- **Revise** o split da memória de cada agente (`memory/<agente>/`) antes de apagar o backup.
- Próximo: descreva uma feature e o Arquiteto coordena, ou rode `/mad-doctor`."

Para migrar **um agente por vez** (sem migrar o projeto inteiro de uma vez), use `/mad-migrate-agent <agente>`.
