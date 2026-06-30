---
description: "Gera o Agent Card (A2A — Linux Foundation) de um agente, para interop com agentes externos."
argument-hint: "<agente> [--write]"
---

Gere o Agent Card compatível com A2A do agente `$ARGUMENTS`.

1. Rode `python3 scripts/mad.py a2a $ARGUMENTS` (acrescente `--write` para gravar em
   `memory/<agente>/agent-card.json`).
2. Apresente o card (nome, descrição, capabilities, skills, convenção de memória).

O card descreve o agente de forma que sistemas A2A externos (Google, Microsoft, etc.)
consigam descobri-lo e interagir. Servir o card em `/.well-known/agent.json` via HTTP
é roadmap (V2). Hoje o card é gerado a partir do `identity.md` + frontmatter do agente.
