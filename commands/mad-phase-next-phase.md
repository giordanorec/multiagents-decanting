---
description: "Transiciona o projeto para a próxima FASE (ex: piloto → escala), validando o gate de fase."
---

Transicione o projeto mad para a **próxima fase** (por exemplo, discovery → especificação, ou piloto → escala), em português brasileiro. A CLI valida o gate de fase antes de mover — todas as features da fase atual precisam estar em estado terminal para que a transição seja permitida.

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. Rode a transição de fase:

   ```
   python3 scripts/mad_phase.py next-phase
   ```

2. Interprete e apresente o resultado:

   - **Se transicionou:** diga **de qual fase para qual fase** o projeto passou, e o que a nova fase habilita (novos entregáveis, novos agentes, critérios da fase seguinte).
   - **Se NÃO transicionou:** explique **qual gate de fase bloqueou** — normalmente há features ainda abertas, specs não aprovadas ou merges pendentes. Liste objetivamente o que falta fechar antes de tentar de novo, e aponte os comandos que resolvem (`/mad-phase-status`, `/mad-phase-approve-merge F-NNN`, `/mad-phase-rework F-NNN`, etc.).

3. Ao final, sugira `/mad-phase-status` para confirmar o novo quadro.

Atenção: transição de fase é uma decisão de peso. Só avance quando a fase atual estiver realmente concluída — não use este comando para contornar features inacabadas.
