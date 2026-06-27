# 02 — Arquitetura

## 2.1 Visão de 30 segundos

```
┌─────────────────────────────────────────────────────────┐
│  HUMANO                                                  │
│    │                                                     │
│    └──> sessão interativa Claude Code (Arquiteto)        │
│              │                                            │
│              ├──> escreve specs/<feature>.md             │
│              ├──> chama Agent tool                        │
│              │      └──> subagent_type=decanting:<role>   │
│              │              ─ sessão completa do subagent │
│              │              ─ boot lê memory/<agente>/    │
│              │              ─ executa multi-step          │
│              │              ─ decanta antes de retornar   │
│              │              ─ retorna report ao Arquiteto │
│              ├──> (opcional) SendMessage pra continuar    │
│              │      └──> só se v2.1.77+ com env var      │
│              └──> lê reports/<feature>/<agente>.md        │
│                                                           │
│  Em paralelo, browser local:                              │
│    http://localhost:8765 → dashboard HTML                 │
│       │                                                   │
│       └──> WebSocket consome logs/otel/*.jsonl            │
│             ─ um personagem por agente                    │
│             ─ status, ação corrente, métricas             │
└─────────────────────────────────────────────────────────┘
```

**Note bem o que NÃO aparece:** `claude -p`, `sessions.json`, processos vivos em background, spawn de subprocessos, race conditions de inicialização paralela, dashboard tmux. Sessão viva durante a feature (decanting) acontece dentro do `Agent` tool nativo, gerenciada pelo Claude Code. SendMessage retoma quando há continuidade multi-turn.

## 2.2 Atores

**Humano.** Usa sessão Claude Code interativa para conversar com o Arquiteto. Acompanha trabalho no dashboard (browser). Aprova ações irreversíveis.

**Arquiteto.** Instância Claude Code (interativa) onde o humano conversa. Coordena, decide, escreve specs, chama especialistas via Agent tool, integra reports, mantém `docs/DECISOES.md`. Carregado via sistema de skills/agents do Claude Code: `agents/arquiteto.md` é o system prompt.

**Especialista (DBA, pipeline-dev, qa-tester, etc).** Subagente registrado como `subagent_type=multiagents-decanting:<role>`. Invocado pelo Arquiteto via `Agent` tool. Sessão viva durante a feature (que tipicamente cabe numa call multi-step, com multi-tool, multi-turn interno). Continuidade entre calls via `SendMessage` quando aplicável; fallback de boot reconstruindo de `handoff.md` quando não. Em ambos os casos, **decanting obrigatório ao fim da feature**.

**Dashboard.** Web app local em Python (HTTP + WebSocket). Consome telemetria OpenTelemetry GenAI emitida pelos agentes. Mostra cada agente como personagem visual.

## 2.3 Fluxo canônico

### Setup do projeto

```
$ cd ~/meu-projeto
$ claude  # sessão Claude Code interativa abre
> /multiagents-init
```

O comando dispara o skill `multiagents-workflow`:

1. Verifica que está em projeto novo (sem estrutura).
2. Cria estrutura de pastas (definida em 03).
3. Pergunta ao usuário (uma pergunta por vez) o contexto do projeto.
4. Escreve `CLAUDE.md`, `docs/00_OBJETIVO.md`, `multiagents-decanting.toml`.
5. Sugere quais especialistas habilitar inicialmente (registra `subagent_type` em `.claude/agents/`).
6. **Não spawna processo nenhum.** Só cria os arquivos de identidade e dossiê para cada agente em `memory/<agente>/`.
7. Inicia dashboard local em background (processo Python único do plugin).
8. Reporta: "pronto, dashboard em http://localhost:8765. Os especialistas estão prontos pra serem chamados quando você descrever uma feature."

### Trabalho em feature

```
> Vamos implementar a feature X.
```

Arquiteto:

