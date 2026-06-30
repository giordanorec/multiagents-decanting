---
description: "Envia uma notificação (Telegram/Slack) se houver canal configurado."
argument-hint: "<mensagem>"
---

Envie a notificação `$ARGUMENTS` pelos canais configurados.

1. Rode `python3 scripts/mad.py notify "$ARGUMENTS"` (fallback `python`).
2. Apresente o resultado: em quais canais foi enviado, ou que nenhum está configurado.

Se nada estiver configurado, explique ao usuário (em PT-BR) como ligar: preencher
`[notify]` em `multiagents-decanting.toml` (`telegram_bot_token` + `telegram_chat_id`
e/ou `slack_webhook_url`) **ou** definir as env vars `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`, `SLACK_WEBHOOK_URL`. Nada é enviado pra fora sem configuração
explícita; é opt-in.

Dica: o Arquiteto pode usar isto para avisar o usuário quando uma feature longa
termina ou quando o budget cruza o limiar de alerta.
