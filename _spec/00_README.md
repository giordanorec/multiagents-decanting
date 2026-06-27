# Plugin `multiagents-decanting` — Superespecificação

**Status:** Spec v1.0, pronta para implementação.
**Autor da spec:** Arquiteto Claude (sessão de Discovery do projeto ML_AtivosJudiciais).
**Destinatário:** sessão Claude Code que vai implementar o plugin.
**Data:** Junho/2026.

---

## O que é este documento

Este conjunto de 14 arquivos descreve, em densidade suficiente para implementação direta, um **novo plugin** para Claude Code chamado `multiagents-decanting`. É um sucessor filosófico (não um upgrade) do plugin `multiagentes-giordano` v0.2.0, com diferenças arquiteturais fundamentais que justificam repo separado.

Nome no marketplace: `multiagents-decanting`.
Prefixo de comandos: `/decanting-` (ex: `/decanting-init`, `/decanting-spawn`, `/decanting-dashboard`).

## Por que repo separado, não upgrade

A filosofia muda. v0.2.0 assume:

- Dashboard tmux/Tilix (Linux-only).
- Sessões persistentes via `claude -p --resume`.
- Comunicação file-based como complemento à sessão viva.
- Sem protocolo formal de decanting.
- Sem dashboard visual web-based.
- Sem trust ladder.

Plugin novo assume:

- **Decanting nativo do Claude Code.** Sessão viva durante a feature via `Agent` tool (+ `SendMessage` quando disponível para continuidade multi-turn). Decanting obrigatório ao fim de cada feature. Próxima feature começa nova call lendo o decantado. Sem `claude -p`, sem `sessions.json`, sem processos vivos em background — toda a gestão de continuidade é nativa do Claude Code.
- **Multi-turn Arquiteto ↔ Especialista** quando necessário, via `SendMessage` (Claude Code v2.1.77+) — também dentro da assinatura, também ephemeral-friendly.
- **Dashboard HTML local cross-platform** (Windows nativo, macOS, Linux), cada agente representado como personagem visual. Consome telemetria OpenTelemetry GenAI nativa.
- **Decanting como protocolo obrigatório** (não opcional) ao fim de toda unidade de trabalho.
- **Memória institucional rica e estruturada** em `memory/<agente>/` com 7 arquivos especializados.
- **Trust ladder** que escala autonomia com performance demonstrada.
- **Thin wrapper sobre Claude Code** — não reinventa SDK, não reinventa SDD (usa Spec Kit do GitHub onde aplicável), não envelopa primitivas.

## Como ler esta spec

Em ordem, primeira leitura:

1. `01_CONTEXTO_E_FILOSOFIA.md` — por que existe e princípios.
2. `02_ARQUITETURA.md` — diagrama lógico, processos, fluxo.
3. `03_ESTRUTURA_DE_PASTAS.md` — layout do projeto-cliente.
4. `04_PROTOCOLOS.md` — protocolo do especialista e do arquiteto.
5. `05_TEMPLATES.md` — templates de cada arquivo de memória.
6. `06_AGENT_TYPES.md` — lista de tipos + system prompts.
7. `07_SKILLS_E_COMMANDS.md` — comandos do plugin.
8. `08_DASHBOARD.md` — implementação do dashboard HTML local.
9. `09_MULTIPLATAFORMA.md` — Windows/Mac/Linux.
10. `10_MIGRACAO_E_COEXISTENCIA.md` — guia para projetos vindos de v0.2.0.
11. `11_CRITERIOS_DE_ACEITE.md` — testes funcionais que validam a implementação.
12. `12_RISCOS_E_FRONTEIRA.md` — limites conhecidos.
13. `13_BRIEFING_PRA_OUTRA_SESSAO.md` — texto pronto para colar como prompt inicial na sessão que vai implementar.

## Princípios não-negociáveis (resumo de uma linha cada)

1. **Decanting obrigatório** ao fim de cada unidade de trabalho.
2. **Decanting nativo do Claude Code.** Sessão viva via `Agent` tool + `SendMessage` durante a feature; externalização obrigatória ao fim; próxima feature começa fresh lendo o decantado.
3. **Memória institucional em arquivo**, não em sessão.
4. **Thin wrapper sobre Claude Code**, nunca envelopar SDK.
5. **Paved road, não golden cage** — agente sempre pode optar por não usar.
6. **Guardrails (poucos, catastróficos), não gatekeepers** (uniformes).
7. **Fricção proporcional a blast radius**, não uniforme.
8. **Trust ladder** — autonomia escala com outcomes.
9. **Cross-platform** Windows nativo + macOS + Linux. Sem tmux, Tilix, jq, uuidgen, claude -p.
10. **Sem inventar o que vendor faz** — Agent tool, MCP, Spec Kit nativo.
11. **Começar mínimo** — adicionar complexidade só com dor real medida.

## Princípio meta

> *Em domínio onde a fronteira anda rápido, abstrações grossas e controles uniformes convertem velocidade alheia em dívida própria. Construa menos, nos lugares certos.*

## Onde está o contexto que motivou esta spec

O artigo `_artigo/memoria_agentes_2026_v2.pdf` (28 capítulos, ~25 páginas) é a meta-pesquisa completa que fundamenta todas as decisões aqui. Quem implementa deve ler pelo menos a Parte I (Memória), seções 3-8.

## Sobre o usuário e o projeto-mãe

- O usuário é consultor sênior em IA/ML, baseado no Brasil, trabalhando para AX (Aluisio Xavier Advogados) num módulo ML para ativos judiciais.
- Windows 11 Pro nativo, **sem WSL**. Bash via Git Bash, PowerShell disponível.
- Já usa Claude Code com plano Max.
- Tem familiaridade com o plugin antigo v0.2.0 do `multiagentes-giordano`.
- Trabalha em PT-BR. Tom direto, sem rodeios.
- Prefere uma pergunta por vez em Discovery.
