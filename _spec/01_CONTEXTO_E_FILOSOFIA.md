# 01 — Contexto e Filosofia

## 1.1 Por que este plugin existe

Três forças combinadas tornam o plugin antigo (`multiagentes-giordano` v0.2.0) insuficiente em 2026:

**Força 1 — Mudança (pausada mas armada) no billing da Anthropic.** Em junho/2026 a Anthropic anunciou separação entre uso interativo de Claude Code e uso programático via `claude -p` headless, com este último indo para um pool separado de créditos API. A mudança foi pausada, mas pode religar a qualquer momento. Plugin que depende essencialmente de `claude -p` em escala está estruturalmente exposto.

**Força 2 — Windows nativo sem WSL.** O usuário-alvo opera em Windows 11 sem WSL. O dashboard tmux/Tilix da v0.2.0 não roda nativo. Operação multi-agente precisa ser cross-platform real.

**Força 3 — Conhecimento consolidado sobre memória de agentes.** O ano de 2026 trouxe vocabulário (working/long-term, checkpointer/store), benchmarks (LOCOMO, RULER, MRCR v2), padrões emergentes (Anthropic Multi-Agent Research, Claude Code v2.1.33 memory field, Claude Code v2.1.77 SendMessage, MemGPT/Letta, Mem0), e — sobretudo — o paradigma do **decanting**. Plugin v0.2.0 foi feito antes desse conhecimento; não tem protocolo formal de externalização.

## 1.2 Filosofia central: decanting

**Definição operacional:** deixe a sessão viver enquanto for produtiva. Ao fim de cada unidade de trabalho, o agente é **obrigado** a extrair sistematicamente os aprendizados para artefatos externos. A próxima unidade de trabalho começa em sessão fresca lendo o decantado.

Componentes:

- **Unidade de trabalho** = uma feature, um experimento, uma spec. Não "o projeto inteiro" (insustentável por context rot), nem "uma chamada arbitrariamente curta" (perde sentido de unidade).
- **Decantar** = protocolo obrigatório executado pelo agente ao concluir a unidade. Não opcional, não delegado a humano.
- **Sessão fresca** = nova working memory; cada call do Agent tool é uma sessão completa do subagente, mas memória conversacional **entre** calls é zerada — a continuidade vem dos arquivos.

**O que decanting resolve:**

| Problema | Solução do decanting |
|---|---|
| Context rot acumulado | Sessão é curta (uma feature) o suficiente para não rodar contra o limite |
| Tacit knowledge perdido | Protocolo força extração antes de fechar sessão |
| Memória institucional opaca | Artefatos do decanting são auditáveis |
| Custo de tokens explosivo | Bounded por unidade de trabalho |
| Onboarding impossível | Próxima sessão (ou novo agente) começa lendo artefatos |
| Fluência multi-turno em modo stateless puro | Preservada *dentro* da call do Agent tool (que faz multi-step internamente) |

## 1.3 Modo de operação: decanting nativo do Claude Code

**O plugin implementa decanting usando primitivas nativas do Claude Code.** Não é "frio puro" (que seria Modo B do artigo de meta-pesquisa, no qual cada chamada é zerada sem memória institucional). É **decanting**: sessão viva durante a unidade de trabalho (a feature), externalização obrigatória ao fim, próxima feature começa fresh lendo o decantado.

A diferença em relação ao plugin antigo é apenas **qual primitiva nativa entrega a sessão viva durante a feature**:

| Primitiva | Plugin antigo (v0.2.0) | Plugin novo (v1.0) |
|---|---|---|
| Sessão viva durante a feature | `claude -p --resume <uuid>` (processo separado) | `Agent` tool + `SendMessage` (Claude Code gerencia) |
| Onde mora | Filesystem + processo OS | Memória do Claude Code |
| Quem gerencia continuidade | Plugin (sessions.json, dashboard de processos) | Claude Code nativo (zero código próprio) |

Em ambos os casos: **mesma filosofia decanting**, mesma fluência durante a feature, mesma externalização obrigatória.

A escolha pela primitiva nativa (`Agent` tool + `SendMessage`) tem seis justificativas convergentes:

1. **Anthropic Multi-Agent Research** (sistema interno da Anthropic) usa subagents ephemeral com orchestrator persistente. Padrão da casa que faz o modelo.
2. **Claude Code v2.1.33 memory field + v2.1.77 SendMessage** entregam nativos exatamente o que decanting precisa.
3. **Imune ao billing change** anunciado (e pausado) da Anthropic. `Agent` tool roda dentro da assinatura; `claude -p` não tem garantia.
4. **Custo previsível e bounded** por feature. Sem risco de sessão viva acumulando indefinidamente.
5. **Operação muito mais simples.** Sem gerenciar `sessions.json`, processos órfãos, race conditions de spawn paralelo.
6. **Auditabilidade total.** Cada call é unidade fechada com transcript próprio gerenciado pelo Claude Code.

### Como funciona a sessão viva durante a feature

Caso comum: feature simples que cabe numa única call do `Agent` tool.

```
Agent(subagent_type="multiagents-decanting:pipeline-dev",
      prompt="Leia specs/feature-X.md, execute, decante, retorne.")
```

