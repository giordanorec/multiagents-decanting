---
description: "Inspeciona estado de um agente (memória, decisões, telemetria recente)."
argument-hint: "<agente> (ex: pipeline-dev, dba)"
---

Mostre o estado completo do agente `$ARGUMENTS`. Tudo em português brasileiro, com seções claras.

## Convenção de invocação da CLI

Use `python3 scripts/mad.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad.py <subcomando>`.

## Passos

1. Rode o inspetor da CLI, que reúne memória + telemetria do agente:

   ```
   python3 scripts/mad.py inspect $ARGUMENTS
   ```

2. Se o agente não estiver habilitado (sem `memory/$ARGUMENTS/`), avise e sugira `/mad-enable $ARGUMENTS`.
3. Apresente o resultado formatado, cobrindo:
   - **Handoff** — conteúdo de `memory/$ARGUMENTS/handoff.md` (a cabeça de tudo: onde parou, o que ficou pendente).
   - **Decisões recentes** — últimas 5 entradas de `memory/$ARGUMENTS/decisions.md`.
   - **Estado** — `memory/$ARGUMENTS/state.md`, se existir.
   - **Lições recentes** — últimas 5 de `memory/$ARGUMENTS/lessons.md`, se existir.
   - **Trust** — score atual + últimas 5 entradas de `memory/$ARGUMENTS/trust.json`.
   - **Telemetria (24h)** — contagem de calls, tokens consumidos, última call (timestamp, spec, outcome).
   - **Status inferido** — idle / working / error, com base nos spans OTel recentes.

Se a CLI não trouxer algum desses blocos, complemente lendo os arquivos diretamente em `memory/$ARGUMENTS/` e `logs/otel/`.
