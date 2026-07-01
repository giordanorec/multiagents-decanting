---
description: "ÚLTIMO RECURSO: registra um bypass do gate de workflow (quebra rastreabilidade). Exige confirmação dupla."
---

Registre um **emergency bypass** do gate de workflow do projeto mad, em português brasileiro.

**LEIA COM ATENÇÃO — isto é o último recurso.** O bypass permite pular um gate que estaria bloqueando o fluxo. Ele **quebra a rastreabilidade** da máquina de estados: a partir dele, o histórico em `logs/workflow.jsonl` deixa de refletir um caminho válido de gates. Só use quando o fluxo normal está genuinamente travado e não há outra saída (`/mad-phase-rework`, `/mad-phase-rollback` e `/mad-doctor` já foram considerados e não resolvem).

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. **Obtenha um motivo detalhado, com no mínimo 50 caracteres.** Se o Giordano não deu, **pergunte** e explique que o motivo precisa ser substantivo (o que travou, por que os caminhos normais não servem). Conte os caracteres: se tiver menos de 50, peça para detalhar mais. Não prossiga com motivo curto ou vago.

2. **Confirmação dupla.** Antes de rodar qualquer coisa:
   - Explique em uma frase o que o bypass vai pular e que a rastreabilidade será quebrada.
   - Peça ao Giordano que digite **literalmente** `EU ENTENDO` para prosseguir.
   - Só continue se a resposta for exatamente `EU ENTENDO`. Qualquer outra coisa → **aborte** e não rode nada.

3. Confirmado, rode o bypass com o motivo entre aspas (escape aspas internas se houver):

   ```
   python3 scripts/mad_phase.py emergency-bypass --reason "<motivo com >= 50 caracteres>"
   ```

4. Apresente o resultado da CLI e então **instrua o Giordano** sobre o passo manual necessário: o bypass só tem efeito para a **próxima ação** se ele exportar a variável de ambiente, e apenas para essa ação:

   ```
   export MAD_WORKFLOW_BYPASS=1
   ```

   Deixe claro que essa variável deve valer **só para a próxima ação** e ser removida/deixada expirar em seguida — não é para ficar setada permanentemente no ambiente, pois desligaria os gates de forma contínua. Recomende rodar `/mad-doctor` depois para checar a integridade do estado.
