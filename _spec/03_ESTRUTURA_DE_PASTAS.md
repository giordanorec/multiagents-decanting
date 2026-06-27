# 03 — Estrutura de Pastas

## 3.1 Layout do projeto-cliente após `/decanting-init`

```
meu-projeto/
├── .claude/
│   └── agents/                          # registros de subagent_type
│       ├── arquiteto.md                 # system prompt + frontmatter (skill-compatible)
│       ├── pipeline-dev.md
│       ├── qa-tester.md
│       └── ... (outros conforme habilitados)
│
├── CLAUDE.md                            # descrição do projeto, regras globais
│
├── multiagents-decanting.toml           # config do plugin no projeto
│
├── docs/                                # especificação viva
│   ├── 00_OBJETIVO.md                   # o quê e por quê
│   ├── 01_ARQUITETURA.md                # tecnologia e desenho
│   ├── 02_REGRAS_DE_NEGOCIO.md          # regras do domínio
│   ├── 03_GLOSSARIO.md                  # vocabulário compartilhado
│   ├── DECISOES.md                      # log cronológico append-only
│   └── STATE.md                         # snapshot global do estado atual
│
├── specs/                               # tickets que o Arquiteto escreve
│   ├── feature-001-<slug>.md
│   ├── feature-002-<slug>.md
│   └── ...
│
├── reports/                             # entregas dos especialistas
│   └── feature-001/
│       ├── pipeline-dev.md
│       ├── qa-tester.md
│       └── arquiteto-merge.md
│
├── memory/                              # memória persistente por agente
│   ├── arquiteto/
│   │   ├── identity.md                  # quem é, escopo, restrições
│   │   ├── dossier.md                   # contexto do projeto (sob a ótica dele)
│   │   ├── decisions.md                 # decisões + restrições decorrentes
│   │   ├── handoff.md                   # última nota: onde parei
│   │   ├── state.md                     # snapshot do trabalho dele (opcional)
│   │   ├── lessons.md                   # aprendizados não-spec (opcional)
│   │   ├── glossary.md                  # vocabulário (opcional)
│   │   ├── trust.json                   # score + histórico
│   │   └── playbooks/                   # receitas para tarefas recorrentes
│   │       └── <tarefa>.md
│   ├── pipeline-dev/
│   │   └── (mesmo layout)
│   └── qa-tester/
│       └── (mesmo layout)
│
├── logs/                                # telemetria
│   └── otel/                            # OpenTelemetry GenAI spans (JSONL)
│       ├── 2026-06-27.jsonl
│       └── 2026-06-26.jsonl
│
├── dashboard/                           # web app local (estático servido)
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── manifest.json                    # PWA
│   ├── sw.js                            # service worker
│   └── assets/
│       └── avatars/                     # SVG por agente
│
└── scripts/                             # CLI do plugin (Python)
    ├── decanting.py                     # entry point único
    ├── init.py
    ├── inspect.py
    ├── dashboard_server.py
    ├── doctor.py
    └── _utils.py
```

**Note bem o que NÃO aparece** (vs v0.2.0 e vs versão anterior desta spec):

- ❌ `sessions.json` — não há mais session_ids manuais; Claude Code gerencia.
- ❌ `status/<agente>.json` — não há mais processos vivos com estado runtime; agente é "pronto" sempre, status emerge dos logs OTel.
- ❌ `logs/<agente>/current.log` + `stream.jsonl` — não há mais stream-json por agente; telemetria estruturada vai em `logs/otel/`.
- ❌ `scripts/spawn.py` + `drive.py` + `stream_parser.py` — desnecessários no modo frio.

## 3.2 Layout do plugin (repo do `multiagents-decanting`)

