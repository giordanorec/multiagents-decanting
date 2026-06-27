# 04 — Protocolos (boot, execução, decanting, comunicação)

## 4.1 Protocolo do Especialista — boot (toda call)

Executado *antes* de qualquer outra ação, no início de cada `Agent` tool call. Sem exceção. O system prompt do especialista (em `.claude/agents/<role>.md`) prescreve este protocolo explicitamente.

```
1. Ler ./memory/<eu>/identity.md
2. Ler ./memory/<eu>/handoff.md   ← MAIS IMPORTANTE — última nota
3. Ler ./memory/<eu>/state.md (se existir)
4. Ler últimas 10 entradas de ./memory/<eu>/decisions.md
5. Ler ./memory/<eu>/lessons.md (se existir; é o ativo de longo prazo)
6. Ler ./memory/<eu>/glossary.md (se existir)
7. Ler ./docs/DECISOES.md (últimas 5 entradas) e ./docs/STATE.md
8. Ler ./specs/<spec-corrente>.md
9. Ler subconjunto da codebase indicado na spec (paths explícitos)
10. Apenas então: começar a executar.
```

O boot deve consumir 5-10% do orçamento de tokens da sessão. Mal-feito (skip de etapas), agente perde memória institucional. Bem-feito, sessão fresca não significa amnésia.

Em modo frio, este boot acontece em **toda call do Agent tool**. Não é overhead — é a substituição completa da memória conversacional que o modo vivo dava de graça.

## 4.2 Protocolo do Especialista — execução

Durante a execução (que pode ser longa, multi-step, multi-tool dentro da call):

- **Atualiza `decisions.md`** assim que toma decisão não-trivial, não no final. Decisão registrada tarde é decisão perdida (especialmente em frio, onde a sessão acaba quando a call retorna).
- **Atualiza `handoff.md`** a cada milestone interno (não esperar fim). Se a call falhar ou retornar antes do esperado, há onde retomar.
- **Emite spans OTel GenAI** automaticamente via hook `post-otel-emit.py` (ver 4.10).
- **Respeita guardrails do plugin** (ver 4.6).
- **Aplica blast radius judgment** (ver 4.7).

## 4.3 Protocolo do Especialista — decanting (obrigatório antes de retornar)

Antes de devolver controle ao Arquiteto (último passo da call do Agent tool), **sem exceção**, executar:

```
1. Escrever ./reports/<feature>/<eu>.md
   - Status: completed | partial | blocked | failed
   - Resumo do que foi feito
   - Critérios de aceite: cada um marcado [x] ou [ ] com nota
   - Evidências (path de testes rodados, prints de output, etc)
   - Pendências
   - Recomendação para próximo passo

2. Atualizar ./memory/<eu>/decisions.md (append)
   - Toda decisão não-trivial não ainda registrada
   - Formato fixo (ver template em 05)

3. Sobrescrever ./memory/<eu>/handoff.md
   - "Em andamento" / "Próximos passos" / "Avisos para o próximo eu"
   - Mesmo se feature terminada, deixar nota sobre estado do trabalho global

4. (Opcional) Atualizar ./memory/<eu>/state.md
   - Lista de features completadas/em andamento/bloqueadas
   - Débitos técnicos novos

5. (Opcional) Append em ./memory/<eu>/lessons.md
   - Aprendizado que NÃO estava na spec
   - Contexto + o quê + quando aplicar + quando não aplicar

6. (Se tarefa repetiu 2-3 vezes com sucesso) criar ou atualizar
   ./memory/<eu>/playbooks/<tarefa>.md

7. Atualizar ./memory/<eu>/trust.json
   - Adicionar entrada ao histórico (outcome será preenchido pelo Arquiteto)

8. Emitir span OTel "decanting.complete" com checksum dos arquivos atualizados.

9. Retornar resumo curto ao Arquiteto (este é o output natural da Agent tool call).
```

Decanting é a **última coisa** que o agente faz antes de retornar. Sinal de catástrofe: o resumo retornado menciona trabalho concluído mas `handoff.md` não foi atualizado (verificável via hash).

## 4.4 Hook de safety: decanting check ao fim de sessão Claude Code

Hook `session-end-decant-check.py` roda quando a sessão do Arquiteto termina. Para cada agente com call recente:

```
1. Lê últimos spans OTel do agente.
2. Verifica se houve "decanting.complete" após a última "agent.start".
3. Se não houve: marca em logs/otel/<date>.jsonl como
   "decanting.skipped" e diminui trust score (-10).
4. Próxima sessão Arquiteto vê alerta no doctor.
```

Não é hard guard (sessão já terminou), mas é instrumentação que pune omissão.

## 4.5 Protocolo do Arquiteto

### 4.5.1 No início de cada sessão

