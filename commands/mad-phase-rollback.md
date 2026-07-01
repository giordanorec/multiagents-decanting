---
description: "Reverte uma feature para um estado anterior do workflow, com motivo registrado."
argument-hint: "<F-NNN>"
---

Faça **rollback** da feature `$ARGUMENTS` — reverta-a para um estado anterior da máquina de estados, em português brasileiro. Use quando uma feature avançou indevidamente ou precisa voltar atrás de forma controlada.

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. **Obtenha o motivo do rollback.** Se o Giordano já explicou na mensagem, use isso. Caso contrário, **pergunte**: "Qual o motivo do rollback desta feature?". O motivo é **obrigatório** — não rode o comando sem ele. Sem motivo, pare e peça.

2. (Opcional, se ajudar) rode antes `python3 scripts/mad_phase.py status` para mostrar em que estado a feature está agora e para onde o rollback deve levá-la, confirmando que é isso mesmo o desejado.

3. Rode o rollback, passando o motivo entre aspas (escape aspas internas se houver):

   ```
   python3 scripts/mad_phase.py rollback $ARGUMENTS --reason "<motivo do rollback>"
   ```

4. Apresente o resultado da CLI: confirme **para qual estado** a feature voltou e que o motivo ficou registrado em `logs/workflow.jsonl`. Aponte o próximo passo para retomar o fluxo a partir do estado revertido (por exemplo `/mad-phase-approve-spec $ARGUMENTS` ou `/mad-phase-next`). Sugira `/mad-phase-status` para confirmar o quadro.