```
multiagents-decanting/
├── README.md                            # apresentação, instalação, primeiros passos
├── LICENSE                              # MIT
├── plugin.json                          # manifest do plugin
│
├── agents/                              # templates de subagent_type (system prompts)
│   ├── arquiteto.md
│   ├── pipeline-dev.md
│   ├── qa-tester.md
│   ├── dba.md                           # (v1.1+)
│   ├── frontend-dev.md                  # (v1.1+)
│   ├── mobile-dev.md                    # (v1.2+)
│   ├── llm-prompt.md                    # (v1.2+)
│   ├── devops-installer.md              # (v1.1+)
│   ├── docs-writer.md                   # (v1.1+)
│   └── asset-designer.md                # (v1.2+)
│
├── commands/                            # slash commands (prefixo /decanting-)
│   ├── decanting-init.md
│   ├── decanting-enable.md              # habilita especialista novo (não spawna; só cria memory/)
│   ├── decanting-inspect.md
│   ├── decanting-dashboard.md
│   ├── decanting-decant.md              # força decanting manual via nova call do Agent
│   ├── decanting-trust.md               # mostra trust.json de um agente
│   ├── decanting-doctor.md
│   ├── decanting-upgrade.md
│   ├── decanting-explain.md
│   └── decanting-tutorial.md
│
├── skills/
│   └── decanting-workflow/
│       └── SKILL.md                     # filosofia, carregada quando triggered
│
├── templates/                           # copiados pro projeto no init
│   ├── CLAUDE.md
│   ├── multiagents-decanting.toml
│   ├── docs/
│   │   ├── 00_OBJETIVO.md
│   │   ├── 01_ARQUITETURA.md
│   │   ├── 02_REGRAS_DE_NEGOCIO.md
│   │   ├── 03_GLOSSARIO.md
│   │   ├── DECISOES.md
│   │   └── STATE.md
│   ├── memory/                          # templates dos arquivos de memória
│   │   ├── identity.md
│   │   ├── dossier.md
│   │   ├── decisions.md
│   │   ├── handoff.md
│   │   ├── state.md
│   │   ├── lessons.md
│   │   ├── glossary.md
│   │   └── trust.json
│   └── specs/
│       └── _template.md
│
├── scripts/                             # copiados pro projeto no init
│   ├── decanting.py                     # entry point único
│   ├── init.py
│   ├── inspect.py
│   ├── doctor.py
│   ├── dashboard_server.py
│   └── _utils.py
│
├── dashboard/                           # copiado pro projeto no init
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── manifest.json
│   ├── sw.js
│   └── assets/
│       ├── avatars/                     # SVG por agente
│       │   ├── arquiteto.svg
│       │   ├── pipeline-dev.svg
│       │   └── ...
│       └── colors.json                  # paleta por agente
│
├── hooks/                               # hooks Claude Code que o init copia
│   ├── pre-guardrail-force-push.sh
│   ├── pre-guardrail-rm-rf.sh
│   ├── pre-guardrail-secret-commit.sh
│   ├── pre-guardrail-identity-change.sh
│   ├── post-otel-emit.py
│   └── session-end-decant-check.py
│
└── tests/                               # testes do próprio plugin
    ├── test_init.py
    ├── test_boot_protocol.py
    ├── test_decanting.py
    ├── test_dashboard.py
    ├── test_doctor.py
    └── fixtures/
```

## 3.3 Propósito de cada arquivo no `memory/<agente>/`

### `identity.md`

Quem o agente é. Seu papel, escopo, restrições. **Reforça** o system prompt mas mora num arquivo separado porque pode ser editado pelo humano sem mexer no template do plugin.

Exemplo de uso pelo agente: "Sou pipeline-dev. Meu escopo é código backend do pipeline em `src/pipeline/`. Não toco em frontend, não toco em infra, não toco em testes (essa é a qa-tester)."

### `dossier.md`

Contexto profundo do projeto **sob a ótica desse agente**. Denso, mastigado. Filtra apenas o que ele precisa saber. Escrito pelo Arquiteto no spawn ou atualizado em decanting.

Exemplo: pra um DBA do projeto de ML jurídico — "A base de processos vem do RCP. Os campos chave são X, Y, Z. As convenções de naming são W. O schema atual está em V."

### `decisions.md`

Append-only. **Toda decisão não-trivial** que o agente toma. Formato fixo:

```markdown
## 2026-06-25 — Decisão #N: <título curto>

**Decisão:** <o que foi decidido>
**Alternativas consideradas:** <as outras opções>
**Por quê:** <razão>
**Restrição decorrente:** <o que doravante NÃO deve ser feito>
**Como reabrir:** <que sinal indicaria que vale reavaliar>
```

A "restrição decorrente" é crucial — é o que evita que próxima sessão volte atrás.

### `handoff.md`

**Sobrescrito** a cada decanting. É a nota mais importante. "Onde parei, o que estava fazendo, o que a próxima sessão deve saber para continuar sem retroceder."

Formato:

```markdown
# Handoff — última atualização 2026-06-25T14:32:00-03:00

## Em andamento
- Feature X — fase Y de Z. Bloqueado em W aguardando decisão A.

## Próximos passos imediatos
1. <ação concreta>
2. <ação concreta>

## Avisos para o próximo eu
- <gotcha que descobri tarde>
- <inconsistência no código que está documentada mas ainda não resolvida>
```

