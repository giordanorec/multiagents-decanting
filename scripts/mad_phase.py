"""
mad_phase.py — CLI das transições de workflow (backend dos /mad-phase-*).

Única forma legítima de mexer no workflow_state. Cada ação valida gate + loga.
Uso: python scripts/mad_phase.py <status|next|next-phase|approve-spec|approve-merge|
     rework|rollback|activate|emergency-bypass> [args]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402
import workflow as wf  # noqa: E402


def _root() -> Path | None:
    return wf.find_root()


def _norm(nnn: str) -> str:
    nnn = nnn.upper()
    if not nnn.startswith("F-"):
        nnn = "F-" + nnn.zfill(3)
    return nnn


def _load(root):
    try:
        return wf.WorkflowState.load(root)
    except Exception as e:
        print(u.c(f"✗ workflow_state inválido: {e}. Rode /mad-doctor.", "red"))
        return None


# ---------------------------------------------------------------------------
def cmd_status(root, st, args) -> int:
    print(u.c(f"\n  {st.data.get('project_name')}", "bold", "cyan"))
    print(u.c(f"  Agora: {wf.human_label(st.phase)}", "bold") +
          f" — {wf.human_doing(st.phase)}")
    print(u.c(f"  (etapa técnica: {st.phase})", "dim"))
    f = st.feature
    if f:
        print(u.c("\n  Item atual", "bold"))
        print(f"    {f['id']} — {f.get('slug','')}  ·  {wf.SUBPHASE_HUMAN.get(st.subphase, st.subphase)}")
        print(f"    assistente: {f.get('agent_assigned') or '(a definir)'}")
    print(u.c("\n  Próximo passo:", "bold"))
    print(f"    → {st.next_action()}")
    allowed, blocked = st.allowed_summary()
    print(u.c("\n  Permitido:", "green"))
    for a in allowed:
        print(f"    ✓ {a}")
    print(u.c("  Bloqueado:", "red"))
    for b in blocked:
        print(f"    ✗ {b}")
    bl = st.data.get("backlog_features", [])
    if bl:
        print(u.c(f"\n  Backlog ({len(bl)}):", "bold"))
        for feat in bl[:12]:
            g = {"concluida": "●", "em_andamento": "◐", "pendente": "○", "cancelada": "✗"}.get(feat.get("status"), "·")
            print(f"    {g} {feat['id']} {feat.get('slug','')}  ({feat.get('status')})")
    warns = st.data.get("warnings", [])
    if warns:
        print(u.c("\n  ⚠ Warnings:", "yellow"))
        for w in warns:
            print(f"    - {w}")
    print()
    return 0


def cmd_next(root, st, args) -> int:
    if st.phase != "LOOP_FEATURES":
        ok, msg = st.can_advance_phase()
        if not ok:
            print(u.c(f"✗ Ainda não dá pra avançar de {st.phase}:", "yellow"))
            print(f"  {msg}")
            return 1
        ok, target = st.advance_phase(by="human")
        print(u.c(f"✓ {st.phase}... → {target}", "green"))
        print(f"  Próximo: {st.next_action()}")
        return 0

    sp = st.subphase
    f = st.feature or {}
    nnn = f.get("id")
    if f is None or not nnn:
        st._activate_next_from_backlog()
        st.save()
        if st.feature:
            print(u.c(f"✓ feature ativada: {st.feature['id']} (spec_pendente)", "green"))
            return 0
        print(u.c("○ backlog vazio ou tudo concluído. Talvez /mad-phase next-phase.", "dim"))
        return 1

    if sp == "spec_pendente":
        ok, msg = wf.gate_spec_written(root, nnn)
        if not ok:
            print(u.c(f"✗ spec de {nnn} incompleta: {msg}", "yellow"))
            return 1
        sp_path = wf._spec_path(root, nnn)
        f["spec_path"] = str(sp_path.relative_to(root)) if sp_path else None
        st.set_subphase("spec_validada", by="arquiteto")
        # FULL AUTO: item reversível (baixo risco) flui direto pra construção,
        # sem travar pedindo aprovação. Só o irreversível pede o humano.
        if f.get("blast_radius") in wf.BLAST_REVERSIBLE:
            st.set_subphase("executando", by="arquiteto")
            wf.log_event(root, "spec_auto_approved", feature=nnn, by="arquiteto",
                         reason="blast reversível — flui sem travar")
            print(u.c(f"✓ {nnn} pronto — seguindo direto pra construção (baixo risco).", "green"))
            return 0
        print(u.c(f"✓ spec de {nnn} pronta. Item de risco alto: precisa da sua aprovação.", "green"))
        return 0
    if sp == "spec_validada":
        print(u.c(f"✗ {nnn} é item de risco alto e aguarda sua aprovação.", "yellow"))
        print(f"  (só isto trava; itens reversíveis fluem sozinhos)")
        return 1
    if sp == "executando":
        print(u.c(f"✗ {nnn} em execução. Chame o Agent tool (mad:{f.get('agent_assigned')}).", "yellow"))
        print("  A sub-fase avança sozinha quando o especialista decantar.")
        return 1
    if sp == "validando":
        ok, msg = wf.gate_arquiteto_validated(root, nnn)
        if not ok:
            print(u.c(f"✗ validação de {nnn} incompleta: {msg}", "yellow"))
            return 1
        # Art. 4: teste é ground-truth executável (não prosa).
        ok, msg = wf.gate_tests_green(root, nnn)
        if not ok:
            print(u.c(f"✗ {nnn} — verificação: {msg}", "yellow"))
            return 1
        # Separação de deveres: autor != verificador.
        ok, msg = wf.gate_independent_review(root, nnn)
        if not ok:
            print(u.c(f"✗ {nnn} — revisão independente: {msg}", "yellow"))
            return 1
        # CONSTITUIÇÃO Art. 1: não fecha (nem vai pra aprovação) sem spec+docs
        # espelhando o código.
        ok, msg = wf.gate_docs_synced(root, nnn)
        if not ok:
            print(u.c(f"✗ {nnn} — doc desatualizado: {msg}", "yellow"))
            print("  Atualize a spec pro as-built + os docs vivos afetados, e escreva")
            print(f"  reports/feature-{nnn.replace('F-','').lstrip('0').zfill(3)}/docs-sync.md.")
            return 1
        # FULL AUTO por padrão: flui mesmo se irreversível. Só trava se o projeto
        # pediu explicitamente ([workflow].confirm_irreversible = true).
        cfg = u.load_config(root).get("workflow", {})
        confirm = bool(cfg.get("confirm_irreversible", False))
        if f.get("blast_radius") in wf.BLAST_REVERSIBLE or not confirm:
            return _close_feature(root, st, nnn, args)
        st.set_subphase("aprovacao_humano", by="arquiteto")
        print(u.c(f"✓ {nnn} validado. Item difícil de desfazer — pede sua confirmação.", "green"))
        return 0
    if sp == "aprovacao_humano":
        print(u.c(f"✗ {nnn} aguarda /mad-phase approve-merge {nnn}.", "yellow"))
        return 1
    return 0


def cmd_next_phase(root, st, args) -> int:
    ok, msg = st.can_advance_phase()
    if not ok:
        print(u.c(f"✗ gates de {st.phase} pendentes: {msg}", "yellow"))
        return 1
    ok, target = st.advance_phase(by="human")
    print(u.c(f"✓ fase: → {target}", "green"))
    return 0


def cmd_approve_spec(root, st, args) -> int:
    nnn = _norm(args.feature)
    f = st.feature or {}
    if f.get("id") != nnn or st.subphase != "spec_validada":
        print(u.c(f"✗ {nnn} não está em spec_validada (está: {st.subphase}).", "yellow"))
        return 1
    wf.log_event(root, "approve_spec", feature=nnn, by="human")
    f["approvals"]["spec_approved_by_human"] = True
    f["approvals"]["spec_approved_at"] = u.iso_now()
    st.set_subphase("executando", by="human")
    print(u.c(f"✓ spec de {nnn} APROVADA pelo humano.", "green"))
    print(f"  Liberado: Agent tool com subagent_type=mad:{f.get('agent_assigned')}.")
    return 0


def cmd_approve_merge(root, st, args) -> int:
    nnn = _norm(args.feature)
    f = st.feature or {}
    if f.get("id") != nnn or st.subphase != "aprovacao_humano":
        print(u.c(f"✗ {nnn} não está em aprovacao_humano (está: {st.subphase}).", "yellow"))
        return 1
    wf.log_event(root, "approve_merge", feature=nnn, by="human")
    f["approvals"]["merge_approved_by_human"] = True
    f["approvals"]["merge_approved_at"] = u.iso_now()
    return _close_feature(root, st, nnn, args)


def cmd_rework(root, st, args) -> int:
    nnn = _norm(args.feature)
    if not args.note:
        print(u.c("✗ rework exige --note.", "red"))
        return 2
    if st.subphase != "validando":
        print(u.c(f"✗ rework só em validando (está: {st.subphase}).", "yellow"))
        return 1
    mag = args.magnitude or "minor"
    f = st.feature or {}
    f["rework_count"] = int(f.get("rework_count", 0)) + 1
    max_rw = int(u.load_config(root).get("verify", {}).get("max_rework", 3) or 3)
    agent = f.get("agent_assigned", "")
    tp = root / "memory" / agent / "trust.json"
    if tp.is_file():
        u.apply_trust_outcome(tp, nnn, "rework_major" if mag == "major" else "rework_minor")
    if f["rework_count"] > max_rw:
        # dead-letter: parou de ciclar; escala pro humano decidir.
        st.set_subphase("aprovacao_humano", by="arquiteto")
        wf.log_event(root, "dead_letter", feature=nnn, by="arquiteto",
                     rework_count=f["rework_count"], note=args.note)
        print(u.c(f"✗ {nnn} atingiu o teto de {max_rw} reworks. Não fica ciclando — "
                  f"escalei pra você decidir (aprovar assim mesmo, replanejar ou "
                  f"descartar). Motivo do último: {args.note}", "yellow", "bold"))
        return 0
    st.set_subphase("executando", by="arquiteto")
    wf.log_event(root, "rework", feature=nnn, by="arquiteto", note=args.note,
                 magnitude=mag, attempt=f["rework_count"])
    print(u.c(f"✓ rework de {nnn} solicitado ({mag}, tentativa {f['rework_count']}/{max_rw}). "
              f"Volta a executando.", "green"))
    return 0


def cmd_rollback(root, st, args) -> int:
    nnn = _norm(args.feature)
    if not args.reason:
        print(u.c("✗ rollback exige --reason.", "red"))
        return 2
    f = st.feature or {}
    if f.get("id") != nnn:
        print(u.c(f"✗ {nnn} não é a feature ativa.", "yellow"))
        return 1
    st.set_subphase("spec_pendente", by="human")
    wf.log_event(root, "rollback", feature=nnn, by="human", reason=args.reason)
    print(u.c(f"✓ rollback de {nnn} → spec_pendente. Motivo registrado.", "green"))
    return 0


def cmd_activate(root, st, args) -> int:
    nnn = _norm(args.feature)
    for feat in st.data.get("backlog_features", []):
        if feat["id"] == nnn and feat.get("status") == "pendente":
            feat["status"] = "em_andamento"
            st.data["active_feature"] = {
                "id": nnn, "slug": feat.get("slug", ""), "subphase": "spec_pendente",
                "subphase_entered_at": u.iso_now(), "spec_path": None, "report_path": None,
                "agent_assigned": feat.get("agent", ""), "blast_radius": feat.get("blast_radius", "reversivel_baixo"),
                "approvals": {"spec_approved_by_human": False, "spec_approved_at": None,
                              "merge_approved_by_human": False, "merge_approved_at": None},
                "subphase_transitions": []}
            st.save()
            print(u.c(f"✓ {nnn} ativada (spec_pendente).", "green"))
            return 0
    print(u.c(f"✗ {nnn} não encontrada como pendente no backlog.", "yellow"))
    return 1


def cmd_emergency_bypass(root, st, args) -> int:
    if not args.reason or len(args.reason) < 50:
        print(u.c("✗ emergency-bypass exige --reason com ≥50 chars.", "red"))
        return 2
    wf.log_event(root, "emergency_bypass", by="human", reason=args.reason)
    st.data.setdefault("warnings", []).append(
        f"Bypass usado em {u.iso_now()[:16]}. Investigar.")
    st.save()
    print(u.c("⚠ BYPASS registrado. Libera a PRÓXIMA ação (uso único).", "yellow", "bold"))
    print("  Exporte no shell da ação: export MAD_WORKFLOW_BYPASS=1  (e unset depois).")
    return 0


def _close_feature(root, st, nnn, args) -> int:
    f = st.feature or {}
    agent = f.get("agent_assigned", "")
    tp = root / "memory" / agent / "trust.json"
    if tp.is_file():
        u.apply_trust_outcome(tp, nnn, "accepted")
    num = nnn.replace("F-", "").lstrip("0").zfill(3)
    sync = root / "reports" / f"feature-{num}" / "docs-sync.md"
    sync_txt = u.read_text(sync).strip() if sync.is_file() else ""
    u.append_text(root / "docs" / "DECISOES.md",
                  f"\n## {u.today_str()} — {nnn} concluída ({f.get('slug','')})\n\n"
                  f"Por {agent}. Blast: {f.get('blast_radius')}. "
                  f"Spec e docs sincronizados (Constituição Art. 1).\n\n"
                  + (f"{sync_txt}\n" if sync_txt else ""))
    for feat in st.data.get("backlog_features", []):
        if feat["id"] == nnn:
            feat["status"] = "concluida"
            feat["concluded_at"] = u.iso_now()
    st.set_subphase("concluida", by="human")
    st.data["active_feature"] = None
    st._activate_next_from_backlog()
    st.save()
    nxt = st.feature
    print(u.c(f"✓ {nnn} CONCLUÍDA (trust +5, DECISOES atualizado, backlog marcado).", "green", "bold"))
    if nxt:
        print(f"  Próxima feature ativa: {nxt['id']} — {nxt.get('slug','')} (spec_pendente).")
    else:
        print("  Backlog concluído. Talvez /mad-phase next-phase (PRE_RELEASE).")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="mad-phase")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("next").set_defaults(func=cmd_next)
    sub.add_parser("next-phase").set_defaults(func=cmd_next_phase)
    for name, fn in [("approve-spec", cmd_approve_spec), ("approve-merge", cmd_approve_merge),
                     ("activate", cmd_activate)]:
        sp = sub.add_parser(name); sp.add_argument("feature"); sp.set_defaults(func=fn)
    rw = sub.add_parser("rework"); rw.add_argument("feature"); rw.add_argument("--note", default="")
    rw.add_argument("--magnitude", choices=["minor", "major"], default="minor"); rw.set_defaults(func=cmd_rework)
    rb = sub.add_parser("rollback"); rb.add_argument("feature"); rb.add_argument("--reason", default="")
    rb.set_defaults(func=cmd_rollback)
    eb = sub.add_parser("emergency-bypass"); eb.add_argument("--reason", default=""); eb.set_defaults(func=cmd_emergency_bypass)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = _root()
    if root is None:
        print(u.c("✗ não é um projeto mad (sem .mad/ ou multiagents-decanting.toml).", "red"))
        return 2
    st = _load(root)
    if st is None:
        return 2
    return args.func(root, st, args)


if __name__ == "__main__":
    sys.exit(main())
