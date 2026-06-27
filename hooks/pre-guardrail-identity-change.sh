#!/usr/bin/env bash
# pre-guardrail-identity-change.sh — PreToolUse(Edit, Write, MultiEdit)
#
# Bloqueia edição/escrita de memory/<agente>/identity.md, a menos que
# DECANTING_ALLOW_IDENTITY_CHANGE=1 esteja setado.
#
# A identidade do agente (papel, escopo, restrições não-negociáveis) é o
# contrato dele. Mudá-la silenciosamente corrompe a memória institucional.
#
# Bloqueio = exit 2 + stderr. Parse falho / path não-identity = exit 0. Sem jq.
INPUT="$(cat)"
DECANTING_HOOK_INPUT="$INPUT" python3 <<'PYEOF'
import os, sys, json, re

def allow():
    sys.exit(0)

try:
    d = json.loads(os.environ.get("DECANTING_HOOK_INPUT", "") or "{}")
except Exception:
    allow()

if d.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
    allow()

if os.environ.get("DECANTING_ALLOW_IDENTITY_CHANGE") == "1":
    allow()

ti = d.get("tool_input") or {}
path = ti.get("file_path") or ti.get("path") or ti.get("notebook_path") or ""
if not path:
    allow()

# Normaliza separadores (Windows) e casa memory/<agente>/identity.md.
norm = str(path).replace("\\", "/")
if not re.search(r"(?:^|/)memory/[^/]+/identity\.md$", norm):
    allow()

sys.stderr.write(
    "\n[multiagents-decanting] BLOQUEADO: alteração de identity.md.\n\n"
    "  Arquivo: " + str(path) + "\n\n"
    "identity.md define papel, escopo e restrições não-negociáveis do agente —\n"
    "é o contrato dele. Mudanças aqui não são trabalho de rotina e precisam de\n"
    "decisão consciente.\n\n"
    "Se a mudança é intencional, rode a ação com a flag de liberação:\n"
    "  DECANTING_ALLOW_IDENTITY_CHANGE=1 <sua operação>\n\n"
    "Para ajustes de estado/aprendizado do agente, use os outros arquivos de\n"
    "memória (handoff.md, decisions.md, lessons.md, state.md), não identity.md.\n"
)
sys.exit(2)
PYEOF
