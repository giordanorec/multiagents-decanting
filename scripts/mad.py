#!/usr/bin/env python3
"""
mad.py — entry point único da CLI do multiagents-decanting.

Subcomandos determinísticos (rodados pelo Claude via slash commands ou pelo
usuário direto). Os subcomandos conversacionais (decant retroativo, explain,
tutorial) são conduzidos pelos próprios slash commands em Markdown — aqui só
ficam as partes que são puro filesystem/diagnóstico.

Uso:
    python scripts/mad.py doctor [--json]
    python scripts/mad.py init [--name N] [--type T] [--agents a,b,c]
    python scripts/mad.py enable <agente>
    python scripts/mad.py inspect <agente>
    python scripts/mad.py trust <agente>
    python scripts/mad.py dashboard [--background|--stop|--status] [--port P] [--no-open] [--bind ADDR]
    python scripts/mad.py version
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

PLUGIN_VERSION = "1.0.0"


def _cmd_doctor(args) -> int:
    import doctor
    return doctor.run(as_json=args.json)


def _cmd_init(args) -> int:
    import init
    return init.run(
        name=args.name,
        project_type=args.type,
        agents=[a.strip() for a in args.agents.split(",")] if args.agents else None,
        budget_usd=args.budget,
    )


def _cmd_enable(args) -> int:
    import init
    return init.enable_agent(args.agente)


def _cmd_inspect(args) -> int:
    import inspect_agent
    return inspect_agent.run(args.agente)


def _cmd_trust(args) -> int:
    import inspect_agent
    return inspect_agent.trust(args.agente)


def _cmd_dashboard(args) -> int:
    import dashboard_server
    return dashboard_server.cli(args)


def _cmd_notify(args) -> int:
    import notify
    return notify.cli(args.message)


def _cmd_a2a(args) -> int:
    import a2a
    return a2a.cli(args.agente, write=args.write)


def _cmd_voice(args) -> int:
    import voice
    return voice.cli(args)


def _cmd_version(args) -> int:
    print(f"mad (MultiAgent Decanting) {PLUGIN_VERSION}")
    ccv = u.get_claude_code_version()
    print(f"claude code: {'.'.join(map(str, ccv)) if ccv else 'não detectado'}")
    print(f"python: {sys.version.split()[0]}  ·  plataforma: {u.get_platform()}"
          f"{' (WSL)' if u.is_wsl() else ''}")
    print(f"sendmessage: {'on' if u.supports_sendmessage() else 'off (fallback Agent call)'}")
    return 0


def _cmd_bootstrap(args) -> int:
    """Setup 1-comando: instala a dep opcional (websockets p/ dashboard) e roda doctor."""
    import subprocess
    print(u.c("→ mad bootstrap: preparando o ambiente…", "cyan"))
    try:
        import websockets  # noqa: F401
        print(u.c("  ✓ websockets já presente", "green"))
    except Exception:
        print("  instalando websockets (dashboard ao vivo)…")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "websockets"],
                           check=False, timeout=180)
        except Exception as e:  # noqa: BLE001
            print(u.c(f"  ⚠ não instalei websockets automaticamente: {e}", "yellow"))
    import doctor
    return doctor.run(u.find_project_root())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mad", description="mad — MultiAgent Decanting CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="diagnóstico de saúde do projeto")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=_cmd_doctor)

    i = sub.add_parser("init", help="scaffold do projeto (estrutura + templates)")
    i.add_argument("--name", default=None)
    i.add_argument("--type", default="outro",
                   choices=["ml", "web", "cli", "jogo", "documento", "outro"])
    i.add_argument("--agents", default=None, help="lista separada por vírgula")
    i.add_argument("--budget", type=float, default=50.0)
    i.set_defaults(func=_cmd_init)

    e = sub.add_parser("enable", help="habilita um especialista adicional")
    e.add_argument("agente")
    e.set_defaults(func=_cmd_enable)

    ins = sub.add_parser("inspect", help="estado completo de um agente")
    ins.add_argument("agente")
    ins.set_defaults(func=_cmd_inspect)

    t = sub.add_parser("trust", help="trust score e histórico de um agente")
    t.add_argument("agente")
    t.set_defaults(func=_cmd_trust)

    dash = sub.add_parser("dashboard", help="servidor do dashboard web local")
    dash.add_argument("--background", action="store_true")
    dash.add_argument("--stop", action="store_true")
    dash.add_argument("--status", action="store_true")
    dash.add_argument("--tui", action="store_true")
    dash.add_argument("--no-open", action="store_true")
    dash.add_argument("--port", type=int, default=None)
    dash.add_argument("--bind", default=None)
    dash.set_defaults(func=_cmd_dashboard)

    n = sub.add_parser("notify", help="envia notificação (Telegram/Slack) se configurado")
    n.add_argument("message")
    n.set_defaults(func=_cmd_notify)

    a = sub.add_parser("a2a", help="gera Agent Card A2A de um agente")
    a.add_argument("agente")
    a.add_argument("--write", action="store_true")
    a.set_defaults(func=_cmd_a2a)

    vo = sub.add_parser("voice", help="transcreve áudio localmente (faster-whisper opcional)")
    vo.add_argument("audio")
    vo.add_argument("--model", default=None)
    vo.set_defaults(func=_cmd_voice)

    v = sub.add_parser("version", help="versões")
    v.set_defaults(func=_cmd_version)

    bs = sub.add_parser("bootstrap", help="setup 1-comando: instala deps opcionais + doctor")
    bs.set_defaults(func=_cmd_bootstrap)

    # alias: dashboard-status (usado por alguns command md)
    ds = sub.add_parser("dashboard-status")
    ds.set_defaults(func=lambda a: _cmd_dashboard(argparse.Namespace(
        background=False, stop=False, status=True, tui=False,
        no_open=True, port=None, bind=None)))

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
