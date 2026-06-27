# 07 — Skills e Commands

## 7.1 Skills do plugin

Plugin expõe **1 skill principal** que carrega a filosofia quando triggered, alinhado com `anthropic/skills` pattern.

### `skills/multiagents-workflow/SKILL.md`

```yaml
---
name: multiagents-workflow
description: |
  Filosofia e protocolo do plugin multiagents-decanting. Carrega papel
  de Arquiteto coordenador, protocolo de boot/decanting, workflow patterns
  Anthropic, blast radius judgment, trust ladder. Frio-first: Agent tool
  + memória em arquivo + SendMessage opcional pra continuação.
  Use quando: usuário pede "fluxo multi-agente", "decanting",
  "arquitetura multi-agente", "vamos montar um time de agentes",
  ou invoca /multiagents-init.
---

# Skill — multiagents-decanting

[Conteúdo: resumo do 01_CONTEXTO_E_FILOSOFIA.md + 02_ARQUITETURA.md,
densidade tal que o Arquiteto possa operar só lendo isto + os arquivos
de memória do projeto.]
```

## 7.2 Slash commands

Cada comando vive em `commands/<nome>.md`. Conteúdo é prompt template que o Claude Code executa quando o usuário digita o comando. Prefixo padrão: `/multiagents-`.

### `commands/multiagents-init.md`

```markdown
---
description: Inicializa projeto multiagente (Discovery + estrutura + agentes habilitados + dashboard).
---

Você vai iniciar um projeto multiagente em modo decanting nativo (sessão viva por feature via Agent tool + SendMessage, decanting ao fim).

## Pré-check

1. Verifique se já existe `multiagents-decanting.toml` na raiz. Se sim,
   projeto já inicializado — aborte com mensagem "projeto já tem
   multiagentes ativo; use /multiagents-dashboard ou /multiagents-doctor".
2. Verifique se Python 3.9+ está disponível: `python --version` ou
   `python3 --version`. Se não, aborte com instrução de instalação.
3. Verifique versão do Claude Code: `claude --version`. Se ≥ 2.1.77,
   informe disponibilidade de SendMessage (testar env var
   CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS).

## Discovery (uma pergunta por vez)

Faça as perguntas abaixo em sequência, esperando resposta entre cada uma.
NÃO despeje todas de uma vez.

1. "Qual é o objetivo principal do projeto, em uma frase?"
2. "Quem usa o resultado disso, e como?"
3. "Que tecnologia/stack já está definida? (linguagem, frameworks, infra)
   Ou ainda em aberto?"
4. "Que tipo de projeto é? [ ] ML/pipeline de dados [ ] App web
   [ ] CLI/automação [ ] Jogo [ ] Documento/conteúdo [ ] Outro"
5. "Há restrições não-óbvias? (compliance, dados sensíveis, prazo
   apertado, time pequeno, etc)"
6. "Quanto orçamento de tokens é razoável por dia? (default $50)"

## Setup

7. Crie estrutura de pastas (ver `_spec/03_ESTRUTURA_DE_PASTAS.md`).
8. Copie templates (ver `_spec/05_TEMPLATES.md`).
9. Preencha `CLAUDE.md`, `docs/00_OBJETIVO.md` com as respostas.
10. Crie `multiagents-decanting.toml` com defaults + ajustes do Discovery (budget).
11. Baseado no tipo de projeto, sugira lista de especialistas a habilitar:
    - ML/pipeline: arquiteto, pipeline-dev, qa-tester, dba (se há dados)
    - App web: arquiteto, pipeline-dev, frontend-dev, qa-tester
    - CLI: arquiteto, pipeline-dev, qa-tester, docs-writer
    - Jogo: arquiteto, pipeline-dev, qa-tester, asset-designer
    - Documento: arquiteto, docs-writer
    - Outro: pergunte ao usuário
12. Confirme a lista com usuário.
13. Para cada especialista da lista: copie template `agents/<role>.md` para
    `.claude/agents/<role>.md` (registra subagent_type) e crie
    `memory/<role>/` com templates iniciais (identity, dossier, decisions,
    handoff, trust.json com score 50).
14. **Não há spawn.** Os agentes ficam "prontos" — primeira Agent call
    será a primeira execução.
15. Inicie dashboard em background: `python scripts/multiagents.py dashboard --background`.
16. Verifique saúde: `python scripts/multiagents.py doctor`.

## Mensagem final

"Pronto. Projeto multiagente iniciado (decanting nativo).
- Dashboard: http://localhost:8765
- Especialistas habilitados: <lista>
- Próximo passo: descreva sua primeira feature e eu (Arquiteto) coordeno.

Cada especialista é invocado sob demanda via Agent tool (sem processos
em background, sem session_id manual). Memória vive em memory/<agente>/.

Use /multiagents-dashboard para reabrir o dashboard, /multiagents-doctor
para verificar saúde, /multiagents-decant <agente> para forçar decanting
manual."
```