1. Analisa, propõe abordagem, alinha com usuário.
2. Decide pattern Anthropic (chain/route/parallelize/orchestrator-worker/evaluator-optimizer). Em paralelo: apresenta opções de custo (1 agente sequencial vs N em paralelo) com estimativa de tokens.
3. Escreve `specs/feature-X.md` (objetivo, inputs, outputs, critérios de aceite, restrições, blast radius esperado).
4. Para cada especialista necessário, chama via `Agent` tool nativo:
   ```
   Agent(subagent_type="multiagents-decanting:pipeline-dev",
         description="...",
         prompt="Leia specs/feature-X.md, siga seu protocolo de boot
                 (memory/pipeline-dev/), execute, decante, retorne report.")
   ```
5. O subagente roda em sessão própria (Claude Code gerencia). Executa multi-step. Decanta. Retorna resumo.
6. Arquiteto lê `reports/feature-X/<agente>.md`. Valida contra critérios de aceite.
7. Se OK: registra em `docs/DECISOES.md` e atualiza `trust.json` do agente.
8. Se rework: nova call do `Agent` tool com instrução de correção, ou `SendMessage` se disponível.

### Decanting (ao fim da unidade de trabalho)

O subagente, antes de retornar resumo final ao Arquiteto, **obrigatoriamente** escreve:

1. `reports/feature-X/<agente>.md` — entrega da feature.
2. `memory/<agente>/decisions.md` — append-only, decisões + restrições decorrentes.
3. `memory/<agente>/handoff.md` — sobrescrito, "o que ficou pendente, em que ponto parei".
4. `memory/<agente>/lessons.md` — append-only, aprendizados *que não estavam na spec*.
5. (Quando aplicável) `memory/<agente>/state.md` — snapshot do trabalho global.
6. (Quando aplicável) `memory/<agente>/playbooks/<tarefa>.md`.

O Arquiteto, ao receber o resumo, valida o decanting (lê os arquivos). Se faltou algo crítico, nova call: "decante o aprendizado X que ficou implícito no report".

### Pausa de sessão

```
> Vamos parar por hoje.
```

Arquiteto:

1. Atualiza `docs/STATE.md` com snapshot global.
2. Atualiza `docs/DECISOES.md` com decisões da sessão.
3. Sobrescreve `memory/arquiteto/handoff.md`.
4. Dashboard permanece ativo (processo Python único); pode ser encerrado com `/multiagents-dashboard --stop`.
5. Usuário fecha sessão Claude Code. **Não há processo de agente em background a encerrar** (nunca houve).

### Retomada

```
$ claude  # nova sessão
> /multiagents-dashboard  # confirma/reabre dashboard
> Onde paramos?
```

Arquiteto (nova working memory):

1. Lê `docs/STATE.md`, `docs/DECISOES.md` (últimas 10), `memory/arquiteto/handoff.md`.
2. Reconstrói contexto. Pergunta ao humano se confere.
3. Resume estado e propõe próximos passos.

Especialistas continuam "prontos" sem precisar respawn. Próxima call do Agent tool funciona idêntica à anterior; subagent lê seu `memory/<agente>/` e segue.

## 2.4 Multi-turn Arquiteto ↔ Especialista (quando necessário)

Cenário comum: pipeline-dev entrega report, Arquiteto vê problema, quer ajuste sem o agente perder contexto da implementação que acabou de fazer.

**Opção A — `SendMessage` (Claude Code v2.1.77+ com `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`):**

```
SendMessage(to="<agent-id-from-previous-Agent-call>",
            message="Bom trabalho, mas ajuste X conforme...")
```

Subagent retoma seu próprio contexto da call anterior. Zero código próprio do plugin pra gerenciar isso. Fluido.

**Opção B — Nova call do `Agent` tool (fallback universal):**

```
Agent(subagent_type="multiagents-decanting:pipeline-dev",
      prompt="Leia specs/feature-X.md + memory/pipeline-dev/handoff.md
              + reports/feature-X/pipeline-dev.md (sua entrega anterior),
              e ajuste X conforme...")
```

Sessão zerada, mas como o agente acabou de decantar, `handoff.md` está fresco e o report está em disco. Reconstrução é trivial. Ligeiramente menos fluido que SendMessage, funcionalmente equivalente.

