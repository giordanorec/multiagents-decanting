---
description: "Inicializa projeto multiagente (Discovery + estrutura + agentes habilitados + dashboard)."
---

Você vai iniciar um projeto multiagente em **modo decanting nativo**: cada feature é uma sessão viva via Agent tool (com SendMessage quando disponível), e o aprendizado é externalizado obrigatoriamente ao fim (decanting). Nada de `claude -p`, `sessions.json` ou processos em background.

Toda interação com o usuário é em **português brasileiro**, tom didático.

## Convenção de invocação da CLI

Use `python3 scripts/decanting.py <subcomando>`. Se `python3` não existir no sistema (comum no Windows), caia para `python scripts/decanting.py <subcomando>`. Detecte uma vez no começo e reutilize a forma que funcionou.

## Pré-check

1. Verifique se já existe `multiagents-decanting.toml` na raiz. Se sim, o projeto já foi inicializado — **aborte** com a mensagem: "Projeto já tem multiagentes ativo; use /decanting-dashboard ou /decanting-doctor."
2. Verifique Python 3.9+: rode `python3 --version` (ou `python --version`). Se não houver Python ou for < 3.9, aborte com instrução curta de instalação.
3. Verifique a versão do Claude Code: `claude --version`. Se >= 2.1.77, informe que SendMessage está disponível (continuação multi-turn via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). Se for mais antigo, informe que a continuidade entre calls será via boot reconstruindo de `handoff.md` (fallback universal, funcionalmente equivalente).

## Discovery (UMA pergunta por vez)

Faça as perguntas abaixo **em sequência**, esperando a resposta do usuário entre cada uma. NUNCA despeje todas de uma vez.

1. "Qual é o objetivo principal do projeto, em uma frase?"
2. "Quem usa o resultado disso, e como?"
3. "Que tecnologia/stack já está definida? (linguagem, frameworks, infra) Ou ainda em aberto?"
4. "Que tipo de projeto é? [ ] ML/pipeline de dados  [ ] App web  [ ] CLI/automação  [ ] Jogo  [ ] Documento/conteúdo  [ ] Outro"
5. "Há restrições não-óbvias? (compliance, dados sensíveis, prazo apertado, time pequeno, etc)"
6. "Quanto orçamento de tokens é razoável por dia? (default $50)"

## Setup

Depois de coletar as respostas, rode o inicializador da CLI passando os parâmetros do Discovery como flags:

```
python3 scripts/decanting.py init \
  --name "<nome-do-projeto>" \
  --type "<ml|web|cli|jogo|documento|outro>" \
  --agents "<lista,separada,por,virgula>" \
  --budget "<valor-em-USD-por-dia>"
```

O `init` cria a estrutura de pastas (ver `_spec/03_ESTRUTURA_DE_PASTAS.md`), copia os templates de memória (`_spec/05_TEMPLATES.md`), gera `multiagents-decanting.toml` com defaults + ajustes do Discovery, e prepara `memory/<agente>/` para cada especialista da lista (identity, dossier, decisions, handoff, trust.json com score 50). Para cada especialista, o registro de `subagent_type` vai para `.claude/agents/<role>.md`.

Antes de rodar o `init`, **sugira a lista de especialistas** com base no tipo de projeto e confirme com o usuário:

- **ML/pipeline:** arquiteto, pipeline-dev, qa-tester, dba (se houver dados)
- **App web:** arquiteto, pipeline-dev, frontend-dev, qa-tester
- **CLI/automação:** arquiteto, pipeline-dev, qa-tester, docs-writer
- **Jogo:** arquiteto, pipeline-dev, qa-tester, asset-designer
- **Documento/conteúdo:** arquiteto, docs-writer
- **Outro:** pergunte ao usuário quais papéis fazem sentido

Depois que o `init` rodar, complemente `CLAUDE.md` e `docs/00_OBJETIVO.md` com as respostas do Discovery (objetivo, público, stack, restrições) caso o `init` não as tenha preenchido por completo.

**Não há spawn.** Os agentes ficam "prontos" — a primeira Agent call será a primeira execução de cada um.

Por fim:

- Inicie o dashboard em background: `python3 scripts/decanting.py dashboard --background`
- Verifique a saúde: `python3 scripts/decanting.py doctor`

## Despacho de especialistas (como o Arquiteto trabalha depois)

Não existe comando `drive` próprio. O Arquiteto escreve a spec em `specs/feature-NNN-<slug>.md` e despacha via Agent tool nativo:

```
Agent(subagent_type="multiagents-decanting:<role>",
      description="...",
      prompt="Leia specs/feature-NNN-<slug>.md, siga seu protocolo de boot
              (memory/<role>/), execute, decante, retorne report.")
```

Paralelismo é trivial: múltiplas Agent calls numa única resposta rodam em paralelo (o Claude Code gerencia). Apresente sempre opções de custo (sequencial vs paralelo) antes de paralelizar.

## Mensagem final

```
Pronto. Projeto multiagente iniciado (decanting nativo).
- Dashboard: http://localhost:8765
- Especialistas habilitados: <lista>
- Próximo passo: descreva sua primeira feature e eu (Arquiteto) coordeno.

Cada especialista é invocado sob demanda via Agent tool (sem processos em
background, sem session_id manual). Memória vive em memory/<agente>/.

Use /decanting-dashboard para reabrir o dashboard, /decanting-doctor para
verificar saúde, /decanting-decant <agente> para forçar decanting manual.
```
