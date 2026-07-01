---
description: "Aprova a spec de uma feature para execução por um especialista (exige confirmação humana explícita)."
argument-hint: "<F-NNN>"
---

Aprove a spec da feature `$ARGUMENTS` para ser executada por um especialista, em português brasileiro.

**Este é um gate humano obrigatório.** Sem esta aprovação, o hook do workflow **bloqueia o Agent tool** — nenhum especialista consegue ser invocado para trabalhar nessa feature. A aprovação só pode acontecer com confirmação humana explícita; você **não** pode aprovar sozinho.

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. **Mostre a spec ao Giordano.** Localize e leia o arquivo `specs/feature-NNN-*.md` correspondente a `$ARGUMENTS` (o número da feature — por exemplo, `F-012` → `specs/feature-012-*.md`). Apresente um resumo fiel do conteúdo:
   - objetivo da feature
   - inputs esperados / outputs esperados
   - critérios de aceite
   - **qual especialista** vai executá-la
   Se o arquivo da spec não existir, avise e **pare** — não há o que aprovar.

2. **Peça confirmação explícita.** Pergunte literalmente:

   > "Aprova esta spec para ser executada por **<especialista>**? (responda 'sim')"

   Deixe claro que, sem aprovar, o Agent tool fica bloqueado pelo hook e o especialista não roda.

3. **Só rode a aprovação se o humano confirmar** com "sim" (ou equivalente inequívoco). Se ele não confirmar, ou pedir ajustes, **não** rode nada — reporte que a aprovação foi cancelada e, se for o caso, sugira `/mad-phase-rework $ARGUMENTS` para revisar a spec antes.

   Confirmado, rode:

   ```
   python3 scripts/mad_phase.py approve-spec $ARGUMENTS
   ```

4. Apresente o resultado da CLI e confirme que a feature está liberada para execução. Sugira `/mad-phase-next` ou `/mad-phase-status` como próximo passo.
