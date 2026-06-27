# Exemplos por tipo de projeto

Como o `/multiagents-init` configura o time conforme o tipo, e que primeira
feature faz sentido em cada caso. Todos começam igual: `claude` →
`/multiagents-init` → responda o Discovery → `/multiagents-dashboard`.

## ML / pipeline de dados

**Time sugerido:** arquiteto, pipeline-dev, qa-tester, dba.

**Primeira feature típica:** "Ingerir o dataset bruto, normalizar encoding
(latin-1 → utf-8) e materializar uma tabela limpa."

O Arquiteto escreve `specs/feature-001-ingestao.md`, despacha o `dba` para o
schema e o `pipeline-dev` para o parsing. Cada um decanta o que aprendeu sobre o
formato dos dados em `memory/<agente>/lessons.md`.

## App web

**Time sugerido:** arquiteto, pipeline-dev, frontend-dev, qa-tester.

**Primeira feature típica:** "Tela de login com sessão e validação de e-mail."

Pattern `chain`: pipeline-dev faz a API de auth → frontend-dev faz a tela →
qa-tester valida o fluxo ponta a ponta.

## CLI / automação

**Time sugerido:** arquiteto, pipeline-dev, qa-tester, docs-writer.

**Primeira feature típica:** "Comando que lê um CSV e gera um relatório."

Pattern `chain`: pipeline-dev implementa → qa-tester testa casos de borda →
docs-writer escreve o `USO.md`.

## Jogo

**Time sugerido:** arquiteto, pipeline-dev, qa-tester, asset-designer.

**Primeira feature típica:** "Loop básico: jogador que move e pontua."

asset-designer gera placeholders visuais enquanto pipeline-dev faz a mecânica.

## Documento / conteúdo

**Time sugerido:** arquiteto, docs-writer.

**Primeira feature típica:** "Estruturar o documento em capítulos e escrever a
introdução."

Time mínimo: o Arquiteto coordena e o docs-writer escreve, decantando o tom e as
convenções de estilo em `memory/docs-writer/lessons.md`.

## Outro

O Discovery pergunta quais especialistas você quer. Habilite mais a qualquer
momento com `/multiagents-enable <agente>`.

---

Em todos os casos, ao terminar a feature o especialista **decanta** (grava
report, decisões, handoff, aprendizados) e o Arquiteto valida e atualiza o
`trust.json`. A próxima feature começa lendo o decantado — sem amnésia.
