---
description: "Mostra trust score e histórico de um agente."
argument-hint: "<agente> (ex: pipeline-dev)"
---

Mostre o trust score e o histórico do agente `$ARGUMENTS`. Tudo em português brasileiro.

## Convenção de invocação da CLI

Use `python3 scripts/multiagents.py <subcomando>`. Se `python3` não existir, caia para `python scripts/multiagents.py <subcomando>`.

## Passos

1. Rode:

   ```
   python3 scripts/multiagents.py trust $ARGUMENTS
   ```

   (Se a CLI não cobrir tudo, complemente lendo `memory/$ARGUMENTS/trust.json` diretamente.)

2. Apresente formatado:

   - **Score atual** com gauge visual, ex: `▓▓▓▓▓▓▓░░░ 65/100`.
   - **Histórico** — últimas 20 entradas (feature, outcome, weight, timestamp).
   - **Estatística:**
     - Total de features: N
     - % aceitas de primeira: M%
     - % rework_minor
     - % rework_major
     - Tendência nas últimas 10: melhorando | estável | piorando
   - **Nível atual de fricção** (derivado do score):
     - 0–29: "todas as ações de médio+ risco precisam de confirmação humana."
     - 30–69: "só ações irreversíveis precisam de confirmação."
     - 70–100: "alta autonomia; só ações catastróficas precisam de confirmação."

3. Lembre que a escala não é burocracia de gating — é **instrumentação de competência** do agente ao longo do tempo.
