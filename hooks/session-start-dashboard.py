#!/usr/bin/env python3
"""
Hook SessionStart — sobe o painel de observabilidade e mostra o link, sem o
usuário pedir. Observabilidade é item central do mad: a pessoa deve poder ver o
que os assistentes estão fazendo, ao vivo.

- Se já está rodando, só reimprime o link.
- Se não, inicia em background e tenta abrir o browser (best-effort; em máquina
  remota/headless o link impresso resolve).
- Respeita [dashboard].auto_start = false (opt-out) e [dashboard].auto_open.
Falha em silêncio; nunca derruba a sessão.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def _find_root():
    cur = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for c in [cur, *cur.parents]:
        if (c / "multiagents-decanting.toml").is_file():
            return c
    return None


def main():
    root = _find_root()
    if root is None:
        return
    scripts = root / "scripts"
    if not (scripts / "mad.py").is_file():
        return
    sys.path.insert(0, str(scripts))
    try:
        import _utils as u  # type: ignore
    except Exception:
        return

    cfg = u.load_config(root).get("dashboard", {})
    if cfg.get("auto_start") is False:
        return
    auto_open = cfg.get("auto_open", True)

    pidfile = root / "status" / "dashboard.pid"
    info = u.read_json(pidfile, {}) or {}
    pid = info.get("pid")
    alive = False
    if pid:
        try:
            os.kill(int(pid), 0)
            alive = True
        except Exception:
            alive = False

    if alive:
        url = f"http://{info.get('bind', '127.0.0.1')}:{info.get('port', 8765)}"
        _announce(url, u)
        return

    # inicia em background
    py = sys.executable or "python3"
    args = [py, str(scripts / "mad.py"), "dashboard", "--background"]
    if not auto_open:
        args.append("--no-open")
    try:
        subprocess.run(args, cwd=str(root), capture_output=True, text=True, timeout=15)
    except Exception:
        pass
    info = u.read_json(pidfile, {}) or {}
    url = f"http://{info.get('bind', '127.0.0.1')}:{info.get('port', 8765)}"
    _announce(url, u, started=True)


def _announce(url, u, started=False):
    verb = "no ar" if started else "já rodando"
    msg = (f"\n  📊  Painel ao vivo ({verb}): {url}\n"
           f"      (abra no navegador pra ver os assistentes trabalhando em tempo real)\n")
    sys.stderr.write(msg)
    # injeta no contexto pra o Arquiteto lembrar o usuário do link
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
          "additionalContext": f"[PAINEL] O dashboard de observabilidade está em {url} — "
          f"lembre o usuário de abri-lo para acompanhar os assistentes ao vivo."}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"[mad] hook dashboard falhou: {e}\n")
