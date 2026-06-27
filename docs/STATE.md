# Estado — multiagents-decanting (plugin) — 2026-06-27

> Snapshot global do desenvolvimento do plugin. Sobrescrito a cada sessão.

## Onde estamos

v1.0 Tier 1 implementado e verde (54 testes). Núcleo, agentes, comandos, hooks,
dashboard, resiliência e i18n funcionais e validados end-to-end no Linux.

## Componentes

| Componente | Estado |
|---|---|
| CLI Python (`_utils`, `decanting`, `doctor`, `init`, `inspect_agent`, `dashboard_server`, `resilience`) | ✅ funcional |
| 3 agentes (arquiteto, pipeline-dev, qa-tester) | ✅ self-contained |
| 10 slash commands `/mad-*` | ✅ |
| Skill `mad-workflow` | ✅ |
| 8 hooks (4 guardrails + budget/circuit + OTel + trust + decant-check) | ✅ wireados via settings.json |
| Dashboard HTML+WS+PWA vanilla + 11 avatares | ✅ servindo HTTP + WS ao vivo |
| Templates (memory/docs/spec/report/agent) | ✅ validados |
| Locale PT-BR/EN | ✅ |
| Wrappers shell (bash/bat/ps1) | ✅ |
| Testes (54, pytest) | ✅ verde |

## Gaps conhecidos (honestos)

- **Execução real Win/macOS:** código portável (pathlib, utf-8, sem unix-only),
  mas só rodado no Linux. Validar nas máquinas-alvo (CA-080/081).
- **CA-017 decant de emergência SIGTERM:** em modo frio não há processo de agente
  para sinalizar; o mecanismo real é o protocolo "atualiza handoff a cada
  milestone". Não há signal handler dedicado.
- **CA-073 métricas OTel formais:** emitimos spans com atributos de token/custo
  que o dashboard agrega; não emitimos instrumentos de métrica OTLP separados.
- **CI matrix cross-platform (CA-080..082):** workflow do GitHub Actions ainda
  não escrito.

## Próximos passos

1. CI GitHub Actions (matrix Win/Mac/Linux × Python 3.9-3.13).
2. Validação real nas máquinas-alvo.
3. Instalar como plugin no Claude Code do Giordano e dogfoodar `/mad-init`
   num projeto real (E2E da invocação via Agent tool — fora do escopo dos testes).
4. Tier 2 (dba/frontend-dev/devops-installer/docs-writer + migração v0.2).
