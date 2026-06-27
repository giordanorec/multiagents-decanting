---
description: "Habilita um especialista adicional num projeto já iniciado."
argument-hint: "<agente> (ex: dba, frontend-dev, docs-writer)"
---

Habilite o especialista `$ARGUMENTS` no projeto atual. Tudo em português brasileiro.

## Convenção de invocação da CLI

Use `python3 scripts/mad.py <subcomando>`. Se `python3` não existir, caia para `python scripts/mad.py <subcomando>`.

## Passos

1. Verifique que `multiagents-decanting.toml` existe na raiz. Se não existir, avise que o projeto ainda não foi inicializado e sugira `/mad-init`.
2. Verifique que existe um template de agente para `$ARGUMENTS` no plugin (`agents/$ARGUMENTS.md` ou template equivalente). Se o papel não existir, liste os papéis disponíveis e peça que o usuário escolha um válido.
3. Verifique que o agente ainda não foi habilitado (não existe `memory/$ARGUMENTS/`). Se já existir, **não sobrescreva** — informe que ele já está habilitado e sugira `/mad-inspect $ARGUMENTS`.
4. Rode o habilitador da CLI:

   ```
   python3 scripts/mad.py enable $ARGUMENTS
   ```

   Isso copia o template para `.claude/agents/$ARGUMENTS.md` (registrando o `subagent_type`) e cria `memory/$ARGUMENTS/` com os templates iniciais (identity, dossier, decisions, handoff, trust.json com score 50).
5. Pergunte ao usuário: "Quer que eu personalize o dossiê dele com contexto específico do projeto? (Sim/Não)"
6. Se **Sim**, conduza um mini-Discovery (3-4 perguntas focadas no papel) e atualize `memory/$ARGUMENTS/dossier.md` com o que coletar.
7. Confirme: "`$ARGUMENTS` habilitado. Pronto para ser invocado via Agent tool (`subagent_type=mad:$ARGUMENTS`)."
