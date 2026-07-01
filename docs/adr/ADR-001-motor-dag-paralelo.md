# ADR-001 — Motor DAG + execução paralela de features

Status: **proposto** (design; implementação em investida dedicada)
Data: 2026-07-01
Autor: Arquiteto (mad)

## Contexto

Hoje o motor (`scripts/workflow.py`) é **sequencial-escalar**:
- um único `active_feature`; backlog linear `F-001..N` sem dependências;
- `parse_backlog` descarta tudo menos `id`+`slug`;
- o gate em sub-fase `executando` (`decide_tool`) amarra a feature a **um**
  `agent_assigned` e **bloqueia** qualquer outro `subagent_type` — ou seja, a
  enforcement **ativamente impede** o orchestrator-worker paralelo que o próprio
  Arquiteto prega.

Estado da arte (LangGraph, Devin, OpenHands) gira em torno de um **DAG** com
fan-out/fan-in. A filosofia do mad ("determinístico bate autônomo — a máquina
governa o fluxo, o LLM só nos nós") **é** a certa; falta o plano ser um grafo.

## Decisão

Trocar o núcleo de "1 feature ativa" para **fronteira de features prontas rodando
em paralelo**, dirigida por um DAG de dependências declarado no backlog. Enforcement
continua determinístico (hooks + gates puros); só o LLM nos nós.

### Modelo de dados (mudanças)

1. **Backlog com schema por linha** (`docs/BACKLOG_V1.md`):
   `F-NNN | slug | prioridade | blast | especialistas:[...] | depende:[F-..] | critério`
   `parse_backlog` passa a extrair tudo isso (hoje joga fora).
2. **Estado:** `active_feature` (escalar) → `active_features: {F-NNN: {subphase,
   agent_assigned, rework_count, approvals, ...}}` (mapa). `backlog_features` ganha
   `depends_on: [F-..]`.
3. **Fronteira:** `ready_features()` = features `pendente` cujas dependências estão
   todas `concluida`. É o conjunto seguro de paralelismo (ordenação topológica).
4. **Concorrência:** `[workflow].max_parallel_features` (default 3) — teto de features
   simultâneas, alinhado ao custo/tokens que o usuário escolheu no "montar o time".

### Gates / enforcement

- `gate_espec_done`: valida que as dependências existem e **rejeita ciclos** (DFS).
- `decide_tool` em `executando`: aceita **qualquer** `subagent_type` no conjunto
  `especialistas:[]` da spec da feature ativa correspondente — não mais um só.
  Precisa saber **qual feature** um dado despacho serve: o Arquiteto passa
  `feature=F-NNN` no prompt/label; o gate valida contra `active_features[F-NNN]`.
- Fan-in: só avança de `LOOP_FEATURES` quando a fronteira **fecha** (todas concluídas).
- Todos os gates de fechamento por-feature (v1.9–1.14: testes, revisor independente,
  docs-sync, dead-letter) continuam **por feature**, inalterados.

### Sub-máquina por feature

Inalterada (`spec_pendente → … → concluida`), mas **por entrada** de `active_features`,
não global. Cada feature tem sua sub-fase. `_activate_next_from_backlog` vira
`_refresh_frontier` (ativa todas as prontas até `max_parallel_features`).

## Migração (sem quebrar projetos existentes)

- Backlog antigo (sem `depende:`) → todas as features sem dependência → funciona como
  hoje, mas já podendo paralelizar as independentes.
- `active_feature` (escalar) no state antigo → migrado para `active_features` de 1
  entrada por `migrate_*`/load (compat de leitura).
- Feature-flag `[workflow].engine = "sequential" | "dag"` (default `sequential` no
  primeiro release do motor, virar `dag` quando maduro) — permite rollback instantâneo.

## Estratégia de teste (reforçada — pré-requisito do merge)

- Testes de grafo: topo-sort, detecção de ciclo, fronteira correta.
- Enforcement: `decide_tool` libera os N especialistas certos em paralelo e bloqueia
  os de features não-prontas; fan-in só fecha com a fronteira toda concluída.
- Migração: state/backlog v1.x carrega e roda no motor novo.
- Paralelismo real: 2 features independentes fecham concorrentes; 1 dependente espera.
- Não-regressão: toda a suíte atual (107) verde nos dois modos (`engine=sequential`
  e `engine=dag`).
- Dashboard: burn-down + caminho crítico da fronteira.

## Riscos e mitigação

- **Corromper o coração enforçado** → feature-flag `engine`, migração com compat de
  leitura, suíte dupla, rollout gradual.
- **Complexidade de UX** (leigo vendo 3 coisas ao mesmo tempo) → o painel já mostra
  múltiplos agentes; a narrativa humana agrupa por "estou construindo X, Y e Z juntos".
- **Custo/tokens** → `max_parallel_features` amarrado à conversa de custo do SETUP_TIME.

## Consequências

O mad passa a realizar o multi-agente **paralelo** de ponta a ponta (o que o roadmap
SOTA aponta como o maior gap único), sem abrir mão do determinismo — que é o seu maior
ativo. Implementação numa investida dedicada, atrás da feature-flag, com a bateria de
testes acima como gate de merge.
