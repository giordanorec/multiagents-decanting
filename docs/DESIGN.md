# DESIGN — mad (MultiAgent Decanting)

> Documento de arquitetura definitivo do plugin `mad`, versão de referência
> **1.15.0**. Destina-se a ser a fonte de um artigo defendendo o design. Denso por
> intenção: cada seção traz o racional, o mecanismo concreto (com `arquivo:linha`) e
> os trade-offs. Escrito em PT-BR. Sintetiza `CHANGELOG.md`, `docs/CONSTITUICAO.md`
> (template em `templates/CONSTITUICAO.md`), `docs/ROADMAP_SOTA.md`,
> `docs/adr/ADR-001-motor-dag-paralelo.md`, os módulos em `scripts/`, os agentes em
> `agents/`, as skills em `skills/` e os hooks em `hooks/`.

---

## 1. Resumo e tese

`mad` é um plugin de orquestração multi-agente para o Claude Code. Um único agente
coordenador — o **Arquiteto** — conduz um projeto de software do zero ("entender a
ideia") até o piloto ("no ar"), delegando trabalho a especialistas (pipeline-dev,
frontend-dev, dba, qa-tester, security-auditor, devops-installer, docs-writer,
llm-prompt, mobile-dev, asset-designer) via a **Agent tool nativa** do Claude Code —
sem `claude -p`, sem processos em background, dentro da assinatura.

A tese central tem duas metades, e o resto do documento é a demonstração de que o
código a honra:

1. **O determinístico governa o fluxo; o LLM só age nos nós.** O *processo* do
   projeto — em que fase estamos, o que pode rodar agora, quando uma feature fecha —
   é uma **máquina de estados hardcoded** (`scripts/workflow.py`), não a
   boa-vontade de um LLM seguindo instruções em prosa. O LLM decide *conteúdo*
   (o que escrever, como resolver); a máquina decide *o que é permitido*.

2. **Prosa é sugestão; hook é garantia.** Qualquer regra que exista apenas como
   texto no system prompt de um agente é, na prática, opcional — o LLM pode ignorá-la
   sob pressão de contexto, injeção ou simples deriva. `mad` promove cada regra que
   importa a um **mecanismo executável**: um *gate* (função pura que lê o filesystem
   e retorna `(bool, msg)`) ou um *hook* `PreToolUse`/`SessionStart` que **bloqueia**
   a tool call (exit 2), em vez de pedir educadamente para o agente não fazer.

O nome resume o segundo pilar operacional: **decanting** é o protocolo obrigatório de
externalizar aprendizado para arquivos ao fim de cada feature. A sessão é memória de
trabalho descartável; a fonte da verdade são `memory/<agente>/`, `docs/`, `reports/`
e o git. "Sessão fresca" deixa de significar "amnésia".

A consequência de design: `mad` troca autonomia irrestrita por **governança
determinística**. Onde sistemas concorrentes apostam em um agente mais esperto que
"lembra" de seguir o processo, `mad` aposta em um processo que o agente **não
consegue** furar. É a mesma lição que a indústria aprendeu com workflows duráveis
(Temporal): coloque o determinismo exatamente onde o custo de errar é alto.

---

## 2. O problema — por que orquestração multi-agente falha

Times de agentes falham de maneiras recorrentes e previsíveis. `mad` foi desenhado
contra cada uma delas, a partir da experiência concreta do plugin antecessor do
próprio autor (`multiagentes-giordano`, aqui chamado **v0.2**).

**a) Processo como prosa — o agente pula etapas.** Na v0.2 o "processo" (Discovery →
Especificação → time → implementação) vivia como texto no `CLAUDE.md`. Nada impedia o
Arquiteto de despachar um especialista antes de haver spec, ou de declarar uma
feature "pronta" sem verificação. Instrução em prosa é uma preferência estatística do
modelo, não uma invariante. Este é o **buraco estrutural** que `mad` v1.3 fechou ao
converter o processo em máquina de estados imposta por hooks (CHANGELOG 1.3.0).

**b) O bug real de "funciona" que não funciona.** A v0.2 paralelizava lançando
processos `claude -p` em background (`spawn.sh`/`drive.sh`), com IPC por arquivo. Um
sintoma concreto e documentado: sem `--permission-mode bypassPermissions`, o agente
headless produzia a resposta completa mas **não gravava arquivo nenhum** — ficava
preso num prompt de permissão que nunca chegava, e o trabalho aparecia no log só como
"bloqueador". O sistema reportava progresso que não existia. `mad` elimina a classe
inteira ao usar a Agent tool nativa (sem processos, sem IPC por arquivo, sem gestão
manual de sessão) e ao tornar a **observabilidade verdadeira** (§8): estado e ações
são derivados de artefatos reais, não de auto-relato.

