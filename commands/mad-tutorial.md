---
description: "Tutorial interativo embutido (walkthrough guiado para os primeiros usos)."
---

Conduza um walkthrough guiado de 5–7 minutos do multiagents-decanting. Narre cada passo em **português brasileiro**, com tom didático, esperando o usuário acompanhar.

## Convenção de invocação da CLI

Use `python3 scripts/mad.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad.py <subcomando>`.

## Roteiro

1. **Apresentação (1 parágrafo).** Explique o que é o mad: um Arquiteto que coordena especialistas via Agent tool nativo do Claude Code, sem processos em background; cada feature é uma sessão viva que externaliza aprendizado ao fim (decanting); memória institucional em arquivo, trust ladder por agente e um dashboard local.

2. **Projeto fictício temporário.** Crie um diretório de tutorial isolado, ex: `/tmp/mad-tutorial-<timestamp>/` (no Windows, use a pasta temp equivalente). Avise que nada disso toca o projeto real do usuário.

3. **Habilite 2 agentes** — `arquiteto` e `pipeline-dev` — usando `python3 scripts/mad.py init` (ou `enable`) dentro do diretório de tutorial. Mostre os arquivos de `memory/` criados.

4. **Mostre o dashboard.** Inicie com `python3 scripts/mad.py dashboard --background` e aponte a URL `http://localhost:8765`. Explique brevemente o que aparece (um personagem por agente, status, métricas).

5. **Escreva uma spec simples** em `specs/feature-001-soma.md`: "crie um script Python que soma 2 e 2 e imprime o resultado". Mostre o conteúdo da spec.

6. **Despache o especialista.** Faça uma Agent call para o pipeline-dev:
   ```
   Agent(subagent_type="mad:pipeline-dev",
         description="Tutorial — soma 2+2",
         prompt="Leia specs/feature-001-soma.md, siga seu protocolo de boot,
                 execute, decante e retorne report.")
   ```
   Narre o processo e mostre os eventos OTel chegando no dashboard.

7. **Mostre o resultado** — o `reports/feature-001-soma/pipeline-dev.md` devolvido e os arquivos de `memory/pipeline-dev/` que foram atualizados (decisions, lessons, trust).

8. **Mostre o handoff** que ficou: `memory/pipeline-dev/handoff.md`. Explique que é por ele que a próxima call reconstrói contexto.

9. **Encerramento.** Pergunte se o usuário quer **apagar o tutorial** (remova o diretório temporário) ou **explorar mais**. Lembre dos comandos reais: `/mad-init`, `/mad-dashboard`, `/mad-doctor`, `/mad-inspect`, `/mad-decant`.
