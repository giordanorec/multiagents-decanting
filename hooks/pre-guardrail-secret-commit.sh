#!/usr/bin/env bash
# pre-guardrail-secret-commit.sh — PreToolUse(Bash)
#
# Em `git commit` / `git add`, escaneia o conteúdo prestes a entrar no repo por
# padrões de secret (AWS keys, blocos de chave privada, password=, api_key=,
# tokens longos tipo ghp_/sk-/xox*). Bloqueia com aviso acionável.
#
# Override: DECANTING_ALLOW_SECRET_COMMIT=1 (use com cuidado).
# Bloqueio = exit 2 + stderr. Best-effort: se git falhar, libera (exit 0). Sem jq.
INPUT="$(cat)"
DECANTING_HOOK_INPUT="$INPUT" python3 <<'PYEOF'
import os, sys, json, re, shlex, subprocess
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

if os.environ.get("DECANTING_ALLOW_SECRET_COMMIT") == "1":
    allow()

is_commit = bool(re.search(r"\bgit\s+commit\b", cmd))
is_add = bool(re.search(r"\bgit\s+add\b", cmd))
if not (is_commit or is_add):
    allow()

cwd = d.get("cwd") or os.getcwd()

# (nome amigável, regex). Não imprimimos o valor casado — só a regra e o arquivo.
RULES = [
    ("AWS Access Key ID",      re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bloco de chave privada", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("password=",              re.compile(r"(?i)\bpassword\s*[:=]\s*['\"]?[^\s'\"]{4,}")),
    ("api_key=",               re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
    ("secret=/token=",         re.compile(r"(?i)\b(?:secret|access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{12,}")),
    ("GitHub token (ghp_)",    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")),
    ("Slack token (xox)",      re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI-style key (sk-)", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("Google API key",         re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
]

MAX_BYTES = 1_000_000  # não escaneia arquivos gigantes/binários grandes


def git(args):
    try:
        r = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return None
        return r.stdout
    except Exception:
        return None


def looks_binary(text):
    return "\x00" in text[:4096]


# Coleta (rótulo, conteúdo) a escanear.
chunks = []

# 1) Diff já staged (cobre o caso git commit).
staged_diff = git(["diff", "--cached", "--unified=0"])
if staged_diff:
    chunks.append(("(conteúdo staged)", staged_diff))

# 2) git add com arquivos explícitos: lê o conteúdo desses paths.
explicit_paths = []
add_all = False
if is_add:
    for seg in re.split(r"[;&|\n]+", cmd):
        if not re.search(r"\bgit\s+add\b", seg):
            continue
        try:
            toks = shlex.split(seg)
        except Exception:
            toks = seg.split()
        if "add" not in toks:
            continue
        for t in toks[toks.index("add") + 1:]:
            if t.startswith("-"):
                if t in ("-A", "--all", "-u", "--update"):
                    add_all = True
                continue
            if t in (".", "*", "./"):
                add_all = True
                continue
            explicit_paths.append(t)

# git add . / -A : pega os modificados/novos via porcelain.
if add_all:
    porc = git(["status", "--porcelain", "--untracked-files=all"])
    if porc:
        for line in porc.splitlines():
            if len(line) > 3:
                explicit_paths.append(line[3:].strip().strip('"'))

for rel in explicit_paths:
    p = Path(rel)
    if not p.is_absolute():
        p = Path(cwd) / rel
    try:
        if p.is_file() and p.stat().st_size <= MAX_BYTES:
            txt = p.read_text(encoding="utf-8", errors="replace")
            if not looks_binary(txt):
                chunks.append((rel, txt))
    except Exception:
        continue

# Sem nada para escanear → libera.
if not chunks:
    allow()

hits = []
for label, content in chunks:
    for name, rx in RULES:
        if rx.search(content):
            hits.append((name, label))

if not hits:
    allow()

# Dedup, mantém ordem.
seen = set()
uniq = []
for h in hits:
    if h not in seen:
        seen.add(h)
        uniq.append(h)

lines = "".join(
    "  - %s  (em: %s)\n" % (name, label) for name, label in uniq[:20]
)
sys.stderr.write(
    "\n[multiagents-decanting] BLOQUEADO: possível secret no commit/add.\n\n"
    + lines +
    "\nSegredos não devem entrar no histórico do Git — uma vez commitados,\n"
    "consideram-se vazados mesmo que removidos depois.\n\n"
    "O que fazer:\n"
    "  - mova o valor para um arquivo .env (que esteja no .gitignore);\n"
    "  - referencie via variável de ambiente, não hardcoded;\n"
    "  - se for um falso positivo (ex: fixture de teste), rode com:\n"
    "      DECANTING_ALLOW_SECRET_COMMIT=1 <seu comando>\n"
)
sys.exit(2)
PYEOF