**c) Spec que envelhece / teste que é prosa.** O clássico "a documentação mente":
a spec descreve a intenção inicial, o código diverge, e ninguém reconcilia. Pior: o
"teste" é uma frase que o LLM escreve no report ("pytest → todos passaram") sem nunca
rodar nada — a verificação é ficção auto-reportada (ROADMAP_SOTA quick-win #2). `mad`
responde com o gate de docs-sync (Art. 1) e o gate de teste **executável** (§5).

**d) Skill rot / amnésia entre sessões.** Sem externalização disciplinada, cada nova
sessão recomeça do zero e o conhecimento tácito evapora. O decanting obrigatório
(Art. 7) e a memória estruturada por agente (§3) atacam isso.

**e) Agentes com privilégio total.** Na ausência de allowlist, todo subagente herda
**todas** as ferramentas — o qa-tester "não altera produção" só por promessa em
prosa, mas tecnicamente pode `Write`, `Edit`, `Bash`, `git push` (ROADMAP_SOTA
quick-win #3). `mad` aplica least-privilege nativo por papel (§6).

**f) Parada e ociosidade.** Um Arquiteto que pergunta "continuar?" a cada micro-passo
trava o usuário leigo, que não quer microgerenciar. `mad` opera em **full auto**: age
por padrão e só para em bifurcação genuinamente crítica ou ação catastrófica
(CHANGELOG 1.4.0/1.5.0; `agents/arquiteto.md`).

**g) Jargão para leigo.** Expor "DISCOVERY", "gate", "sub-fase spec_validada" a um
usuário não-técnico é ruído que afoga. `mad` mantém uma **camada de linguagem
adaptativa** (assume leigo por padrão, sobe o registro só com sinal claro), com
mapa técnico→humano em `workflow.py` (`PHASE_HUMAN`, `SUBPHASE_HUMAN`).

---

## 3. Arquitetura

### 3.1 Visão geral

O sistema tem quatro camadas, da mais dura para a mais mole:

1. **Máquina de estados** (`scripts/workflow.py`) — a verdade sobre o processo.
2. **Enforcement por hooks** (`hooks/*`) — impõe a máquina no runtime do Claude Code.
3. **Agentes** (`agents/*.md`) — os nós de LLM que produzem conteúdo, com
   least-privilege e protocolos de boot/decanting.
4. **Memória e docs** (`memory/`, `docs/`, `reports/`, `specs/`) — a fonte da verdade
   persistente, alimentada pelo decanting.

O ponto de contato humano é **exclusivamente o Arquiteto**. Especialistas nunca
falam com o usuário; comunicam-se com o Arquiteto por arquivos (`specs/` de ida,
`reports/` de volta). Esse funil único é o que torna a governança tratável: há um só
lugar onde decisões de peso passam.

### 3.2 A máquina de fases

Sete fases em transição linear (`workflow.py:28`), com uma reentrada de PILOTO para
LOOP_FEATURES em extensões:

```
BOOTSTRAP → DISCOVERY → ESPEC_V1 → SETUP_TIME → LOOP_FEATURES ⇄ PRE_RELEASE → PILOTO
```

Cada fase tem um **gate de saída** (`PHASE_GATES`, `workflow.py:522`): uma função
pura `gate_*(root) -> (bool, msg)` que lê o filesystem e decide se a transição é
permitida. Exemplos:

- `gate_discovery_done` exige `docs/00_OBJETIVO.md` com >200 chars e ≥3 decisões
  datadas em `docs/DECISOES.md` (`workflow.py:317`).
- `gate_espec_done` exige `docs/BACKLOG_V1.md` com ≥1 feature `F-NNN`, valida que as
  dependências declaradas existem e **rejeita ciclos** via DFS (`workflow.py:328`).
- `gate_pilot_ready` exige backtesting **e** ao menos uma auditoria de coerência em
  `reports/audits/` — o `/mad-audit` como gate duro (`workflow.py:509`).

A transição só acontece por `mad_phase.py` (backend dos `/mad-phase-*`), que valida o
gate, muda o estado atomicamente e loga o evento (`advance_phase`, `workflow.py:762`).

### 3.3 A sub-máquina por feature

Dentro de LOOP_FEATURES, cada feature percorre uma sub-máquina própria
(`SUBPHASES`, `workflow.py:36`):

```
spec_pendente → spec_validada → executando → validando → [aprovacao_humano] → concluida
```

A sub-fase determina o que a Agent tool pode fazer. A leitura política vive em
`WorkflowState.decide_tool` (`workflow.py:637`): por exemplo, em `spec_validada` o
despacho de especialista é negado até haver aprovação humana; em `executando` só o
`subagent_type` atribuído àquela feature é liberado; em `aprovacao_humano` **toda
escrita** é bloqueada até `approve-merge`.

### 3.4 Gates como funções puras, fail-closed

