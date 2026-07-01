"""
verify.py — verificação com DENTES: roda testes/lint/typecheck de VERDADE e grava
o resultado em reports/feature-<NNN>/verify.json. O gate de fechamento lê esse
arquivo — teste é ground-truth executável, não prosa auto-reportada.

Uso:  python scripts/verify.py <F-NNN>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402


def _run(cmd: str, cwd: Path, timeout: int = 900) -> dict:
    try:
        p = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True,
                           text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return {"cmd": cmd, "returncode": p.returncode, "passed": p.returncode == 0,
                "tail": out[-1500:]}
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "returncode": 124, "passed": False,
                "tail": f"timeout após {timeout}s"}
    except Exception as e:  # noqa: BLE001
        return {"cmd": cmd, "returncode": 1, "passed": False, "tail": repr(e)}


def run(root: Path, nnn: str) -> dict:
    cfg = u.load_config(root).get("verify", {})
    num = nnn.replace("F-", "").lstrip("0").zfill(3)
    results = []
    for name in ("test_cmd", "lint_cmd", "typecheck_cmd"):
        cmd = str(cfg.get(name, "") or "").strip()
        if cmd:
            r = _run(cmd, root)
            r["name"] = name
            results.append(r)
    all_passed = all(r["passed"] for r in results) if results else None
    report = {"feature": nnn, "at": u.iso_now(), "results": results,
              "all_passed": all_passed, "configured": bool(results)}
    dest = root / "reports" / f"feature-{num}" / "verify.json"
    u.write_json(dest, report)
    return report


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/verify.py <F-NNN>", file=sys.stderr)
        return 2
    root = u.find_project_root()
    if root is None:
        print("Projeto não inicializado.", file=sys.stderr)
        return 2
    rep = run(root, sys.argv[1])
    if not rep["configured"]:
        print(u.c("⚠ Nenhum comando de verificação configurado em [verify]. "
                  "Configure test_cmd para ter gate de teste real.", "yellow"))
        return 0
    for r in rep["results"]:
        mark = u.c("✓", "green") if r["passed"] else u.c("✗", "red")
        print(f"  {mark} {r['name']}: {r['cmd']}  (rc={r['returncode']})")
    if rep["all_passed"]:
        print(u.c("✓ verificação PASSOU.", "green", "bold"))
        return 0
    print(u.c("✗ verificação FALHOU — a feature não fecha até passar.", "red", "bold"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
