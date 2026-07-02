# Sandbox (opcional) — full-auto seguro

O mad é **plug-and-play e NÃO exige Docker**. Este documento é só para quem quer uma
camada extra de isolamento ao rodar em **full-auto** (`--dangerously-skip-permissions`).

## Por que sandbox

Sem sandbox, full-auto dá ao agente acesso à sua máquina inteira. Com sandbox
(devcontainer/Docker), o agente roda **isolado**, só enxergando a pasta do projeto —
então você liga o full-auto à vontade, e um erro/injeção fica **preso no contêiner**.
O sandbox **habilita** o full-auto tranquilo; não impede nada.

## Como (opt-in, quem já tem Docker)

O repo já traz `.devcontainer/`. Abra o projeto no devcontainer (VS Code: "Reopen in
Container") ou rode o Claude Code dentro dele. Monte só a raiz do projeto como
read-write. Fora isso, nada muda: mesmos comandos, mesmo `mad`.

## Se você NÃO usa Docker

Tudo funciona igual, sem instalar nada. A proteção vem dos guardrails do próprio mad
(gates, escopo de escrita, guardrails catastróficos, audit-log). O sandbox é um extra,
não um pré-requisito.
