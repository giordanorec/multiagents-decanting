---
description: "Verifica a saúde do projeto multiagente (verde / amarelo / vermelho)."
---

Verifique a saúde do projeto multiagente e apresente um diagnóstico claro, em português brasileiro.

## Convenção de invocação da CLI

Use `python3 scripts/decanting.py <subcomando>`. Se `python3` não existir, caia para `python scripts/decanting.py <subcomando>`.

## Passos

1. Rode o diagnóstico:

   ```
   python3 scripts/decanting.py doctor
   ```

   (Se precisar parsear o resultado, use `doctor --json`.)

2. Apresente o relatório organizado nas seções abaixo, marcando cada item como **OK / atenção / falha**:

   **Versões**
   - Python: >= 3.9?
   - Claude Code: versão + suporte a SendMessage (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`).
   - Plugin multiagents-decanting: versão instalada vs última no marketplace.

   **Estrutura**
   - `multiagents-decanting.toml` presente.
   - `docs/` presente e populado (ou: faltam quais).
   - `memory/<cada agente>/` completo (ou: faltam quais arquivos).
   - `.gitignore` presente e correto.

   **Telemetria**
   - Spans OTel nas últimas 24h.
   - Última atividade por agente.
   - Agentes sem decanting há > 7 dias.

   **Budget**
   - Tokens consumidos hoje (vs máximo).
   - Custo estimado hoje (vs máximo).
   - % do budget.

   **Trust scores** — lista de cada agente com seu score.

   **Alertas**
   - Agentes habilitados mas nunca invocados (> 7 dias).
   - Agentes com último decanting > 7 dias atrás.
   - `lessons.md` de algum agente > 10000 palavras (sugerir poda).
   - Decanting "skipped" detectado em alguma call recente.

3. Veredito final: **🟢 Verde** (tudo saudável), **🟡 Amarelo** (avisos não-bloqueantes) ou **🔴 Vermelho** (problemas que exigem ação). Liste objetivamente o que corrigir em caso de amarelo/vermelho.
