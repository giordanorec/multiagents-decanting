#!/usr/bin/env python3
"""
Hook SessionStart — injeta o WORKFLOW STATE no contexto do Arquiteto.

O LLM não tem como esquecer a fase: o estado + próximo passo obrigatório +
ações permitidas/bloqueadas entram no contexto a cada sessão. Fail-safe: se não
for projeto mad, silêncio. Se corrompido, avisa e injeta bloco de emergência.
"""
import json
import os
import sys
from pathlib import Path


def _find_root():
    cur = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for c in [cur, *cur.parents]:
        if (c / ".mad" / "workflow_state.json").is_file() or (c / "multiagents-decanting.toml").is_file():
            return c
    return None


def _emit_context(text: str):
    # Claude Code SessionStart: additionalContext entra no contexto da sessão.
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": text}}))


def main():
    root = _find_root()
    if root is None:
        return  # não é projeto mad
    state_path = root / ".mad" / "workflow_state.json"
    if not state_path.is_file():
        print("[mad] projeto mad sem workflow_state.json — rode /mad-init.", file=sys.stderr)
        return
    scripts = root / "scripts"
    if (scripts / "workflow.py").is_file():
        sys.path.insert(0, str(scripts))
    try:
        import workflow as wf  # type: ignore
        st = wf.WorkflowState.load(root)
    except Exception as e:  # corrompido ou sem módulo → bloco de emergência
        _emit_context(
            "═══ MAD WORKFLOW — ESTADO INDISPONÍVEL ═══\n"
            f"workflow_state.json não pôde ser lido ({e}).\n"
            "TODAS as ações de despacho estão bloqueadas até reparo.\n"
            "Rode /mad-doctor para reparo guiado. NÃO tente reparar editando o JSON à mão.")
        print(f"[mad] ERRO no workflow_state: {e}", file=sys.stderr)
        return

    allowed, blocked = st.allowed_summary()
    f = st.feature or {}
    feat_block = ""
    if st.phase == "LOOP_FEATURES" and f:
        ap = f.get("approvals", {})
        feat_block = (
            f"\nFEATURE CORRENTE: {f.get('id')} — {f.get('slug')}\n"
            f"SUB-FASE: {st.subphase}\n"
            f"ESPECIALISTA: {f.get('agent_assigned') or '(não atribuído)'}\n"
            f"BLAST RADIUS: {f.get('blast_radius')}\n"
            f"SPEC APROVADA PELO HUMANO: {'sim' if ap.get('spec_approved_by_human') else 'não'}\n"
            f"MERGE APROVADO PELO HUMANO: "
            f"{'n.a. (reversível)' if f.get('blast_radius') in ('reversivel_baixo','reversivel_medio') else ('sim' if ap.get('merge_approved_by_human') else 'não')}\n")
    warnings = st.data.get("warnings") or []
    block = (
        "═══════════════════════════════════════════════════════════════\n"
        "  ESTADO DO WORKFLOW MAD (injetado automaticamente, INALTERÁVEL)\n"
        "═══════════════════════════════════════════════════════════════\n\n"
        f"PROJETO: {st.data.get('project_name')}\n"
        f"FASE ATUAL: {st.phase}\n"
        f"{feat_block}\n"
        f"PRÓXIMO PASSO OBRIGATÓRIO:\n  {st.next_action()}\n\n"
        f"AÇÕES PERMITIDAS AGORA:\n  - " + "\n  - ".join(allowed) + "\n\n"
        f"AÇÕES BLOQUEADAS NESTE ESTADO (o hook vai IMPEDIR):\n  - " + "\n  - ".join(blocked) + "\n\n"
        + (("WARNINGS PERSISTENTES:\n  - " + "\n  - ".join(warnings) + "\n\n") if warnings else "")
        + "═══════════════════════════════════════════════════════════════\n"
        "Você é o Arquiteto. Este estado é mantido por hooks; você NÃO o muda\n"
        "direto — apenas via /mad-phase-*. Agent tool, git push e escrita fora\n"
        "do estado serão BLOQUEADOS por hook PreToolUse. Pule fases = impossível.\n"
        "═══════════════════════════════════════════════════════════════")
    _emit_context(block)
    print(f"[mad] estado: fase={st.phase}"
          + (f", feature={f.get('id')}/{st.subphase}" if f else "")
          + f", próximo={st.next_action()[:60]}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # nunca derruba a sessão
        print(f"[mad] hook session-start falhou: {e}", file=sys.stderr)
