"""
doctor.py — diagnóstico de saúde de um projeto multiagents-decanting.

Verifica versões, estrutura, telemetria, budget, trust e emite veredito
verde/amarelo/vermelho. É o teste vivo de integridade do sistema: tudo que o
plugin promete tem uma invariante checada aqui.

Uso:  python scripts/mad.py doctor [--json]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

MANDATORY_MEMORY = ["identity.md", "dossier.md", "decisions.md", "handoff.md", "trust.json"]
DOCS_EXPECTED = ["00_OBJETIVO.md", "DECISOES.md", "STATE.md"]
STALE_DAYS = 7
LESSONS_WORD_LIMIT = 10_000


class Report:
    def __init__(self):
        self.sections: list[tuple[str, list[tuple[str, str]]]] = []
        self.problems = 0   # vermelho
        self.warnings = 0   # amarelo

    def section(self, title: str):
        items: list[tuple[str, str]] = []
        self.sections.append((title, items))
        return items

    def ok(self, items, msg):
        items.append(("ok", msg))

    def warn(self, items, msg):
        self.warnings += 1
        items.append(("warn", msg))

    def fail(self, items, msg):
        self.problems += 1
        items.append(("fail", msg))

    def verdict(self) -> str:
        if self.problems:
            return "vermelho"
        if self.warnings:
            return "amarelo"
        return "verde"


def _agents(root: Path) -> list[str]:
    mem = root / "memory"
    if not mem.is_dir():
        return []
    return sorted(p.name for p in mem.iterdir() if p.is_dir())


def _recent_spans(root: Path, hours: int = 24) -> list[dict]:
    d = root / "logs" / "otel"
    if not d.is_dir():
        return []
    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(hours=hours)
    spans: list[dict] = []
    for f in sorted(d.glob("*.jsonl")):
        for line in u.read_text(f).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                sp = json.loads(line)
                ts = datetime.fromisoformat(sp.get("timestamp", ""))
                if ts >= cutoff:
                    spans.append(sp)
            except (json.JSONDecodeError, ValueError):
                continue
    return spans


def run(root: Path | None = None, as_json: bool = False) -> int:
    root = root or u.find_project_root()
    rep = Report()

    if root is None:
        if as_json:
            print(json.dumps({"verdict": "vermelho",
                              "error": "projeto não inicializado (sem multiagents-decanting.toml)"}))
        else:
            print(u.c("✗ Projeto não inicializado.", "red", "bold"))
            print("  Rode /mad-init neste diretório primeiro.")
        return 2

    cfg = u.load_config(root)

    # --- 1. Versões ---
    items = rep.section("Versões")
    pv = sys.version_info
    if pv >= (3, 9):
        rep.ok(items, f"Python {pv.major}.{pv.minor}.{pv.micro} (>= 3.9)")
    else:
        rep.fail(items, f"Python {pv.major}.{pv.minor} < 3.9 — não suportado")
    ccv = u.get_claude_code_version()
    if ccv:
        rep.ok(items, f"Claude Code {ccv[0]}.{ccv[1]}.{ccv[2]}")
    else:
        rep.warn(items, "Claude Code não detectado no PATH (claude --version falhou)")
    if u.supports_sendmessage():
        rep.ok(items, "SendMessage habilitado (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)")
    else:
        rep.warn(items, "SendMessage desligado — multi-turn usa nova Agent call (fallback). "
                        "Para máxima fluência: export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1")
    plugin_v = cfg.get("plugin", {}).get("version", "?")
    rep.ok(items, f"Plugin multiagents-decanting {plugin_v}")

    # --- 2. Estrutura ---
    items = rep.section("Estrutura")
    rep.ok(items, f"{u.CONFIG_FILENAME} presente")
    docs = root / "docs"
    missing_docs = [d for d in DOCS_EXPECTED if not (docs / d).is_file()]
    if not missing_docs:
        rep.ok(items, "docs/ populado (00_OBJETIVO, DECISOES, STATE)")
    else:
        rep.warn(items, f"docs/ faltando: {', '.join(missing_docs)}")
    if (root / ".gitignore").is_file():
        rep.ok(items, ".gitignore presente")
    else:
        rep.warn(items, ".gitignore ausente (logs/ e status/ deveriam ser ignorados)")

    agents = _agents(root)
    if not agents:
        rep.warn(items, "Nenhum agente habilitado ainda (memory/ vazio)")
    for ag in agents:
        miss = [m for m in MANDATORY_MEMORY if not (root / "memory" / ag / m).is_file()]
        if miss:
            rep.fail(items, f"memory/{ag}/ incompleto: faltam {', '.join(miss)}")
        else:
            rep.ok(items, f"memory/{ag}/ completo")

    # --- 3. Telemetria ---
    items = rep.section("Telemetria (24h)")
    spans = _recent_spans(root, 24)
    rep.ok(items, f"{len(spans)} spans OTel nas últimas 24h")
    now = datetime.now(timezone.utc).astimezone()
    last_decant: dict[str, datetime] = {}
    for sp in spans:
        if sp.get("name") == "decanting.complete":
            ag = sp.get("attributes", {}).get("agent.name")
            if ag:
                try:
                    last_decant[ag] = datetime.fromisoformat(sp["timestamp"])
                except ValueError:
                    pass

    # --- 4. Budget ---
    items = rep.section("Budget (hoje)")
    tokens_today = 0
    cost_today = 0.0
    for sp in _recent_spans(root, 24):
        a = sp.get("attributes", {})
        tokens_today += int(a.get("gen_ai.usage.input_tokens", 0) or 0)
        tokens_today += int(a.get("gen_ai.usage.output_tokens", 0) or 0)
        cost_today += float(a.get("gen_ai.cost.estimate", 0) or 0)
    budget = cfg.get("budget", {})
    max_cost = float(budget.get("max_cost_per_day_usd", 0) or 0)
    rep.ok(items, f"Tokens hoje: {tokens_today:,}")
    if max_cost > 0:
        pct = cost_today / max_cost
        msg = f"Custo hoje: ${cost_today:.2f} / ${max_cost:.2f} ({pct*100:.0f}%)"
        warn_thr = float(budget.get("warning_threshold", 0.8) or 0.8)
        if pct >= 1.0:
            rep.fail(items, msg + " — TETO ATINGIDO")
        elif pct >= warn_thr:
            rep.warn(items, msg + " — acima do limiar de alerta")
        else:
            rep.ok(items, msg)
    else:
        rep.ok(items, f"Custo hoje estimado: ${cost_today:.2f} (sem teto configurado)")

    # --- 5. Trust scores ---
    items = rep.section("Trust scores")
    for ag in agents:
        tj = u.read_json(root / "memory" / ag / "trust.json", {})
        score = tj.get("score", "?")
        rep.ok(items, f"{ag}: {score}")

    # --- 6. Alertas ---
    items = rep.section("Alertas")
    any_alert = False
    for ag in agents:
        ld = last_decant.get(ag)
        if ld is None:
            # nunca decantou nas 24h; checa se já foi invocado alguma vez
            tj = u.read_json(root / "memory" / ag / "trust.json", {})
            if not tj.get("history"):
                rep.warn(items, f"{ag}: habilitado mas nunca invocado")
                any_alert = True
        elif (now - ld) > timedelta(days=STALE_DAYS):
            rep.warn(items, f"{ag}: último decanting há > {STALE_DAYS} dias")
            any_alert = True
        lessons = root / "memory" / ag / "lessons.md"
        if lessons.is_file():
            words = len(u.read_text(lessons).split())
            if words > LESSONS_WORD_LIMIT:
                rep.warn(items, f"{ag}: lessons.md com {words} palavras — considere poda")
                any_alert = True
    for sp in spans:
        if sp.get("name") == "decanting.skipped":
            ag = sp.get("attributes", {}).get("agent.name", "?")
            rep.warn(items, f"{ag}: decanting pulado detectado (sanção -10 no trust)")
            any_alert = True
    if not any_alert:
        rep.ok(items, "Nenhum alerta.")

    # --- saída ---
    if as_json:
        out = {
            "verdict": rep.verdict(),
            "problems": rep.problems,
            "warnings": rep.warnings,
            "sections": [
                {"title": t, "items": [{"level": lv, "msg": m} for lv, m in its]}
                for t, its in rep.sections
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        _print_human(rep, root)
    return 0 if rep.problems == 0 else 1


def _print_human(rep: Report, root: Path):
    print(u.c(f"\n  multiagents-decanting · doctor · {root.name}", "bold", "cyan"))
    glyph = {"ok": u.c("✓", "green"), "warn": u.c("▲", "yellow"), "fail": u.c("✗", "red")}
    for title, items in rep.sections:
        print(u.c(f"\n  {title}", "bold"))
        for lv, msg in items:
            print(f"    {glyph[lv]} {msg}")
    v = rep.verdict()
    color = {"verde": "green", "amarelo": "yellow", "vermelho": "red"}[v]
    badge = {"verde": "VERDE — saudável",
             "amarelo": f"AMARELO — {rep.warnings} aviso(s)",
             "vermelho": f"VERMELHO — {rep.problems} problema(s)"}[v]
    print(u.c(f"\n  ► {badge}\n", color, "bold"))


if __name__ == "__main__":
    sys.exit(run(as_json="--json" in sys.argv))
