# 12 — Riscos e Fronteira

## 12.1 Riscos conhecidos (gerenciáveis)

### R-001 — Anthropic religar billing API (largamente mitigado pela arquitetura)
A mudança de junho/2026 está pausada mas pode religar a qualquer momento. **Plugin v1.0 NÃO usa `claude -p` em momento algum** — toda invocação de especialista é via `Agent` tool nativo do Claude Code, que roda dentro da assinatura. Logo, religação do billing API afeta minimamente o plugin.

**Exposição residual:**
- `SendMessage` é feature experimental (env var `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`); pode mudar de status. Plugin tem fallback (nova call do Agent tool lendo handoff) que funciona sem.
- Se a Anthropic vier a separar billing do próprio `Agent` tool em algum momento futuro: plugin terá que reavaliar. Sem precedente até a data desta spec.

**Mitigações ativas mesmo sem exposição direta:**
- Budget enforcement (`max_cost_per_day_usd`) protege contra qualquer surpresa de fatura.
- Doctor reporta status de billing e alerta antes de teto.
- Comunicação clara ao usuário no init sobre custo estimado.

### R-002 — Quebra de compatibilidade na evolução do Claude Code
v2.1.77 removeu `Agent.resume`. v2.2 pode remover `SendMessage`. v2.3 pode mudar formato de hooks.

**Mitigação:**
- Plugin tem layer de compatibilidade (`_utils.py:get_claude_code_version()`) que adapta.
- Testes CI rodam contra última versão do Claude Code.
- Versionamento independente do plugin (semver) — patches absorvem mudanças menores.
- Documentação clara sobre versões mínimas suportadas.

### R-003 — Decanting não executado por agente desatento
Agente pode "esquecer" de decantar se prompt não é claro ou se sessão é interrompida.

**Mitigação:**
- Decanting é hard requirement no protocolo (em todos os system prompts).
- Hook `SessionEnd` detecta saída sem decanting e tenta decanting de emergência.
- Trust ladder pune `decanting_skipped` com -10 (sanção forte).
- Doctor reporta agentes sem decanting > 7 dias.

### R-004 — Memória institucional fica stale
`decisions.md` cresce, lessons.md acumula, mas ninguém revisa. Decisões obsoletas viram dogma.

**Mitigação parcial:**
- Cada entrada de `decisions.md` tem campo "Como reabrir" (gatilho de revisão).
- Doctor alerta lessons.md > 10000 palavras (sugere poda).
- "Verify before assert" no protocolo: agente deve checar codebase antes de invocar memória crítica.

**Risco residual:** real. Plugin não resolve sozinho; precisa disciplina humana.

### R-005 — Context rot do próprio Arquiteto
O Arquiteto, em sessão longa, sofre context rot como qualquer outro agente.

**Mitigação:**
- Arquiteto tem seu próprio `memory/arquiteto/` e segue o mesmo protocolo de decanting.
- Doctor alerta quando sessão do Arquiteto excede limiar configurável.
- Próxima sessão do Arquiteto começa lendo `docs/STATE.md` + `docs/DECISOES.md` + `memory/arquiteto/handoff.md`.

### R-006 — Dashboard fica sem dados em projeto pequeno
Em projeto com 1 agente e 1 feature, dashboard parece superdimensionado.

**Mitigação:**
- Layout responde ao número de agentes (não fixa grid).
- Em projeto com 1 agente, mostra ele em destaque + métricas + dicas de uso.
- Modo CLI puro disponível (`--no-dashboard`) para quem prefere terminal.

### R-007 — Hooks como falsa segurança
Como documentado no artigo de meta-pesquisa, hooks do Claude Code podem ser modificados pelo próprio Claude. Guardrails via hook não são à prova de bypass intencional.

**Mitigação:**
- Hooks do plugin são para erro acidental, não malícia.
- Guardrails críticos (push force, rm rf) são também verificados em código Python do plugin.
- Documentação explícita: "guardrails são proteção contra acidente, não contra agente malicioso".

