---
description: "Migra um projeto mad v1.2 (sem .mad/) para v1.3: backup, inferência de fase, instalação dos hooks novos."
---

Migre este projeto mad da versão **v1.2** (sem diretório `.mad/`) para a **v1.3** (com máquina de estados em `.mad/workflow_state.json` e hooks novos), em português brasileiro.

Esta migração é **conservadora e reversível**: `memory/`, `docs/`, `specs/` e `reports/` são **preservados** intactos. Só é adicionada a camada de workflow por cima do que já existe.

## Convenção de invocação da CLI

Use `python3 <script>`. Se `python3` não existir, caia para `python <script>`.

## Passos

1. **Backup do estado atual.** Antes de tocar em qualquer coisa, gere um timestamp e copie os artefatos de configuração/estado para uma pasta de backup:

   ```
   mkdir -p .backup-pre-v1_3-$(date +%Y%m%d-%H%M%S)
   ```

   Copie para dentro dela o que existir e for relevante ao rollback: `.claude/settings.json` (e `settings.local.json`), `sessions.json`, `status/`, e qualquer `.mad/` pré-existente. Confirme ao Giordano o caminho do backup criado. (Não copie `memory/`, `docs/`, `specs/`, `reports/` — eles não são alterados; se quiser um backup total, avise que é opcional.)

2. **Rode o migrador.** Ele cria `.mad/workflow_state.json` **inferindo a fase atual a partir de evidências no filesystem** (specs aprovadas, reports presentes, features em andamento, etc.) e **instala os hooks novos** no `settings.json`:

   ```
   python3 scripts/migrate_v1_3.py
   ```

3. **Se a inferência for ambígua, PERGUNTE — não chute.** Se o migrador reportar incerteza sobre qual fase/estado o projeto está (por exemplo, há uma spec sem report claro, ou features em estados conflitantes), **pare e apresente as opções ao Giordano** com o contexto que motivou a dúvida, e deixe ele decidir a fase/estado correto. Só então aplique a escolha dele. Nunca resolva a ambiguidade silenciosamente.

4. **Valide a migração.** Ao final, rode e apresente:

   ```
   python3 scripts/mad_phase.py status
   ```

   e, em seguida, o diagnóstico de saúde:

   ```
   /mad-doctor
   ```

   (ou `python3 scripts/mad.py doctor` diretamente).

5. **Reporte o resultado** ao Giordano: caminho do backup, fase/estado inferidos (e se houve escolha manual em algum ponto), hooks instalados, e o veredito do doctor. Reforce que `memory/`, `docs/`, `specs/` e `reports/` foram preservados. Se o doctor apontar amarelo/vermelho, liste objetivamente o que corrigir e, se necessário, como reverter usando o backup.
