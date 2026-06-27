---
description: "Explica um conceito do plugin em linguagem natural acessível (para leigos)."
argument-hint: "<conceito> (ex: decanting, trust ladder, blast radius)"
---

Explique o conceito `$ARGUMENTS` em **português brasileiro**, linguagem acessível, sem jargão técnico. Use uma analogia do mundo real e dê pelo menos 1 exemplo concreto.

Se `$ARGUMENTS` estiver vazio ou não corresponder a nenhum conceito conhecido, liste os conceitos disponíveis e peça que o usuário escolha um.

## Conceitos cobertos

- **decanting** — protocolo de extração de aprendizado ao fim de cada feature: o especialista "despeja" o que aprendeu em arquivos de memória antes de devolver controle. (Analogia: decantar vinho — separar o que importa do sedimento.)
- **trust ladder** — autonomia que escala com a performance do agente: quanto melhor o histórico, menos confirmações ele precisa pedir.
- **blast radius** — quão irreversível/abrangente é uma ação. Quanto maior o raio, mais cuidado e confirmação antes de agir.
- **circuit breaker** — proteção contra loops descontrolados: corta a execução quando algo dispara repetidamente sem progresso.
- **modo frio / decanting nativo** — como funciona uma chamada ao especialista: sem processo vivo em background; cada call é uma sessão própria que lê memória, executa e decanta.
- **boot protocol** — o que o agente lê antes de começar a trabalhar (identidade, dossiê, handoff, decisões), para reconstruir contexto.
- **SendMessage** — primitiva para continuar a conversa com o mesmo agente sem ele perder o contexto da call anterior (Claude Code v2.1.77+ com env var).
- **Agent tool** — primitiva nativa do Claude Code que invoca um subagente (`subagent_type=...`).
- **agente / especialista** — papéis dentro do sistema (arquiteto, pipeline-dev, qa-tester, dba, etc); um agente = um papel concreto.
- **arquiteto** — o coordenador, único ponto de contato do humano; escreve specs, despacha especialistas, integra entregas.
- **spec** — o "ticket" que o Arquiteto escreve para um especialista (objetivo, inputs, outputs, critérios de aceite).
- **report** — a entrega do especialista ao fim da feature.
- **handoff** — a nota da última call para a próxima ("onde parei, o que ficou pendente").
- **OTel (OpenTelemetry)** — padrão de observabilidade; a telemetria que alimenta o dashboard.
- **dashboard** — web app local que mostra cada agente como personagem, com status, ação corrente e métricas.

(Adicione conceitos correlatos conforme a pergunta exigir, mantendo o tom didático.)
