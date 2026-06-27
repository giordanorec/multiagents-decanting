#!/usr/bin/env python3
"""session-end-decant-check.py — SessionEnd.

Safety net da omissão de decanting (ver _spec/04_PROTOCOLOS.md §4.4).

Para cada agente em memory/, lê os spans OTel recentes. Se o evento terminal
mais recente (decanting.complete OU decanting.skipped) for ANTERIOR ao último
`agent.start` daquele agente, então uma call foi feita sem decantar:
  - grava span `decanting.skipped`;
  - aplica -10 no trust score (cap [0,100]), com entry no history (outcome
    "decanting_skipped", weight -10).

Idempotente entre sessões: como o próprio decanting.skipped vira evento
terminal, a próxima execução não pune de novo o mesmo agent.start.

Não é hard guard (a sessão já acabou) — é instrumentação que pune a omissão.
Qualquer erro → exit 0 silencioso; nunca trava o encerramento da sessão.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
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


def _parse_ts(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _span_agent(span: dict) -> str:
    attrs = span.get("attributes") or {}
    return attrs.get("agent.name") or attrs.get("agent") or ""


def _load_spans(root: Path):
    spans = []
    otel = root / "logs" / "otel"
    if not otel.is_dir():
        return spans
    for f in sorted(otel.glob("*.jsonl")):
        try:
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    spans.append(json.loads(line))
                except Exception:
                    continue
        except Exception:
            continue
    return spans


def main():
    d = _read_stdin()
    root = _find_root(d.get("cwd") or os.getcwd())
    if root is None:
        sys.exit(0)

    sys.path.insert(0, str(root / "scripts"))
    try:
        import _utils  # type: ignore
    except Exception:
        sys.exit(0)

    mem = root / "memory"
    if not mem.is_dir():
        sys.exit(0)

    agents = [p.name for p in mem.iterdir() if p.is_dir() and (p / "trust.json").is_file()]
    if not agents:
        sys.exit(0)

    spans = _load_spans(root)

    for agent in agents:
        last_start = None
        last_done = None
        penalized_starts = set()
        for sp in spans:
            if _span_agent(sp) != agent:
                continue
            name = sp.get("name")
            ts = _parse_ts(sp.get("timestamp"))
            if ts is None:
                continue
            if name == "agent.start":
                if last_start is None or ts > last_start:
                    last_start = ts
            elif name in ("decanting.complete", "decanting.skipped"):
                if last_done is None or ts > last_done:
                    last_done = ts
                if name == "decanting.skipped":
                    ref = (sp.get("attributes") or {}).get("last_agent_start")
                    if ref:
                        penalized_starts.add(str(ref))

        # Nunca invocado, ou já decantou/penalizou depois do último start → ok.
        if last_start is None:
            continue
        if last_done is not None and last_done >= last_start:
            continue
        # Idempotência robusta (independe de clock): já penalizamos este start?
        if last_start.isoformat() in penalized_starts:
            continue

        # Omissão detectada: span + sanção.
        try:
            _utils.emit_span(
                "decanting.skipped",
                {
                    "agent.name": agent,
                    "reason": "nenhum decanting.complete apos a ultima agent.start",
                    "last_agent_start": last_start.isoformat(),
                },
                root=root,
            )
        except Exception:
            pass

        _penalize(_utils, root, agent)

    sys.exit(0)


def _penalize(_utils, root: Path, agent: str):
    trust_path = root / "memory" / agent / "trust.json"
    try:
        data = _utils.read_json(trust_path, default=None)
    except Exception:
        data = None
    if not isinstance(data, dict):
        return

    try:
        score = int(data.get("score", 50))
    except Exception:
        score = 50
    new_score = max(0, min(100, score - 10))

    history = data.get("history")
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "feature": "unknown",
            "outcome": "decanting_skipped",
            "weight": -10,
            "timestamp": _utils.iso_now(),
            "source": "session-end-decant-check",
        }
    )

    data["score"] = new_score
    data["history"] = history
    data["last_updated"] = _utils.iso_now()

    try:
        _utils.write_json(trust_path, data)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
