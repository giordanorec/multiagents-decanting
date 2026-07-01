---
description: "Aprova o merge do trabalho de uma feature irreversível (exige confirmação humana explícita)."
argument-hint: "<F-NNN>"
---

Aprove o **merge** do trabalho entregue na feature `$ARGUMENTS`, em português brasileiro.

**Este é um gate humano obrigatório para features irreversíveis** (mudanças que, uma vez integradas, não dão para desfazer facilmente). Sem esta aprovação, o hook do workflow **bloqueia a integração**. A aprovação só pode acontecer com confirmação humana explícita; você **não** pode aprovar sozinho.

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. **Mostre o que será integrado.** Localize e leia:
   - o(s) **report(s)** do especialista em `reports/<feature>/*.md` referentes a `$ARGUMENTS`
   - o parecer do arquiteto em `reports/<feature>/arquiteto-merge.md`

   Apresente um resumo fiel: o que foi implementado, arquivos tocados, decisões não-óbvias, riscos, e a recomendação do arquiteto (aprovar / voltar ao dev). Se algum desses arquivos não existir, avise e **pare** — não há entrega consolidada para aprovar.

2. **Peça confirmação explícita.** Deixe claro que é uma ação sobre feature irreversível. Pergunte literalmente:

   > "Aprova o merge da feature $ARGUMENTS? Isto integra o trabalho de forma irreversível. (responda 'sim')"

3. **Só rode a aprovação se o humano confirmar** com "sim" (ou equivalente inequívoco). Se ele não confirmar, ou pedir ajustes, **não** rode nada — reporte que o merge foi cancelado e sugira `/mad-phase-rework $ARGUMENTS` para mandar de volta ao especialista.

   Confirmado, rode:

   ```
   python3 scripts/mad_phase.py approve-merge $ARGUMENTS
   ```

4. Apresente o resultado da CLI e confirme que o merge foi liberado. Sugira `/mad-phase-next` ou `/mad-phase-status` como próximo passo.
