# Estado — multiagents-decanting (plugin) — 2026-06-30

> Snapshot global do desenvolvimento do plugin. Sobrescrito a cada sessão.

## Onde estamos

**v1.2 (Tier 3) implementado e verde (68 testes).** Tier 1, 2 e 3 entregues e
lançados (releases `mad--v1.0.0`, `v1.1.0`, `v1.2.0`). Distribuição via hub
`giordanorec/ai-coding-tools`. Discovery canônica cross-tool em `giordanorec/skills`.

## Componentes

| Componente | Estado |
|---|---|
| CLI Python (mad, doctor, init, inspect, dashboard, resilience, notify, a2a, voice) | ✅ |
| **11 agentes** (Tier 1: arquiteto/pipeline-dev/qa-tester; Tier 2: dba/frontend-dev/devops-installer/docs-writer; Tier 3: llm-prompt/mobile-dev/asset-designer/security-auditor) | ✅ |
| 15 slash commands `/mad-*` (init, dashboard, doctor, inspect, trust, decant, enable, explain, tutorial, upgrade, migrate×2, notify, voice, a2a) | ✅ |
| Skills `mad-workflow` + `mad-discovery` | ✅ |
| Hooks (guardrails + budget/circuit + OTel + trust + decant-check) | ✅ |
| Dashboard HTML+WS+PWA + polish (drag-drop/filtros/pin/sons) | ✅ |
| Notificações (Telegram/Slack), A2A card, voz local (faster-whisper opt-in) | ✅ |
| Docker + devcontainer | ✅ |
| Testes (68, pytest) | ✅ verde |

## Roadmap restante (honesto)

- **Cross-tool real:** mad/brainstorm ainda Claude Code; portar via dual-format
  (SKILL.md + MCP). Estrutura do `catalog.json` pronta.
- **Integrações que precisam de credencial/serviço:** WhatsApp Business API (CA-303),
  TTS de saída (CA-301), Ollama ativo (CA-305), eval contínuo DeepEval/Promptfoo
  (CA-309), sandboxing E2B/Firecracker (CA-308) — scaffolds/configs prontos, ativação
  depende do usuário.
- **Validação real Win/macOS** + habilitar GitHub Actions (CI matrix escrito).
- **A2A V2:** servir o card em `/.well-known/agent.json` via HTTP.

## Como manter

`docs/DECISOES.md` = log de decisões. Fonte da verdade da discovery =
`giordanorec/skills/discovery` (mad sincroniza). Plugins novos = entrada no
`catalog.json` do hub. Versão = bump no `plugin.json` + tag `mad--vX.Y.Z` + release.