O design deliberado dos gates: **funções puras** que só leem o filesystem e retornam
`(bool, msg)`, sem efeitos colaterais e sem estado oculto. Isso as torna testáveis
isoladamente e determinísticas — o análogo correto ao "workflow determinístico" do
Temporal, e, segundo a auto-auditoria, o maior ativo do sistema (ROADMAP_SOTA §"onde
já é SOTA"). A postura padrão é **fail-closed**: em dúvida ou corrupção, bloqueia
(o docstring do módulo o crava: "Fail-closed: em dúvida, bloqueia", `workflow.py:10`).

### 3.5 Enforcement por hooks

A máquina só tem dentes porque hooks a impõem no runtime:

- `session-start-inject-state.py` (SessionStart) injeta no contexto do Arquiteto, a
  cada sessão, a fase atual, o item corrente, o **próximo passo obrigatório** e as
  ações permitidas/bloqueadas — em linguagem humana e técnica. O LLM não tem como
  "esquecer" a fase; ela é injeção determinística, não memória do modelo.
- `pre-workflow-gate.py` (PreToolUse) chama `decide_tool` e **bloqueia** (exit 2 +
  `permissionDecision: deny`) qualquer tool call fora do estado. É fail-closed: se
  `workflow.py` faltar ou o estado estiver corrompido, despacho e `git push` são
  negados por segurança (`pre-workflow-gate.py:73`).
- `post-decanting-update-state.py` (PostToolUse) avança a sub-fase quando o
  especialista decanta.

### 3.6 O Arquiteto como orquestrador

O Arquiteto (`agents/arquiteto.md`, `model: opus`) tem quatro eixos — Decidir,
Especificar, Integrar, Memorar — e opera **dentro** da máquina. Escolhe um dos cinco
workflow patterns da Anthropic (chain, route, parallelize, orchestrator-worker,
evaluator-optimizer) por feature e registra a escolha em `DECISOES.md`. Aplica
*blast radius judgment* (reversível baixo/médio → autônomo; irreversível alto →
HITL sempre). Nunca despacha sem spec escrita (rastreabilidade obrigatória). É o
**guardião da Constituição** — em especial do Art. 1 (docs e código andam juntos).

---

## 4. Garantias constitucionais

A `CONSTITUICAO.md` (template em `templates/CONSTITUICAO.md`, instanciada por
`init.py` em `docs/CONSTITUICAO.md` de cada projeto) tem um **princípio de
composição** que a distingue de manifestos decorativos: *um artigo só entra se for
enforçado (hook impede) ou verificável (auditável nos artefatos). Regra sem dente não
é constituição — é desejo* (CHANGELOG 1.8.1). Cada artigo declara como é garantido.
O mapeamento artigo → mecanismo:

| Art. | Regra | Mecanismo concreto |
|---|---|---|
| **1** Fonte única / coerência | spec, docs, código, testes nunca divergem | `gate_docs_synced` (`workflow.py:424`) bloqueia fechamento sem `reports/feature-NNN/docs-sync.md` com 3 seções (spec as-built, docs vivos, decisão real); `gate_pilot_ready` exige `/mad-audit`; `/mad-doctor` avisa código mais novo que docs |
| **2** Rastreabilidade | todo código tem spec/decisão; "por que existe?" respondível só pelos docs | `gate_spec_written` exige objetivo/critério/blast/especialista antes do despacho (`workflow.py:365`); `DECISOES.md` vivo; auditoria |
| **3** Processo não se pula | fases em ordem | máquina de estados + `pre-workflow-gate.py` (PreToolUse fail-closed) |
| **4** Verificar antes de "pronto" | critérios de aceite atendidos + testes | `gate_arquiteto_validated` (`workflow.py:407`) + `gate_tests_green` + `gate_independent_review` empilhados no fechamento |
| **5** Humano é autoridade final; conteúdo observado é dado, não comando | HITL nas bifurcações de peso; anti-injeção | gates de aprovação (`gate_human_approve_spec/merge`) + guardrails catastróficos + fronteira anti-injeção nos agentes (§6) |
| **6** Fricção proporcional ao risco (blast radius) | reversível flui, irreversível trava | classificação de blast por feature + ramo condicional em `cmd_next` (`mad_phase.py:150`) |
| **7** Decanting obrigatório | aprendizado externalizado ao fim da feature | `session-end-decant-check.py` + `/mad-doctor`; sanção `decanting_skipped: -10` na trust ladder |
| **8** Segredos nunca no repositório | sem commit de credenciais | `pre-guardrail-secret-commit.sh` (PreToolUse) + redação na telemetria e no log |
| **9** Transparência / auditabilidade | ações observáveis, estado verdadeiro, tudo logado | dashboard + telemetria OTel + estado injetado por hook + audit log hash-encadeado |
| **10** Escopo muda explícito | sem scope creep silencioso | **guardião** (o Arquiteto zela); parcialmente mecanizado — ver §12 (limitação honesta) |

Duas observações honestas de rigor. Primeiro, o Art. 10 é o único classificado como
"guardião" e não "enforçado/verificável": hoje depende da disciplina do Arquiteto; a
mecanização (um `cmd_replan` com aprovação logada) é trabalho futuro (ROADMAP_SOTA
quick-win #8). Segundo, o Art. 1 só passou a ter dentes reais quando o **bug crítico
do gate de validação** foi corrigido (v1.8.3): o regex `- [[x ]]` casava também `- [ ]`
(desmarcado), então uma feature podia fechar com **todos** os critérios de aceite em
aberto — o Art. 4 virava decoração. A correção (`gate_arquiteto_validated`,
`workflow.py:413`) agora exige ≥1 `[x]`, nenhum `[ ]` sem uma linha `WAIVER:`
explícita, e tem teste de regressão. É o exemplo canônico de "regra sem enforcement
correto é ilusão de garantia".

---

## 5. Verificação

`mad` empilha quatro gates no fechamento de cada feature (na sub-fase `validando`,
orquestrados por `cmd_next`, `mad_phase.py:123`), nessa ordem, cada um bloqueante:

1. **Critérios de aceite** — `gate_arquiteto_validated`: `reports/feature-NNN/
   arquiteto-merge.md` com ≥1 `[x]` e nenhum `[ ]` sem `WAIVER:`.

2. **Teste REAL como ground-truth** — `gate_tests_green` (`workflow.py:446`) lê
   `reports/feature-NNN/verify.json`, gerado por `scripts/verify.py`, que roda de
   verdade `test_cmd`/`lint_cmd`/`typecheck_cmd` da seção `[verify]` do toml via
   subprocess e grava `returncode`/`passed`/`tail`. Se `test_cmd` está setado, a
   feature **não fecha** sem `all_passed=true`. É o fim de "teste é prosa que o LLM
   escreve" (CHANGELOG 1.9.0). Projetos sem testes configurados passam (o gate é
   no-op quando nada está configurado) — decisão pragmática para não travar pilotos.

3. **Revisor independente (autor ≠ verificador)** — `gate_independent_review`
   (`workflow.py:465`): a feature não fecha sem que um agente **diferente** do que a
   construiu (`agent_assigned`) escreva um `reports/feature-NNN/<agente>.md` com a
   linha parseável `VEREDITO: aprovar`. É separação de deveres mecanizada — o
   princípio central de verificação, e o loop evaluator-optimizer que antes só existia
   como sugestão em prosa.

4. **Docs-sync (Art. 1)** — `gate_docs_synced`: exige o `docs-sync.md` com as três
   seções e um mínimo de substância (≥120 chars). No fechamento, `_close_feature`
   (`mad_phase.py:278`) copia a decisão real do docs-sync para o `DECISOES.md` — não
   um toco genérico.

Acima do nível da feature, dois mecanismos:

- **`/mad-audit`** — auditoria de coerência: um revisor (docs-writer/qa) lê spec +
  docs + código e aponta divergências reais, que o Arquiteto corrige no mesmo ciclo.
  Virou **gate duro** de ir ao ar (`gate_pilot_ready` exige `reports/audits/*.md`,
  `workflow.py:514`) — fechando o Art. 1 de ponta a ponta.
- **Dead-letter** — o teto de rework (`[verify].max_rework`, default 3): após N
  reworks, `cmd_rework` (`mad_phase.py:214`) escala a feature para o humano decidir
  (aprovar, replanejar, descartar) em vez de ciclar infinitamente. Loop de rework sem
  fim é uma falha de confiabilidade tratada como estado explícito e logado.

---

## 6. Segurança e governança

O modelo de segurança é **defesa em profundidade**: least-privilege, escopo de
escrita, HITL proporcional, guardrails catastróficos independentes de fase,
audit-log à prova de adulteração e fronteira anti-injeção.

**Least-privilege por agente (blast radius de capacidade).** Os 11 agentes declaram
`tools:` (allowlist) no frontmatter — mecanismo **nativo** do Claude Code, antes
desperdiçado (CHANGELOG 1.10.0). Só o Arquiteto tem `Agent`/`Task` (só ele despacha).
qa-tester, security-auditor, docs-writer e llm-prompt **não têm `Bash` nem `Edit` de
código** (`Read, Grep, Glob, Bash?, Write` — o security-auditor lê tudo mas propõe via
report, nunca altera produção). devops-installer é o único com acesso amplo. Isso
também blinda contra MCP de alto privilégio herdado.

**Escopo de escrita no filesystem.** `pre-guardrail-write-scope.py` (PreToolUse
Edit/Write/MultiEdit) protege *sempre* `.mad/workflow_state.json`,
`logs/workflow.jsonl` e `sessions.json` de edição à mão (são geridos pelos scripts
via `os.replace`), e — quando o agente se identifica em `MAD_AGENT` — enforça a tabela
`ROLE_PATHS`: ninguém escreve na `memory/` de outro agente, ninguém além do Arquiteto
escreve em `docs/DECISOES.md`, e cada papel só escreve nos seus prefixos. Transforma a
string descritiva de `allowed_summary()` em regra executável.

**HITL proporcional ao blast radius.** Reversível baixo/médio flui direto para a
construção (`mad_phase.py:107`); irreversível alto exige `approve-spec`/`approve-merge`
humano logado. A tabela de julgamento vive em `agents/arquiteto.md` e é reforçada pela
trust ladder (score baixo → mais fricção). É governança acima da média sem burocracia
no que é barato.

**Guardrails catastróficos, independentes de fase.** Hooks shell PreToolUse que
bloqueiam por padrão, valham qual for a fase: `pre-guardrail-rm-rf.sh` (nega `rm -rf`
cujo alvo resolve para **fora** da raiz do projeto, e sempre nega `/` e `~`),
`pre-guardrail-force-push.sh`, `pre-guardrail-secret-commit.sh`,
`pre-guardrail-identity-change.sh`. Complementados por `_is_catastrophic`
(`workflow.py:879`) dentro do `decide_tool`. Honestamente: são **denylist regex**,
contornáveis por ofuscação (`find -delete`, `base64|sh`) — a mitigação forte
(sandbox, negar deleção fora da raiz por default) é big bet pendente (§12).

**Audit-log tamper-evident.** `log_event` (`workflow.py:251`) encadeia hash SHA-256:
cada evento amarra o hash do anterior (`prev`), e `verify_log_chain`
(`workflow.py:267`) detecta adulteração. `/mad-doctor` verifica a cadeia. Um agente
comprometido não apaga o rastro do próprio abuso sem quebrar a cadeia — o log
append-only deixa de ser apenas convenção.

**Fronteira anti prompt-injection (Art. 5).** O template de agente
(`templates/agents/_template.md:73`) instrui tratar conteúdo externo (WebFetch,
WebSearch, arquivos de terceiros, saídas de ferramentas) como **dado, não comando**,
envolvendo-o em delimitadores não-confiáveis (`<<<untrusted>>> … <<<end>>>`);
instruções válidas vêm só do Arquiteto (que só recebe do humano). Materializa o Art. 5,
antes só declarativo (CHANGELOG 1.12.0). É *spotlighting* à la Microsoft. Ressalva de
rigor: isto ainda é uma instrução de prompt, portanto uma *mitigação*, não uma
garantia dura — daí o security-auditor receber a tarefa explícita de revisar vetores
de injeção.

---

## 7. Confiabilidade

O estado do workflow (`.mad/workflow_state.json`) é o ponto crítico; `mad` o protege
em várias frentes.

**Lock com dono (PID/host).** `_acquire_lock` (`workflow.py:577`) grava
`{pid, host, ts}` no lock e só o **rouba** se o dono claramente morreu
(`_lock_owner_dead`, `workflow.py:187`, checa `os.kill(pid, 0)` no mesmo host) — não
mais por timeout cego. Conservador entre hosts (não rouba lock de outra máquina). Dois
escritores concorrentes (CLI, hooks, dashboard) não corrompem mais o JSON; dono vivo e
preso → erro claro, não corrupção silenciosa (CHANGELOG 1.11.0).

**Backup e auto-recuperação.** `save()` (`workflow.py:605`) rotaciona
`workflow_state.json.bak` antes de sobrescrever; `load()` (`workflow.py:565`) cai no
`.bak` se o principal estiver corrompido ou fora do conjunto de fases válidas. O
estado deixou de ser ponto único de falha. Escrita atômica via `write_json`/
`os.replace`.

**Circuit breaker (ressuscitado).** `resilience.guard` (`resilience.py:127`) abre o
circuito quando `recent_failures` (`resilience.py:94`) conta ≥ N `agent.error`/
`tool.use` com erro numa janela. O breaker era placebo até v1.10: **nenhum**
`agent.error` era emitido. `post-otel-emit.py:154` passou a emitir `agent.error`
quando um despacho de especialista (`Agent`/`Task`) falha, e `recent_failures` conta
também `tool.use` com `tool.outcome == "error"`. Agora funciona de verdade.

**Retry com backoff + jitter.** `resilience.retry` (`resilience.py:31`) faz backoff
exponencial com jitter para I/O de rede do lado Python (ex.: export OTLP). As
retentativas das chamadas de modelo em si são nativas do Claude Code — `mad` não as
reimplementa. Ressalva honesta: o retry ainda não envolve a decisão de re-despacho de
especialista (ROADMAP_SOTA quick-win #5).

**Checkpoint / resume (durable execution).** Uma feature é uma sessão da Agent tool,
tudo-ou-nada; se morre no meio, re-despachar recomeçaria do zero. `mad` v1.14 exige
**decanting incremental**: o especialista anexa checkpoints em
`reports/feature-NNN/progress.jsonl` (append-only) a cada entrega parcial; no
re-despacho o Arquiteto injeta o progresso como "já feito, continue daqui" — resume
sem duplicar (skill `mad-workflow`, passo 3).

---

## 8. Observabilidade

**Trace causal.** `emit_span` (`_utils.py:256`) grava spans OTel-GenAI (subset) em
`logs/otel/<date>.jsonl` carimbando `trace_id` (o id da feature ativa, agrupando o run
multi-agente numa **árvore** por feature), `span_id` por invocação e, opcionalmente,
`parent_span_id`/`duration_ms`. O run deixa de ser eventos flat — vira uma árvore
causal, base do waterfall real (CHANGELOG 1.13.0). Se `OTEL_EXPORTER_OTLP_ENDPOINT`
estiver setado, tenta export OTLP HTTP best-effort (silencioso em falha — telemetria
nunca derruba o fluxo).

**Emissão por hook.** `post-otel-emit.py` (PostToolUse *) emite um span `tool.use`
por tool call concluído, com sanitização de secrets e truncamento de blobs (`content`,
`old_string`... viram `<N chars>`). Atribui a ação ao agente (`MAD_AGENT`, ou
`arquiteto` na sessão principal) e produz um `detail` legível por tipo de tool para o
stream do dashboard.

**Painel ao vivo.** O dashboard (HTML + WebSocket + PWA, `scripts/dashboard_server.py`)
abre sozinho a cada sessão (`session-start-dashboard.py`, opt-out via
`[dashboard].auto_start`). Mostra a fase em **linguagem humana** com trilha de fases,
um **mapa educativo do workflow** (7 fases em ciclo com "você está aqui", condições de
cada caminho, sub-loop de "Construindo"; backend `workflow.phase_guide()`,
`workflow.py:152`), personagens por status, feed de atividade e — o diferencial — um
**stream por agente** estilo tmux: cada agente tem um mini-terminal mostrando o texto
real que produz, colorido por tipo, tornando visível o time trabalhando em paralelo.
20 skins selecionáveis. Nunca exibe nomes técnicos de fase ao usuário.

**Uso em tokens, não dólar.** Como `mad` roda dentro da assinatura (Agent tool nativo,
sem API paga), o padrão `[budget].mode="subscription"` mede **uso em tokens**, não
custo em $ (CHANGELOG 1.6.0). A guarda contra loop é teto de tokens/dia + circuit
breaker; "$" só aparece em `mode="paid_api"`.

Honestidade de rigor: "OTel GenAI" ainda é um JSONL bespoke; o export OTLP não usa o
envelope `resourceSpans/scopeSpans` que um Collector real aceita, e os atributos não
seguem 100% o semconv GenAI. Serialização OTLP correta + ingestão da telemetria nativa
do Claude Code (custo/tokens reais) é big bet pendente (ROADMAP_SOTA big-bet #3).

---

## 9. Motor DAG (IMPLEMENTADO — v1.17, opt-in)

> **Atualização pós-1.15:** o motor DAG foi **implementado** em v1.16–v1.17 (esta
> seção descreve o ponto de partida 1.15). Com `[workflow].engine="dag"`, features
> independentes (deps satisfeitas + paths disjuntos via `Toca:`) rodam **em paralelo**
> (`active_features[]`, `decide_tool` libera N especialistas concorrentes,
> `mad_phase next <F-NNN>` por-feature, fechar feature ativa dependentes). Default
> segue `sequential` até validação em campo. Ver ADR-001 (status IMPLEMENTADO) e
> CHANGELOG v1.15–1.17 para o estado atual.

No ponto de partida (1.15) o motor era **sequencial-escalar**: um único
`active_feature`, backlog linear sem dependências, e o gate em `executando` **amarrava**
a feature a um único `agent_assigned` — a enforcement *ativamente impedia* o
orchestrator-worker paralelo que o próprio Arquiteto prega. O ADR-001 documenta a evolução.

**Fundação já entregue (v1.15).** `parse_backlog` (`workflow.py:814`) extrai
`depende:/deps:` por feature (com a correção de não criar "feature fantasma" a partir
de menção inline de `F-NNN`). `gate_espec_done` valida que as dependências existem e
**rejeita ciclos** por DFS three-color (`has_cycle`, `workflow.py:843`). Os primitivos
`ready_features` (`workflow.py:871`, fronteira topológica: pendentes com todas as
dependências concluídas) e `has_cycle` estão prontos. Tudo retrocompatível: backlog
sem `depende:` = comportamento de hoje.

**O que o motor DAG passa a fazer** (atrás de flag `[workflow].engine =
"sequential"|"dag"`): trocar `active_feature` (escalar) por `active_features` (mapa);
`decide_tool` em `executando` aceita **qualquer** `subagent_type` no conjunto
`especialistas:[]` da spec (rastreando um report por especialista), desde que
identificado por `feature=F-NNN`; fan-in que só avança de LOOP_FEATURES quando a
fronteira **fecha**. Concorrência limitada por `max_parallel_features` (default 3),
amarrado à conversa de custo do SETUP_TIME.

**Resolução de conflitos — três camadas determinísticas:** (1) o **DAG** garante que
tarefas com dependência entre si nunca rodam juntas; (2) **disjunção de paths**: duas
features só paralelizam se o campo `touches:` (paths que a spec declara mexer) não se
sobrepõe — sobreposição serializa mesmo com dependências satisfeitas; (3)
**isolamento + escopo de escrita**: opcionalmente cada feature paralela roda em git
worktree própria (Agent tool `isolation:"worktree"`), e o `pre-guardrail-write-scope`
impede pisar em estado/memória alheios; conflito de merge → rework/decisão humana,
nunca silencioso.

**vs. v0.2.** A v0.2 paralelizava lançando processos `claude -p` em background
(pesado, consumia créditos de API, gestão manual de sessão, IPC por arquivo, sem
governança de dependência/conflito) — spawnava processos ad-hoc. `mad` paraleliza
**pela máquina de estados**: dependency-aware, conflict-guarded, subagentes nativos
(dentro da assinatura), observável no painel. O grafo + gates decidem o que roda
junto; nada de agentes se auto-coordenando ad-hoc.

A migração preserva projetos existentes (backlog antigo = sem dependências; state
escalar migrado para mapa de 1 entrada) e a suíte de testes dupla (ambos os modos)
é pré-requisito de merge. É o maior gap único vs. classe mundial e a aposta
declarada como próxima grande investida.

---

## 10. Comparação com o estado da arte

Baseado na auditoria multi-agente em `docs/ROADMAP_SOTA.md` (8 dimensões pesquisando
o melhor do mundo + auditoria adversarial do próprio plugin).

**vs. Devin / OpenHands (agentes autônomos de dev).** Eles apostam em autonomia
ampla dentro de um runtime isolado (Docker/VM efêmera) com teste + revisor antes de
"pronto". `mad` **iguala** na verificação com dentes (teste executável + revisor
independente + dead-letter) e **difere** na filosofia: menos autonomia, mais
governança determinística por máquina de estados. **Perde** no isolamento de execução
— `mad` roda no host (sandbox é big bet pendente); least-privilege é necessário mas
não suficiente.

**vs. Aider (repo map).** Aider constrói um repo map por tree-sitter + PageRank.
`mad` **perdia** aqui (dependia de "paths explícitos na spec") e fechou parte do gap
integrando o **Serena MCP** (find_symbol/get_symbols_overview/find_referencing_symbols)
como tool padrão dos 5 agentes de código, com fallback gracioso para grep
(CHANGELOG 1.13.0). Aider também tratou primeiro teste verde como ground-truth
(`--auto-test`); `mad` alcançou isso com o gate de testes real.

**vs. LangGraph (DAG + checkpointer).** LangGraph é o padrão de grafo com fan-out/
fan-in e checkpointer para durable execution. `mad` **está atrás** no paralelismo real
(o motor DAG está em fundação, §9) mas **já entregou** o checkpoint/resume por
`progress.jsonl` e compartilha a filosofia central ("determinístico para o fluxo, LLM
só nos nós") — que a auditoria classifica como exatamente a lição de 2025-26.

**vs. CrewAI (times de agentes por prosa).** CrewAI define papéis e tarefas
majoritariamente declarativos. `mad` **difere fundamentalmente**: os papéis têm
enforcement (least-privilege nativo, escopo de escrita, gates), não só descrição. É
a diferença entre "honra" e "garantia".

**vs. Claude Code subagents cru.** `mad` é um *thin wrapper* que usa os subagents
nativos, mas adiciona a camada que falta: máquina de estados, gates, memória
estruturada com decanting, trust ladder, observabilidade e a camada de linguagem para
leigos. Onde os subagents nativos dão o mecanismo, `mad` dá o **método**.

**Onde `mad` já é estado da arte** (auto-auditoria): injeção determinística de estado
por hook (melhor que muitos concorrentes); memória estruturada e persistente por
agente (rivaliza com Letta/MemGPT/Devin na *estrutura* — falta retrieval por
relevância em cima); gates como funções puras fail-closed (análogo ao Temporal);
skill de Discovery com premortem/Mom-Test/saturação (nível de produto sênior); trust
ladder por agente; HITL proporcional ao blast radius; maturidade cross-platform.

---

## 11. DX / plug-and-play

`mad` é deliberadamente **stdlib puro** (Python 3.9+), **zero install** obrigatório: a
única dependência opcional é `websockets`, só para o dashboard. Toda a máquina de
estados, gates, hooks, verificação e telemetria roda sem instalar nada. `mad
bootstrap` dá o setup 1-comando (instala a dep opcional + roda o doctor,
CHANGELOG 1.12.0), atingindo a paridade "add + install + funciona".

**Cross-platform** é eixo maduro (ROADMAP_SOTA): `pathlib`, UTF-8 explícito,
`subprocess` por lista, Windows nativo sem WSL, wrappers `bin/mad{,.bat,.ps1}`, CI
matrix (ubuntu/macos/windows × Python 3.9-3.12), devcontainer para Codespaces.

**Onboarding e operação.** `/mad-init` é idempotente e context-aware (RETOMA / MIGRA
de v1.2 / ADOTA trabalho prévio detectando backlog e auto-spawnando especialistas /
CRIA do zero). `/mad-doctor` é o semáforo verde/amarelo/vermelho de saúde (integridade
do workflow, cadeia do audit log, frescor doc↔código, presença da constituição, Serena
configurado). `/mad-tutorial`, `/mad-explain`, `/mad-migrate-from-v02`. Docker opcional
e **não** pré-requisito — o plugin segue plug-and-play (ADR-001).

Filosofia de DX: o usuário leigo **não roda comandos de processo**. O Arquiteto conduz,
apresenta decisões como artefatos para olhar (não muros de texto), aceita feedback em
linguagem natural (inclusive áudio via `mad.py voice`), e roda a mecânica por baixo.
Full auto por padrão; só para em bifurcação crítica.

---

## 12. Limitações e trabalho futuro

Honestidade acima de bajulação. O que ainda falta:

**Big bets pendentes** (ROADMAP_SOTA):

1. **Motor DAG paralelo completo** (§9) — o maior gap único. A fundação existe
   (dependências, ciclo, fronteira); falta trocar o núcleo escalar por mapa,
   liberar N especialistas em paralelo no `decide_tool`, e o fan-in por fronteira.
   Atrás de flag `engine`, com suíte dupla como gate de merge.

2. **Sandbox de execução isolada.** Tudo roda no host com acesso total; os guardrails
   são denylist regex contornável. Sem isolamento (Docker/devcontainer/bubblewrap por
   agente com Bash), o least-privilege de tools é necessário mas não suficiente. O
   repo já tem Dockerfile/devcontainer; falta o modo `--sandboxed` e uma
   policy-as-code única (`.mad/policy.toml`) em vez de política dispersa em
   `decide_tool` + 4 hooks shell + prosa.

3. **Observabilidade OTel de verdade** (§8): envelope OTLP correto, semconv GenAI,
   ingestão da telemetria nativa do Claude Code (custo/tokens reais em vez da tabela
   `PRICING_USD_PER_MTOK` que envelhece), store SQLite com p50/p95 e replay de trace.

4. **Retrieval por relevância na memória.** A estrutura de memória é SOTA, mas o boot
   do especialista lê `lessons.md` **inteiro** sem ranking (cresce unbounded), e o
   campo `confiança` dos templates é decorativo. Falta BM25/keyword (recency ×
   confiança × relevância, top-k) com injeção determinística por hook PreToolUse(Agent)
   — hoje o especialista só recebe *instrução* de ler o handoff, dependendo de
   obediência do LLM (enquanto o Arquiteto já tem injeção determinística).

5. **MCP server do estado + portabilidade cross-tool.** O MCP é passthrough; o card
   A2A está três majors atrás (v0.1, path errado, capabilities hardcoded, sem servir
   por HTTP). Falta o MCP server `decanting-state` e `mad export` para AGENTS.md.

**Limitações estruturais assumidas:**

- **Art. 10 (scope creep) não é mecanizado** — é guardião soft. Falta `cmd_replan`
  com diff de backlog e aprovação humana logada, e um gate humano na transição
  ESPEC_V1→SETUP_TIME (assinar o roadmap inteiro, o "plan mode").
- **Anti-injeção é mitigação, não garantia** — é instrução de prompt (spotlighting) +
  revisão do security-auditor, não um mecanismo que *detecta* obediência a instrução
  plantada. Um agente que faz WebFetch e obedece viola o Art. 5 sem que nada detecte.
- **Guardrails catastróficos são denylist regex** — contornáveis por ofuscação. A
  postura correta seria negar-por-default fora da raiz e escalar ofuscação óbvia para
  HITL.
- **Retry não cobre o re-despacho de especialista** — só I/O de rede opcional, justo
  o ponto que menos falha.
- **Trust ladder coleta reputação mas não fecha o loop** — o score gera fricção, mas
  ainda não roteia trabalho por `trust × task-type`.

O fio condutor de todo o trabalho futuro é o mesmo do design: promover cada
mitigação-em-prosa restante a mecanismo executável, e levar o determinismo — o maior
ativo do sistema — até onde ele ainda não chegou (o paralelismo e o isolamento), sem
jamais abrir mão dele.

---

*Fim. Este documento reflete `mad` 1.15.0. Emendá-lo é decisão de peso: registre em
`docs/DECISOES.md`.*
