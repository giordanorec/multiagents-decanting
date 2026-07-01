#!/usr/bin/env python3
"""pre-guardrail-write-scope.py — PreToolUse(Edit|Write|MultiEdit).

Escopo de escrita no filesystem (complementa o least-privilege de `tools:`):
1. Paths SEMPRE protegidos de escrita direta por qualquer agente — são geridos
   pelos scripts (via os.replace), não editados à mão: .mad/workflow_state.json,
   logs/workflow.jsonl (audit append-only), sessions.json.
2. Se o agente se identifica em MAD_AGENT, enforça o allowlist de paths do papel
   e proíbe escrever em memory/<outro>/.

Bloqueio = exit 2 + permissionDecision deny. Erro interno = permite (fail-open só
para não travar por bug do próprio guardrail; a proteção crítica é o item 1).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# papel -> prefixos de path onde PODE escrever (relativos à raiz do projeto)
ROLE_PATHS = {
    "qa-tester": ["tests/", "reports/"],
    "security-auditor": ["reports/"],
    "docs-writer": ["docs/", "reports/"],
    "llm-prompt": ["config/", "prompts/", "reports/"],
    "asset-designer": ["assets/", "reports/", "dashboard/"],
    # devs de código escrevem em src/lib/app + reports; ajuste conforme a stack
    "pipeline-dev": ["src/", "lib/", "app/", "backend/", "reports/", "tests/"],
    "frontend-dev": ["src/", "app/", "frontend/", "dashboard/", "reports/"],
    "mobile-dev": ["src/", "app/", "mobile/", "reports/"],
    "dba": ["migrations/", "db/", "sql/", "reports/"],
    "devops-installer": [".", ],  # amplo
}
ALWAYS_PROTECTED = (".mad/workflow_state.json", "logs/workflow.jsonl", "sessions.json")


def _root(start):
    for c in [Path(start).resolve(), *Path(start).resolve().parents]:
        if (c / "multiagents-decanting.toml").is_file():
            return c
    return None


def _deny(msg):
    sys.stderr.write("AÇÃO BLOQUEADA (escopo de escrita): " + msg + "\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
          "permissionDecision": "deny", "permissionDecisionReason": msg}}))
    sys.exit(2)


def main():
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    ti = d.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("notebook_path")
    if not fp:
        sys.exit(0)
    root = _root(d.get("cwd") or os.getcwd())
    if root is None:
        sys.exit(0)
    try:
        rel = os.path.relpath(os.path.abspath(fp), str(root)).replace("\\", "/")
    except Exception:
        sys.exit(0)

    # 1) paths sempre protegidos
    for prot in ALWAYS_PROTECTED:
        if rel == prot:
            _deny(f"{prot} é gerido pelos scripts do mad (não edite à mão). "
                  f"Use o comando apropriado (/mad-phase, etc.).")

    agent = os.environ.get("MAD_AGENT", "").strip()
    if not agent:
        sys.exit(0)  # sessão principal (Arquiteto) — escopo amplo

    # 2) ninguém escreve na memória de outro agente
    if rel.startswith("memory/") and not rel.startswith(f"memory/{agent}/") \
       and not rel.startswith("memory/_shared/"):
        _deny(f"{agent} não escreve na memória de outro agente ({rel}).")
    # DECISOES é do Arquiteto
    if rel == "docs/DECISOES.md":
        _deny(f"docs/DECISOES.md é mantido pelo Arquiteto, não por {agent}.")

    allowed = ROLE_PATHS.get(agent)
    if allowed and "." not in allowed:
        if not any(rel.startswith(p) for p in allowed):
            _deny(f"{agent} só escreve em {', '.join(allowed)} (tentou: {rel}).")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