```
1. Ler ~/.claude/CLAUDE.md (global, se existir).
2. Ler ./CLAUDE.md (projeto).
3. Ler ./docs/STATE.md, ./docs/DECISOES.md (últimas 10 entradas).
4. Ler ./memory/arquiteto/handoff.md.
5. Verificar saúde: scripts/multiagents.py doctor.
6. Apresentar resumo ao usuário e perguntar "Onde paramos?" /
   "Em que parte quer trabalhar?".
7. Não executar até confirmação.
```

### 4.5.2 Ao despachar trabalho

```
1. Determinar pattern apropriado (ver 4.8):
   - chain (sequencial)
   - route (classificação + especialista certo)
   - parallelize (mesma tarefa, perspectivas múltiplas)
   - orchestrator-worker (delegação)
   - evaluator-optimizer (loop crítico)
2. Estimar custo (tokens) das opções (sequencial vs paralelo).
3. Apresentar ao usuário e ESPERAR confirmação se custo > threshold.
4. Escrever ./specs/feature-NNN-<slug>.md no formato canônico (ver 3.5).
5. Despachar via Agent tool:
   Agent(subagent_type="multiagents-decanting:<role>",
         description="<descrição curta>",
         prompt="Leia ./specs/feature-NNN-<slug>.md, siga seu protocolo
                 de boot (memory/<eu>/), execute, decante
                 (memory/<eu>/ + reports/...), retorne resumo.")
6. Em paralelismo: múltiplas calls Agent em UMA resposta = paralelo nativo.
7. Aguardar retorno. Ler resumo + reports.
8. Validar contra critérios de aceite.
9. Se OK: registrar em ./docs/DECISOES.md. Atualizar trust.json do
   agente (outcome="accepted").
10. Se rework: SendMessage (se disponível) ou nova Agent call com
    correção. Atualizar trust.json conforme magnitude.
```

### 4.5.3 Ao fim da sessão

```
1. Atualizar ./docs/STATE.md (snapshot global).
2. Append em ./docs/DECISOES.md (decisões da sessão).
3. Atualizar ./memory/arquiteto/handoff.md (o que ficou pendente
   pro próximo eu).
4. Commit Git (conventional commits leve: feat:, fix:, docs:,
   refactor:). Push só se usuário pediu.
5. Resumo conciso ao usuário: feito, próximo passo, custo da sessão.
```

## 4.6 Guardrails do plugin (deterministic, raros, catastróficos)

Implementados via hooks PreToolUse:

| Ação | Bloqueio |
|---|---|
| `git push --force` em `main` | bloqueia; pede confirmação explícita do humano |
| `rm -rf` em path fora da raiz do projeto | bloqueia; nunca |
| Modificar `memory/*/identity.md` sem flag `--allow-identity-change` | bloqueia |
| Commit de arquivo com secret detectado (regex env, key, password) | bloqueia; warn |

Esses são guardrails verdadeiros: previnem catástrofe, não direcionam workflow. Nada além disso vira hook.

**Note** que removemos o guardrail "spawn de agente sem session_id" e "claude -p sem bypassPermissions" — ambos eram específicos do modo vivo aposentado.

## 4.7 Blast radius judgment

Cada ação do agente é classificada em três níveis (na spec ou inferido):

| Nível | Exemplos | Default |
|---|---|---|
| **Reversível, baixo risco** | read, run test, create branch, list files | Autônomo, sem prompt |
| **Reversível, médio risco** | edit em branch, install dep em venv, run migration em dev | Autônomo + log; trust score < 30 pede confirmação |
| **Irreversível, alto risco** | push em main, deploy prod, drop table, gasto pago, mensagem em canal cliente | Human-in-the-loop obrigatório, sempre |

Implementado no Arquiteto: ao ler spec ou pedido do especialista, classifica → decide se prossegue, se pede confirmação humana, ou se bloqueia.

## 4.8 Workflow patterns (Anthropic Building Effective Agents)

O Arquiteto escolhe um pattern por feature. Documentado em `docs/DECISOES.md`.

### Chain (prompt chaining)
Saída de um agente alimenta o próximo, em sequência. Útil quando a tarefa decompõe linearmente.
- pipeline-dev escreve → qa-tester testa → docs-writer documenta.

### Route (routing)
Classifica input e direciona ao especialista certo.
- Pergunta do usuário sobre desempenho? → DBA. Sobre UI? → frontend-dev. Sobre deploy? → devops-installer.

### Parallelize
Mesma tarefa, perspectivas múltiplas, para confiança maior.
- 3 abordagens diferentes para um problema, depois Arquiteto sintetiza.
- Em modo frio: múltiplas Agent calls em uma única resposta do Arquiteto = paralelo nativo, sem complicação.

### Orchestrator-worker
Arquiteto decompõe em subtarefas paralelas independentes, cada uma a um worker, depois sintetiza.
- Padrão Anthropic Multi-Agent Research: +90% qualidade, 15× tokens.
- Só usar quando a tarefa genuinamente paraleliza.