### `commands/multiagents-enable.md`

```markdown
---
description: Habilita um especialista adicional num projeto já iniciado.
arguments: <agente>
---

Habilite o especialista `{{arg1}}` no projeto atual.

1. Verifique que `multiagents-decanting.toml` existe.
2. Verifique que `agents/{{arg1}}.md` existe nos templates do plugin.
3. Verifique que agente já não tem pasta `memory/{{arg1}}/` (evite sobrescrita).
4. Copie template `agents/{{arg1}}.md` para `.claude/agents/{{arg1}}.md`.
5. Crie `memory/{{arg1}}/` com templates iniciais.
6. Pergunte ao usuário: "Quer que eu personalize o dossier dele com
   contexto específico do projeto? Sim/Não".
7. Se sim, conduza mini-discovery e atualize `memory/{{arg1}}/dossier.md`.
8. Confirme: "{{arg1}} habilitado. Pronto para ser invocado via Agent tool."
```

### `commands/multiagents-inspect.md`

```markdown
---
description: Inspeciona estado de um agente (memória, decisões, telemetria recente).
arguments: <agente>
---

Mostre estado completo de {{arg1}}:

1. Conteúdo de `memory/{{arg1}}/handoff.md` (cabeça de tudo).
2. Últimas 5 decisões de `memory/{{arg1}}/decisions.md`.
3. Estado em `memory/{{arg1}}/state.md` (se existir).
4. Últimas 5 lessons de `memory/{{arg1}}/lessons.md` (se existir).
5. Trust score e últimas 5 entries de `memory/{{arg1}}/trust.json`.
6. Telemetria OTel últimas 24h: contagem de calls, tokens consumidos,
   última call (timestamp, spec, outcome).
7. Status inferido (idle / working / error baseado em spans recentes).

Apresente formatado, em PT-BR, com seções claras.
```

### `commands/multiagents-dashboard.md`

```markdown
---
description: Abre ou reabre o dashboard web local.
---

1. Verifique se há processo dashboard rodando: `python scripts/multiagents.py
   dashboard-status`.
2. Se não, inicie em background: `python scripts/multiagents.py dashboard
   --background`.
3. Abra URL no browser cross-platform.
4. Confirme: "Dashboard em http://localhost:8765. Use
   `/multiagents-dashboard --stop` para encerrar."
```

### `commands/multiagents-decant.md`

