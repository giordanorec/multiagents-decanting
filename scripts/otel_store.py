"""
otel_store.py — índice SQLite dos spans OTel (stdlib sqlite3, ZERO instalação).

Os spans são escritos em logs/otel/<date>.jsonl (write-ahead). Aqui ingerimos
incrementalmente para logs/otel.db, que permite consultas rápidas: árvore causal de
um trace (por feature), percentis de duração por tool/agente, custo/uso — sem reescanear
JSONL a cada segundo. Também serve o "waterfall" do painel.

CLI:  python scripts/mad.py trace [--trace <id>] [--stats]
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

DB_REL = "logs/otel.db"


def _db(root: Path) -> sqlite3.Connection:
    p = root / DB_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("""CREATE TABLE IF NOT EXISTS spans(
        span_id TEXT PRIMARY KEY, trace_id TEXT, name TEXT, ts TEXT,
        agent TEXT, tool TEXT, outcome TEXT, duration_ms REAL,
        tokens_in INTEGER, tokens_out INTEGER, cost REAL, attrs TEXT)""")
    con.execute("CREATE TABLE IF NOT EXISTS ingest_state(file TEXT PRIMARY KEY, lines INTEGER)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_trace ON spans(trace_id)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_toolagent ON spans(tool, agent)")
    return con


def ingest(root: Path) -> int:
    """Sincroniza JSONL -> SQLite incrementalmente. Retorna nº de novos spans."""
    d = root / "logs" / "otel"
    if not d.is_dir():
        return 0
    con = _db(root)
    seen = dict(con.execute("SELECT file, lines FROM ingest_state").fetchall())
    added = 0
    for f in sorted(d.glob("*.jsonl")):
        start = int(seen.get(f.name, 0))
        lines = u.read_text(f).splitlines()
        for i in range(start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            try:
                sp = json.loads(line)
            except json.JSONDecodeError:
                continue
            a = sp.get("attributes", {}) or {}
            sid = sp.get("span_id") or f"{f.name}:{i}"
            con.execute(
                "INSERT OR IGNORE INTO spans VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, sp.get("trace_id"), sp.get("name"), sp.get("timestamp"),
                 a.get("agent.name"), a.get("tool.name"), a.get("tool.outcome"),
                 sp.get("duration_ms"),
                 int(a.get("gen_ai.usage.input_tokens", 0) or 0),
                 int(a.get("gen_ai.usage.output_tokens", 0) or 0),
                 float(a.get("gen_ai.cost.estimate", 0) or 0),
                 json.dumps(a, ensure_ascii=False)))
            added += 1
        con.execute("INSERT OR REPLACE INTO ingest_state VALUES (?,?)", (f.name, len(lines)))
    con.commit()
    con.close()
    return added


def percentiles(root: Path) -> list[dict]:
    """p50/p95 de duração (quando houver) + contagem/erros por tool."""
    ingest(root)
    con = _db(root)
    rows = con.execute("""SELECT tool, COUNT(*) n,
        SUM(CASE WHEN outcome='error' THEN 1 ELSE 0 END) errs,
        AVG(duration_ms) avg_ms FROM spans WHERE tool IS NOT NULL
        GROUP BY tool ORDER BY n DESC""").fetchall()
    con.close()
    return [{"tool": t, "n": n, "errors": e, "avg_ms": round(a, 1) if a else None}
            for t, n, e, a in rows]


def trace(root: Path, trace_id: str | None = None) -> dict:
    """Spans de um trace (feature) em ordem — a árvore causal do run."""
    ingest(root)
    con = _db(root)
    if trace_id is None:
        r = con.execute("SELECT trace_id FROM spans WHERE trace_id IS NOT NULL "
                        "ORDER BY ts DESC LIMIT 1").fetchone()
        trace_id = r[0] if r else None
    rows = con.execute("SELECT ts, agent, tool, name, outcome, duration_ms FROM spans "
                       "WHERE trace_id=? ORDER BY ts", (trace_id,)).fetchall()
    con.close()
    return {"trace_id": trace_id,
            "spans": [{"ts": ts, "agent": ag, "tool": tl, "name": nm,
                       "outcome": oc, "duration_ms": d} for ts, ag, tl, nm, oc, d in rows]}


def cli(args) -> int:
    root = u.find_project_root()
    if root is None:
        print(u.c("✗ Projeto não inicializado.", "red")); return 2
    n = ingest(root)
    if getattr(args, "stats", False):
        print(u.c(f"\n  Telemetria (SQLite, {n} novos spans indexados)", "bold", "cyan"))
        for r in percentiles(root):
            print(f"    {r['tool']:<14} {r['n']:>4}x  erros={r['errors']}  "
                  f"média={r['avg_ms'] or '—'}ms")
        return 0
    t = trace(root, getattr(args, "trace", None))
    print(u.c(f"\n  Trace {t['trace_id']} ({len(t['spans'])} spans)", "bold", "cyan"))
    for s in t["spans"]:
        mark = u.c("✗", "red") if s["outcome"] == "error" else u.c("·", "dim")
        print(f"    {mark} {s['ts'][11:19]} {s['agent'] or '?':<14} {s['tool'] or s['name']}")
    return 0