### Evaluator-optimizer
Um agente produz; outro critica; primeiro itera. Loop com critério de parada.
- pipeline-dev escreve → qa-tester critica → pipeline-dev refatora → loop até qa-tester aprovar ou N iterações.
- Em modo frio: usa SendMessage pro pipeline-dev manter contexto entre iterações, ou Agent call nova lendo report anterior.

## 4.9 Trust ladder — protocolo de atualização

`memory/<agente>/trust.json` formato:

```json
{
  "agente": "pipeline-dev",
  "score": 65,
  "history": [
    {"feature": "feature-001", "outcome": "accepted", "weight": 5, "timestamp": "2026-06-20T14:30:00-03:00"},
    {"feature": "feature-002", "outcome": "rework_minor", "weight": 1, "timestamp": "2026-06-22T10:15:00-03:00"},
    {"feature": "feature-003", "outcome": "rework_major", "weight": -3, "timestamp": "2026-06-23T16:45:00-03:00"}
  ],
  "last_updated": "2026-06-27T14:32:00-03:00"
}
```

Pesos sugeridos:
- accepted: +5
- accepted_with_minor_note: +3
- rework_minor: +1 (pequena correção)
- rework_major: -3 (revisão grande)
- rejected: -7
- decanting_skipped: -10 (sanção forte — detectado por hook session-end-decant-check)

Score cap: [0, 100]. Default ao habilitar agente: 50.

Score → ajuste de fricção:
- 0-29: irreversíveis E médio-risco pedem confirmação humana.
- 30-69: só irreversíveis pedem.
- 70-100: só irreversíveis catastróficas pedem.

## 4.10 OpenTelemetry GenAI emit

Todo evento relevante emite span OTel GenAI compatível (spec v1.41). Hook `post-otel-emit.py` (PostToolUse) captura a chamada e grava em `logs/otel/<date>.jsonl`. Se `OTEL_EXPORTER_OTLP_ENDPOINT` definido, exporta também via OTLP HTTP.

Spans emitidos:

| Span | Quando | Atributos chave |
|---|---|---|
| `agent.start` | Início de call do Agent tool | `agent.name`, `agent.role`, `subagent.id` |
| `agent.boot` | Início de boot protocol | `agent.name`, `files_read[]` |
| `workflow.feature` | Spec sendo executada | `workflow.name`, `agent.name`, `spec.path`, `pattern` (chain/route/...) |
| `model.call` | Chamada Claude | `gen_ai.system="anthropic"`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| `tool.use` | Tool call | `tool.name`, `tool.args` (sanitizado), `tool.outcome` |
| `decanting.start` | Início decanting | `agent.name`, `feature` |
| `decanting.complete` | Fim decanting | `agent.name`, `files_written[]`, `checksum` |
| `agent.error` | Erro detectado | `error.type`, `error.message`, `retry.attempt` |
| `agent.end` | Retorno da Agent call | `agent.name`, `outcome`, `duration` |

Métricas:
- `gen_ai.token.usage` (counter, por modelo)
- `gen_ai.cost.estimate` (counter, USD)
- `agent.feature.duration` (histogram, segundos)
- `agent.trust.score` (gauge, por agente)

Compatibilidade: Langfuse, Phoenix, Arize, Helicone — todos aceitam OTLP HTTP nativamente. Plugin não acopla a nenhum específico.

O **dashboard consome esses spans direto** (tail de `logs/otel/*.jsonl` + broadcast WS) — sem stream-json proprietário, sem parser próprio.

## 4.11 Comunicação entre agentes (futuro: A2A)

**V1.0:** comunicação inter-agente é mediada pelo Arquiteto via arquivos (`specs/`, `reports/`). Nenhuma comunicação direta entre especialistas.

**Roadmap V2.0:** suporte opcional a A2A protocol (Linux Foundation). Cada agente do plugin pode expor endpoint A2A compatível, permitindo agentes externos (Google, Microsoft, etc) conversarem.

Estrutura preparatória: `memory/<agente>/identity.md` já é compatível com Agent Card do A2A (nome, descrição, capabilities). Migração futura: adicionar endpoint HTTP que serve o Agent Card.

## 4.12 Constitutional principles (alinhamento Anthropic jan/2026)

System prompt de cada agente referencia (não duplica) a hierarquia 4-tier da nova constitution Anthropic:

```
Você opera sob a seguinte hierarquia de prioridades, em ordem:
1. Broadly safe — não comprometa supervisão humana.
2. Broadly ethical — seja honesto; evite ações inapropriadas, perigosas ou prejudiciais.
3. Compliant with Anthropic's guidelines.
4. Genuinely helpful — beneficie o usuário e o projeto.

Em conflito, escolha o nível mais alto. Em dúvida, pergunte ao Arquiteto.
```

Não reinventa, alinha. Quando Anthropic atualizar a constitution, plugin atualiza referência sem reescrita.
