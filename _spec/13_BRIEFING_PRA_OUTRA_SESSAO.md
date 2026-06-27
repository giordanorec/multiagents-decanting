# 13 — Briefing pra outra sessão (texto pronto para colar)

Este é o **prompt inicial** que você (usuário) deve colar na nova sessão Claude Code que vai implementar o plugin `multiagents-decanting`. O texto abaixo é completo: contém contexto suficiente para a outra Claude iniciar bem o trabalho.

---

## Como usar este arquivo

1. Crie um diretório local para o novo plugin (sugestão: `~/projetos/multiagents-decanting/`).
2. Inicialize um repo git lá: `git init`.
3. Copie a pasta `_spec/` inteira deste projeto para a raiz do novo repo.
4. Abra Claude Code naquele diretório: `cd ~/projetos/multiagents-decanting && claude`.
5. Cole o texto abaixo (entre as duas linhas `---`) como primeiro prompt.

---

## ⬇️ TEXTO A COLAR ⬇️

---

Olá. Você vai implementar um plugin para Claude Code chamado `multiagents-decanting`. O plugin completo está especificado, em densidade suficiente para você implementar diretamente, na pasta `_spec/` deste repositório.

## Antes de começar a codificar

Leia, em ordem, todos os 14 arquivos da `_spec/`:

```
_spec/
├── 00_README.md
├── 01_CONTEXTO_E_FILOSOFIA.md
├── 02_ARQUITETURA.md
├── 03_ESTRUTURA_DE_PASTAS.md
├── 04_PROTOCOLOS.md
├── 05_TEMPLATES.md
├── 06_AGENT_TYPES.md
├── 07_SKILLS_E_COMMANDS.md
├── 08_DASHBOARD.md
├── 09_MULTIPLATAFORMA.md
├── 10_MIGRACAO_E_COEXISTENCIA.md
├── 11_CRITERIOS_DE_ACEITE.md
├── 12_RISCOS_E_FRONTEIRA.md
└── 13_BRIEFING_PRA_OUTRA_SESSAO.md (este arquivo)
```

Leia o `00_README.md` primeiro — ele orienta a leitura dos demais e lista os princípios não-negociáveis.

## Contexto que vem de fora desta spec

A spec foi escrita por outra instância Claude (o "Arquiteto" de uma sessão de Discovery do projeto `ML_AtivosJudiciais`, do usuário Giordano). Ela é o resultado de:

1. **Conversa longa de Discovery sobre filosofia de memória de agentes** (junho/2026). Síntese: o paradigma "decanting" — sessão viva por unidade de trabalho + protocolo de externalização ao fim — é a tese central.

2. **Meta-pesquisa em ~30 fontes 2026** sobre: stateful vs stateless agents, context rot, frameworks proprietários (LangChain como cautionary tale), Anthropic Multi-Agent Research, Claude Code v2.1.33 e v2.1.77, MemGPT/Letta, LangGraph, Mem0, A2A protocol, OpenTelemetry GenAI conventions, MCP, Spec Kit, Skills Anthropic, cost circuit breakers, Anthropic Constitution 2026, padrões de UX onboarding leigo, Whisper local, Textual TUI, PWA, multiplataforma, etc. O artigo consolidado está em `_artigo/memoria_agentes_2026_v2.pdf` (~25 páginas, 28 capítulos, 50+ referências). Vale ler ao menos a Parte I (Memória).

3. **Decisões já fechadas que você não precisa re-debater:**
   - Repo separado, não upgrade do `multiagentes-giordano` v0.2.0.
   - Python 3.9+ puro como linguagem do CLI (sem deps exóticas além de `websockets`).
   - Dashboard HTML local + WebSocket + PWA (não tmux).
   - Decanting obrigatório como filosofia central.
   - Trust ladder com `trust.json` por agente.
   - OpenTelemetry GenAI emit nativo.
   - Circuit breaker + budget enforcement obrigatórios.
   - Alinhamento com `anthropic/skills` pattern.
   - i18n PT-BR default + EN.
   - **Decanting nativo do Claude Code**: sessão viva durante a feature via `Agent` tool (+ `SendMessage` quando disponível); decanting obrigatório ao fim; próxima feature começa nova call lendo o decantado. **NÃO usa `claude -p` em momento algum.** Isto NÃO é "frio puro" — é decanting genuíno cuja primitiva de sessão viva é nativa do Claude Code em vez de processo OS separado.
   - Constitutional principles 4-tier referenciados (não duplicados) nos system prompts.

## O que eu (Arquiteto desta sessão) preciso de você

### Fase 1 — Confirmação de entendimento (10-15 min)

1. Leia toda a `_spec/`.
2. Volte e me diga (em PT-BR, conciso):
   - Sua compreensão dos princípios não-negociáveis em uma frase cada.
   - O que está claro.
   - O que precisa clarificação minha antes de você começar.
   - Sua estimativa de esforço para v1.0 Tier 1 (CA-001 a CA-103 + CQ-001 a CQ-005 em `_spec/11_CRITERIOS_DE_ACEITE.md`).

