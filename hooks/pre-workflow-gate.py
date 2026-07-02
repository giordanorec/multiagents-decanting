#!/usr/bin/env python3
"""
Hook PreToolUse — BLOQUEIA tool calls que não correspondem ao estado do workflow.

Este é o guardrail real: não pede pra LLM "não fazer" — IMPEDE. Fail-closed:
se o estado estiver corrompido ou o módulo faltar em projeto mad, bloqueia
ações de despacho por segurança. Se não for projeto mad, libera tudo.

Bloqueio = exit 2 + mensagem acionável no stderr (mecanismo comprovado do
Claude Code). Também emite permissionDecision=deny no stdout para versões que
leem JSON.
"""
import json
import os
import sys
from pathlib import Path

BYPASS_ENV = "MAD_WORKFLOW_BYPASS"  # setado por /mad-phase emergency-bypass


def _allow():
    sys.exit(0)


def _deny(reason: str, suggestion: str, state=None):
    msg = (
        "\n[mad workflow] AÇÃO BLOQUEADA pela state machine.\n\n"
        + (f"  Estado: {state.phase}" + (f" / {state.subphase}" if state and state.subphase else "") + "\n" if state else "")
        + f"  Motivo: {reason}\n"
        + (f"  Sugestão: {suggestion}\n" if suggestion else "")
        + "\n  Ver estado: /mad-phase status"
        + "\n  Bypass (último recurso, logado): /mad-phase emergency-bypass --reason \"...\"\n")
    sys.stderr.write(msg)
    try:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason + " " + suggestion}}))
    except Exception:
        pass
    sys.exit(2)


def _consume_bypass_token(root) -> bool:
    """Bypass de uso único: valida e CONSOME .mad/bypass_token.json (uses_left>0 e
    não expirado). Retorna True se liberou (e consumiu). Substitui a env var global."""
    from datetime import datetime
    tok_path = root / ".mad" / "bypass_token.json"
    if not tok_path.is_file():
        return False
    try:
        tok = json.loads(tok_path.read_text())
        if int(tok.get("uses_left", 0)) < 1:
            return False
        if datetime.fromisoformat(tok["expires_at"]) < datetime.now().astimezone():
            tok_path.unlink(missing_ok=True)
            return False
    except Exception:
        return False
    # consome
    try:
        tok_path.unlink(missing_ok=True)
    except Exception:
        pass
    return True


def main():
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        _allow()  # sem input parseável, não é nosso caso

    tool = data.get("tool_name", "")
    tin = data.get("tool_input", {}) or {}
    cwd = Path(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    # acha raiz
    root = None
    for c in [cwd.resolve(), *cwd.resolve().parents]:
        if (c / ".mad" / "workflow_state.json").is_file() or (c / "multiagents-decanting.toml").is_file():
            root = c
            break
    if root is None:
        _allow()  # não é projeto mad

    # bypass de USO ÚNICO com validade (consome o token). Substitui a env var global.
    if _consume_bypass_token(root):
        _allow()

    scripts = root / "scripts"
    if (scripts / "workflow.py").is_file():
        sys.path.insert(0, str(scripts))
    try:
        import workflow as wf  # type: ignore
    except Exception:
        # projeto mad mas sem o módulo → fail-closed só para despacho/push
        if tool in ("Agent", "Task") or (tool == "Bash" and "git push" in tin.get("command", "")):
            _deny("workflow.py indisponível; despacho bloqueado por segurança.",
                  "Rode /mad-doctor.")
        _allow()

    if not wf.WorkflowState.exists(root):
        _allow()  # ainda em bootstrap puro sem state → init cuidará

    try:
        st = wf.WorkflowState.load(root)
    except Exception as e:
        if tool in ("Agent", "Task") or (tool == "Bash" and "git push" in tin.get("command", "")):
            _deny(f"workflow_state.json inválido ({e}); despacho bloqueado.", "Rode /mad-doctor.")
        _allow()

    allow, reason, suggestion = st.decide_tool(tool, tin)
    if allow:
        _allow()
    # loga o bloqueio (auditoria)
    try:
        wf.log_event(root, "tool_blocked", tool=tool, phase=st.phase,
                     subphase=st.subphase, reason=reason)
    except Exception:
        pass
    _deny(reason, suggestion, st)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # bug inesperado do hook não deve bricar a sessão inteira; as decisões
        # críticas (Agent/push) já são fail-closed dentro de main().
        sys.stderr.write(f"[mad] hook pre-workflow-gate erro: {e}\n")
        sys.exit(0)
