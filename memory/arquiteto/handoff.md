# Handoff — arquiteto (plugin multiagents-decanting)

**Última atualização:** 2026-06-27 (sessão de implementação inicial)

## Em andamento agora
- v1.0 Tier 1 implementado e verde (54 testes). Commitado.
- Faltam: CI cross-platform, validação real Win/Mac, instalação como plugin e
  dogfood E2E da invocação via Agent tool num projeto real.

## Próximos passos imediatos
1. Escrever `.github/workflows/ci.yml` (matrix os × python).
2. Instalar o plugin no Claude Code do Giordano e rodar `/decanting-init` num
   projeto-teste real para validar o despacho via Agent tool.
3. Decidir com o Giordano: publicar no marketplace `giordanorec/...`?

## Avisos para o próximo eu
- A spec (`_spec/`) foi escrita por outra IA; trata versões/specs como suspeitas.
  Já corrigido: feature-detection em vez de versão hardcodada (DECISÕES #1).
- WebSocket roda em `porta_http + 1000` (decisão de design pra evitar ASGI); o
  frontend já conecta lá. Não "consertar" isso achando que é bug.
- Hooks wireados SÓ em `.claude/settings.json` do projeto (não plugin-level) pra
  evitar double-fire — DECISÕES #6.
- Dois caminhos de subagent_type (namespaced do plugin + project-local) —
  DECISÕES #5. Validação E2E da invocação exige plugin instalado.
- Budget/circuit são enforced de verdade pelo hook `pre-budget-circuit.py`
  (soma custo dos spans OTel do dia). Testado.

## Como retomar em um minuto
Leia `docs/STATE.md` (estado dos componentes + gaps) e `docs/DECISOES.md` (6
decisões registradas). Rode `.venv/bin/python -m pytest tests/ -q` para confirmar
verde. O código é todo Python stdlib + pathlib; entry point `scripts/decanting.py`.
