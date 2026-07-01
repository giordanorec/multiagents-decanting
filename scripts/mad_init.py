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
BACKLOG_LOCATIONS = [
    "docs/BACKLOG_V1.md", "docs_projeto/tecnico/06_backlog_v1.md",
    "docs_projeto/BACKLOG_V1.md", "BACKLOG.md", "BACKLOG_V1.md",
]


def available_specialists() -> list[str]:
    ad = PLUGIN_ROOT / "agents"
    return [p.stem for p in ad.glob("*.md")] if ad.is_dir() else []


def find_backlog(root: Path) -> Path | None:
    for rel in BACKLOG_LOCATIONS:
        p = root / rel
        if p.is_file():
            return p
    return None


def parse_backlog_rich(path: Path) -> list[dict]:
    """Extrai features do backlog: id, slug, especialista, blast_radius, status.

    Formato flexível: cada feature é uma linha/bloco com `F-NNN` e, opcionalmente,
    uma linha `**Especialista:** <role>` e `**Blast:** <br>` no bloco seguinte.
    """
    text = u.read_text(path)
    # divide em blocos por ocorrência de F-NNN
    feats = []
    parts = re.split(r"(?=\bF-\d{3}\b)", text)
    seen = set()
    for blk in parts:
        m = re.search(r"\bF-(\d{3})\b", blk)
        if not m:
            continue
        fid = "F-" + m.group(1)
        if fid in seen:
            continue
        seen.add(fid)
        # slug: texto após o F-NNN na mesma linha
        line = blk.splitlines()[0] if blk.splitlines() else ""
        after = re.sub(r".*\bF-\d{3}\b\s*[—:\-]?\s*", "", line).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", after.lower()).strip("-")[:40] or "feature"
        spec_m = re.search(r"(?i)\*\*especialista:?\*\*\s*`?([a-z][a-z0-9-]+)`?", blk)
        br_m = re.search(r"(?i)\*\*blast[_ ]?radius:?\*\*\s*`?([a-z_]+)`?", blk)
        st_m = re.search(r"(?i)\*\*(status|situa[çc][ãa]o):?\*\*\s*`?(\w+)`?", blk)
        status = (st_m.group(2).lower() if st_m else "pendente")
        if status in ("concluida", "concluída", "done", "feito"):
            status = "concluida"
        feats.append({
            "id": fid, "slug": slug,
            "agent": spec_m.group(1) if spec_m else "",
            "blast_radius": br_m.group(1).lower() if br_m else "reversivel_baixo",
            "status": status, "concluded_at": None,
        })
    return feats


def enable_specialist(root: Path, role: str) -> bool:
    """Idempotente: cria .claude/agents/<role>.md + memory/<role>/. True se criou."""
    import init as _init
    if (root / ".claude" / "agents" / f"{role}.md").is_file():
        return False
    _init._scaffold_memory(root, role, root.name)
    _init._register_agent(root, role)
    return True


def autospawn_from_backlog(root: Path) -> dict:
    bp = find_backlog(root)
    res = {"backlog_found": bp is not None, "backlog_path": str(bp.relative_to(root)) if bp else None,
           "features": [], "spawned": [], "skipped": [], "first_feature": None, "warnings": []}
    if bp is None:
        return res
    feats = parse_backlog_rich(bp)
    res["features"] = feats
    if not feats:
        res["warnings"].append(f"Backlog em {res['backlog_path']} sem features F-NNN parseáveis.")
        return res
    avail = available_specialists()
    required = []
    for f in feats:
        r = f.get("agent")
        if r and r not in required:
            required.append(r)
    for role in required:
        if role in avail:
            enable_specialist(root, role)
            res["spawned"].append(role)
        else:
            res["skipped"].append(role)
            res["warnings"].append(
                f"Backlog menciona '{role}', mas o plugin não tem esse agente. Ignorado.")
    # arquiteto sempre
    enable_specialist(root, "arquiteto")
    first = next((f for f in feats if f.get("status") == "pendente"), None)
    res["first_feature"] = first
    return res


def compute_final_phase(inferred: str, aut: dict) -> str:
    feats = aut.get("features", [])
    if aut.get("backlog_found") and feats:
        if aut.get("spawned") and aut.get("first_feature"):
            return "LOOP_FEATURES"
        if all(f.get("status") == "concluida" for f in feats):
            return "PRE_RELEASE"
        if aut.get("spawned"):
            return "LOOP_FEATURES"  # tem time; ativa próxima
        return "SETUP_TIME"
    return inferred


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

    # AUTO-SPAWN de especialistas a partir do backlog (spec 13 §Auto-spawn)
    aut = autospawn_from_backlog(target)
    final_phase = compute_final_phase(phase, aut)

    # estado na fase final
    now = u.iso_now()
    others = [p.stem for p in (target / ".claude" / "agents").glob("*.md")]
    data = wf.initial_state(target.name)
    data["team_enabled"] = [{"role": r, "enabled_at": now} for r in others]
    # backlog rico (com agente) se houver; senão o simples
    if aut.get("features"):
        data["backlog_features"] = [
            {"id": f["id"], "slug": f["slug"], "status": f["status"], "concluded_at": None,
             "agent": f.get("agent", ""), "blast_radius": f.get("blast_radius", "reversivel_baixo")}
            for f in aut["features"]]
    else:
        data["backlog_features"] = wf.parse_backlog(target)
    data["current_phase"] = final_phase
    data["phase_entered_at"] = now
    data["phase_transitions"] = [{
        "from": "BOOTSTRAP", "to": final_phase, "at": now, "by": "adoption",
        "gates_checked": ["mad_init_adopt"],
        "evidence": {"backup": str(backup.name), "inferred": phase,
                     "autospawn": aut.get("spawned", [])},
    }]
    warns = ["Projeto adotado; revise a fase com /mad-phase status se algo destoar."]
    warns += aut.get("warnings", [])
    data["warnings"] = warns
    st = wf.WorkflowState(target, data)
    # ativa a primeira feature pendente se entramos em LOOP_FEATURES
    if final_phase == "LOOP_FEATURES" and aut.get("first_feature"):
        st._activate_next_from_backlog()
    st.save()
    wf.log_event(target, "adopted", phase=final_phase, inferred=phase,
                 backup=str(backup.name), specialists_autospawned=aut.get("spawned", []),
                 first_feature=(aut.get("first_feature") or {}).get("id"))

    print(u.c(f"\n✓ Projeto adotado em fase {final_phase}.", "green", "bold"))
    print(f"  Backup: {backup.name}")
    if aut.get("spawned"):
        print(f"  Especialistas habilitados automaticamente (do backlog): {', '.join(aut['spawned'])}")
    for w in aut.get("warnings", []):
        print(u.c(f"  ▲ {w}", "yellow"))
    if final_phase == "LOOP_FEATURES" and st.feature:
        print(f"  Primeira feature ativa: {st.feature['id']} — {st.feature.get('slug','')} "
              f"(sub-fase spec_pendente).")
        print(f"  Próximo: o Arquiteto escreve specs/feature-{st.feature['id'][2:]}-*.md.")
    else:
        print("  Próximo: abra uma sessão nova e rode /mad-phase status.")
    print("  Docs pré-existentes preservados. Hooks do workflow instalados.")
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
