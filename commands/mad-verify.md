---
description: "Verificação com dentes: roda testes/lint/typecheck de VERDADE e grava o resultado (gate de fechamento)."
---

Você é o Arquiteto. Este comando roda a **verificação executável** de uma feature —
teste é ground-truth, não prosa. O resultado (`reports/feature-<NNN>/verify.json`) é
lido pelo gate de fechamento: sem `all_passed=true`, a feature não fecha (Art. 4).

## Passos

1. Garanta que o projeto configurou `[verify]` em `multiagents-decanting.toml`
   (`test_cmd`, opcionalmente `lint_cmd`, `typecheck_cmd`). Se estiver vazio, avise o
   usuário que sem `test_cmd` não há gate de teste real — e pergunte qual é o comando
   de teste do projeto (ex.: `pytest -q`, `npm test`, `go test ./...`).

2. Rode a verificação da feature corrente:

   ```
   python3 scripts/verify.py F-NNN
   ```

3. Se **passou**: siga o fechamento (`/mad-phase next`). Se **falhou**: NÃO force —
   leia o `tail` do `verify.json`, devolva o erro ao especialista (`/mad-phase rework
   F-NNN --note "<stack trace>"`) e deixe ele corrigir. Repita até passar.

**Regra (Art. 4):** nada é "pronto" sem os critérios de aceite atendidos e os testes
verdes de verdade. Alegar aprovação sem rodar é violação — o gate bloqueia.
