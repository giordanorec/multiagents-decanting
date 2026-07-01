# Constituição do Projeto — {{projeto}}

> Regras **inegociáveis**. Valem acima de conveniência, pressa ou "boa vontade".
> O **Arquiteto** (orquestrador/maestro) é o **guardião** desta constituição.
> A máquina de estados e os hooks do mad **enforçam** o que dá pra enforçar;
> o resto é dever constitucional do Arquiteto, verificável nos artefatos.

## Art. 1 — Documentação e código andam JUNTOS (a regra-mãe)

O código e a documentação do projeto **nunca divergem**. Em todo ciclo:

1. A **especificação** de cada feature reflete o **as-built** (o que foi de fato
   construído), não só a intenção inicial. Se a implementação divergiu do
   planejado, a spec é **atualizada** — não abandonada.
2. A **documentação viva** (`docs/`: arquitetura, schema, pipeline, regras de
   negócio, etc.) é **atualizada** sempre que a feature a afeta.
3. As **decisões** relevantes viram entrada real no `docs/DECISOES.md` (o quê,
   por quê, alternativas descartadas) — não um toco.

**Nenhuma feature é "concluída" com spec ou docs desatualizados.** O fechamento
exige o registro `reports/feature-<NNN>/docs-sync.md` comprovando a sincronia.
Isso permite que **qualquer pessoa** (dev, DBA, arquiteto, tech lead, PM, tester)
ou **IA externa** entenda o projeto **além da codebase**, só pelos documentos.

## Art. 2 — O processo não se pula

As fases do projeto (entender → especificar → montar time → construir → validar →
recomeçar) seguem em ordem. O Agent tool, git push e escrita fora do estado são
bloqueados por hook fora da fase certa. Pular etapa é impossível, não indesejável.

## Art. 3 — Decisões difíceis de desfazer pedem gente

Ações irreversíveis de alto impacto (deploy destrutivo, apagar dados, gastar
dinheiro, força em produção) exigem confirmação humana explícita. Guardrails
catastróficos são duros e não se contornam sem bypass registrado.

## Art. 4 — Decanting é obrigatório

Ao fim de cada feature, o especialista externaliza o aprendizado em arquivo
(`memory/<agente>/`, `reports/`). Sessão é memória de trabalho; a fonte da
verdade são os documentos versionados.

## Art. 5 — Segredos nunca entram no repositório

`.env`, chaves, tokens e credenciais jamais são commitados. A telemetria
sanitiza segredos. Violação é bloqueada por hook.

## Art. 6 — Transparência

O que os agentes fazem é observável (painel ao vivo). O estado do workflow é
sempre visível e verdadeiro. Nada de progresso fantasma.

---

*Emendar esta constituição é uma decisão de peso: registre a emenda no
`docs/DECISOES.md` com justificativa. O Arquiteto zela por ela em toda sessão.*
