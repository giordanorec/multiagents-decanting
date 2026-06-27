#!/usr/bin/env python3
"""post-trust-update.py — PostToolUse(Agent).

Best-effort: registra o fim de uma call do Agent tool emitindo um span OTel
`agent.end`. NÃO escreve em trust.json — a autoridade de outcome (accepted /
rework / rejected) é exclusivamente do Arquiteto, que avalia o report contra os
critérios de aceite. Aqui só instrumentamos.

Telemetria nunca derruba o fluxo: qualquer erro → exit 0 silencioso.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _read_stdin() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _find_root(start: str):
    try:
        cur = Path(start).resolve()
    except Exception:
        return None
    for c in [cur, *cur.parents]:
        if (c / "multiagents-decanting.toml").is_file():
            return c
    return None


def _agent_name(d: dict) -> str:
    ti = d.get("tool_input") or {}
    # subagent_type vem como "multiagents-decanting:<role>" — pega o role.
    sub = ti.get("subagent_type") or ti.get("subagentType") or ""
    if sub:
        return sub.split(":")[-1]
    return ti.get("description") or "unknown"


def _outcome(d: dict) -> str:
    resp = d.get("tool_response")
    if isinstance(resp, dict) and (resp.get("is_error") or resp.get("error")):
        return "error"
    if isinstance(resp, str) and resp.lower().startswith("error"):
        return "error"
    return "completed"


def main():
    d = _read_stdin()
    if d.get("tool_name") != "Agent":
        sys.exit(0)

    root = _find_root(d.get("cwd") or os.getcwd())
    if root is None:
        sys.exit(0)

    sys.path.insert(0, str(root / "scripts"))
    try:
        import _utils  # type: ignore
    except Exception:
        sys.exit(0)

    try:
        attrs = {
            "agent.name": _agent_name(d),
            "outcome": _outcome(d),
        }
        sid = d.get("session_id")
        if sid:
            attrs["session.id"] = sid
        _utils.emit_span("agent.end", attrs, root=root)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
