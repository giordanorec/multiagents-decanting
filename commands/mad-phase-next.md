---
description: "Tenta avançar o workflow para o próximo passo, validando o gate atual."
---

Avance o workflow do projeto mad para o próximo passo, em português brasileiro. A CLI valida o gate atual antes de mover — se o gate não estiver satisfeito, ela recusa e explica o porquê.

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. Rode o avanço:

   ```
   python3 scripts/mad_phase.py next
   ```

2. Interprete e apresente o resultado:

   - **Se avançou:** diga claramente **de qual estado para qual estado** o workflow passou, e o que isso libera (por exemplo, "agora o especialista pode ser invocado", ou "aguardando aprovação de merge").
   - **Se NÃO avançou:** explique **exatamente qual gate bloqueou** e o que falta para satisfazê-lo. Aponte o comando concreto que destrava — por exemplo:
     - falta aprovar uma spec → `/mad-phase-approve-spec F-NNN`
     - falta aprovar um merge → `/mad-phase-approve-merge F-NNN`
     - falta transição de fase de projeto → `/mad-phase-next-phase`
     - a feature precisa de correção → `/mad-phase-rework F-NNN`

3. Ao final, se útil, sugira rodar `/mad-phase-status` para ver o quadro completo atualizado.

Este comando avança apenas o passo natural do fluxo. Não use para forçar transições de fase de projeto (isso é `/mad-phase-next-phase`) nem para pular gates (isso é `/mad-phase-emergency-bypass`, último recurso).
