#!/usr/bin/env python3
"""post-otel-emit.py — PostToolUse(*).

Emite um span OTel GenAI `tool.use` em logs/otel/<date>.jsonl para cada tool
call concluído. Sanitiza os argumentos (nunca loga secrets nem blobs grandes).

Telemetria nunca derruba o fluxo: qualquer erro → exit 0 silencioso.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _silent_ok():
    sys.exit(0)


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


# --- redação de secrets em valores logados --------------------------------
_SECRET_RX = re.compile(
    r"AKIA[0-9A-Z]{16}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{8,}"
    r"|sk-[A-Za-z0-9]{16,}"
    r"|AIza[0-9A-Za-z_\-]{20,}"
    r"|-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"
)
_SECRET_KV_RX = re.compile(
    r"(?i)(password|api[_-]?key|secret|token)(\s*[:=]\s*)['\"]?[^\s'\"]+"
)

_MAX_STR = 200
# Campos volumosos: registramos só o tamanho, não o conteúdo.
_BULK_KEYS = {"content", "old_string", "new_string", "new_str", "old_str", "file_text"}


def _redact(s: str) -> str:
    s = _SECRET_RX.sub("[REDACTED]", s)
    s = _SECRET_KV_RX.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", s)
    if len(s) > _MAX_STR:
        s = s[:_MAX_STR] + "…(+%d chars)" % (len(s) - _MAX_STR)
    return s


def _sanitize(value, key=None, depth=0):
    if key in _BULK_KEYS and isinstance(value, str):
        return "<%d chars>" % len(value)
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if depth >= 3:
        return "<...>"
    if isinstance(value, dict):
        return {k: _sanitize(v, k, depth + 1) for k, v in list(value.items())[:30]}
    if isinstance(value, list):
        return [_sanitize(v, None, depth + 1) for v in value[:20]]
    return _redact(str(value))


def _stream_detail(tool: str, args) -> str:
    """Linha legível pro mini-terminal do agente (o que ele está fazendo)."""
    if not isinstance(args, dict):
        return str(tool)
    if tool in ("Read", "Write", "NotebookRead"):
        return args.get("file_path", "")
    if tool in ("Edit", "MultiEdit"):
        return args.get("file_path", "")
    if tool == "Bash":
        return str(args.get("command", ""))[:120]
    if tool == "Grep":
        p = args.get("pattern", "")
        path = args.get("path", "")
        return f"{p}" + (f"  @ {path}" if path else "")
    if tool == "Glob":
        return args.get("pattern", "")
    if tool in ("WebFetch", "WebSearch"):
        return args.get("url") or args.get("query", "")
    return ""


def _outcome(d: dict) -> str:
    resp = d.get("tool_response")
    if isinstance(resp, dict):
        if resp.get("is_error") or resp.get("error") or resp.get("isError"):
            return "error"
        return "ok"
    if isinstance(resp, str):
        return "error" if resp.lower().startswith("error") else "ok"
    # PostToolUse normalmente traz tool_response; ausência = desconhecido.
    return "unknown"


def main():
    d = _read_stdin()
    tool_name = d.get("tool_name")
    if not tool_name:
        _silent_ok()

    root = _find_root(d.get("cwd") or os.getcwd())
    if root is None:
        _silent_ok()

    sys.path.insert(0, str(root / "scripts"))
    try:
        import _utils  # type: ignore
    except Exception:
        _silent_ok()

    try:
        # A sessão principal do mad É o Arquiteto (ponto único de contato). Um
        # subagente pode marcar MAD_AGENT no ambiente para se auto-atribuir.
        agent = os.environ.get("MAD_AGENT") or "arquiteto"
        args = _sanitize(d.get("tool_input") or {})
        attrs = {
            "agent.name": agent,
            "tool.name": tool_name,
            "tool.args": args,
            "tool.outcome": _outcome(d),
            "detail": _stream_detail(tool_name, args),
        }
        # despacho de especialista aparece de forma humana no stream do Arquiteto
        if tool_name in ("Agent", "Task"):
            sub = (d.get("tool_input") or {}).get("subagent_type", "")
            attrs["detail"] = f"despachando {sub or 'especialista'} para trabalhar"
        sid = d.get("session_id")
        if sid:
            attrs["session.id"] = sid
        _utils.emit_span("tool.use", attrs, root=root)
    except Exception:
        pass
    _silent_ok()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
