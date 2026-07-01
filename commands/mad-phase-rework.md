---
description: "Manda uma feature de volta para correção (rework), com nota do que ajustar."
argument-hint: "<F-NNN>"
---

Mande a feature `$ARGUMENTS` de volta para **rework** (correção), em português brasileiro. Isso devolve a feature ao especialista com uma nota explicando o que precisa ser ajustado.

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. **Obtenha a nota do que corrigir.** Se o Giordano já descreveu o ajuste na mensagem, use isso. Caso contrário, **pergunte**: "O que precisa ser corrigido nesta feature?". A nota é **obrigatória** — não rode o comando com nota vazia. Se não houver nota, pare e peça.

2. **Determine a magnitude do rework:**
   - `minor` — ajuste pequeno, pontual (typo, tweak de parâmetro, pequena correção de lógica). Não reabre a spec.
   - `major` — mudança de fundo (redesenho, requisito mal-entendido, retrabalho significativo). Pode exigir reaprovação de spec depois.

   Escolha a magnitude a partir da descrição. Em caso de dúvida entre as duas, pergunte ao Giordano; não chute em silêncio numa mudança de peso.

3. Rode o rework, passando a nota entre aspas (escape aspas internas se houver):

   ```
   python3 scripts/mad_phase.py rework $ARGUMENTS --note "<nota do que corrigir>" --magnitude <minor|major>
   ```

4. Apresente o resultado da CLI: confirme que a feature voltou ao especialista, com a nota registrada em `logs/workflow.jsonl`. Se a magnitude foi `major` e isso reabriu o gate de spec, avise que uma nova aprovação (`/mad-phase-approve-spec $ARGUMENTS`) será necessária depois. Sugira `/mad-phase-status` para acompanhar.
