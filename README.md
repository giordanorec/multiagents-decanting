# multiagents-decanting

> Orquestração multi-agente para Claude Code em **modo decanting nativo**.
> O Arquiteto coordena especialistas via `Agent` tool — sem `claude -p`, sem
> processos em background, sem `tmux`. Cada feature é uma sessão viva que
> **externaliza o aprendizado obrigatoriamente** ao terminar. Windows nativo,
> macOS e Linux.

## A ideia em 30 segundos

Um único Claude Code interativo é o **Arquiteto**: ele conversa com você,
escreve specs e delega trabalho a **especialistas** (pipeline-dev, qa-tester,
…) invocados pelo `Agent` tool nativo do Claude Code.

Cada especialista vive uma sessão completa enquanto trabalha numa feature e,
**antes de devolver controle, decanta**: grava o que decidiu, o que aprendeu e
onde parou em arquivos versionados (`memory/<agente>/`). A próxima invocação
começa fresca lendo o decantado. Memória mora em arquivo, não na sessão.

Resultado: sem context rot acumulado, sem conhecimento tácito perdido, custo
de tokens limitado por feature, e tudo auditável.

## Por que não o plugin antigo (`multiagentes-giordano` v0.2.0)

| | v0.2.0 | multiagents-decanting v1.0 |
|---|---|---|
| Sessão viva | `claude -p --resume` (processo OS) | `Agent` tool nativo + `SendMessage` opcional |
| Dashboard | tmux/Tilix (Linux-only) | HTML + WebSocket + PWA (Win/Mac/Linux) |
| Memória | `MEMORY.md` único | arquivos especializados + `trust.json` |
| Observabilidade | logs livres | OpenTelemetry GenAI nativo |
| Custo | sem teto | budget enforcement + circuit breaker |
| Confiança | — | trust ladder por agente |

Os dois coexistem (prefixos `/multiagente-` vs `/multiagents-`). Veja
`_spec/10_MIGRACAO_E_COEXISTENCIA.md`.

## Requisitos

- Claude Code (qualquer versão recente; capacidades são detectadas em runtime).
- Python 3.9+ (`websockets` é a única dependência; `pip install -r requirements.txt`).

## Início rápido

```
cd meu-projeto
claude
> /multiagents-init        # Discovery + estrutura + agentes + dashboard
> /multiagents-dashboard   # abre o painel local
> Descreva sua primeira feature — o Arquiteto coordena.
```

## Comandos

| Comando | O que faz |
|---|---|
| `/multiagents-init` | Discovery e scaffold do projeto |
| `/multiagents-enable <agente>` | Habilita um especialista adicional |
| `/multiagents-inspect <agente>` | Estado completo de um agente |
| `/multiagents-dashboard` | Abre/encerra o dashboard local |
| `/multiagents-decant <agente>` | Força decanting retroativo |
| `/multiagents-doctor` | Diagnóstico verde/amarelo/vermelho |
| `/multiagents-trust <agente>` | Trust score e histórico |
| `/multiagents-upgrade` | Atualiza o plugin (preserva memória) |
| `/multiagents-explain <conceito>` | Explica um conceito em PT-BR acessível |
| `/multiagents-tutorial` | Walkthrough guiado de 5-7 min |

## Conceitos

- **decanting** — protocolo obrigatório de extração de aprendizado ao fim de
  cada feature.
- **blast radius** — fricção proporcional ao risco: reversível-baixo é
  autônomo, irreversível-alto sempre pede confirmação humana.
- **trust ladder** — autonomia que escala com competência demonstrada
  (`trust.json` por agente).
- **guardrails** — poucos e catastróficos (force-push, rm -rf, secret commit,
  identity change). Proteção contra acidente, não contra agente malicioso.

Rode `/multiagents-explain <conceito>` para qualquer um deles em linguagem
acessível.

## Filosofia

> *Em domínio onde a fronteira anda rápido, abstrações grossas e controles
> uniformes convertem velocidade alheia em dívida própria. Construa menos, nos
> lugares certos.*

Thin wrapper sobre o Claude Code: usamos `Agent` tool, MCP, hooks e Skills como
vêm. O plugin só abstrai convenção de pastas, protocolo de boot/decanting,
dashboard, uma CLI fina e templates.

## Aviso

Este plugin orquestra agentes que executam código, fazem chamadas pagas a APIs
e modificam seu sistema de arquivos. Os guardrails já vêm ligados; monitore o
dashboard e revise commits antes de push. MIT — os autores não respondem por
uso indevido.

## Licença

MIT © 2026 Giordano Ribeiro Eulalio Cabral.
