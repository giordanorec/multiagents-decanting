# Migrando para o mad v1.3 (workflow state machine)

## O que mudou (e por quê)

Até a v1.2, o workflow do projeto era **descrito em prosa** no prompt do Arquiteto.
LLM sob pressão pula fases. A v1.3 transforma o workflow numa **state machine
hardcoded** (`.mad/workflow_state.json`) imposta por **hooks que bloqueiam** ações
fora de fase. Não é mais sugestão — é garantia.

- Você **não consegue** despachar um especialista (Agent tool) antes de escrever a
  spec E o humano aprovar (`/mad-phase approve-spec`).
- A cada sessão, o estado + próximo passo é **injetado** no contexto do Arquiteto.
- Ações irreversíveis exigem `/mad-phase approve-merge` explícito.

## Como migrar

**Você não precisa fazer nada especial.** Basta rodar `/mad-init` no projeto — ele
é idempotente e detecta em cascata:

1. **Já tem `.mad/`** → retoma de onde parou.
2. **Projeto v1.2** (tem `multiagents-decanting.toml`, sem `.mad/`) → **migra
   automaticamente**: faz backup, infere a fase pelo estado atual do filesystem,
   instala os hooks. Memória, docs, specs e reports são **preservados**.
3. **Trabalho prévio sem plugin** (discovery já feita, `docs_projeto/`, `_spec/`) →
   **adota**: infere a fase e, se a confiança for baixa, pergunta a você.
4. **Vazio** → discovery do zero.

Se a inferência de fase parecer errada, ajuste com `/mad-phase status` e
`/mad-phase rollback`/`next`.

## Comandos novos

`/mad-phase status` · `next` · `next-phase` · `approve-spec <F-NNN>` ·
`approve-merge <F-NNN>` · `rework <F-NNN>` · `rollback <F-NNN>` ·
`emergency-bypass` (último recurso). Veja `mad-workflow`.

## Rollback da migração

O backup fica em `.mad-backup-pre-*` (adoção) ou `.backup-pre-v1_3-*` (migração).
Para desfazer: remova `.mad/` e restaure do backup.

## Se algo travar

`/mad-doctor` reporta a integridade do workflow (fase, feature ativa, warnings, e
se os hooks estão wireados). O `emergency-bypass` libera uma ação (logado).
