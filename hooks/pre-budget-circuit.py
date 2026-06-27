#!/usr/bin/env python3
"""
pre-budget-circuit.py — PreToolUse(Agent|Task).

Antes de cada nova invocação de especialista, verifica budget diário e circuit
breaker via resilience.guard(). Se negado, bloqueia (exit 2 + razão acionável no
stderr) — protege contra fatura-surpresa e loops descontrolados.

Falha com graça (exit 0) sem projeto, sem _utils, ou com stdin inválido:
proteção é contra acidente, nunca deve travar o fluxo por bug próprio.
"""
import json
import os
import sys
from pathlib import Path


def _allow():
    sys.exit(0)


def _find_root(start: Path) -> Path | None:
    for c in [start, *start.parents]:
        if (c / "multiagents-decanting.toml").is_file():
            return c
    return None


def main():
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        _allow()

    tool = data.get("tool_name", "")
    if tool not in ("Agent", "Task"):
        _allow()

    # cwd do hook ~ raiz do projeto; resolve para achar scripts/resilience.py
    cwd = Path(data.get("cwd") or os.getcwd())
    root = _find_root(cwd)
    if root is None:
        _allow()

    scripts = root / "scripts"
    if not (scripts / "resilience.py").is_file():
        _allow()
    sys.path.insert(0, str(scripts))
    try:
        import resilience  # type: ignore
    except Exception:
        _allow()

    g = resilience.guard(root)
    if g.allowed:
        _allow()

    sys.stderr.write(
        "\n[multiagents-decanting] BLOQUEADO: nova invocação de especialista.\n\n"
        f"  {g.reason}\n\n"
        "Esta é uma proteção catastrófica (budget/circuit breaker). Ajuste a\n"
        "config em multiagents-decanting.toml se for intencional, ou aguarde a\n"
        "janela de reset.\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
