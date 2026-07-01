"""
dashboard_server.py — servidor local do dashboard (HTTP estático + WebSocket).

- HTTP serve dashboard/ (index.html, css, js, manifest, sw, avatars).
- WebSocket /ws faz broadcast em tempo real do estado dos agentes, derivado
  dos spans OTel em logs/otel/<date>.jsonl + handoff.md + trust.json.
- Sem frameworks. Dep única: websockets. Bind 127.0.0.1 por padrão.
- --background reexecuta destacado e grava pid em status/dashboard.pid.

Status do agente é INFERIDO dos spans (não há status/<agente>.json em modo frio):
  agent.start sem agent.end recente  -> working
  decanting.start sem decanting.complete -> decanting
  agent.error sem retry              -> error
  sem spans > 5min                   -> idle
  agente sem nenhum span             -> sleeping
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

DEFAULT_PORT = 8765
PORT_RANGE = range(DEFAULT_PORT, DEFAULT_PORT + 11)  # 8765..8775
IDLE_AFTER_S = 300


# ---------------------------------------------------------------------------
# Estado derivado
# ---------------------------------------------------------------------------
def _read_spans(root: Path, hours: int = 48) -> list[dict]:
    d = root / "logs" / "otel"
    if not d.is_dir():
        return []
    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(hours=hours)
    out = []
    for f in sorted(d.glob("*.jsonl")):
        try:
            lines = u.read_text(f).splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                sp = json.loads(line)
                ts = datetime.fromisoformat(sp.get("timestamp", ""))
            except (json.JSONDecodeError, ValueError):
                continue
            if ts >= cutoff:
                sp["_ts"] = ts
                out.append(sp)
    return out


def _list_agents(root: Path) -> list[str]:
    mem = root / "memory"
    if not mem.is_dir():
        return []
    return sorted(p.name for p in mem.iterdir() if p.is_dir())


def _infer_status(agent: str, spans: list[dict], now: datetime) -> tuple[str, str]:
    mine = [s for s in spans if s.get("attributes", {}).get("agent.name") == agent]
    if not mine:
        return "sleeping", "descansando"
    mine.sort(key=lambda s: s["_ts"])
    last = mine[-1]
    name = last.get("name", "")
    age = (now - last["_ts"]).total_seconds()
    if name == "agent.error":
        return "error", "precisa retomada"
    if name == "decanting.start":
        return "decanting", "decantando aprendizado"
    if age > IDLE_AFTER_S:
        return "idle", "aguardando"
    if name in ("agent.start", "tool.use", "agent.boot", "workflow.feature", "model.call"):
        a = last.get("attributes", {})
        summary = a.get("tool.name") or a.get("spec.path") or a.get("feature") or name
        return "working", str(summary)
    if name in ("agent.end", "decanting.complete"):
        return "idle", "aguardando"
    return "idle", "aguardando"


def snapshot(root: Path) -> dict:
    now = datetime.now(timezone.utc).astimezone()
    spans = _read_spans(root)
    agents = []
    tokens_today = 0
    cost_today = 0.0
    today = u.today_str()
    for sp in spans:
        if sp.get("timestamp", "").startswith(today):
            a = sp.get("attributes", {})
            tokens_today += int(a.get("gen_ai.usage.input_tokens", 0) or 0)
            tokens_today += int(a.get("gen_ai.usage.output_tokens", 0) or 0)
            cost_today += float(a.get("gen_ai.cost.estimate", 0) or 0)
    for ag in _list_agents(root):
        status, bubble = _infer_status(ag, spans, now)
        tj = u.read_json(root / "memory" / ag / "trust.json", {})
        handoff = root / "memory" / ag / "handoff.md"
        note = ""
        if handoff.is_file():
            for line in u.read_text(handoff).splitlines():
                if line.strip() and not line.startswith("#") and not line.startswith(">"):
                    note = line.strip()[:80]
                    break
        agents.append({
            "agente": ag, "status": status, "bubble": bubble,
            "trust": int(tj.get("score", 50)), "note": note,
        })
    cfg = u.load_config(root)
    budget = cfg.get("budget", {})
    completed = _features_completed_today(root)
    return {
        "type": "snapshot",
        "project": root.name,
        "agents": agents,
        "workflow": _workflow_summary(root),
        "metrics": {
            "tokens_today": tokens_today,
            "cost_today_usd": round(cost_today, 4),
            "max_cost_per_day_usd": float(budget.get("max_cost_per_day_usd", 0) or 0),
            "features_completed": completed,
        },
        "activity": _recent_activity(spans),
    }


def _workflow_summary(root: Path) -> dict:
    """Estado da state machine (v1.3) para o banner do dashboard. {} se v1.2."""
    wd = u.read_json(root / ".mad" / "workflow_state.json", None)
    if not isinstance(wd, dict):
        return {}
    af = wd.get("active_feature") or {}
    return {
        "phase": wd.get("current_phase"),
        "feature": af.get("id"),
        "subphase": af.get("subphase"),
        "next": _wf_next(wd),
        "warnings": len(wd.get("warnings", []) or []),
        "bypasses": sum(1 for w in (wd.get("warnings") or []) if "Bypass" in w),
        "phases": ["BOOTSTRAP", "DISCOVERY", "ESPEC_V1", "SETUP_TIME",
                   "LOOP_FEATURES", "PRE_RELEASE", "PILOTO"],
    }


def _wf_next(wd: dict) -> str:
    phase = wd.get("current_phase")
    if phase != "LOOP_FEATURES":
        return {"BOOTSTRAP": "rode /mad-init", "DISCOVERY": "faça a discovery",
                "ESPEC_V1": "escreva o backlog", "SETUP_TIME": "habilite especialistas",
                "PRE_RELEASE": "backtesting", "PILOTO": "em piloto"}.get(phase, "")
    af = wd.get("active_feature") or {}
    return {"spec_pendente": "escreva a spec", "spec_validada": "humano aprova a spec",
            "executando": "especialista trabalhando", "validando": "arquiteto valida",
            "aprovacao_humano": "humano aprova o merge",
            "concluida": "próxima feature"}.get(af.get("subphase"), "ative uma feature")


def _features_completed_today(root: Path) -> int:
    rep = root / "reports"
    if not rep.is_dir():
        return 0
    today = u.today_str()
    n = 0
    for d in rep.iterdir():
        if d.is_dir():
            for f in d.glob("*.md"):
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
                    if mtime == today:
                        n += 1
                        break
                except OSError:
                    pass
    return n


def _recent_activity(spans: list[dict], limit: int = 20) -> list[dict]:
    icon = {"tool.use": "▶", "agent.start": "◆", "decanting.complete": "✓",
            "agent.error": "✗", "agent.boot": "·", "workflow.feature": "◆"}
    out = []
    for sp in sorted(spans, key=lambda s: s["_ts"], reverse=True)[:limit]:
        a = sp.get("attributes", {})
        ag = a.get("agent.name", "?")
        name = sp.get("name", "")
        detail = a.get("tool.name") or a.get("feature") or a.get("spec.path") or name
        out.append({
            "ts": sp.get("timestamp", "")[11:19],
            "icon": icon.get(name, "·"),
            "text": f"{ag} · {name} · {detail}",
        })
    return out


# ---------------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------------
def _pick_port(preferred: int | None, bind: str) -> int | None:
    import socket
    candidates = [preferred] if preferred else list(PORT_RANGE)
    if preferred and preferred not in PORT_RANGE:
        candidates = [preferred] + list(PORT_RANGE)
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((bind, port))
                return port
            except OSError:
                continue
    return None


def _serve(root: Path, port: int, bind: str):
    import asyncio
    try:
        import websockets
    except ModuleNotFoundError:
        print(u.c("✗ Falta a dependência 'websockets'. Rode: pip install -r requirements.txt",
                  "red"))
        return 1

    dash_dir = root / "dashboard"
    if not dash_dir.is_dir():
        print(u.c("✗ dashboard/ não encontrado no projeto.", "red"))
        return 1

    # HTTP estático numa thread
    handler = partial(SimpleHTTPRequestHandler, directory=str(dash_dir))
    httpd = ThreadingHTTPServer((bind, port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    clients: set = set()

    async def ws_handler(ws):
        clients.add(ws)
        try:
            await ws.send(json.dumps(snapshot(root), ensure_ascii=False))
            async for _msg in ws:
                # cliente é majoritariamente read-only; reenvia snapshot sob pedido
                await ws.send(json.dumps(snapshot(root), ensure_ascii=False))
        except Exception:
            pass
        finally:
            clients.discard(ws)

    async def broadcaster():
        last = None
        while True:
            snap = snapshot(root)
            payload = json.dumps(snap, ensure_ascii=False)
            if payload != last and clients:
                dead = set()
                for ws in clients:
                    try:
                        await ws.send(payload)
                    except Exception:
                        dead.add(ws)
                clients.difference_update(dead)
                last = payload
            await asyncio.sleep(1.0)

    async def amain():
        # websockets serve no mesmo host/porta+1 para o /ws? Não: usamos a
        # mesma porta via path /ws exigiria ASGI. Mantemos WS na porta+1000
        # e o frontend conecta nela. Simplicidade > elegância.
        ws_port = port + 1000
        async with websockets.serve(ws_handler, bind, ws_port):
            print(u.c(f"✓ Dashboard: http://{bind}:{port}  (ws: {ws_port})", "green", "bold"))
            await broadcaster()

    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
    return 0


# ---------------------------------------------------------------------------
# Gestão de processo (background / stop / status)
# ---------------------------------------------------------------------------
def _pidfile(root: Path) -> Path:
    return root / "status" / "dashboard.pid"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
    except Exception:
        return False


def cli(args) -> int:
    root = u.project_root_or_cwd()
    bind = args.bind or "127.0.0.1"
    pidfile = _pidfile(root)
    pidfile.parent.mkdir(parents=True, exist_ok=True)

    if getattr(args, "status", False):
        info = u.read_json(pidfile, {})
        pid = info.get("pid")
        if pid and _pid_alive(pid):
            print(u.c(f"● rodando · pid {pid} · http://{bind}:{info.get('port')}", "green"))
            return 0
        print(u.c("○ dashboard não está rodando", "dim"))
        return 1

    if getattr(args, "stop", False):
        info = u.read_json(pidfile, {})
        pid = info.get("pid")
        if pid and _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                print(u.c(f"✓ dashboard parado (pid {pid})", "green"))
            except OSError as e:
                print(u.c(f"✗ falha ao parar pid {pid}: {e}", "red"))
        else:
            print(u.c("○ nada para parar", "dim"))
        try:
            pidfile.unlink()
        except OSError:
            pass
        return 0

    if getattr(args, "tui", False):
        return _run_tui(root)

    port = _pick_port(args.port, bind)
    if port is None:
        print(u.c(f"✗ nenhuma porta livre em {PORT_RANGE.start}-{PORT_RANGE.stop-1}", "red"))
        return 1

    if getattr(args, "background", False):
        # reexecuta destacado
        cmd = [sys.executable, str(Path(__file__).resolve().parent / "mad.py"),
               "dashboard", "--port", str(port), "--bind", bind, "--no-open"]
        kwargs = {}
        if u.get_platform() == "windows":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) \
                | getattr(subprocess, "DETACHED_PROCESS", 0)
        else:
            kwargs["start_new_session"] = True
        logf = open(root / "logs" / "dashboard.log", "a", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=logf, stderr=logf, **kwargs)
        u.write_json(pidfile, {"pid": proc.pid, "port": port, "bind": bind,
                               "started": u.iso_now()})
        time.sleep(0.6)
        url = f"http://{bind}:{port}"
        print(u.c(f"✓ dashboard em background · pid {proc.pid} · {url}", "green", "bold"))
        if not args.no_open:
            u.open_url(url)
        print("  parar: /mad-dashboard --stop")
        return 0

    # foreground
    u.write_json(pidfile, {"pid": os.getpid(), "port": port, "bind": bind,
                           "started": u.iso_now()})
    if not args.no_open:
        u.open_url(f"http://{bind}:{port}")
    return _serve(root, port, bind)


def _run_tui(root: Path) -> int:
    try:
        import textual  # noqa: F401
    except ModuleNotFoundError:
        print(u.c("✗ TUI requer 'textual'. Rode: pip install -r requirements-tui.txt", "yellow"))
        # fallback: dump textual simples sem dep
        snap = snapshot(root)
        print(u.c(f"\n  multiagente · {snap['project']}", "bold", "cyan"))
        for a in snap["agents"]:
            print(f"    {a['agente']:<16} {a['status']:<10} trust {a['trust']:>3} "
                  f"{u.bar(a['trust']/100)}  {a['bubble']}")
        m = snap["metrics"]
        print(f"\n  tokens hoje: {m['tokens_today']:,}  ·  custo: ${m['cost_today_usd']}")
        return 0
    from tui_app import run_tui  # type: ignore
    return run_tui(root)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--background", action="store_true")
    p.add_argument("--stop", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--tui", action="store_true")
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--bind", default=None)
    sys.exit(cli(p.parse_args()))
