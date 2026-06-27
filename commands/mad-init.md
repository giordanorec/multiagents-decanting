---
description: "Inicializa projeto multiagente (Discovery + estrutura + agentes habilitados + dashboard)."
---

Você vai iniciar um projeto multiagente em **modo decanting nativo**: cada feature é uma sessão viva via Agent tool (com SendMessage quando disponível), e o aprendizado é externalizado obrigatoriamente ao fim (decanting). Nada de `claude -p`, `sessions.json` ou processos em background.

Toda interação com o usuário é em **português brasileiro**, tom didático.

## Convenção de invocação da CLI

**Importante:** no `init` o projeto ainda NÃO tem `scripts/` (é o init que os cria). Portanto, para o passo de `init`, use a CLI **empacotada no plugin**. Descubra a raiz do plugin:

```bash
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
if [ -z "$PLUGIN_ROOT" ] || [ ! -f "$PLUGIN_ROOT/scripts/mad.py" ]; then
  PLUGIN_ROOT=$(find "$HOME/.claude/plugins" -maxdepth 6 -type f -path "*/mad/*/scripts/mad.py" 2>/dev/null | head -1 | xargs -r dirname | xargs -r dirname)
fi
PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
```

Use `"$PY" "$PLUGIN_ROOT/scripts/mad.py" <subcomando>` para o **init**. Depois que o init rodar, o projeto passa a ter seu próprio `scripts/`, e os demais comandos podem usar `"$PY" scripts/mad.py <subcomando>` (ou continuar usando `$PLUGIN_ROOT` — ambos funcionam).

## Pré-check

1. Verifique se já existe `multiagents-decanting.toml` na raiz. Se sim, o projeto já foi inicializado — **aborte** com a mensagem: "Projeto já tem multiagentes ativo; use /mad-dashboard ou /mad-doctor."
2. Verifique Python 3.9+: rode `python3 --version` (ou `python --version`). Se não houver Python ou for < 3.9, aborte com instrução curta de instalação.
3. Verifique a versão do Claude Code: `claude --version`. Se >= 2.1.77, informe que SendMessage está disponível (continuação multi-turn via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). Se for mais antigo, informe que a continuidade entre calls será via boot reconstruindo de `handoff.md` (fallback universal, funcionalmente equivalente).

## Discovery (conduzido pela skill `mad-discovery`)

**Primeiro, invoque a skill `mad-discovery`** (via a ferramenta Skill, ou carregando
`skills/mad-discovery/SKILL.md` do plugin) e conduza o Discovery por ela — é o
protocolo completo (postura + rigor). **Não faça um formulário.** O resumo abaixo é
só o esqueleto; o detalhe (mapa de cobertura, premortem, saturação) vive na skill:

1. **Calibre a profundidade no começo** — pergunte se o usuário quer modo **expresso**
   ou **profundo**, recomendando com base no que farejou.
2. **Postura, não checklist** — antecipe, desconfie, exponha hipóteses como suspeitas,
   alterne entre afunilar e abrir portas, recomende em vez de dar menu. Um fio por vez.
3. **Disciplina Mom-Test** — quando o usuário especular sobre o futuro, puxe pro
   comportamento passado e concreto ("como resolvem isso hoje? o que já tentaram?").
   Nunca pergunta capciosa.
4. **Ilumine o mapa de cobertura** (rubrica privada, não recitada): problema & dor;
   quem usa/opera/decide; comportamento atual & alternativas; critério de sucesso;
   escopo **e não-objetivos**; restrições (stack, custo/budget, compliance, prazo,
   time, infra); blast-radius; premissas; unknowns; quem opera no fim; tipo de projeto.
5. **No modo profundo**, antes de cravar: rode um **premortem** ("imagine que fracassou
   em 6 meses — o que matou?") e **nomeie as premissas** (desejável/viável/factível).
6. **Read-back periódico** e pare só na **saturação** (mapa iluminado + read-back limpo
   + nenhuma premissa nova). Veja `mad-discovery` §8.

O `--type` sai da dimensão "tipo de projeto"; o `--budget` da dimensão "restrições"
(default $50/dia); o `--name` do nome próprio do projeto (NÃO use "mad" nem "decanting");
o `--agents` da sugestão por tipo (abaixo), confirmada com o usuário.

## Setup

Fechada a saturação do Discovery, rode o inicializador da CLI com os parâmetros colhidos:

```
"$PY" "$PLUGIN_ROOT/scripts/mad.py" init \
  --name "<nome-do-projeto>" \
  --type "<ml|web|cli|jogo|documento|outro>" \
  --agents "<lista,separada,por,virgula>" \
  --budget "<valor-em-USD-por-dia>"
```

O `init` cria a estrutura de pastas, copia os templates de memória, gera `multiagents-decanting.toml` com defaults + ajustes do Discovery, prepara `memory/<agente>/` para cada especialista (identity, dossier, decisions, handoff, trust.json com score 50), copia `scripts/`, `dashboard/`, hooks e wira os hooks em `.claude/settings.json`. Para cada especialista, o registro de `subagent_type` vai para `.claude/agents/<role>.md`.

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

- Inicie o dashboard em background: `"$PY" scripts/mad.py dashboard --background`
- Verifique a saúde: `"$PY" scripts/mad.py doctor`

## Despacho de especialistas (como o Arquiteto trabalha depois)

Não existe comando `drive` próprio. O Arquiteto escreve a spec em `specs/feature-NNN-<slug>.md` e despacha via Agent tool nativo:

```
Agent(subagent_type="mad:<role>",
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

Use /mad-dashboard para reabrir o dashboard, /mad-doctor para
verificar saúde, /mad-decant <agente> para forçar decanting manual.
```
