"""
mad_init.py — /mad-init em cascata idempotente e context-aware.

Um único comando decide sozinho: RETOMAR (já há workflow_state), MIGRAR (projeto
v1.2), ADOTAR (trabalho prévio sem plugin: docs_projeto/, _spec/, discovery já
feita) ou CRIAR do zero. Cascata estrita — cada passo só roda se o anterior não
casou. A detecção é pura/testável; a conversa (confirmar, perguntar fase) fica no
command /mad-init.

Uso:
  python scripts/mad_init.py detect            # imprime JSON da decisão
  python scripts/mad_init.py adopt --phase X    # executa adoção
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402
import workflow as wf  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SUSPECT_DIRS = ["docs_projeto", "_artigo", "_spec", "_docs", "_mad_v1.3_spec"]


# ---------------------------------------------------------------------------
# detecção de tipo de projeto
# ---------------------------------------------------------------------------
def is_v1_2(target: Path) -> bool:
    if (target / ".mad" / "workflow_state.json").is_file():
        return False
    if (target / u.CONFIG_FILENAME).is_file():
        return True
    if (target / "sessions.json").is_file():
        return True
    mem = target / "memory"
    if mem.is_dir() and any((d / "MEMORY.md").is_file() for d in mem.iterdir() if d.is_dir()):
        return True
    return False


def detect_prior_context(target: Path) -> dict:
    """Sinais de trabalho prévio sem plugin. Retorna dict com found/…/phase/confidence."""
    docs_paths = []
    for cand in [target / "docs_projeto", target / "docs"]:
        if cand.is_dir():
            for f in cand.rglob("*.md"):
                try:
                    if f.stat().st_size > 500:
                        docs_paths.append(f)
                except OSError:
                    pass
    suspects = [d for d in SUSPECT_DIRS if (target / d).is_dir()]
    backlogs = [str(p.name) for p in target.glob("backlog*.md")] + \
               ([ "docs/BACKLOG_V1.md" ] if (target / "docs" / "BACKLOG_V1.md").is_file() else [])
    # memória persistente do Claude Code (best-effort; formato de hash varia)
    claude_mem = []
    proj_root = Path.home() / ".claude" / "projects"
    if proj_root.is_dir():
        key = target.name
        for d in proj_root.glob("*"):
            if key in d.name and (d / "memory").is_dir():
                claude_mem = [f for f in (d / "memory").glob("*.md") if f.name != "MEMORY.md"]
                break

    signals = len(docs_paths) + len(suspects) + len(backlogs) + (1 if claude_mem else 0)
    if signals < 2:
        return {"found": False}

    phase, conf = _infer_phase_from_signals(target, docs_paths, backlogs)
    return {
        "found": True,
        "docs_files": len(docs_paths),
        "docs_paths": [str(p.relative_to(target)) for p in docs_paths[:20]],
        "suspect_dirs": suspects,
        "backlogs": backlogs,
        "claude_memory_files": len(claude_mem),
        "inferred_phase": phase,
        "confidence": conf,
    }


def _infer_phase_from_signals(target, docs_paths, backlogs) -> tuple[str, float]:
    # objetivo claro?
    obj = target / "docs" / "00_OBJETIVO.md"
    has_obj = (obj.is_file() and len(u.read_text(obj)) >= 200) or len(docs_paths) >= 3
    if not has_obj:
        return "DISCOVERY", 0.85
    if backlogs:
        # há backlog → time/execução pode ter começado
        return "ESPEC_V1", 0.6
    return "DISCOVERY", 0.5


def detect(target: Path) -> dict:
    """Cascata estrita de 4 passos → dict com 'action'."""
    if (target / ".mad" / "workflow_state.json").is_file():
        try:
            st = wf.WorkflowState.load(target)
            return {"action": "resume", "project": st.data.get("project_name"),
                    "phase": st.phase, "subphase": st.subphase,
                    "next": st.next_action()}
        except Exception as e:
            return {"action": "repair", "reason": str(e)}
    if is_v1_2(target):
        return {"action": "migrate", "note": "Projeto v1.2 detectado (toml/MEMORY/sessions sem .mad)."}
    ctx = detect_prior_context(target)
    if ctx.get("found"):
        return {"action": "adopt", **ctx}
    return {"action": "new"}


# ---------------------------------------------------------------------------
# adoção
# ---------------------------------------------------------------------------
def adopt(target: Path, phase: str) -> int:
    import init as _init
    if phase not in wf.PHASES:
        print(u.c(f"✗ fase inválida: {phase}", "red"))
        return 2
    ts = u.iso_now().replace(":", "").replace("-", "")[:15]
    backup = target / f".mad-backup-pre-adoption-{ts}"
    for d in ["docs", "docs_projeto"]:
        src = target / d
        if src.is_dir():
            shutil.copytree(src, backup / d, dirs_exist_ok=True)

    # estrutura mínima (sem sobrescrever)
    for d in ["docs", "specs", "reports", "memory/arquiteto", "logs/otel",
              ".claude/agents", ".claude/hooks", ".mad", "scripts"]:
        (target / d).mkdir(parents=True, exist_ok=True)
    if not (target / u.CONFIG_FILENAME).is_file():
        _init._write_toml(target, 50.0)
    # arquiteto identity + agente
    if not (target / "memory" / "arquiteto" / "identity.md").is_file():
        _init._scaffold_memory(target, "arquiteto", target.name)
    _init._register_agent(target, "arquiteto")
    # refresca scripts + hooks + wira settings
    for s in _init.COPY_SCRIPTS:
        srcp = PLUGIN_ROOT / "scripts" / s
        if srcp.is_file():
            shutil.copy2(srcp, target / "scripts" / s)
    _init._copy_tree(PLUGIN_ROOT / "hooks", target / ".claude" / "hooks")
    _init._copy_tree(PLUGIN_ROOT / "dashboard", target / "dashboard")
    _init._write_hooks_settings(target)

    # referencia contexto prévio nas DECISOES (sem copiar/sobrescrever)
    ctx = detect_prior_context(target)
    ref = "\n## " + u.today_str() + " — Adoção de trabalho prévio\n\n" \
          "Projeto ADOTADO pelo mad em fase " + phase + ". Contexto pré-existente " \
          "preservado e referenciado:\n"
    for p in ctx.get("docs_paths", [])[:10]:
        ref += f"- `{p}`\n"
    for d in ctx.get("suspect_dirs", []):
        ref += f"- pasta `{d}/`\n"
    if ctx.get("claude_memory_files"):
        ref += f"- {ctx['claude_memory_files']} arquivo(s) de memória persistente do Claude Code\n"
    u.append_text(target / "docs" / "DECISOES.md", ref)

    # estado na fase adotada
    now = u.iso_now()
    others = [p.stem for p in (target / ".claude" / "agents").glob("*.md")]
    data = wf.initial_state(target.name)
    data["team_enabled"] = [{"role": r, "enabled_at": now} for r in others]
    data["backlog_features"] = wf.parse_backlog(target)
    data["current_phase"] = phase
    data["phase_entered_at"] = now
    data["phase_transitions"] = [{
        "from": "BOOTSTRAP", "to": phase, "at": now, "by": "adoption",
        "gates_checked": ["mad_init_adopt"], "evidence": {"backup": str(backup.name)},
    }]
    data["warnings"] = ["Projeto adotado; revise a fase com /mad-phase status se algo destoar."]
    wf.WorkflowState(target, data).save()
    wf.log_event(target, "adopted", phase=phase, backup=str(backup.name),
                 prior_files=ctx.get("docs_files", 0))

    print(u.c(f"\n✓ Projeto adotado em fase {phase}.", "green", "bold"))
    print(f"  Backup: {backup.name}")
    print("  Docs pré-existentes preservados. Hooks do workflow instalados.")
    print("  Próximo: abra uma sessão nova e rode /mad-phase status.")
    return 0


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="mad-init")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect").set_defaults(fn="detect")
    ad = sub.add_parser("adopt"); ad.add_argument("--phase", required=True); ad.set_defaults(fn="adopt")
    args = p.parse_args(argv)
    target = Path.cwd()
    if args.fn == "detect":
        print(json.dumps(detect(target), ensure_ascii=False, indent=2))
        return 0
    return adopt(target, args.phase)


if __name__ == "__main__":
    sys.exit(main())
