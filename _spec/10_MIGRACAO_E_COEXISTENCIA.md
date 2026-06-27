# 10 — Migração e Coexistência (v0.2.0 → v1.0)

## 10.1 Decisão central: substituição, não upgrade

Plugin v0.2.0 (`multiagentes-giordano`) e v1.0 (`multiagents-decanting`) são **plugins diferentes**, com filosofias diferentes. Não há mecanismo automático de upgrade. Projetos novos usam v1.0; projetos antigos podem migrar com guia ou continuar em v0.2.0 indefinidamente (este pode permanecer no marketplace).

Razões da separação:
- Filosofia muda (decanting vs sessão crescente).
- Infra muda (HTML+WS vs tmux+Tilix).
- Convenção de pastas muda (`memory/` rica vs `MEMORY.md` único).
- Comandos mudam (alguns novos, alguns aposentados).
- Dependências mudam (Python obrigatório; Bash não suficiente).

## 10.2 Coexistência local

Usuário pode ter os dois plugins instalados simultaneamente em Claude Code. Projetos antigos continuam funcionando com `multiagentes-giordano`; projetos novos usam `multiagents-decanting`. Não há colisão de namespaces porque os comandos são distintos:

| v0.2.0 (`multiagentes-giordano`) | v1.0 (`multiagents-decanting`) |
|---|---|
| `/multiagente-init` (giordano) | `/multiagents-init` — sem colisão |
| `/multiagente-spawn` | `/multiagents-enable` — sem colisão |
| `/multiagente-dashboard` | `/multiagents-dashboard` — sem colisão |

**Sem colisão de namespaces** porque o plugin novo usa prefixo `/multiagents-` em vez de `/multiagente-`. Plugins coexistem nativamente.

Lista completa dos comandos novos:

- `/multiagents-init`
- `/multiagents-enable <agente>`
- `/multiagents-inspect <agente>`
- `/multiagents-dashboard`
- `/multiagents-decant <agente>`
- `/multiagents-doctor`
- `/multiagents-trust <agente>`
- `/multiagents-upgrade`
- `/multiagents-explain <conceito>`
- `/multiagents-tutorial`

## 10.3 Migração projeto v0.2.0 → v1.0

Comando dedicado: `/multiagents-migrate-from-v02`.

Faz:

1. **Backup completo** do projeto atual em `.backup-pre-migrate-<timestamp>/`.
2. **Detecta** estrutura v0.2.0 (`sessions.json`, `MEMORY.md`, `logs/`, etc).
3. **Preserva** sem tocar:
   - `docs/` (espec viva)
   - `specs/`
   - `reports/`
   - `.claude/agents/`
   - `CLAUDE.md`
4. **Migra** `memory/<agente>/MEMORY.md` → split em:
   - `memory/<agente>/handoff.md`: últimas N entradas
   - `memory/<agente>/lessons.md`: identifica aprendizados explícitos
   - `memory/<agente>/decisions.md`: identifica decisões explícitas
   - `memory/<agente>/state.md`: snapshot atual
   - `memory/<agente>/identity.md`: cria do template
   - `memory/<agente>/dossier.md`: cria com placeholder
   - `memory/<agente>/trust.json`: cria com score 50 default
   (split é heurístico via LLM call ao próprio Claude; resultado vai pra revisão do usuário)
5. **Descarta** `sessions.json` do v0.2.0 (plugin novo não usa session_ids manuais; Claude Code gerencia subagents).
6. **Descarta** ou arquiva:
   - `logs/` antigo (move pra `.backup-pre-migrate/logs/`)
   - `status/` antigo (recria do zero)
   - Scripts antigos em `scripts/` (substitui pelos novos)
   - Dashboard tmux (remove `scripts/open_dashboard.sh`, etc)
7. **Cria** estruturas novas:
   - `multiagente.toml` com defaults + perguntas ao usuário
   - `dashboard/` (HTML+WS)
   - `.claude/hooks/` com guardrails
   - `bin/` com wrappers
8. **Inicia** dashboard novo: `python scripts/multiagents.py dashboard --background`.
9. **Roda doctor** para confirmar.
10. **Apresenta** ao usuário o diff: o que mudou, o que ficou, o que precisa revisão manual.

Risco: split de `MEMORY.md` em arquivos novos é heurístico e pode misturar coisas. Por isso o backup é obrigatório e o usuário deve revisar antes de descartar.

## 10.4 Migração agente por agente (opcional)

Caso usuário não queira migrar tudo de uma vez:

```bash
/multiagents-migrate-agent <agente>
```

Migra só um agente, deixando os outros em formato v0.2.0. Útil quando há time grande de agentes e migração precisa ser gradual.

## 10.5 Quem deve migrar e quem não deve

**Deve migrar:**
- Projetos novos, ainda em Discovery → use v1.0 direto.
- Projetos antigos com problema de billing (cuidado com `claude -p` em escala).
- Projetos antigos em Windows nativo (dashboard novo resolve).
- Projetos onde memória institucional é importante (decanting é decisivo).

**Pode continuar em v0.2.0:**
- Projetos terminados, em manutenção mínima.
- Projetos em Linux com tmux funcionando bem.
- Projetos pequenos onde over-engineering não justifica.

**Decisão recomendada para projeto ML_AtivosJudiciais (caso atual):** migrar. Windows nativo + memória institucional crítica + projeto longo.

## 10.6 Aposentadoria gradual de v0.2.0

Sugestão de timeline (decisão do mantenedor):

- **Mês 0:** v1.0 lança. v0.2.0 continua disponível e suportado.
- **Mês 3:** v0.2.0 entra em "maintenance only" (security fixes; sem features).
- **Mês 6:** v0.2.0 marca-se como "deprecated" no README. Aviso no init.
- **Mês 12:** v0.2.0 archive (last release tagged). Repo permanece read-only para referência histórica.

## 10.7 Comparação rápida v0.2.0 ↔ v1.0

| Aspecto | v0.2.0 | v1.0 |
|---|---|---|
| Filosofia | sessão persistente como ativo crescente | decanting: sessão por feature |
| Dashboard | tmux + Tilix (Linux-only) | HTML+WS local + PWA + TUI fallback |
| Memória | `memory/<agente>/MEMORY.md` único | 7 arquivos especializados + trust.json |
| Workflow patterns | improviso | 5 patterns Anthropic explícitos |
| Resilience | retry básico | circuit breaker + budget + graceful degradation |
| Observabilidade | logs livres | OpenTelemetry GenAI nativo |
| Cost guard | nenhum | budget enforcement com auto-encerramento |
| Trust | nenhum | trust ladder com `trust.json` por agente |
| Claude Code | resume direto | detecção de versão + SendMessage adaptive |
| i18n | inglês implícito | PT-BR default + EN |
| Plataforma | Linux primário | Windows/Mac/Linux igualmente |
| Onboarding leigo | nenhum | Discovery conversacional + templates + tutorial |
| Constitutional | nenhum | hierarquia 4-tier Anthropic embutida |
| Distribuição | bash + python misto | Python puro + wrappers shell + Docker (roadmap) |

## 10.8 Compatibilidade de templates entre versões

Se o usuário tiver criado templates próprios em `templates/docs/00_OBJETIVO.md` etc no v0.2.0, esses continuam aplicáveis no v1.0 — o formato Markdown não muda. Migração script preserva.

## 10.9 Suporte transitivo

Se v0.2.0 estava configurado com hook custom do usuário, migração tenta importar. Hooks não-óbvios precisam de revisão manual. Plugin novo documenta diferenças de hook API (se houver).
