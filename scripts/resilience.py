"""
resilience.py — budget enforcement, circuit breaker e retry/backoff.

Em modo decanting (frio) não há um processo de agente vivo para "matar", mas a
proteção catastrófica é enforçável no ponto de invocação: um hook PreToolUse no
Agent/Task chama `guard()` antes de cada nova call. `guard()` soma o custo do
dia a partir dos spans OTel e conta falhas recentes; se o teto diário foi
atingido ou o circuito está aberto, NEGA a call (o hook bloqueia).

Retry/backoff com jitter é oferecido para qualquer I/O de rede do lado Python
(ex: export OTLP). As retentativas das chamadas de modelo em si são nativas do
Claude Code — o plugin não as reimplementa.
"""
from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402


# ---------------------------------------------------------------------------
# Retry / backoff
# ---------------------------------------------------------------------------
def retry(fn, *, attempts=3, initial_ms=1000, max_ms=30000, jitter=True,
          exceptions=(Exception,), sleep=time.sleep):
    """Executa fn() com exponential backoff. Reerguer após esgotar tentativas."""
    delay = initial_ms / 1000.0
    last = None
    for i in range(attempts):
        try:
            return fn()
        except exceptions as e:  # noqa: PERF203
            last = e
            if i == attempts - 1:
                break
            d = min(delay, max_ms / 1000.0)
            if jitter:
                d = d * (0.5 + random.random() / 2)
            sleep(d)
            delay *= 2
    raise last  # type: ignore


# ---------------------------------------------------------------------------
# Estado de custo e falhas (derivado dos spans OTel — fonte única)
# ---------------------------------------------------------------------------
def cost_today_usd(root: Path) -> float:
    today = u.today_str()
    d = root / "logs" / "otel"
    total = 0.0
    if not d.is_dir():
        return 0.0
    f = d / f"{today}.jsonl"
    if not f.is_file():
        return 0.0
    for line in u.read_text(f).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            sp = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += float(sp.get("attributes", {}).get("gen_ai.cost.estimate", 0) or 0)
    return total


def tokens_today(root: Path) -> int:
    today = u.today_str()
    f = root / "logs" / "otel" / f"{today}.jsonl"
    if not f.is_file():
        return 0
    total = 0
    for line in u.read_text(f).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            a = json.loads(line).get("attributes", {})
        except json.JSONDecodeError:
            continue
        total += int(a.get("gen_ai.usage.input_tokens", 0) or 0)
        total += int(a.get("gen_ai.usage.output_tokens", 0) or 0)
    return total


def recent_failures(root: Path, window_s: int) -> int:
    d = root / "logs" / "otel"
    if not d.is_dir():
        return 0
    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(seconds=window_s)
    n = 0
    for f in sorted(d.glob("*.jsonl")):
        for line in u.read_text(f).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                sp = json.loads(line)
                name = sp.get("name")
                a = sp.get("attributes", {})
                is_err = name == "agent.error" or (
                    name == "tool.use" and a.get("tool.outcome") == "error")
                if not is_err:
                    continue
                ts = datetime.fromisoformat(sp.get("timestamp", ""))
            except (json.JSONDecodeError, ValueError):
                continue
            if ts >= cutoff:
                n += 1
    return n


@dataclass
class Guard:
    allowed: bool
    reason: str = ""


def guard(root: Path | None = None) -> Guard:
    """Decide se uma nova invocação de agente pode prosseguir."""
    root = root or u.find_project_root()
    if root is None:
        return Guard(True)
    cfg = u.load_config(root)
    budget = cfg.get("budget", {})
    resil = cfg.get("resilience", {})
    mode = str(budget.get("mode", "subscription")).lower()

    # Assinatura (padrão): NÃO há custo em $ — o Agent tool roda dentro da
    # assinatura Max, não via API paga. Então não bloqueamos por dólar; a
    # proteção contra loop descontrolado é o teto de tokens/dia + circuit breaker.
    if mode == "paid_api":
        max_cost = float(budget.get("max_cost_per_day_usd", 0) or 0)
        if max_cost > 0:
            spent = cost_today_usd(root)
            if spent >= max_cost:
                return Guard(False,
                             f"Teto diário de API paga atingido: ${spent:.2f} / ${max_cost:.2f}.")
    max_tok = int(budget.get("max_tokens_per_day", 0) or 0)
    if max_tok > 0:
        used = tokens_today(root)
        if used >= max_tok:
            return Guard(False,
                         f"Teto de uso diário atingido: {used:,} / {max_tok:,} tokens. "
                         f"Ajuste max_tokens_per_day em multiagents-decanting.toml, ou "
                         f"deixe o loop retomar depois. (Sem custo em $ — é só um limite de uso.)")

    cb_failures = int(resil.get("circuit_breaker_failures", 0) or 0)
    cb_reset = int(resil.get("circuit_breaker_reset_seconds", 300) or 300)
    if cb_failures > 0:
        fails = recent_failures(root, cb_reset)
        if fails >= cb_failures:
            return Guard(False,
                         f"Circuit breaker aberto: {fails} falhas em {cb_reset}s. "
                         f"Aguarde {cb_reset}s ou investigue agent.error nos logs OTel "
                         f"antes de novas invocações.")
    return Guard(True)


def warning(root: Path | None = None) -> str | None:
    """Aviso de aproximação do teto (warning_threshold). None se ok."""
    root = root or u.find_project_root()
    if root is None:
        return None
    cfg = u.load_config(root)
    budget = cfg.get("budget", {})
    max_cost = float(budget.get("max_cost_per_day_usd", 0) or 0)
    thr = float(budget.get("warning_threshold", 0.8) or 0.8)
    if max_cost <= 0:
        return None
    spent = cost_today_usd(root)
    if spent >= max_cost * thr:
        return f"Budget em {spent/max_cost*100:.0f}% (${spent:.2f}/${max_cost:.2f})."
    return None


if __name__ == "__main__":
    g = guard()
    print(json.dumps({"allowed": g.allowed, "reason": g.reason}, ensure_ascii=False))
    sys.exit(0 if g.allowed else 2)