Dentro dessa call, o subagente vive uma sessão completa: faz boot lendo memory/, executa multi-step (várias tool uses, multi-turn interno), decanta, retorna. **Isso é sessão viva durante a feature.** Não é "frio puro".

Caso multi-turn: feature requer idas e voltas Arquiteto ↔ Especialista.

- Se `SendMessage` disponível (Claude Code v2.1.77+ com `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`): retoma a sessão interna do subagent. **Sessão viva continuada**, sem boot novamente.
- Se não disponível: faz nova call do `Agent` tool, especialista relê `handoff.md` (que foi atualizado no decanting parcial da call anterior). Boot rápido, continua. Ligeiramente menos fluido, funcionalmente equivalente.

A unidade de trabalho continua sendo a feature, não a call individual. Decanting acontece ao fim da feature.

## 1.4 Princípio: thin wrapper sobre Claude Code

O plugin é **fino** propositalmente. Não envelopa Claude Code SDK. Não inventa formato proprietário de spec (usa Spec Kit quando aplicável). Não constrói "framework de memória" (usa convenção de pastas e arquivos markdown). Não cria sistema de permissões próprio (depende dos hooks e do permission model do Claude Code).

Razões, documentadas no artigo de meta-pesquisa:

- LangChain morreu de over-abstração; ninguém repete o erro com olho aberto.
- Anthropic recomenda explicitamente reduzir camadas em produção.
- Primitivas Claude Code mudam mensalmente; wrapper grosso vira dívida.

O plugin abstrai apenas cinco coisas:

1. Convenção de pastas (`memory/<agente>/`, `specs/`, `reports/`, etc).
2. Protocolo de boot e de decanting que o agente segue.
3. Dashboard HTML local (cross-platform, com personagens, consome OTel).
4. CLI fina em Python para `init`, `inspect`, `doctor`, `dashboard`, `decant`, `trust` (sem deps exóticas).
5. Templates iniciais dos arquivos de memória.

Tudo mais — invocação de modelo, tools, MCP, hooks, permission model, persistência de subagent — fica como Claude Code entrega nativo.

## 1.5 Princípio: paved road, não golden cage

Toda restrição do plugin deve ser **opcional** ou **óbvia (catastrófica)**. Diagnóstico operacional:

> Um desenvolvedor sênior pode escolher não usar isto numa tarefa específica?

Se sim: paved road, OK.
Se não: golden cage, refatorar.

Aplicações práticas:

- Spec format sugerido, não obrigatório. Agente que quer trabalhar sem spec pode.
- Templates de memória são templates, não schema rígido. Agente pode adicionar arquivos próprios.
- Decanting é obrigatório no protocolo de saída, mas o conteúdo é livre.
- Trust ladder dá sugestões; usuário pode sobrescrever.

## 1.6 Princípio: guardrails poucos, gatekeepers nenhum

**Guardrails do plugin** (deterministic, raros, catastróficos):

- Não permitir `git push --force` em `main` sem confirmação explícita do humano.
- Não permitir `rm -rf` em pasta fora da raiz do projeto.
- Não permitir commit de arquivo com secret detectado.
- Não permitir Edit/Write em `memory/*/identity.md` sem flag explícita.

**Não-guardrails (deliberadamente ausentes):**

- Não aprovar cada Edit, cada Read, cada Bash.
- Não exigir review humano em decisão arquitetural padrão (vira gatekeeper).
- Não validar saída de cada agente contra schema rígido (eval contínuo, não sync block).

## 1.7 Princípio: fricção proporcional a blast radius

Implementação concreta no plugin:

| Tipo de ação | Default | Override |
|---|---|---|
| Reversível, baixo risco (read, run test, create branch) | Autônomo, sem prompt | — |
| Reversível, médio risco (edit em branch, install dep em venv) | Autônomo + log no dashboard | Modo strict pede confirmação |
| Irreversível, alto risco (push main, deploy, drop table, gasto pago) | Human-in-the-loop obrigatório | Nunca pular |

## 1.8 Princípio: trust ladder

Cada agente tem `memory/<agente>/trust.json` que registra:

- Score de confiança (0-100, default 50).
- Histórico de outcomes (features completadas, aceitas pelo arquiteto, com qual qualidade).
- Permissões expandidas conforme score sobe.

Não é gating bureaucrático — é **observabilidade de competência demonstrada**. Em modo strict, score baixo significa mais pedidos de confirmação; score alto, menos.

## 1.9 Princípio: começar mínimo

Versão alfa do plugin entrega o **mínimo viável**:

- Estrutura de pastas (definida em 03).
- Protocolo de boot + decanting (definido em 04).
- 3 tipos de agente (arquiteto, pipeline-dev, qa-tester) — não 10.
- 3 arquivos de memória por agente mandatórios (identity, decisions, handoff); demais (state, lessons, glossary, playbooks, trust.json) opcionais conforme uso.
- Dashboard HTML simples com lista de personagens consumindo OTel.
- Comandos: `init`, `inspect`, `doctor`, `dashboard`, `decant`, `trust`.

Expandir só quando dor real surgir duas vezes. Os outros tipos de agente (dba, frontend-dev, mobile-dev, etc) entram em v0.2 quando o usuário pedir. Os outros arquivos de memória entram em v0.3 quando observação mostrar necessidade.
