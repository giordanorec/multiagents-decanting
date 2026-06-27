#!/usr/bin/env bash
# pre-guardrail-force-push.sh — PreToolUse(Bash)
#
# Bloqueia `git push --force` / `-f` / refspec `+main` contra main|master,
# a menos que DECANTING_ALLOW_FORCE_PUSH=1 esteja setado.
#
# Hook do Claude Code: recebe JSON no stdin {tool_name, tool_input{command}, cwd,...}.
# Bloqueio = exit 2 + mensagem no stderr. Qualquer outra coisa (parse falho,
# comando inofensivo) = exit 0 (libera). Guardrail nunca trava por bug próprio.
#
# Parse em python3 inline (sem jq). Input via env var para liberar aspas no script.
INPUT="$(cat)"
DECANTING_HOOK_INPUT="$INPUT" python3 <<'PYEOF'
import os, sys, json, re

def allow():
    sys.exit(0)

try:
    d = json.loads(os.environ.get("DECANTING_HOOK_INPUT", "") or "{}")
except Exception:
    allow()

if d.get("tool_name") != "Bash":
    allow()

cmd = ((d.get("tool_input") or {}).get("command") or "")
if not cmd.strip():
    allow()

# Override explícito do humano.
if os.environ.get("DECANTING_ALLOW_FORCE_PUSH") == "1":
    allow()

# Precisa ser um `git push`.
if not re.search(r"\bgit\s+push\b", cmd):
    allow()

# Indicadores de force.
has_force_flag = bool(
    re.search(r"--force(-with-lease)?\b", cmd)
    or re.search(r"(?:^|\s)-[a-zA-Z]*f[a-zA-Z]*(?=\s|$)", cmd)
)
plus_refspec = re.search(r"\+\s*(?:refs/heads/)?(main|master)\b", cmd)
mentions_main = re.search(r"\b(main|master)\b", cmd)

# Bare push (sem remote/branch posicional) empurra o branch atual — pode ser main.
bare_push = bool(re.match(r"^\s*git\s+push(?:\s+--?\S+)*\s*$", cmd.strip()))

dangerous = bool(plus_refspec) or (has_force_flag and (mentions_main or bare_push))

if not dangerous:
    allow()

sys.stderr.write(
    "\n[multiagents-decanting] BLOQUEADO: force-push em branch protegido.\n\n"
    "  Comando: " + cmd.strip()[:300] + "\n\n"
    "Force-push em main/master reescreve histórico publicado e é irreversível\n"
    "para quem já clonou. Por isso exige confirmação humana explícita.\n\n"
    "Se você REALMENTE quer fazer isso:\n"
    "  - prefira `git push --force-with-lease` (mais seguro que --force), e\n"
    "  - rode com a flag de liberação:\n"
    "      DECANTING_ALLOW_FORCE_PUSH=1 <seu comando>\n\n"
    "Alternativa segura: faça um merge/rebase normal e um push sem --force.\n"
)
sys.exit(2)
PYEOF