### R-008 — Trust score gameado
Agente pode aprender a maximizar score sem entregar valor real (Goodhart's law).

**Mitigação parcial:**
- Score é input pro Arquiteto, não autoridade final.
- Outcome ainda é marcado pelo Arquiteto (humano supervisiona).
- Roadmap Tier 3: eval contínuo via DeepEval/Promptfoo alimenta sinal independente.

### R-009 — i18n incompleta
PT-BR e EN cobertos. Outros idiomas não.

**Mitigação:**
- Estrutura `locale/<lang>.json` permite contribuição da comunidade.
- Fallback para EN sempre disponível.

### R-010 — Performance do dashboard em projeto grande
Com 10+ agentes ativos, polling de status/ e tail de logs pode pesar.

**Mitigação:**
- WebSocket emite só em mudanças, não em polling cliente.
- Backend Python usa threads não-bloqueantes.
- Roadmap V2.0: usar inotify/FSEvents em vez de polling.

## 12.2 Limites assumidos (intencional, não bug)

- **Single-user.** Não há auth, não há ACLs.
- **Single-machine.** Não roda distribuído.
- **Português + Inglês.** Outros idiomas via comunidade.
- **Claude como modelo primário.** Suporte a Ollama é roadmap; OpenAI/Gemini não está no plano.
- **Sem vector store próprio.** Quem precisa liga Mem0 externamente.
- **Sem deploy em servidor.** Dashboard é local.
- **Sem integração com tickets externos** (Jira, Linear, etc) no core. Pode ser hook.
- **Sem reimplementação de SDD.** Use Spec Kit do GitHub se quiser SDD formal.

## 12.3 O que está fora de escopo permanentemente

- **Wrapper sobre Claude SDK.** Cautionary tale LangChain.
- **Framework próprio de memória.** Convenção de arquivos é suficiente.
- **Marketplace próprio de skills.** Use o do Claude Code.
- **GUI desktop nativa.** HTML local serve.
- **Multi-modelo unified gateway.** Use LiteLLM externamente se precisar.

## 12.4 Fronteira aberta para evolução

Áreas onde 2026 ainda não tem resposta clara e o plugin pode evoluir conforme literatura amadurece:

- **Memória compartilhada entre agentes** (governance, ACLs, TTLs, versionamento).
- **Auto-detecção de tacit knowledge** (quando agente "está aprendendo algo novo", auto-sugerir append em lessons.md).
- **Coordenação multi-agente com 10+ especialistas** (orquestração escala mal).
- **Onboarding ainda mais leigo** (chatbot guia em interface gráfica em vez de slash commands).
- **Eval automatizado de outcomes** (ainda manual: Arquiteto marca accepted/rework).

## 12.5 Critérios para reabrir decisões arquiteturais

Quando essas coisas acontecerem, plugin precisa repensar:

| Sinal | Decisão a revisitar |
|---|---|
| Anthropic descontinua `Agent` tool ou `SendMessage` na forma atual | Reavaliar primitiva de sessão viva durante feature; possível adoção de A2A protocol |
| Claude Code SDK lança memory primitive próprio | Considerar abandonar `memory/<agente>/` em favor do nativo |
| A2A vira padrão dominante de fato | Implementar full A2A compatibility no v2 |
| Ollama atinge paridade de qualidade com Claude em tarefas relevantes | Promover Ollama de roadmap pra default opcional |
| Spec Kit do GitHub vira padrão de fato pra agente coding | Adotar formato Spec Kit nativo no plugin |
| Anthropic publica memory benchmark oficial | Calibrar protocolo de decanting contra ele |
| Constitutional principles 4-tier sofrem rev maior | Atualizar reference nos system prompts |
| Context window de modelo padrão chega a 10M tokens sem context rot | Considerar revisar premissa de decanting curto |

## 12.6 O que pode dar errado e como recuperar

| Falha | Recuperação |
|---|---|
| Call do Agent tool falha mid-feature | `/decanting-doctor` detecta via spans OTel sem `agent.end`; oferece reexecução com `/decanting-decant` retroativo + nova Agent call |
| `memory/<agente>/handoff.md` corrompido | Reconstruir a partir de `logs/otel/<date>.jsonl` recente; manualmente ou via `/decanting-decant` |
| `memory/*/handoff.md` perdido | Reconstruir a partir de `logs/otel/<date>.jsonl` (spans recentes) ou via `/decanting-decant` retroativo |
| Dashboard não inicia (porta ocupada) | Auto-tenta 8765-8775; se falhar, instrução pra usuário |
| Claude Code SDK quebra com plugin | Doctor reporta incompatibilidade; sugere downgrade ou aguardar patch |
| Billing surpresa | Budget enforcement já encerrou; histórico em logs/otel/ |
| Trust score zerado por bug | Re-derivar do histórico em trust.json (preservado) |

## 12.7 Disclaimer pro usuário

No README, em local visível:

> **Aviso:** Este plugin orquestra agentes que executam código, fazem chamadas pagas a APIs, e modificam seu sistema de arquivos. Use guardrails (já configurados por padrão), monitore o dashboard, revise commits antes de push. Em caso de dúvida, prefira modo strict (mais aprovações requeridas). Plugin é open-source MIT; autores não respondem por uso indevido.
