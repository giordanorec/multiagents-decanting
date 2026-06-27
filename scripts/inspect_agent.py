"""
inspect_agent.py — leitura formatada do estado de um agente e do seu trust.

`inspect <agente>` despeja handoff, últimas decisões/lessons, trust e telemetria.
`trust <agente>` foca no score, histórico e nível de fricção atual.
Puro filesystem; o slash command só chama isto e apresenta.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402


def _agent_dir(agent: str) -> Path | None:
    root = u.find_project_root()
    if root is None:
        return None
    d = root / "memory" / agent
    return d if d.is_dir() else None


def _tail_entries(path: Path, n: int) -> str:
    if not path.is_file():
        return "(vazio)"
    blocks = [b for b in u.read_text(path).split("\n## ") if b.strip()]
    if len(blocks) <= 1:
        return u.read_text(path).strip() or "(vazio)"
    tail = blocks[-n:]
    return "\n## ".join(tail)


def _friction_level(score: int) -> str:
    if score < 30:
        return "0-29 · ações de médio+ risco pedem confirmação humana"
    if score < 70:
        return "30-69 · só irreversíveis pedem confirmação"
    return "70-100 · alta autonomia; só catastróficas pedem confirmação"


def run(agent: str) -> int:
    d = _agent_dir(agent)
    if d is None:
        print(u.c(f"✗ Agente '{agent}' não encontrado (memory/{agent}/ inexistente).", "red"))
        return 1
    print(u.c(f"\n  ▌ {agent} · estado completo", "bold", "cyan"))

    print(u.c("\n  handoff.md (última nota)", "bold"))
    print(_indent(u.read_text(d / "handoff.md") if (d / "handoff.md").is_file() else "(vazio)"))

    print(u.c("\n  decisions.md (últimas 5)", "bold"))
    print(_indent(_tail_entries(d / "decisions.md", 5)))

    if (d / "state.md").is_file():
        print(u.c("\n  state.md", "bold"))
        print(_indent(u.read_text(d / "state.md")))

    if (d / "lessons.md").is_file():
        print(u.c("\n  lessons.md (últimas 5)", "bold"))
        print(_indent(_tail_entries(d / "lessons.md", 5)))

    _print_trust_block(d, agent)
    _print_telemetry(agent)
    return 0


def trust(agent: str) -> int:
    d = _agent_dir(agent)
    if d is None:
        print(u.c(f"✗ Agente '{agent}' não encontrado.", "red"))
        return 1
    print(u.c(f"\n  ▌ {agent} · trust", "bold", "cyan"))
    _print_trust_block(d, agent, full=True)
    return 0


def _print_trust_block(d: Path, agent: str, full: bool = False):
    tj = u.read_json(d / "trust.json", {})
    score = int(tj.get("score", 50))
    hist = tj.get("history", [])
    print(u.c("\n  trust", "bold"))
    print(f"    score: {u.bar(score/100)} {score}/100")
    print(f"    fricção: {_friction_level(score)}")
    if hist:
        accepted = sum(1 for h in hist if h.get("outcome") == "accepted")
        total = len(hist)
        print(f"    features: {total}  ·  aceitas 1ª leitura: "
              f"{accepted/total*100:.0f}%")
        last = hist[-10:] if full else hist[-5:]
        print(u.c("    histórico:", "dim"))
        for h in last:
            print(f"      {h.get('timestamp','?')[:10]}  {h.get('feature','?'):<22}"
                  f"  {h.get('outcome','?'):<22} {h.get('weight',0):+d}")
        if full and len(hist) >= 4:
            trend = sum(h.get("weight", 0) for h in hist[-5:])
            label = "melhorando" if trend > 2 else "piorando" if trend < -2 else "estável"
            print(f"    tendência (últimas 5): {label}")
    else:
        print("    histórico: vazio (nunca invocado)")


def _print_telemetry(agent: str):
    root = u.find_project_root()
    if root is None:
        return
    d = root / "logs" / "otel"
    if not d.is_dir():
        return
    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(hours=24)
    calls = tokens = 0
    last = None
    for f in sorted(d.glob("*.jsonl")):
        for line in u.read_text(f).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                sp = json.loads(line)
            except json.JSONDecodeError:
                continue
            if sp.get("attributes", {}).get("agent.name") != agent:
                continue
            try:
                ts = datetime.fromisoformat(sp.get("timestamp", ""))
            except ValueError:
                continue
            if ts < cutoff:
                continue
            if sp.get("name") == "agent.start":
                calls += 1
            a = sp.get("attributes", {})
            tokens += int(a.get("gen_ai.usage.input_tokens", 0) or 0)
            tokens += int(a.get("gen_ai.usage.output_tokens", 0) or 0)
            last = sp.get("timestamp", last)
    print(u.c("\n  telemetria (24h)", "bold"))
    print(f"    calls: {calls}  ·  tokens: {tokens:,}  ·  última atividade: {last or '—'}")


def _indent(text: str, n: int = 4) -> str:
    pad = " " * n
    return "\n".join(pad + ln for ln in (text or "").strip().splitlines()) or pad + "(vazio)"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: inspect_agent.py <agente>")
        sys.exit(2)
    sys.exit(run(sys.argv[1]))
