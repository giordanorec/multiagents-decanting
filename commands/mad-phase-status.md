---
description: "Mostra o estado atual da máquina de estados do workflow (read-only)."
---

Apresente o estado atual do workflow do projeto mad, em português brasileiro. Este comando é **read-only** — não altera nada, só lê e mostra.

## Convenção de invocação da CLI

Use `python3 scripts/mad_phase.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad_phase.py <subcomando>`.

## Passos

1. Rode o status:

   ```
   python3 scripts/mad_phase.py status
   ```

2. Apresente o resultado organizado e legível:

   - **Fase atual** do projeto e em que estado da máquina de estados o workflow está.
   - **Features em andamento** (F-NNN), cada uma com seu estado (spec pendente de aprovação, em execução, aguardando merge, em rework, etc.).
   - **Gates pendentes** — o que está bloqueado esperando ação humana (aprovar spec, aprovar merge) ou ação de agente.
   - **Próximo passo sugerido** — o que fazer para destravar o fluxo.

3. Se houver algo aguardando decisão humana, deixe **explícito** qual comando o Giordano deve rodar em seguida (por exemplo `/mad-phase-approve-spec F-012` ou `/mad-phase-next`).

Não execute nenhuma mutação neste comando. Se o status apontar erro de estado corrompido, sugira rodar `/mad-doctor`.
