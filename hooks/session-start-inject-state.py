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
    try:
        human_label = wf.human_label(st.phase)
        human_doing = wf.human_doing(st.phase)
    except Exception:
        human_label, human_doing = st.phase, ""
    f = st.feature or {}
    feat_block = ""
    if st.phase == "LOOP_FEATURES" and f:
        ap = f.get("approvals", {})
        feat_block = (
            f"\nITEM ATUAL: {f.get('id')} — {f.get('slug')}\n"
            f"SITUAÇÃO (técnica): {st.subphase}\n"
            f"ASSISTENTE: {f.get('agent_assigned') or '(não definido)'}\n"
            f"APROVAÇÃO DA DESCRIÇÃO PELO HUMANO: {'sim' if ap.get('spec_approved_by_human') else 'não'}\n")
    warnings = st.data.get("warnings") or []
    block = (
        "═══════════════════════════════════════════════════════════════\n"
        "  ESTADO DO WORKFLOW MAD (injetado por hook, INALTERÁVEL)\n"
        "═══════════════════════════════════════════════════════════════\n\n"
        f"PROJETO: {st.data.get('project_name')}\n"
        f"AGORA ESTAMOS: {human_label} — {human_doing}\n"
        f"(nome técnico interno, NÃO fale com o usuário: {st.phase})\n"
        f"{feat_block}\n"
        f"PRÓXIMO PASSO OBRIGATÓRIO:\n  {st.next_action()}\n\n"
        f"AÇÕES PERMITIDAS AGORA:\n  - " + "\n  - ".join(allowed) + "\n\n"
        f"AÇÕES BLOQUEADAS (o hook vai IMPEDIR):\n  - " + "\n  - ".join(blocked) + "\n\n"
        + (("AVISOS:\n  - " + "\n  - ".join(warnings) + "\n\n") if warnings else "")
        + "═══════════════════════════════════════════════════════════════\n"
        "REGISTRO DE LINGUAGEM: ASSUMA QUE O USUÁRIO É LEIGO por padrão — se ele não\n"
        "sinalizar o contrário, é leigo. Fale simples: traduza os nomes técnicos\n"
        "(DISCOVERY, SETUP_TIME, 'fase', 'gate'...) para o que ele faz — entender a\n"
        "ideia → combinar o que construir → montar o time (e o custo) → acompanhar a\n"
        "construção → testar/validar → recomeçar. SÓ suba o registro (fases, tokens,\n"
        "arquitetura) quando o usuário DER SINAL CLARO de que é técnico (usa jargão,\n"
        "pede detalhe, demonstra domínio). Na dúvida, simples. É a dança do discovery.\n\n"
        "VOCÊ CONDUZ — o usuário só conversa. Ele NÃO roda comandos de processo\n"
        "(/mad-phase approve-spec, next...) nem digita 'qual fase'. Quando algo precisa\n"
        "da decisão dele, APRESENTE (de preferência como arquivo/artefato pra olhar,\n"
        "não muro de texto), pergunte em linguagem natural, aceite feedback (inclusive\n"
        "áudio via mad.py voice) e ajuste. Ao concordar, VOCÊ roda a mecânica por ele\n"
        "(python scripts/mad_phase.py approve-spec F-NNN, etc., via Bash).\n\n"
        "Você é o Arquiteto. O estado é mantido por hooks; a transição é sempre via\n"
        "mad_phase.py (que você roda). Agent tool/git push/escrita fora do estado\n"
        "serão BLOQUEADOS até a aprovação certa existir.\n"
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
