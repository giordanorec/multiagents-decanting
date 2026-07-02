# Changelog — mad (MultiAgent Decanting)

Formato: [Keep a Changelog](https://keepachangelog.com/). Versionamento semântico.

## [1.19.0] — 2026-07-01 (hardening final)

### Mudado/Adicionado
- **Bypass de USO ÚNICO com validade:** `emergency-bypass` agora grava um token
  `.mad/bypass_token.json` (1 uso, expira em 3min) que o hook CONSOME — substitui a
  env var global `MAD_WORKFLOW_BYPASS`, que ficava ligada o tempo todo. Muito mais seguro.
- **docs/SANDBOX.md:** guia do modo full-auto seguro (devcontainer opcional). Deixa
  explícito: Docker NÃO é pré-requisito; o mad é plug-and-play sem ele.
## [1.18.0] — 2026-07-01 (interoperabilidade + observabilidade do paralelo)

### Adicionado
- **MCP server (`scripts/mcp_server.py`, stdio, stdlib):** expõe o estado decantado
  do mad (memory/<agente>, DECISOES, workflow) como resources + tools MCP
  (mad_agent_state, mad_recent_decisions, mad_workflow_status). Registrado
  automaticamente em `.mcp.json` no init — outras ferramentas (Cursor, IDEs, agentes)
  consomem o conhecimento do mad. Zero dependência.
- **`mad export`:** gera AGENTS.md (lingua franca cross-tool) a partir da constituição
  + CLAUDE.md + identidades. Portabilidade além do Claude Code.
- **Painel enxerga o paralelo:** o dashboard mostra "Construindo N coisas ao mesmo
  tempo" (features da fronteira DAG) e a injeção do SessionStart lista a fronteira.
- **Agent Card A2A v1.0:** schema atualizado (protocolVersion, preferredTransport
  JSONRPC, capabilities reais — streaming=true).
## [1.17.0] — 2026-07-01 (motor DAG completo — execução paralela, opt-in)

### Adicionado
- **Execução PARALELA de features (engine="dag"):** o 4º big bet, completo. Com
  `[workflow].engine="dag"`, features independentes (deps satisfeitas + paths
  disjuntos) rodam ao mesmo tempo, governadas pela máquina de estados. `active_features[]`
  (fronteira paralela), `decide_tool` libera vários especialistas concorrentes,
  `mad_phase next <F-NNN>`/approve/close operam por-feature, e fechar uma feature
  ativa as dependentes prontas. Teto `max_parallel_features`. Conflito resolvido por
  DAG + disjunção de paths + write-scope (ADR-001).
- **Default segue `sequential`** (estável); vira `dag` por default após validação em
  campo. Zero instalação nova; sequential 100% inalterado (código dag é aditivo).
## [1.16.0] — 2026-07-01 (motor DAG — fronteira paralela anti-conflito)

### Adicionado
- **Fronteira paralela segura:** `parallel_frontier()` decide QUAIS features podem
  rodar juntas — prontas (deps concluídas) E com paths **disjuntos** (campo `Toca:` no
  backlog), até `[workflow].max_parallel_features`. É o cérebro anti-conflito do motor.
- **Config `[workflow].engine`** (`sequential` default | `dag`) + `max_parallel_features`.
  Backlog lê `Toca:/Touches:/Paths:` por feature (disjunção). Tudo aditivo/stdlib;
  sequential segue idêntico. Orquestração/conflito documentados no ADR-001.
## [1.15.0] — 2026-07-01 (motor DAG — fundação: dependências)

### Adicionado
- **Backlog com dependências (DAG):** `parse_backlog` extrai `depende:/deps:` por
  feature; `gate_espec_done` valida que as dependências existem e **rejeita ciclos**
  (DFS). Primitivos `ready_features()` (fronteira topológica) e `has_cycle()`.
  Base do motor paralelo. Zero instalação nova (Python stdlib); retrocompatível
  (backlog sem `depende:` = sem dependências, comportamento igual ao de hoje).

### Corrigido
- `parse_backlog` deixou de criar "feature fantasma" a partir de menção inline de
  F-NNN (ex.: em linha 'Depende: F-002'): feature só é linha que COMEÇA com F-NNN.

### Design
- **docs/adr/ADR-001** — design do motor DAG + execução paralela (atrás de flag
  `engine`, migração sem quebra, bateria de testes reforçada). Docker/sandbox é
  opcional e NÃO pré-requisito — o mad segue plug-and-play.
## [1.14.0] — 2026-07-01 (big bet: durable execution — checkpoint + dead-letter)

### Adicionado
- **Teto de rework (dead-letter):** após `[verify].max_rework` (3) reworks, a feature
  escala pro humano em vez de ciclar infinitamente. Fim do loop de rework sem fim.
- **Decanting incremental (checkpoint/resume):** o especialista anexa checkpoints em
  `reports/feature-NNN/progress.jsonl`; no re-despacho o Arquiteto injeta "já feito,
  continue daqui" — resume sem duplicar (skill + spec).
## [1.13.0] — 2026-07-01 (big bets: mapa da codebase + fundação de trace)

### Adicionado
- **Mapa semântico da codebase (Serena MCP):** os 5 agentes de código (arquiteto,
  pipeline-dev, frontend-dev, mobile-dev, dba) ganham os tools do Serena
  (find_symbol/get_symbols_overview/find_referencing_symbols/…) e são instruídos a
  preferir navegação por símbolos a grep cego (fallback gracioso). /mad-doctor detecta
  se o Serena está configurado.
- **Fundação de observabilidade causal:** `emit_span` agora carimba `trace_id` (por
  feature) + `span_id` (+ parent_span_id/duration opcionais) — o run multi-agente
  forma uma árvore por feature, base pro trace/waterfall real. Aditivo (não quebra o painel).
## [1.12.0] — 2026-07-01 (Cluster D: hardening)

### Adicionado
- **Audit log tamper-evident:** `log_event` agora encadeia hash SHA-256 (cada evento
  amarra o anterior); `verify_log_chain` detecta adulteração; `/mad-doctor` verifica a
  cadeia. Um agente comprometido não apaga o rastro do próprio abuso sem quebrar a cadeia.
- **`mad bootstrap`:** setup 1-comando — instala a dep opcional (websockets p/ dashboard)
  e roda o doctor. Paridade com o benchmark "add + install + funciona".
- **Fronteira anti prompt-injection (Art. 5):** o template de agente instrui tratar
  conteúdo externo (WebFetch/arquivos/saídas) como DADO, não comando, envolvendo em
  delimitadores não-confiáveis. Materializa o Art. 5, antes só declarativo.
## [1.11.0] — 2026-07-01 (Cluster C: confiabilidade do estado)

### Corrigido/Adicionado
- **Lock com dono (PID/host):** `_acquire_lock` grava {pid,host,ts} e só ROUBA o
  lock se o dono claramente morreu (os.kill), não mais por timeout cego — dois
  escritores não corrompem mais o estado. Dono vivo preso → erro claro, não corrupção.
- **Backup + auto-recuperação:** `save()` rotaciona `.mad/workflow_state.json.bak`
  antes de sobrescrever; `load()` cai no `.bak` se o principal estiver corrompido.
  O estado deixou de ser ponto único de falha.
## [1.10.0] — 2026-07-01 (Cluster B: segurança / least-privilege)

### Adicionado
- **Least-privilege por agente:** os 11 agentes agora declaram `tools:` (allowlist)
  no frontmatter — antes todos herdavam TODAS as ferramentas. Só o arquiteto despacha
  Agent/Task; qa/security/docs/llm sem Bash executável em src; devops é o único com
  amplo acesso. Mecanismo NATIVO do Claude Code, antes desperdiçado.
- **Hook de escopo de escrita** (`pre-guardrail-write-scope.py`): protege
  `.mad/workflow_state.json`, `logs/workflow.jsonl` e `sessions.json` de edição à mão,
  e enforça o escopo de paths por papel (via MAD_AGENT) — ninguém escreve na memória
  de outro agente nem no DECISOES.

### Corrigido
- **Circuit breaker ressuscitado:** `agent.error` passa a ser emitido quando um
  despacho de especialista falha (antes NENHUM era emitido → breaker placebo), e
  `recent_failures` conta também tool.use com erro. O breaker agora funciona de verdade.
## [1.9.0] — 2026-07-01 (Cluster A: verificação com DENTES)

### Adicionado
- **Teste REAL como gate** (`/mad-verify`, scripts/verify.py, seção `[verify]` no
  toml): roda test_cmd/lint_cmd/typecheck_cmd de verdade e grava verify.json. Se
  test_cmd está setado, a feature NÃO fecha sem `all_passed=true`. Fim do "teste é
  prosa que o LLM escreve".
- **Revisor independente obrigatório** (autor ≠ verificador): a feature não fecha sem
  um agente diferente do que a construiu escrever `VEREDITO: aprovar`. Separação de
  deveres enforçada (gate_independent_review).

### Corrigido
- (1.8.3) gate de validação aceitava critério desmarcado — corrigido e agora com
  gates de teste e revisão empilhados no fechamento.
## [1.8.3] — 2026-07-01 (correção crítica do gate de validação + roadmap SOTA)

### Corrigido
- **BUG CRÍTICO:** `gate_arquiteto_validated` usava o regex `- [[x ]]`, que casava
  também `- [ ]` (desmarcado) — uma feature podia FECHAR com todos os critérios de
  aceite em aberto, anulando o Art. 4 da Constituição. Agora exige ≥1 `[x]` e nenhum
  `[ ]` sem uma linha `WAIVER: <motivo>` explícita. Teste de regressão adicionado.

### Adicionado
- **docs/ROADMAP_SOTA.md** — auditoria multi-agente do mad contra o estado da arte
  mundial (11 quick wins, 6 big bets, 10 pontos já classe mundial). Guia de execução.
## [1.8.2] — 2026-07-01

### Mudado
- **/mad-audit vira gate DURO**: não se vai ao ar (PRE_RELEASE → PILOTO) sem a
  auditoria de coerência (reports/audits/*.md). Era a única peça "guardião"; agora
  é enforçada. Constituição Art. 1 fechada de ponta a ponta.
## [1.8.1] — 2026-07-01 (constituição composta + coerência contínua)

### Mudado
- **Constituição reescrita e composta com critério**: um artigo só entra se for
  ENFORÇADO (hook impede) ou VERIFICÁVEL (auditável) — regra sem dente não é
  constituição, é desejo. 10 artigos, cada um declara COMO é garantido (fonte única
  da verdade, rastreabilidade, processo, verificar antes de pronto, autoridade humana,
  blast radius, decanting, segredos, transparência, escopo explícito) + cláusulas
  condicionais (LGPD, compliance, regras de domínio).

### Adicionado
- **/mad-audit** — auditoria de COERÊNCIA: um revisor (docs-writer/qa) lê spec+docs+
  código e aponta divergências reais; o Arquiteto corrige no mesmo ciclo. Recomendada
  antes do pré-release.
- **/mad-doctor**: check de FRESCOR — avisa quando o código está mais novo que a doc
  (>1h), sinal de que a sincronia ficou pra trás.
## [1.8.0] — 2026-07-01 (Constituição + sincronia doc↔código garantida)

### Adicionado
- **docs/CONSTITUICAO.md** — regras inegociáveis do projeto. Art. 1: código e
  documentação andam JUNTOS; nenhuma feature fecha com doc desatualizado; o
  Arquiteto é o guardião. Criada no init, injetada no contexto do Arquiteto toda sessão.
- **Gate de fechamento `docs_synced`** (garantia de máquina, não sugestão): uma
  feature NÃO fecha (nem vai pra aprovação) sem `reports/feature-<NNN>/docs-sync.md`
  provando (a) spec atualizada pro as-built, (b) docs vivos afetados atualizados,
  (c) a decisão real. O hook/`mad_phase next` bloqueia. Resolve o "spec envelhece
  enquanto o código anda".
- **/mad-doctor**: seção "Constituição & docs" — avisa features concluídas sem
  docs-sync e ausência da constituição.

### Mudado
- Fechamento de feature grava no `DECISOES.md` a decisão REAL (do docs-sync), não um toco.
- Arquiteto, skill e injeção do SessionStart reforçam o dever de guardião da sincronia.
## [1.7.0] — 2026-07-01 (mapa de workflow + 20 skins + fullscreen + atividade do Arquiteto)

### Adicionado
- **Mapa do Workflow educativo** no topo do painel: 7 fases em ciclo com nome/ícone
  didáticos, "você está aqui" pulsante, setas com a CONDIÇÃO de cada caminho e as
  bifurcações, sub-loop de "Construindo" expandido, e painel que explica cada fase
  (o que é, o que faz avançar, pra onde pode ir). Backend: `workflow.phase_guide()`.
- **20 design systems (skins) num dropdown** — visionOS, Suíço, Brutalismo, Neo-brutal,
  Glass, Neumorfismo, Material 3, Terminal, Editorial, Bauhaus, Memphis, Cyberpunk,
  Clay, Skeuomórfico, Dark IDE, Minimal, Win98, Bloomberg, Duolingo, Desenhado à mão.
  1 arquivo CSS por skin, contrato de tema documentado.
- **Card do agente clicável → tela cheia** (stream completo, Esc/fundo fecham, foco).
- **Atividade do próprio Arquiteto visível**: a sessão principal é atribuída ao
  `arquiteto` (post-otel-emit) e ele "acende a pensar" ao receber um pedido
  (UserPromptSubmit).

### Mudado
- Stream por agente e feed com detalhe legível por tool (Read/Edit/Bash…).
## [1.6.0] — 2026-07-01 (stream por agente + avatares humanizados + uso, não $)

### Adicionado
- **Stream por agente (estilo tmux).** Cada agente tem um mini-terminal no card
  mostrando ao vivo o texto real que produz (say/Read/Edit/Bash/decanting…),
  colorido por tipo. Vários agentes visíveis = dá pra ver o time trabalhando EM
  PARALELO, cada um no seu terminal. Backend: `agents[].stream` no snapshot.
- **Avatares humanizados + escolha.** 11 mascotes calorosos em `assets/avatars-human/`
  + botão na topbar pra alternar "🙂 personagens" ⇄ "⬡ ícones" (padrão personagens).
  Basta soltar PNGs próprios na pasta para usar imagens.

### Mudado (correção importante)
- **Custo em $ → USO em tokens.** O mad roda dentro da assinatura (Agent tool nativo,
  sem claude -p / API paga), então NÃO há custo em dólar. Padrão `[budget].mode=
  "subscription"`: painel mostra "uso (tokens)", sem "$" nem budget em dólar. A guarda
  contra loop virou teto de tokens/dia + circuit breaker. "$" só em `mode="paid_api"`.

## [1.5.0] — 2026-07-01 (aja por padrão + observabilidade que abre sozinha)

### Adicionado
- **Painel abre sozinho.** Hook SessionStart `session-start-dashboard.py` sobe o
  dashboard e mostra o link a cada sessão, sem o usuário pedir (opt-out via
  `[dashboard].auto_start=false`). Observabilidade é item central: dá pra ver os
  assistentes trabalhando ao vivo.
- **Dashboard reformado** — bonito e observável: etapa atual em linguagem humana (com
  trilha de fases), personagens vivos por status, feed de atividade ao vivo, métricas
  com barras. Nunca mostra nomes técnicos na tela.

### Mudado
- **Aja por padrão, não fique ocioso.** O usuário leigo só testa o resultado; não
  microgerencia. O sistema age e comunica (chat + painel), sem parar esperando
  resposta. Só para em bifurcação CRÍTICA. Irreversível também flui por padrão
  (`[workflow].confirm_irreversible=false`); guardrails catastróficos seguem duros.

## [1.4.0] — 2026-07-01 (full auto + narração fluida)

### Mudado
- **Full auto — não pausa mais.** O Arquiteto não pergunta "continuar ou pausar?" ao
  fim de etapa. O loop flui; só para em decisão real de conteúdo, algo irreversível,
  ou pausa explícita do usuário. **Specs reversíveis fluem direto pra construção**
  (sem aprovação manual); só o irreversível pede o humano.
- **Narração fluida, por resultado, não técnica.** Nunca despeja o interno ("Estado:
  executando", "Agent tool liberado", "sub-fase"); fala como gente. Detalhe técnico
  vai em bloco recolhível `<details>`, só pra quem quer.
- **Não some em atividade longa:** avisa que leva tempo, aponta o painel ao vivo, dá
  sinais de vida entre passos, volta caloroso ao terminar.

## [1.3.5] — 2026-06-30 (o Arquiteto conduz; o usuário só conversa)

### Mudado
- **O usuário não roda comandos de processo.** Nada de `/mad-phase approve-spec` ou
  "qual a próxima fase". O Arquiteto CONDUZ: faz as perguntas, apresenta o que precisa
  de decisão como **artefato pra olhar** (arquivo/wireframe, não muro de texto),
  aceita feedback (texto/anotação/áudio via `mad.py voice`), ajusta, e quando o
  usuário concorda em linguagem natural, **ele mesmo** roda a mecânica (approve-spec
  etc.) por baixo. Os `/mad-phase-*` viram atalho opcional para avançado.
- Regra cravada no arquiteto, na skill e na injeção do SessionStart.

## [1.3.4] — 2026-06-30

### Mudado
- Default de linguagem explícito: **assuma que o usuário é leigo** (se não sinalizar o
  contrário). Fala simples por padrão; só sobe pra técnico com sinal claro. Na dúvida,
  simples. Ajustado na skill, arquiteto, /mad-init e injeção do SessionStart.

## [1.3.3] — 2026-06-30 (linguagem ADAPTATIVA, não fixa)

### Mudado
- Correção do registro de linguagem: não é "nunca jargão" — é **ler o usuário e
  adaptar**. Padrão simples (público inclui leigos); mas com usuário técnico, sobe o
  registro (fases, tokens, arquitetura). Não infantiliza sênior nem afoga leigo. É a
  dança do discovery aplicada à linguagem. Ajustado na skill, no arquiteto, no
  /mad-init e na injeção do SessionStart.

## [1.3.2] — 2026-06-30 (linguagem humana, zero jargão)

### Mudado
- **Camada de linguagem para leigos.** O usuário nunca mais vê os nomes técnicos das
  fases (DISCOVERY/ESPEC_V1/SETUP_TIME/LOOP_FEATURES/…). Tudo é traduzido para o que
  ele faz: entender a ideia → combinar o que construir → montar o time (com discussão
  de custo/tokens) → acompanhar a construção → testar/validar → recomeçar.
- `/mad-init`, `/mad-phase status`, a injeção do SessionStart, a skill mad-workflow e
  o arquiteto ganham **regra inegociável de "fale como gente"**. A cascata de adoção
  pergunta "onde você sente que está?" (a/b/c/d) em vez de pedir o nome da fase.
- Mapa fase→humano em `workflow.py` (PHASE_HUMAN/SUBPHASE_HUMAN).

## [1.3.1] — 2026-06-30

### Adicionado
- **Auto-spawn de especialistas na adoção** (`/mad-init` cascata, passo adopt): ao
  adotar um projeto com trabalho prévio, o mad detecta o backlog (docs/BACKLOG_V1.md,
  docs_projeto/tecnico/06_backlog_v1.md, etc.), **habilita automaticamente** os
  especialistas mencionados (campo `**Especialista:**`) e **avança a fase** conforme
  o que já está pronto — podendo ir direto pra LOOP_FEATURES com a 1ª feature ativa,
  sem exigir `/mad-enable` manual. Especialista inexistente → aviso, sem falhar;
  arquiteto sempre habilitado; idempotente.

## [1.3.0] — 2026-06-30 (Workflow State Machine)

> ⚠️ **MUDANÇA SIGNIFICATIVA NO WORKFLOW.** O processo do projeto deixa de ser
> prosa (sugestão) e vira uma **state machine hardcoded imposta por hooks**. O
> Arquiteto NÃO consegue mais pular fases. Corrige o buraco estrutural da v1.2.

### Adicionado
- **State machine** (`scripts/workflow.py`): 7 fases (BOOTSTRAP→…→PILOTO) +
  sub-máquina por feature, com gates puros e testáveis.
- **Hooks de enforcement**: `session-start-inject-state.py` (injeta o estado no
  contexto a cada sessão), `pre-workflow-gate.py` (BLOQUEIA tool call fora de
  estado — fail-closed), `post-decanting-update-state.py` (avança sub-fase ao
  decantar).
- **Comandos** `/mad-phase status|next|next-phase|approve-spec|approve-merge|
  rework|rollback|emergency-bypass` — única forma legítima de avançar.
- **`/mad-init` em cascata** (`scripts/mad_init.py`): idempotente e context-aware —
  RETOMA / MIGRA (v1.2) / ADOTA (trabalho prévio) / CRIA do zero.
- **Migração** `scripts/migrate_v1_3.py` + `/mad-migrate-to-v1_3` (backup + infere
  fase + instala hooks, preserva memória).
- **Logs de auditoria** `logs/workflow.jsonl` (sanitizado, append-only).
- Dashboard: banner de fase; doctor: seção de integridade do workflow.

### Mudado (breaking)
- Skill `mad-workflow` **reescrita** como state machine.
- `agents/arquiteto.md`: bloco de aviso da state machine no topo.

### Migração
Rode `/mad-init` — ele detecta e migra/adota automaticamente. Ver
`docs/MIGRATING_TO_V1_3.md`.

## [1.2.0] — 2026-06-30 (Tier 3)

### Adicionado
- **4 agentes Tier 3**: `llm-prompt` (design/tuning de prompts, regressão),
  `mobile-dev` (PWA/responsivo/Capacitor), `asset-designer` (sprites/ícones/paletas),
  `security-auditor` (OWASP, secrets, supply chain — opus, revisor não-implementador).
- **Notificações** (`/mad-notify`, `scripts/notify.py`): Telegram + Slack via stdlib,
  opt-in por `[notify]`/env vars.
- **A2A Agent Card** (`/mad-a2a`, `scripts/a2a.py`): gera card compatível com A2A a
  partir do `identity.md`.
- **Voz local** (`/mad-voice`, `scripts/voice.py`): transcrição via faster-whisper
  (opt-in, 100% local).
- **Docker** (`Dockerfile`, `.dockerignore`) + **devcontainer** para Codespaces.
- Config: `[thinking]`, `[notify]`, `[voice]`, `[models]` (Ollama roadmap) no toml.

### Dashboard polish (Tier 2)
- Drag-drop reorder, filtros (todos/só working/esconder sleeping), pin no topo,
  sons WebAudio em eventos. Tudo persistido, zero deps.

## [1.1.0] — 2026-06-30 (Tier 2)

### Adicionado
- **4 agentes Tier 2**: `dba` (schema/migrations/índices/backup), `frontend-dev`
  (UI/UX, acessibilidade, testa no dev server), `devops-installer` (instalação/CI/
  deploy — único instalador), `docs-writer` (README/USO/CHANGELOG, tom direto).
- **Migração do v0.2**: `/mad-migrate-from-v02` (backup obrigatório + split
  heurístico do `MEMORY.md` nos arquivos de memória do mad) e `/mad-migrate-agent`
  (migração gradual, um agente por vez).
- Discovery profundo (`mad-discovery`) ganhou a guarda "explore antes de perguntar"
  (self-serve) e "não adivinhe o propósito pelo nome da pasta".

### Mudado
- Distribuição via hub único `giordanorec/ai-coding-tools` (catálogo de todos os
  plugins do Giordano), em vez de marketplace solo.

## [1.0.0] — 2026-06-27 (Tier 1)

### Adicionado
- Orquestração multi-agente em **modo decanting nativo** (Agent tool, sem `claude -p`).
- 3 agentes: `arquiteto`, `pipeline-dev`, `qa-tester`.
- Skill `mad-discovery` (postura + rigor) e `mad-workflow`.
- 10 slash commands `/mad-*`; trust ladder; guardrails por blast radius.
- Budget enforced + circuit breaker; dashboard HTML+WS+PWA; OpenTelemetry GenAI.
- CLI Python cross-platform (dep única `websockets`); 54 testes.
