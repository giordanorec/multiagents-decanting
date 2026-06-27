# 05 — Templates (de memória, spec, report, status)

Todos os templates abaixo são copiados pelo `/multiagents-init` para o projeto-cliente. Cada arquivo é Markdown ou JSON puro, sem dependências exóticas. Variáveis no formato `{{var}}` são substituídas no momento da criação.

## 5.1 `templates/memory/identity.md`

```markdown
# Identity — {{agente}}

**Papel:** {{papel_curto}}

**Escopo (o que toco):**
- {{path_1}}
- {{path_2}}

**Fora do escopo (o que NÃO toco):**
- {{fora_1}}
- {{fora_2}}

**Restrições não-negociáveis:**
- Nunca {{restricao_1}}.
- Sempre {{regra_1}}.

**Hierarquia de prioridades** (Anthropic Constitution, jan/2026):
1. Broadly safe — não comprometa supervisão humana.
2. Broadly ethical — seja honesto; evite ações inapropriadas, perigosas ou prejudiciais.
3. Compliant with Anthropic's guidelines.
4. Genuinely helpful — beneficie o usuário e o projeto.

**Em conflito de prioridade ou em dúvida:** pergunte ao Arquiteto, não decida sozinho.

**Protocolo de boot (toda invocação):** ver `04_PROTOCOLOS.md` §4.1.
**Protocolo de decanting (ao fim):** ver `04_PROTOCOLOS.md` §4.3.
```

## 5.2 `templates/memory/dossier.md`

```markdown
# Dossier — {{agente}} — {{projeto}}

> Este é o contexto profundo do projeto **sob a sua ótica específica**.
> Filtra apenas o que você precisa saber. Denso, mastigado.

## O projeto em uma frase
{{objetivo_curto}}

## Por que existe
{{motivacao_negocio}}

## Quem usa
{{usuarios}}

## Estado atual (referência cruzada)
- Documento canônico: `docs/STATE.md`.
- Decisões: `docs/DECISOES.md`.

## Áreas do código que você toca
- {{area_1}}: {{descricao}}
- {{area_2}}: {{descricao}}

## Decisões arquiteturais relevantes para você
{{lista_decisoes_pertinentes}}

## Convenções desse projeto que você precisa respeitar
- {{convencao_1}}
- {{convencao_2}}

## Outros agentes que você interage
- **Arquiteto**: recebe specs, devolve reports.
- **{{outro_agente}}**: {{relacao}}.

## Atualização
Este dossier é mantido pelo Arquiteto. Você pode propor mudanças
escrevendo em `reports/<feature>/dossier-update.md` no decanting.
```

## 5.3 `templates/memory/decisions.md`

```markdown
# Decisões — {{agente}}

> Log append-only de toda decisão não-trivial que você tomou.
> Formato fixo. Não edite entradas anteriores; apenda novas.

---

## YYYY-MM-DD — Decisão #N: <título curto>

**Decisão:** <o que foi decidido em uma frase>

**Alternativas consideradas:** <as outras opções e por que rejeitadas>

**Por quê:** <a razão principal>

**Restrição decorrente:** <o que doravante NÃO deve ser feito por causa desta decisão>

**Como reabrir:** <que sinal ou mudança indicaria que vale revisitar>

**Feature relacionada:** feature-NNN-<slug>

---

(novas entradas vão aqui acima das antigas)
```

## 5.4 `templates/memory/handoff.md`

```markdown
# Handoff — {{agente}}

> A nota mais importante do seu arquivo de memória.
> Sobrescrita a cada decanting. É a sua "última lembrança"
> para a próxima sessão.

**Última atualização:** YYYY-MM-DDTHH:MM:SS-03:00

## Em andamento agora
- {{feature_corrente}}: fase {{X}} de {{Y}}. Bloqueado em {{causa}}.
- (vazio se nada em andamento)

## Próximos passos imediatos
1. {{acao_concreta_1}}
2. {{acao_concreta_2}}
3. {{acao_concreta_3}}

## Avisos para o próximo eu
- {{gotcha_descoberto_tarde}}
- {{inconsistencia_no_codigo_que_nao_resolvi}}
- {{decisao_pendente_que_o_arquiteto_precisa_tomar}}

## Estado emocional / risco
- Confiança nas decisões atuais: alta | média | baixa.
- Áreas de incerteza: {{lista}}.

## Como retomar em um minuto
{{paragrafo_curto_resumo}}
```

## 5.5 `templates/memory/state.md`

