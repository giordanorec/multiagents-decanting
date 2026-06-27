#!/usr/bin/env bash
# pre-guardrail-rm-rf.sh — PreToolUse(Bash)
#
# Bloqueia `rm -rf` (e variações -fr, -r -f, --recursive --force) cujo alvo
# resolve para FORA da raiz do projeto (raiz = dir com multiagents-decanting.toml,
# subindo a árvore a partir do cwd do tool call).
#
# Bloqueio = exit 2 + stderr. Parse falho / alvo seguro = exit 0. Sem jq.
INPUT="$(cat)"
DECANTING_HOOK_INPUT="$INPUT" python3 <<'PYEOF'
import os, sys, json, re, shlex
from pathlib import Path

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

cwd = d.get("cwd") or os.getcwd()

def find_root(start):
    try:
        cur = Path(start).resolve()
    except Exception:
        return None
    for c in [cur, *cur.parents]:
        if (c / "multiagents-decanting.toml").is_file():
            return c
    return None

root = find_root(cwd)

# Quebra o comando em segmentos simples (separadores de shell).
segments = re.split(r"[;&|\n]+", cmd)

def block(reason, target):
    sys.stderr.write(
        "\n[multiagents-decanting] BLOQUEADO: `rm -rf` perigoso.\n\n"
        "  Comando: " + cmd.strip()[:300] + "\n"
        "  Alvo:    " + str(target) + "\n"
        "  Motivo:  " + reason + "\n\n"
        "Remoção recursiva e forçada de um caminho fora da raiz do projeto é\n"
        "irreversível e catastrófica. Este guardrail nunca permite.\n\n"
        "O que fazer:\n"
        "  - confira o caminho; ele deve ficar DENTRO da raiz do projeto;\n"
        "  - se precisa apagar algo de fato externo, faça manualmente, fora\n"
        "    do agente, com plena consciência do que está deletando.\n"
    )
    sys.exit(2)

for seg in segments:
    seg = seg.strip()
    if not seg:
        continue
    try:
        toks = shlex.split(seg)
    except Exception:
        toks = seg.split()
    if "rm" not in toks:
        continue
    idx = toks.index("rm")
    rest = toks[idx + 1:]

    short_flags = "".join(
        t[1:] for t in rest if t.startswith("-") and not t.startswith("--")
    )
    has_r = ("r" in short_flags) or ("R" in short_flags) or ("--recursive" in rest)
    has_f = ("f" in short_flags) or ("--force" in rest)
    if not (has_r and has_f):
        continue

    targets = [t for t in rest if not t.startswith("-")]
    if not targets:
        continue

    for tgt in targets:
        expanded = os.path.expanduser(os.path.expandvars(tgt))
        p = Path(expanded)
        if not p.is_absolute():
            p = Path(cwd) / p
        try:
            rp = p.resolve()
        except Exception:
            rp = p

        # Catastróficos absolutos: bloqueia sempre, mesmo sem projeto detectado.
        rp_str = str(rp)
        if rp_str == os.path.abspath(os.sep) or expanded in ("/", "/*", "~", "~/", os.path.expanduser("~")):
            block("alvo é a raiz do sistema ou home do usuário", rp)

        if root is None:
            # Sem contexto de projeto: só barramos os catastróficos acima.
            continue

        try:
            rp.relative_to(root)
        except ValueError:
            block("alvo resolve para FORA da raiz do projeto (" + str(root) + ")", rp)

allow()
PYEOF
