# Estado — mad (plugin) — 2026-06-30

## Onde estamos

**v1.3.0 — Workflow State Machine.** O buraco estrutural da v1.2 (Arquiteto pula
fases / esquece de delegar) está fechado: o processo agora é uma state machine
hardcoded imposta por hooks. Validado E2E da cópia instalada (Agent tool bloqueado
fora de estado; SessionStart injeta o estado; /mad-init em cascata retoma/migra/adota).

## Entregue

- state machine (scripts/workflow.py): 7 fases + sub-máquina de feature + gates puros
- 3 hooks de enforcement (session-start-inject-state, pre-workflow-gate fail-closed, post-decanting)
- 8 comandos /mad-phase-* (scripts/mad_phase.py) + 9º mad-migrate-to-v1_3
- /mad-init em cascata idempotente (scripts/mad_init.py) + migração (migrate_v1_3.py)
- logs/workflow.jsonl auditável; skill mad-workflow reescrita; arquiteto.md com aviso
- doctor: seção Workflow; dashboard: banner de fase
- 88 testes verdes; releases v1.0..v1.3 publicadas

## Roadmap (honesto — v1.3.1)

- Dashboard visual completo do workflow (sidebar de fases, painel de eventos,
  overlay de bloqueio) — hoje só o banner. Spec 07.
- Testes property-based + CI matrix rodando de verdade (Actions habilitado).
- Reconciliar a prosa antiga de protocolos em arquiteto.md (o aviso + hooks já
  impõem; a prosa v1.2 convive, não conflita).
- Cross-tool (dual-format) do mad.
