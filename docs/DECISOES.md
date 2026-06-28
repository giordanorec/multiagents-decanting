# Decisões — multiagents-decanting (plugin)

> Log cronológico append-only das decisões de arquitetura/implementação do
> **próprio plugin**. O Arquiteto (Claude, esta sessão) dogfooda o protocolo de
> decanting enquanto constrói o plugin. Formato fixo (ver `_spec/05`).

---

## 2026-06-27 — Decisão #1: Feature-detection em runtime, nunca hardcodar versão

**Decisão:** Nenhuma versão de Claude Code / OTel / Constitution é hardcodada;
tudo é detectado em runtime ou degradado com graça.

**Alternativas consideradas:** Seguir a letra da spec (`v2.1.77`, `OTel v1.41`,
`Constitution jan/2026`). Rejeitado.

**Por quê:** A spec foi escrita por outra IA e o Giordano avisou que cada IA
errou em ≥1 ponto. Prova imediata: a spec crava "Claude Code v2.1.77", o
ambiente real roda **2.1.195**. Hardcodar já estaria errado no dia 1.

**Restrição decorrente:** `supports_sendmessage()` detecta por env var +
presença, não por número de versão. `doctor` reporta versões observadas, não
comparadas a constantes mágicas.

**Como reabrir:** Se a Anthropic publicar contrato estável de versão para essas
features.

**Feature relacionada:** fundação / scaffold.

---

## 2026-06-27 — Decisão #2: `max_tokens_per_feature` como unidade canônica de budget

**Decisão:** Unifico o budget por-feature. CA-043 falava `max_tokens_per_session`,
o `.toml` (5.15) falava `max_tokens_per_feature` — conflito interno da spec.

**Alternativas consideradas:** `per_session`. Rejeitado: "sessão" não é unidade
de trabalho no modelo decanting; a feature é.

**Por quê:** Consistência com o princípio "unidade de trabalho = feature".

**Restrição decorrente:** Toda contagem de budget é por feature + agregado diário.

**Como reabrir:** Se surgir necessidade real de teto por-sessão-do-Arquiteto.

**Feature relacionada:** config / toml.

---

## 2026-06-27 — Decisão #3: Escopo v1.0 = Tier 1 completo, supervisão por marco grande

**Decisão:** Implementar CA-001..CA-103 + CQ-001..CQ-005 de uma vez. Reportar ao
Giordano só em marcos grandes.

**Alternativas consideradas:** Walking skeleton primeiro (recomendação do
Arquiteto). Giordano optou por Tier 1 completo.

**Por quê:** Decisão do dono do projeto. Registrado o trade-off: tensão com o
princípio 11 ("começar mínimo"), aceita conscientemente.

**Restrição decorrente:** Não declarar "v1.0 pronto" até Tier 1 + CQ verde.

**Como reabrir:** Se o esforço estourar e o Giordano quiser refatiar.

**Feature relacionada:** planejamento.

---

## 2026-06-27 — Decisão #4: Estrutura de runtime — só `python3`, sem alias `python`

**Decisão:** Wrappers e doctor toleram ambiente sem alias `python` (usam `python3`
com fallback). Python alvo: 3.9+, ambiente de dev é 3.14.

**Por quê:** O ambiente do Giordano só tem `python3`. `tomllib` é stdlib desde
3.11; `tomli` só é dependência em <3.11.

**Restrição decorrente:** Todo shell-out a Python tenta `python3` antes de `python`.

**Como reabrir:** n/a.

**Feature relacionada:** multiplataforma.

---

## 2026-06-27 — Decisão #5: Dois caminhos de subagent_type (plugin namespaced + project-local)

**Decisão:** Os agentes existem em duas camadas, ambas válidas:
(a) **plugin-shipped** em `agents/<role>.md` → invocados pelo Arquiteto como
`subagent_type="mad:<role>"` (funcionam por o plugin estar
instalado); (b) **project-local** copiados pelo `init` para
`.claude/agents/<role>.md` → invocáveis como `<role>` (sem namespace), para
customização do usuário sem mexer no template do plugin (spec §6.8).