```markdown
---
description: Força decanting manual de um agente (útil quando feature foi interrompida).
arguments: <agente> [feature]
---

Force o agente {{arg1}} a executar protocolo de decanting agora.

Como em modo frio o agente não é um processo vivo, "forçar decanting"
significa: fazer nova Agent call que lê o estado atual (transcripts,
trabalho recente) e produz decanting retroativo.

1. Identifique a última feature em que {{arg1}} trabalhou (procurar
   reports/ ou logs/otel/ por menções recentes).
2. Faça Agent call:
   Agent(subagent_type="multiagents-decanting:{{arg1}}",
         prompt="Você está sendo chamado para executar decanting
                 retroativo. Leia memory/{{arg1}}/handoff.md (estado
                 atual), reports/<feature-recente>/{{arg1}}.md (sua
                 última entrega se existir), e logs/otel/<date>.jsonl
                 (sua atividade recente).
                 Atualize: handoff.md, decisions.md, lessons.md,
                 state.md, trust.json. Não execute trabalho novo.
                 Retorne resumo do que decantou.")
3. Aguarde retorno. Verifique que arquivos foram atualizados.
4. Confirme ao usuário: "Decanting retroativo de {{arg1}} completo."
```

### `commands/multiagents-doctor.md`

```markdown
---
description: Verifica saúde do projeto multiagente.
---

Rode `python scripts/multiagents.py doctor`. Reporta:

1. **Versões:**
   - Python: ≥ 3.9 OK / KO
   - Claude Code: versão + suporte SendMessage (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS)
   - Plugin multiagents-decanting: versão instalada vs última no marketplace

2. **Estrutura:**
   - multiagents-decanting.toml presente: OK
   - docs/ presente e populado: OK / faltam X
   - memory/<cada agente>/ completo: OK / faltam Y
   - .gitignore presente e correto: OK

3. **Telemetria:**
   - Spans OTel últimas 24h: N
   - Última atividade por agente
   - Agentes sem decanting há > 7 dias

4. **Budget:**
   - Tokens consumidos hoje: N (max: M)
   - Custo estimado hoje: $X (max: $Y)
   - % do budget: P%

5. **Trust scores:** lista cada agente com score.

6. **Alertas:**
   - Agentes habilitados mas nunca invocados (> 7 dias)
   - Agentes com último decanting > 7 dias atrás
   - lessons.md de algum agente > 10000 palavras (considere poda)
   - Decanting skipped detectado em alguma call recente

7. **Verde / Amarelo / Vermelho** veredito final.
```

### `commands/multiagents-trust.md`

```markdown
---
description: Mostra trust score e histórico de um agente.
arguments: <agente>
---

Mostre `memory/{{arg1}}/trust.json` formatado:

- Score atual (com gauge visual: ▓▓▓▓▓▓▓░░░ 65/100)
- Últimas 20 entries do histórico (feature, outcome, weight, timestamp)
- Estatística:
  - Total features: N
  - % accepted em primeira: M%
  - % rework_minor: ...
  - % rework_major: ...
  - Tendência últimas 10: melhorando | estável | piorando
- Nível atual de fricção (baseado no score):
  - 0-29: "todas ações de médio+ risco precisam confirmação"
  - 30-69: "só irreversíveis precisam confirmação"
  - 70-100: "alta autonomia; só catastróficas precisam confirmação"
```

### `commands/multiagents-upgrade.md`

```markdown
---
description: Atualiza o plugin para nova versão (preserva memória do projeto).
---

1. Verifique versão atual em `multiagents-decanting.toml`.
2. Busque última versão no GitHub.
3. Mostre diff de versão e CHANGELOG.
4. Confirme com usuário.
5. Atualize scripts/, templates/, agents/, dashboard/, commands/, skills/, hooks/
   (sem tocar memory/, docs/, specs/, reports/, CLAUDE.md, multiagents-decanting.toml).
6. Atualize `multiagents-decanting.toml.version`.
7. Verifique compatibilidade: `decanting doctor`.
8. Reporte mudanças relevantes pro usuário.
```

### `commands/multiagents-explain.md`