### Fase 2 — Plano de implementação

Proponha um plano de implementação em fases lógicas:
- Quais arquivos você cria primeiro (scaffold).
- Quais testes você prioriza.
- Onde você vê risco técnico que pode atrasar.
- Como você quer ser supervisionado por mim (passo a passo? marcos grandes?).

### Fase 3 — Implementação iterativa

Após meu OK no plano, implementa. Reporta a cada marco. Aplica decanting próprio (cria `memory/arquiteto/` deste novo projeto, mantém `docs/DECISOES.md`, etc — sim, este novo plugin é construído seguindo seus próprios princípios).

## Restrições não-negociáveis

- **Sem reinventar primitivas.** Use Claude Code SDK, MCP, Skills Anthropic, Spec Kit GitHub como vêm. Plugin é thin wrapper.
- **Sem deps externas além de `websockets`** (e `textual` opcional). Python stdlib + pathlib em tudo.
- **Cross-platform Windows nativo + macOS + Linux.** Sem `jq`, `uuidgen`, `tmux`.
- **Sem golden cage.** Toda restrição do plugin deve ser opcional ou claramente catastrófica.
- **Decanting você mesmo deve seguir.** Você é o Arquiteto deste plugin; suas decisões vão em `docs/DECISOES.md` do projeto do plugin (não do projeto do usuário).

## Contexto do usuário final

O plugin é construído para um espectro amplo:

- Desenvolvedor sênior em IA/ML (o Giordano, primeiro usuário).
- Times de desenvolvimento profissional em geral.
- **Usuários leigos** (advogados, médicos, professores) que querem multiagente sem entender stack — esse é critério qualitativo importante (ver CQ-001 a CQ-005).

Pense em UX desde o início. Onboarding conversacional uma-pergunta-por-vez (já validado em prática), templates por tipo de projeto, comando `/decanting-explain` em PT-BR, dashboard com personagens visuais.

## Boas práticas pra você (Arquiteto do plugin)

1. **Comece pelo doctor.** Implementar `/decanting-doctor` primeiro força você a definir todas as invariantes do sistema. Ele vira o teste vivo de integridade.
2. **TDD nos componentes críticos.** Especialmente decanting protocol e circuit breaker.
3. **Mock generoso do `Agent` tool** nos testes para não pagar API durante CI (subprocesses Python que simulam call + retorno).
4. **Documente cada decisão importante em `docs/DECISOES.md`** do plugin. Mostra a outros (incluindo futuras instâncias suas) por que escolhas foram feitas.
5. **Tutorial interativo (CA-102) é onboarding crítico.** Use-o pra dogfood o plugin enquanto desenvolve.

## Onde estão informações adicionais

- Artigo de meta-pesquisa: `_artigo/memoria_agentes_2026_v2.pdf` (28 capítulos, denso).
- Plugin antigo v0.2.0 instalado em `~/.claude/plugins/cache/giordanorec/multiagentes-giordano/0.2.0/` — leia se quiser ver o que ele faz hoje (para entender o que muda, ver `_spec/10_MIGRACAO_E_COEXISTENCIA.md`).
- Spec Kit do GitHub: <https://github.com/github/spec-kit> (usar como referência de padrão aberto SDD).
- Skills oficiais Anthropic: <https://github.com/anthropics/skills>.

## Atitude que eu espero de você

- Pragmatismo. v1.0 é MVP. Tier 2 e Tier 3 vêm depois.
- Honestidade. Se algo na spec está errado ou inviável, me diga.
- Iniciativa. Decida coisas pequenas; pergunte coisas grandes.
- PT-BR no que vai pro usuário; EN no código se for convenção.
- Decanting próprio — você mesmo segue o protocolo.

Bora? Comece lendo `_spec/00_README.md` agora. Reporte quando tiver lido tudo.

---

## ⬆️ FIM DO TEXTO ⬆️

---

## Após a outra sessão concluir Fase 1

Você (usuário Giordano) recebe da outra Claude:
- Resumo dos princípios não-negociáveis.
- Lista de pontos claros.
- Lista de pontos que pedem clarificação.
- Estimativa de esforço.

Se a outra Claude pedir clarificação que você não sabe responder, traga de volta pra esta sessão (sessão atual, do projeto ML) — eu (Arquiteto da Discovery) posso opinar.

## Após Fase 2

Você revisa o plano. Se concorda, autoriza. Se quer mudar, pede ajuste.

## Após Fase 3

A outra Claude está implementando. Pode levar dias úteis. Você acompanha via:
- Resumos periódicos dela.
- Visita ao dashboard quando ela ativar pela primeira vez.
- Doctor para verificar saúde.

## Quando o plugin estiver pronto

Volta aqui (sessão ML) e me avisa. A gente:
- Instala o plugin no seu ambiente.
- Roda `/decanting-migrate-from-v02` pra portar este projeto ML.
- Continua a Discovery do ML usando o plugin novo.