**Alternativas consideradas:** Só (a) — não copiar pro projeto. Rejeitado: a
spec (CA-001, layout §3.1) quer `.claude/agents/` populado e §6.8 quer
customização local. Só (b) — não usar namespace. Rejeitado: todos os prompts de
despacho usam `mad:<role>`.

**Por quê:** Não há colisão (subagent_types distintos). A cópia local dá o ponto
de customização; o namespaced é o canônico do despacho.

**Restrição decorrente:** O template genérico de agente usa
`subagent_type="{{agente}}"` (project-local, sem prefixo); os agentes do plugin
usam o prefixo. Validação E2E da invocação real exige o plugin instalado no
Claude Code (fora do escopo dos testes automatizados — Agent tool é mockado).

**Como reabrir:** Se o Claude Code passar a expor um mecanismo único de registro.

**Feature relacionada:** agentes / init.

---

## 2026-06-27 — Decisão #6: Wiring de hooks só em .claude/settings.json do projeto

**Decisão:** Os hooks são wireados pelo `init` em `.claude/settings.json` do
projeto (PreToolUse/PostToolUse/SessionEnd → `.claude/hooks/*`), usando
`${CLAUDE_PROJECT_DIR}`. NÃO há `hooks/hooks.json` plugin-level.

**Alternativas consideradas:** Hooks plugin-level (`${CLAUDE_PLUGIN_ROOT}`).
Rejeitado: dispararia em TODO projeto e causaria double-fire com o wiring
local. Project-level escopa corretamente aos projetos decanting.

**Por quê:** O subagente de hooks corretamente apontou que sem wiring os hooks
não disparam (gap em CA-030..033 e CA-070). Project-level é limpo e escopado.

**Restrição decorrente:** `.sh` exigem bash (Git Bash no Windows); `.py` exigem
`python3` no PATH. Ambos já são pré-requisitos. Hooks degradam com graça (exit 0)
sem projeto/`_utils`.

**Como reabrir:** Se o Claude Code padronizar hooks de plugin escopados por
projeto nativamente.

**Feature relacionada:** hooks / guardrails / observabilidade.

---

## 2026-06-27 — Decisão #7: Rebrand das superfícies de usuário para "multiagents"

**Decisão:** As superfícies voltadas ao usuário usam a marca **"multiagents"**
(inglês): skill `mad-workflow`, comandos `/mad-*`, CLI
`multiagents`/`scripts/mad.py`. "decanting" fica só como conceito interno
(o protocolo) e na ação `/mad-decant`. Plugin/repo/marketplace e
`subagent_type` seguem `multiagents-decanting`.

**Alternativas consideradas:** Manter `/decanting-*` (rejeitado pelo Giordano);
usar "multiagentes" em português (rejeitado — ele quer inglês).

**Por quê:** No dogfood ao vivo, a marca "decanting" dominava tudo e o modelo, em
sessão nova, passou a achar que o próprio projeto se chamava "decanting"
(vazamento de identidade). Corrigido também com nota explícita na skill e no
arquiteto separando método × nome-do-projeto.

**Restrição decorrente:** Em código/docs voltados ao usuário, usar "multiagents".
"decanting" só ao descrever o protocolo. Ver memória do projeto
`naming-multiagents-not-decanting`.

**Como reabrir:** Se o Giordano mudar de ideia sobre a marca.

**Feature relacionada:** rebrand / UX / naming.

---

## 2026-06-27 — Decisão #8: Rebrand final para `mad` + política de versionamento

**Decisão:** O plugin passa a se chamar **`mad`** (MultiAgent Decanting). Skill
`mad-workflow`, comandos `/mad-*`, subagent_type `mad:<role>`, CLI `mad`/`scripts/mad.py`.
O repo/pasta e o arquivo de config (`multiagents-decanting.toml`) seguem inalterados.

**Política de versionamento estabelecida (vale daqui pra frente):**
- Mudança **incremental** (sem quebrar projetos existentes) → mesmo nome, bump de
  versão (semver no plugin.json), usuário roda `claude plugin update`.
