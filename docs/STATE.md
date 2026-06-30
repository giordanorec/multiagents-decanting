# Estado — multiagents-decanting (plugin) — 2026-06-30

> Snapshot global do desenvolvimento do plugin. Sobrescrito a cada sessão.

## Onde estamos

**v1.1 (Tier 2) implementado e verde (59 testes).** v1.0 (Tier 1) lançada e
publicada (tag `mad--v1.0.0`, release no GitHub). Plugin instalado e dogfoodado
pelo Giordano (discovery, rename para `mad`, etc.). Distribuição via hub
`giordanorec/ai-coding-tools`.

## Componentes

| Componente | Estado |
|---|---|
| CLI Python (`_utils`, `mad`, `doctor`, `init`, `inspect_agent`, `dashboard_server`, `resilience`) | ✅ funcional |
| 7 agentes (arquiteto, pipeline-dev, qa-tester + Tier 2: dba, frontend-dev, devops-installer, docs-writer) | ✅ self-contained |
| 12 slash commands `/mad-*` (inclui migração v0.2) | ✅ |
| Skills `mad-workflow` + `mad-discovery` (postura + rigor) | ✅ |
| 8 hooks (guardrails + budget/circuit + OTel + trust + decant-check) | ✅ wireados via settings.json |
| Dashboard HTML+WS+PWA vanilla + 11 avatares | ✅ servindo HTTP + WS ao vivo |
| Templates, Locale PT-BR/EN, wrappers shell | ✅ |
| Testes (59, pytest) | ✅ verde |
| Distribuição (hub catálogo + release v1.0) | ✅ |

## Gaps conhecidos / Tier 2 restante (honesto)

- **Dashboard polish (CA-201..204):** drag-drop reorder, filtros, pin, sons — não
  feito (secundário).
- **Extended thinking adaptive (CA-207):** não feito.
- **Execução real Win/macOS:** código portável, só rodado no Linux. CI matrix
  (`.github/workflows/ci.yml`) escrito mas só roda quando Actions for habilitado.
- **CA-017 SIGTERM / CA-073 métricas OTel formais:** decisões de design (ver
  release v1.0); mecanismos atuais cobrem o essencial.

## Próximos passos

1. Tier 2 polish: dashboard (drag-drop/filtros/pin/sons), extended thinking.
2. Validação real Win/macOS + habilitar CI.
3. Tier 3 (llm-prompt, mobile-dev, asset-designer, security-auditor; voice; etc.).
4. Portar `mad` cross-tool (dual-format) — estrutura do `catalog.json` já pronta.
