"""
migrate_v1_3.py — migra um projeto mad v1.2 (sem .mad/) para v1.3 (state machine).

Preserva memory/docs/specs/reports. Refresca scripts e hooks, wira os hooks do
workflow no settings.json, e cria .mad/workflow_state.json INFERINDO a fase a
partir de evidências no filesystem. Se a inferência for de baixa confiança,
mantém DISCOVERY + registra warning pedindo revisão humana.

Uso: python <plugin>/scripts/migrate_v1_3.py   (rode na raiz do projeto)
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402
import workflow as wf  # noqa: E402
import init as _init  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def infer_phase(root: Path) -> tuple[str, float, list[str]]:
    """Retorna (fase, confiança 0-1, notas). Conservador: na dúvida, DISCOVERY."""
    notes = []
    obj = root / "docs" / "00_OBJETIVO.md"
    obj_ok = obj.is_file() and len(u.read_text(obj)) >= 200
    dec_ok = wf._decisoes_count(root) >= 3
    backlog = (root / "docs" / "BACKLOG_V1.md").is_file()
    ad = root / ".claude" / "agents"
    others = [p.stem for p in ad.glob("*.md")] if ad.is_dir() else []
    others = [r for r in others if r != "arquiteto"]
    reports = list((root / "reports").glob("*/**/*.md")) if (root / "reports").is_dir() else []

    if not (obj_ok and dec_ok):
        return "DISCOVERY", 0.9, ["discovery ainda incompleta"]
    if not backlog:
        return "ESPEC_V1", 0.8, ["objetivo pronto; falta BACKLOG_V1.md"]
    if not others:
        return "SETUP_TIME", 0.7, ["backlog pronto; sem especialistas habilitados"]
    if reports:
        notes.append("há reports — projeto já executou features")
        return "LOOP_FEATURES", 0.6, notes
    # backlog + agentes mas sem reports: ambíguo entre SETUP_TIME e LOOP
    return "LOOP_FEATURES", 0.4, ["ambíguo (backlog+agentes, sem reports) — REVISAR"]


def run(target: Path | None = None) -> int:
    target = (target or Path.cwd()).resolve()
    if not (target / u.CONFIG_FILENAME).is_file():
        print(u.c("✗ não parece um projeto mad (sem multiagents-decanting.toml).", "red"))
        return 2
    if (target / ".mad" / "workflow_state.json").is_file():
        print(u.c("▲ projeto já tem .mad/workflow_state.json (já é v1.3).", "yellow"))
        return 1

    # 1. refresca scripts novos
    (target / "scripts").mkdir(exist_ok=True)
    for s in _init.COPY_SCRIPTS:
        src = PLUGIN_ROOT / "scripts" / s
        if src.is_file():
            shutil.copy2(src, target / "scripts" / s)
    # 2. refresca hooks
    _init._copy_tree(PLUGIN_ROOT / "hooks", target / ".claude" / "hooks")
    # 3. re-wira settings (inclui os hooks do workflow)
    _init._write_hooks_settings(target)

    # 4. infere fase
    phase, conf, notes = infer_phase(target)
    project = target.name
    cl = target / "CLAUDE.md"
    if cl.is_file():
        first = u.read_text(cl).splitlines()[0].lstrip("# ").strip()
        if first:
            project = first.split("—")[0].strip()

    now = u.iso_now()
    others = [p.stem for p in (target / ".claude" / "agents").glob("*.md")]
    data = wf.initial_state(project)
    data["team_enabled"] = [{"role": r, "enabled_at": now} for r in others]
    data["backlog_features"] = wf.parse_backlog(target)
    data["current_phase"] = phase
    data["phase_entered_at"] = now
    data["phase_transitions"] = [{
        "from": "BOOTSTRAP", "to": phase, "at": now, "by": "migration",
        "gates_checked": ["migrate_v1_3"], "evidence": {"confidence": conf, "notes": notes},
    }]
    if conf < 0.5:
        data["warnings"] = [
            f"Migração inferiu fase={phase} com confiança baixa ({conf}). "
            f"Revise com /mad-phase status e ajuste se necessário. Notas: {'; '.join(notes)}"]
    st = wf.WorkflowState(target, data)
    st.save()
    wf.log_event(target, "init", project=project, migrated=True, phase=phase, confidence=conf)

    print(u.c(f"\n✓ Migração v1.2 → v1.3 concluída.", "green", "bold"))
    print(f"  Fase inferida: {phase} (confiança {conf:.0%})")
    for n in notes:
        print(f"    · {n}")
    if conf < 0.5:
        print(u.c("  ⚠ Confiança baixa — revise a fase com /mad-phase status.", "yellow"))
    print("  Memory/docs/specs/reports preservados. Hooks do workflow instalados.")
    print("  Próximo: /mad-phase status")
    return 0


if __name__ == "__main__":
    sys.exit(run())