```markdown
# Estado — {{agente}} — última atualização YYYY-MM-DD

## Features completadas
- feature-001-<slug>: YYYY-MM-DD, accepted [score +5]
- feature-002-<slug>: YYYY-MM-DD, accepted_with_minor_note [score +3]

## Features em andamento
- feature-003-<slug>: spec em `specs/`, iniciada YYYY-MM-DD

## Features bloqueadas
- feature-004-<slug>: bloqueada por decisão pendente do Arquiteto em X

## Débitos técnicos pendentes
- Refatorar módulo X (criado em feature-001, marcado para revisitar)

## Débitos de teste
- Cobertura do módulo Y caiu para 60% após feature-002

## Estatísticas
- Total features completadas: N
- % aceitas em primeira leitura: M%
- Tempo médio por feature: T minutos
- Tokens consumidos (últimos 30 dias): K
```

## 5.6 `templates/memory/lessons.md`

```markdown
# Aprendizados — {{agente}}

> Append-only. Aprendizados que **não estavam na spec**.
> Tacit knowledge tornado explícito. Este é o seu ativo de longo prazo.

---

## YYYY-MM-DD — Lição: <título>

**Contexto:** <em que situação descobri>

**O quê:** <o aprendizado em uma frase>

**Quando aplicar:** <em que situações futuras isto vale>

**Quando NÃO aplicar:** <exceções conhecidas>

**Evidência:** <link para feature/report/commit onde foi descoberto>

**Confiança:** alta | média | baixa.

---
```

## 5.7 `templates/memory/glossary.md`

```markdown
# Glossário — {{agente}}

> Vocabulário do domínio que você precisa entender.
> Específico do seu papel (diferente do `docs/03_GLOSSARIO.md`, que é global).

## Termo
**Definição:** ...
**Exemplo:** ...
**Relacionados:** ...

## Termo 2
...
```

## 5.8 `templates/memory/trust.json`

```json
{
  "agente": "{{agente}}",
  "score": 50,
  "history": [],
  "last_updated": "{{iso_timestamp}}",
  "version": 1
}
```

## 5.9 `templates/memory/playbooks/_template.md`

```markdown
# Playbook: <nome>

**Quando usar:** <gatilho específico>

**Pré-requisitos:**
- {{prereq_1}}
- {{prereq_2}}

## Passos
1. {{passo}}
2. {{passo}}
3. {{passo}}

## Pitfalls
- {{armadilha}}

## Variações conhecidas
- Se {{condicao}}, então {{ajuste}}

## Origem
Extraído de: feature-X, feature-Y, feature-Z (3 ocorrências bem-sucedidas).
```

## 5.10 `templates/specs/_template.md`

```markdown
# Spec: feature-{{nnn}} — {{slug}}

**Criada em:** YYYY-MM-DD
**Pattern (Anthropic):** chain | route | parallelize | orchestrator-worker | evaluator-optimizer
**Especialistas envolvidos:** {{lista}}
**Blast radius previsto:** reversível-baixo | reversível-médio | irreversível-alto

## Objetivo
<o quê e por quê em 1-3 frases>

## Inputs
- Arquivos relevantes: <paths>
- Decisões prévias relevantes: <referências a docs/DECISOES.md>
- Outros artefatos: <links>

## Outputs esperados
- <artefato 1> em <path>
- <artefato 2> em <path>

## Critérios de aceite (verificáveis)
- [ ] <critério>
- [ ] <critério>
- [ ] **Decanting completo:** handoff.md, decisions.md, lessons.md atualizados.
- [ ] **Report válido:** `reports/feature-{{nnn}}/<agente>.md` segue template 5.11.

## Restrições (o que NÃO fazer)
- {{restricao}}

## Estimativa de custo
- Tokens estimados: {{N}}
- Tempo estimado: {{minutos}} min

## Notas para o agente
<contexto adicional, dicas, alertas>
```

## 5.11 `templates/reports/_template.md`

```markdown
# Report — feature-{{nnn}} — {{agente}}

**Concluído em:** YYYY-MM-DDTHH:MM:SS-03:00
**Status:** completed | partial | blocked | failed
**Tempo total:** {{minutos}} min
**Tokens consumidos:** {{N}}

## Resumo executivo
<o que foi feito em 2-3 frases>

## Critérios de aceite
- [x] critério 1 — evidência: {{path/teste}}
- [x] critério 2 — evidência: {{path/teste}}
- [ ] critério 3 — não completado porque {{causa}}

## Arquivos modificados
- `path/x.py`: <descrição curta>
- `path/y.py`: <descrição curta>

## Evidências
- Testes rodados: `pytest tests/test_x.py` → todos passaram
- Linter: `ruff check src/` → 0 warnings
- {{outras_evidencias}}

## Decanting executado
- [x] `memory/<eu>/decisions.md` atualizado
- [x] `memory/<eu>/handoff.md` sobrescrito
- [x] `memory/<eu>/state.md` atualizado
- [x] `memory/<eu>/lessons.md` apendado (se aplicável)
- [x] `memory/<eu>/trust.json` atualizado (outcome pendente do Arquiteto)

## Pendências
- {{pendencia_1}}
- {{pendencia_2}}

## Recomendação para próximo passo
<sugestão concreta>

## Notas para o Arquiteto
<o que o Arquiteto deve saber para validar ou despachar próximo>
```