### `state.md`

Snapshot estruturado do trabalho global do agente. Atualizado a cada decanting.

```markdown
# Estado — pipeline-dev — 2026-06-25

## Features completadas
- feature-001-<slug>: 2026-06-20, aceita
- feature-002-<slug>: 2026-06-23, aceita com rework

## Features em andamento
- feature-003-<slug>: spec em specs/, ainda não iniciada

## Débitos técnicos pendentes
- Refatorar módulo X (criado em feature-001, marcado pra revisitar)

## Débitos de teste
- Cobertura de Y caiu pra 60% após feature-002
```

### `lessons.md`

Append-only. **Aprendizados que NÃO estavam na spec.** Gotchas, padrões que funcionaram além do esperado, sutilezas do domínio. Este é o lugar de salvar **tacit knowledge**.

```markdown
## 2026-06-25 — Lição: <título>

**Contexto:** <em que situação descobri>
**O quê:** <o aprendizado>
**Quando aplicar:** <em que situações futuras isto vale>
**Quando NÃO aplicar:** <exceções conhecidas>
```

### `glossary.md` (opcional, v0.2+)

Vocabulário do domínio que o agente precisa entender. Pra DBA do projeto jurídico: "alvará", "bloqueio", "trânsito em julgado". Pra mobile-dev: "PWA", "service worker", "manifest". Só vale criar se há jargão pesado.

### `trust.json`

Score + histórico (definido em 02.6).

### `playbooks/<tarefa>.md`

Quando uma tarefa é repetida duas ou três vezes com sucesso, vira playbook. Exemplo: "Como adicionar uma coluna numa tabela do RCP". Formato:

```markdown
# Playbook: <nome>

**Quando usar:** <gatilho>

## Passos
1. ...
2. ...

## Pitfalls
- ...
```

## 3.4 Propósito de cada arquivo em `docs/`

### `00_OBJETIVO.md`
O quê o projeto é, por quê existe, quem usa, quais critérios de sucesso de alto nível. Escrito no init, raramente atualizado.

### `01_ARQUITETURA.md`
Tecnologia, desenho de alto nível, decisões fundacionais. Atualizado em decisões arquiteturais.

### `02_REGRAS_DE_NEGOCIO.md`
Regras do domínio. Append em decanting do Arquiteto quando uma regra nova emerge.

### `03_GLOSSARIO.md`
Vocabulário compartilhado. Diferente do `memory/<agente>/glossary.md` (que é específico do agente) — este é global.

### `DECISOES.md`
Log cronológico, append-only. Formato igual ao `decisions.md` dos agentes, mas para decisões **cross-agente** (arquiteturais). Atualizado pelo Arquiteto.

### `STATE.md`
Snapshot global. Atualizado pelo Arquiteto ao fim de cada sessão. Inclui status de cada agente, features em andamento, débitos abertos.

## 3.5 Propósito de cada arquivo em `specs/`

### Formato sugerido

```markdown
# Spec: feature-NNN — <slug>

## Objetivo
<o quê e por quê em 1-3 frases>

## Inputs
- Arquivos relevantes: <paths>
- Decisões prévias relevantes: <referências a docs/DECISOES.md>
- Outros agentes envolvidos: <lista>

## Outputs esperados
- <artefato> em <path>
- <artefato> em <path>

## Critérios de aceite (verificáveis)
- [ ] <critério>
- [ ] <critério>
- [ ] **Decanting:** handoff.md, decisions.md, lessons.md atualizados antes de devolver controle.

## Restrições (o que NÃO fazer)
- <restrição>

## Blast radius previsto
<reversível baixo | reversível médio | irreversível alto>

## Notas para o agente
<contexto adicional, dicas, alertas>
```

## 3.6 Princípios da estrutura

- **Tudo é markdown (`.md`) ou JSON estruturado (`.json`).** Sem binários, sem formatos proprietários. Auditável por humano e por agente.
- **Append-only** onde o histórico importa (`decisions.md`, `lessons.md`, `docs/DECISOES.md`).
- **Sobrescrito** onde só importa o estado atual (`handoff.md`, `state.md`, `STATE.md`, `trust.json`).
- **Versionado** sob git (todos os `.md` em `docs/`, `specs/`, `reports/`, `memory/`). Logs e status são gitignored (runtime).
- **Sem nada gerado por SDD proprietário.** Spec format é convenção markdown leve, compatível com Spec Kit caso o projeto adote.