```markdown
---
description: Explica um conceito do plugin em linguagem natural (para leigos).
arguments: <conceito>
---

Explique o conceito `{{arg1}}` em linguagem acessível, em PT-BR.

Conceitos cobertos:
- "decanting" — protocolo de extração de aprendizado ao fim de cada feature.
- "trust ladder" — autonomia que escala com performance do agente.
- "blast radius" — quão irreversível é uma ação.
- "circuit breaker" — proteção contra loops descontrolados.
- "modo frio" — como funciona uma chamada ao especialista.
- "boot protocol" — o que o agente lê antes de começar a trabalhar.
- "SendMessage" — como continuar conversa com o mesmo agente.
- "Agent tool" — primitiva do Claude Code que invoca subagentes.
- "agente / especialista" — papéis dentro do sistema.
- "spec" — ticket que o Arquiteto escreve para um especialista.
- "report" — entrega do especialista.
- "handoff" — nota da última call pra próxima.
- "OTel" — padrão de observabilidade.
- (etc — adicionar conforme necessidade)

Use analogias do mundo real, evite jargão técnico, dê 1 exemplo concreto.
```

### `commands/multiagents-tutorial.md`

```markdown
---
description: Tutorial interativo embutido (para primeiros usos).
---

Execute um walkthrough guiado de 5-7 minutos:

1. Explique brevemente o que é multiagents-decanting (1 parágrafo).
2. Crie um projeto fictício temporário em `/tmp/multiagents-tutorial-<timestamp>/`.
3. Habilite 2 agentes (arquiteto + pipeline-dev).
4. Mostre o dashboard.
5. Escreva uma spec simples ("crie um script Python que soma 2 e 2").
6. Faça Agent call pra pipeline-dev. Mostre processo no dashboard (eventos OTel chegando).
7. Mostre o report devolvido + arquivos de memory atualizados.
8. Mostre o handoff que ficou (memory/pipeline-dev/handoff.md).
9. Pergunte se quer apagar o tutorial ou explorar mais.

Durante todo o tutorial, narre o que está acontecendo em PT-BR, com tom didático.
```

## 7.3 Hooks expostos pelo plugin

Plugin define hooks PreToolUse, PostToolUse e SessionEnd para implementar guardrails (ver 4.6), observabilidade (ver 4.10) e safety net de decanting (ver 4.4). Hooks ficam em `hooks/` no repo do plugin, copiados pra `.claude/hooks/` no projeto.

| Hook | Quando | Ação |
|---|---|---|
| `pre-guardrail-force-push.sh` | PreToolUse (Bash) | Bloqueia `git push --force` em main sem flag |
| `pre-guardrail-rm-rf.sh` | PreToolUse (Bash) | Bloqueia `rm -rf` fora da raiz |
| `pre-guardrail-secret-commit.sh` | PreToolUse (Bash) | Scan regex; bloqueia commit de secret |
| `pre-guardrail-identity-change.sh` | PreToolUse (Edit, Write) | Bloqueia modificação de identity.md sem flag |
| `post-otel-emit.py` | PostToolUse (*) | Emite span OTel pro tool call em `logs/otel/<date>.jsonl` |
| `post-trust-update.py` | PostToolUse (Agent) | Atualiza estatística no trust se for relevante |
| `session-end-decant-check.py` | SessionEnd | Detecta agentes que tiveram call recente sem decanting.complete; loga e penaliza trust |

Hooks são **plugins do Claude Code**, não invenção do plugin. Plugin só fornece os scripts.

## 7.4 MCP servers

Plugin **não** define MCP servers próprios. Usa os MCP nativos do Claude Code (Notion, Gmail, Google Drive, etc) como estão. Se o usuário adicionar MCP server custom, agente o usa transparentemente.

Roadmap V2.0: opcional MCP server `decanting-state` que expõe estado dos agentes (memory, trust, telemetria) via MCP, permitindo agentes externos consultarem.

## 7.5 Auto-discovery de skills do usuário

Se o usuário tem skills próprias em `.claude/skills/` do projeto, plugin não interfere. Agentes podem acionar essas skills naturalmente quando triggered.
