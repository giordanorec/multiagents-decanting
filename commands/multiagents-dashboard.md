---
description: "Abre, reabre ou encerra o dashboard web local."
argument-hint: "[--stop] (opcional)"
---

Gerencie o dashboard web local do projeto. Tudo em português brasileiro.

## Convenção de invocação da CLI

Use `python3 scripts/multiagents.py <subcomando>`. Se `python3` não existir, caia para `python scripts/multiagents.py <subcomando>`.

## Se o argumento for `--stop`

Se `$ARGUMENTS` contiver `--stop`, encerre o dashboard:

```
python3 scripts/multiagents.py dashboard --stop
```

Confirme: "Dashboard encerrado."

## Caso contrário (abrir / reabrir)

1. Verifique se já há um processo do dashboard rodando:

   ```
   python3 scripts/multiagents.py dashboard --status
   ```

2. Se **não** estiver rodando, inicie em background:

   ```
   python3 scripts/multiagents.py dashboard --background
   ```

3. Tente abrir a URL `http://localhost:8765` no browser padrão (cross-platform: `xdg-open` no Linux, `open` no macOS, `start` no Windows). Se não conseguir abrir automaticamente, apenas informe a URL.
4. Confirme: "Dashboard em http://localhost:8765. Use `/multiagents-dashboard --stop` para encerrar."
