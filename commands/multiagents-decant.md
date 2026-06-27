---
description: "Força decanting manual de um agente (útil quando uma feature foi interrompida)."
argument-hint: "<agente> [feature] (ex: pipeline-dev)"
---

Force o agente `$ARGUMENTS` a executar o protocolo de **decanting** agora. Tudo em português brasileiro.

## Contexto

Em modo decanting nativo o agente não é um processo vivo. "Forçar decanting" significa: fazer uma nova Agent call que lê o estado atual (handoff, report recente, telemetria) e produz um **decanting retroativo** — externaliza o aprendizado que ficou implícito, sem executar trabalho novo.

## Passos

1. Identifique a última feature em que `$ARGUMENTS` trabalhou. Procure menções recentes em `reports/` e em `logs/otel/<date>.jsonl`. Se houver ambiguidade e o usuário tiver passado uma feature no argumento, use a indicada.
2. Faça a Agent call de decanting retroativo:

   ```
   Agent(subagent_type="multiagents-decanting:$ARGUMENTS",
         description="Decanting retroativo de $ARGUMENTS",
         prompt="Você está sendo chamado para executar decanting retroativo.
                 Leia memory/$ARGUMENTS/handoff.md (estado atual),
                 reports/<feature-recente>/$ARGUMENTS.md (sua última entrega,
                 se existir) e logs/otel/<date>.jsonl (sua atividade recente).
                 Atualize: handoff.md, decisions.md, lessons.md, state.md e
                 trust.json. NÃO execute trabalho novo. Retorne um resumo do
                 que decantou.")
   ```

   Substitua `<feature-recente>` e `<date>` pelos valores reais identificados no passo 1.
3. Aguarde o retorno. Verifique que os arquivos de `memory/$ARGUMENTS/` foram de fato atualizados (timestamps recentes).
4. Confirme ao usuário: "Decanting retroativo de `$ARGUMENTS` completo." e cole o resumo devolvido pelo agente.
