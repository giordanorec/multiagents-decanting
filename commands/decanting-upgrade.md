---
description: "Atualiza o plugin para nova versão (preserva memória, docs, specs e reports do projeto)."
---

Atualize o plugin multiagents-decanting para uma versão mais recente, **preservando** todo o estado do projeto. Tudo em português brasileiro.

## Convenção de invocação da CLI

Use `python3 scripts/decanting.py <subcomando>`. Se `python3` não existir, caia para `python scripts/decanting.py <subcomando>`.

## Passos

1. Leia a versão atual em `multiagents-decanting.toml` (campo `version`).
2. Busque a última release no GitHub: `gh release view` ou `https://api.github.com/repos/giordanorec/multiagents-decanting/releases/latest`.
3. Compare via semver e mostre o diff de versão + o CHANGELOG relevante.
4. Política de confirmação por tipo de bump:
   - **Patch** (X.Y.Z+1): aplica automaticamente, sem confirmação.
   - **Minor** (X.Y+1.0): mostra changelog e pede confirmação simples.
   - **Major** (X+1.0.0): mostra changelog + nota de breaking changes e pede **confirmação dupla**.
5. Atualize **apenas** estas pastas/arquivos do plugin:
   - `scripts/`, `templates/`, `agents/`, `dashboard/`, `commands/`, `skills/`, `hooks/`
6. **NUNCA** sobrescreva o estado do projeto:
   - `memory/`, `docs/`, `specs/`, `reports/`, `CLAUDE.md`, `multiagents-decanting.toml`
7. Após copiar os arquivos novos, atualize o campo `version` em `multiagents-decanting.toml` para a nova versão (esta é a única edição permitida nesse arquivo).
8. Rode `python3 scripts/decanting.py doctor` para verificar compatibilidade pós-upgrade.
9. Reporte ao usuário um resumo das mudanças relevantes e o veredito do doctor.
