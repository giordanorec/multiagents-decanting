---
description: "Auditoria de COERÊNCIA: um revisor confere se spec, docs e código concordam (Constituição Art. 1)."
---

Você é o Arquiteto. Este comando roda uma **auditoria de coerência** do projeto: garantir
que **especificação, documentação viva, código, testes e decisões concordam entre si**
(Constituição, Art. 1 e 2). Não é o gate por-feature (aquele só checa que o `docs-sync`
existe); aqui um revisor lê de verdade e aponta **divergências**.

## Quando usar
- Antes de ir pra fase de testar/validar (pré-release) — recomendado.
- Quando o `/mad-doctor` avisar que o código está mais novo que a doc.
- Sempre que bater a dúvida "será que a doc ainda reflete o sistema?".

## Passos

1. Determine o que auditar (o projeto todo, ou uma área). Prepare um resumo dos artefatos:
   `docs/` (arquitetura, schema, pipeline, regras), `specs/`, o código-fonte relevante,
   e `docs/DECISOES.md`.

2. **Despache um revisor** (o `docs-writer`; se envolver testes, também o `qa-tester`)
   via Agent tool, com a tarefa: *"Leia a documentação viva (`docs/`), as specs e o
   código correspondente. Aponte TODA divergência entre o que os documentos dizem e o
   que o código faz: doc desatualizada, feature no código sem doc, decisão tomada sem
   registro, spec que não bate com o as-built. Para cada achado: arquivo, o que diverge,
   e a correção sugerida. Escreva o relatório em `reports/audits/<data>-coerencia.md`."*

3. **Leia o relatório.** Para cada divergência real:
   - doc desatualizada → atualize o doc vivo;
   - decisão não registrada → registre no `DECISOES.md`;
   - spec fora do as-built → atualize a spec;
   - código sem doc → documente (ou questione se o código deveria existir).

4. Registre a auditoria no `docs/DECISOES.md` (data, o que foi auditado, divergências
   achadas e corrigidas). Se estava tudo coerente, registre isso também.

5. Reporte ao usuário em linguagem humana: "conferi se a documentação bate com o
   sistema; achei X pontos fora do lugar e já acertei" (ou "está tudo coerente").

**Regra:** auditoria não é decorativa. Divergência achada é divergência corrigida no
mesmo ciclo — a doc volta a espelhar o código antes de seguir.
