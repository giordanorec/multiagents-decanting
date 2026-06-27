# {{projeto}} — CLAUDE.md

## Contexto
{{descricao_curta}}

## Stack
- {{linguagem_principal}}
- {{frameworks}}
- {{infra}}

## Convenções de código
- {{convencao_1}}
- {{convencao_2}}

## Idioma
- Comunicação com usuário e em documentos: PT-BR.
- Comentários e identifiers no código: {{en|pt}}.

## Multiagente
Este projeto usa o plugin `multiagents-decanting`. Estrutura em:
- `docs/` — especificação viva
- `specs/` — tickets do Arquiteto
- `reports/` — entregas dos especialistas
- `memory/` — memória persistente por agente
- `logs/otel/` — telemetria runtime (gitignored)

## Comandos úteis
- `/multiagents-dashboard` — abrir dashboard local
- `/multiagents-doctor` — verificar saúde do projeto
- `/multiagents-decant <agente>` — forçar decanting manual de um agente
- `/multiagents-inspect <agente>` — ver estado de um agente
- `/multiagents-trust <agente>` — ver trust score

## Regras não-negociáveis
- Nunca push em main sem revisão humana.
- Nunca commit de secrets (.env, *.key, credentials.json).
- Sempre conventional commits leves (feat:, fix:, docs:, refactor:).