- Mudança **arquitetural que quebra** → nome NOVO e **distinto** (não homônimo).
  Controle de versão = semver + marketplace + `claude plugin update`; `/mad-doctor`
  reporta instalado vs disponível on-demand (NÃO phone-home a cada chamada);
  release via git tag + `gh release`.

**Alternativas consideradas:** Manter `multiagents-workflow` (rejeitado: diferia
do v0.2 `multiagente-workflow` por UMA letra — confusão real no dogfood). Upgrade
in-place do `multiagentes-giordano` (rejeitado: filosofias incompatíveis).

**Por quê:** Nome distinto elimina a ambiguidade "mesmo comando, versão diferente
pra cada um": `/multiagente-*` = sempre v0.2; `/mad-*` = sempre o novo.

**Restrição decorrente:** Em todas as superfícies de usuário, marca = `mad`.
Side-effect do sed corrigido: URLs do GitHub voltaram a `multiagents-decanting`
(o repo não mudou); `_spec/` restaurado (referência congelada).

**Como reabrir:** Se "mad" provar ambíguo na prática.

**Feature relacionada:** rebrand final / versionamento.

---

## 2026-06-27 — Decisão #9: Monorepo com dois plugins (mad + brainstorm)

**Decisão:** O repo `multiagents-decanting` hospeda DOIS plugins independentes num
mesmo marketplace: `mad` (raiz) e `claude-brainstorm-multiagent` (em
`plugins/brainstorm/`). `marketplace.json` lista ambos. Comandos `/mad-*` e
`/brainstorm` coexistem.

**Alternativas consideradas:** Fundir o brainstorm dentro do plugin `mad`.
Rejeitado: o brainstorm é MCP-based com stack pesada (numpy/sklearn/pyribs/
sentence-transformers→PyTorch via uvx) e dashboard próprio na porta 8765 — fundir
mataria a leveza do `mad` (dep única websockets), colidiria porta, e inflaria o
custo always-on de todo usuário do `mad`.

**Por quê:** Dois plugins num repo (à la `mattpocock/skills`) dá ao usuário tudo
no mesmo lugar sem acoplar arquiteturas. Cada um leve no que é. Nome do plugin
brainstorm preservado (`claude-brainstorm-multiagent`) para não quebrar os
subagent_types internos dos 8 agentes dele.

**Restrição decorrente:** São independentes — instala-se cada um. O primeiro
`/brainstorm` é lento (uvx baixa a stack ML). Atualizações do brainstorm vêm do
upstream e são re-sincronizadas no subdir.

**Como reabrir:** Se fizer sentido um "meta-plugin" que dependa dos dois.

**Feature relacionada:** monorepo / brainstorm.

---

## 2026-06-27 — Decisão #10: Catálogo único (reverte a #9)

**Decisão:** Em vez de o repo `mad` ser seu próprio marketplace (com o brainstorm
copiado dentro), todos os plugins do Giordano ficam num **catálogo único**:
`giordanorec/claude-plugins` (marketplace `giordanorec`). Cada plugin vive no SEU
repo; o catálogo só referencia via `source: github`. O `mad` foi adicionado lá.

**O que mudou no repo `mad`:** removidos `plugins/brainstorm/` (cópia redundante e
congelada — o catálogo aponta pro repo standalone `giordanorec/claude-brainstorm-
multiagent`) e `.claude-plugin/marketplace.json` (o repo é só um plugin agora, não
um marketplace solo). README passa a instruir instalação via catálogo.

**Alternativas consideradas:** Manter o monorepo da #9. Rejeitado pelo Giordano:
duplica o brainstorm e fragmenta os marketplaces. Um catálogo, plugins escolhíveis.

**Por quê:** Marketplace é catálogo; `source` pode apontar pra repos diferentes.
Um lugar só pra todos os plugins, usuário instala o que quer. Sem duplicação.

**Restrição decorrente:** Install canônico = `marketplace add giordanorec/claude-
plugins` + `install <plugin>`. O repo `mad` não é mais instalável como marketplace
solo. Atualizações de versão do mad: bump no plugin.json + (catálogo lê do repo).

**Como reabrir:** Se um plugin precisar de marketplace próprio por algum motivo.

**Feature relacionada:** distribuição / marketplace.