O plugin **detecta** automaticamente se SendMessage está disponível (versão do Claude Code + env var) e usa preferencialmente quando há continuidade lógica de feature.

## 2.5 Decisão de paralelismo (heurística do Arquiteto)

O Arquiteto sempre apresenta opções antes de paralelizar:

```
Tarefa X. Posso atacar de três formas:
(a) Sequencial — 1 especialista por vez, baseline ~N tokens, ~T minutos.
(b) Paralelo seletivo — 2 especialistas em paralelo (uma call Agent
    cada, em mesma resposta), ~3×N tokens, ~0.6×T minutos.
(c) Paralelo agressivo — 5 especialistas em paralelo, ~12×N tokens,
    ~0.3×T minutos.

Recomendação: (b), porque [racional do problema].

Qual?
```

Em modo frio, paralelismo é trivial: múltiplas calls do `Agent` tool em uma única resposta do Arquiteto rodam em paralelo nativamente (Claude Code gerencia). Sem race conditions de spawn.

Resposta vai pra `docs/DECISOES.md`. Próxima feature pode reavaliar.

## 2.6 Trust ladder na arquitetura

Cada agente tem `memory/<agente>/trust.json`:

```json
{
  "score": 65,
  "history": [
    {"feature": "f-001", "outcome": "accepted", "weight": 5},
    {"feature": "f-002", "outcome": "rework_minor", "weight": 1},
    {"feature": "f-003", "outcome": "rework_major", "weight": -3}
  ],
  "last_updated": "2026-06-27T14:32:00-03:00"
}
```

O Arquiteto, ao decidir nível de approval para uma ação proposta pelo especialista, consulta o score:

- Score < 30: irreversíveis E médio-risco pedem confirmação humana.
- 30 ≤ Score < 70: só irreversíveis pedem confirmação.
- Score ≥ 70: irreversíveis catastróficas pedem confirmação; resto autônomo.

A escala não é gating bureaucrático: é instrumentação de competência.

## 2.7 Componentes implementados

| Componente | Tecnologia | Função |
|---|---|---|
| CLI (`init`, `inspect`, `doctor`, `dashboard`, `decant`, `trust`, `upgrade`, `explain`, `tutorial`) | Python 3.9+, dep única: `websockets` | Comandos de operação |
| Wrapper shell para conveniência | `.bat` + `.ps1` + `bash` | Atalho para Python |
| Dashboard backend | Python (`http.server` + `websockets`) | Servidor HTTP + WS local |
| Dashboard frontend | HTML + CSS + JS vanilla | Personagens, logs, status, métricas, PWA |
| OTel consumer | Python (parte do dashboard) | Tail de `logs/otel/*.jsonl`, broadcast WS |
| Agentes (registros de subagent_type) | Markdown em `.claude/agents/` | Carregados pelo Claude Code nativamente |
| Templates de memória | Markdown em `templates/` | Copiados no `init` |
| Skills do plugin | Markdown em `skills/` | Loaded pelo Claude Code |
| Commands do plugin | Markdown em `commands/` | Slash commands `/multiagents-*` |
| Hooks (guardrails + OTel emit) | Markdown / scripts | Hooks Claude Code nativos |

**Note o que NÃO aparece:** `spawn.py`, `drive.py`, `sessions.json`, stream parser próprio, `claude -p` wrapper. Tudo isso desapareceu junto com a complexidade de modo vivo.

## 2.8 O que está fora do escopo do plugin

- Vector store, embeddings, retrieval semântico. Use Mem0 se precisar — não está acoplado ao plugin.
- Autenticação multi-usuário. Plugin é single-user, single-machine.
- Deploy em servidor. Roda local.
- Integração com tickets externos (Jira, Linear). Pode ser adicionada por hooks, fora do core.
- Substituir spec-driven development próprio. Use Spec Kit do GitHub.
- Substituir MCP. MCP é nativo do Claude Code; plugin não interfere.
- Modo vivo legado (`claude -p --resume` com processos OS separados). Plugin usa exclusivamente primitivas nativas do Claude Code (`Agent` tool + `SendMessage`) para sessão viva durante a feature.
