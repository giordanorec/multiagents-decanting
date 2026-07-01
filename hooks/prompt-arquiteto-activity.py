#!/usr/bin/env python3
"""prompt-arquiteto-activity.py — UserPromptSubmit.

Emite um span do Arquiteto quando o usuário manda um pedido, para o card do
Arquiteto no painel "acender" (pensando/processando) mesmo antes de qualquer
tool call. Observabilidade: a atividade do próprio Arquiteto também é visível.

Telemetria nunca derruba o fluxo: erro → exit 0 silencioso.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _root(start):
    try:
        cur = Path(start).resolve()
    except Exception:
        return None
    for c in [cur, *cur.parents]:
        if (c / "multiagents-decanting.toml").is_file():
            return c
    return None


def main():
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        d = {}
    root = _root(d.get("cwd") or os.getcwd())
    if root is None:
        return
    sys.path.insert(0, str(root / "scripts"))
    try:
        import _utils  # type: ignore
    except Exception:
        return
    prompt = (d.get("prompt") or "").strip().replace("\n", " ")
    say = "analisando seu pedido e decidindo o próximo passo…"
    if prompt:
        say = f"recebi: “{prompt[:60]}” — analisando…"
    try:
        _utils.emit_span("say", {"agent.name": "arquiteto", "detail": say}, root=root)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