## 5.12 (removido)

Não há mais `status/<agente>.json` em modo frio. O estado runtime do agente é "sempre pronto" (subagent_type está registrado, é invocável). O estado atual (working, decanting) emerge dos spans OTel em tempo real. O dashboard infere status a partir do último span recente do agente:

- Span `agent.start` recente sem `agent.end` correspondente → **working**
- Span `decanting.start` recente sem `decanting.complete` → **decanting**
- Sem spans recentes (> 5 min) → **idle**
- Span `agent.error` sem retry → **error**

Sem polling de arquivos JSON, sem race conditions de atualização, sem status stale.

## 5.13 `templates/CLAUDE.md`

```markdown
# {{projeto}} — CLAUDE.md

## Contexto
{{descricao_curta}}

## Stack
- {{linguagem_principal}}
- {{frameworks}}
- {{infra}}

## Convenções de código
- {{convencao_1}}
- {{convencao_2}}

## Idioma
- Comunicação com usuário e em documentos: PT-BR.
- Comentários e identifiers no código: {{en|pt}}.

## Multiagente
Este projeto usa o plugin `multiagents-decanting`. Estrutura em:
- `docs/` — especificação viva
- `specs/` — tickets do Arquiteto
- `reports/` — entregas dos especialistas
- `memory/` — memória persistente por agente
- `logs/otel/` — telemetria runtime (gitignored)

## Comandos úteis
- `/multiagents-dashboard` — abrir dashboard local
- `/multiagents-doctor` — verificar saúde do projeto
- `/multiagents-decant <agente>` — forçar decanting manual de um agente
- `/multiagents-inspect <agente>` — ver estado de um agente
- `/multiagents-trust <agente>` — ver trust score

## Regras não-negociáveis
- Nunca push em main sem revisão humana.
- Nunca commit de secrets (.env, *.key, credentials.json).
- Sempre conventional commits leves (feat:, fix:, docs:, refactor:).
```

## 5.14 `templates/docs/00_OBJETIVO.md`, etc

Templates similares para cada arquivo de `docs/`. Conteúdo mínimo com headers padrão, a serem preenchidos no `init`.

## 5.15 `templates/multiagents-decanting.toml` (config do plugin no projeto)

```toml
[plugin]
version = "1.0.0"

[budget]
max_tokens_per_feature = 100000   # alerta no Arquiteto se ultrapassar numa única feature
max_cost_per_day_usd = 50.0       # encerra calls subsequentes; força decanting do que está em curso
warning_threshold = 0.8            # avisa em 80% do limite

[resilience]
retry_attempts = 3
retry_backoff_initial_ms = 1000
retry_backoff_max_ms = 30000
retry_jitter = true
circuit_breaker_failures = 3
circuit_breaker_reset_seconds = 300

[fallback]
opus_to_sonnet = true
sonnet_to_haiku = true

[observability]
otel_enabled = true
otel_local_path = "logs/otel"
otel_exporter_endpoint = ""  # ou variável de ambiente OTEL_EXPORTER_OTLP_ENDPOINT

[dashboard]
port = 8765
auto_open_browser = true
theme = "dark"  # dark | light | auto

[i18n]
default_locale = "pt-BR"
fallback_locale = "en"

[guardrails]
block_force_push_to_main = true
block_rm_rf_outside_project = true
block_secret_commit = true
block_identity_change_without_flag = true

[trust]
default_score = 50
weights = { accepted = 5, accepted_with_minor_note = 3, rework_minor = 1, rework_major = -3, rejected = -7, decanting_skipped = -10 }

[multiturn]
# Quando especialista precisa continuar conversa durante a feature:
# - "sendmessage": usa SendMessage se Claude Code v2.1.77+ e env var set
# - "agent_call": sempre nova call do Agent tool lendo handoff
# - "auto": detecta capacidade e escolhe (default)
strategy = "auto"
```
