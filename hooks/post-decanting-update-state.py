#!/usr/bin/env python3
"""
Hook PostToolUse(Agent) — avança a sub-fase quando o especialista decantou.

Depois que o Agent tool retorna, se a feature ativa estava em `executando` e há
report + decanting, transita para `validando` automaticamente. Se não decantou,
registra warning e penaliza o trust do agente. Falha em silêncio (nunca derruba).
"""
import json
import os
import sys
from pathlib import Path


def _find_root():
    cur = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for c in [cur, *cur.parents]:
        if (c / ".mad" / "workflow_state.json").is_file():
            return c
    return None


def main():
    root = _find_root()
    if root is None:
        return
    scripts = root / "scripts"
    if (scripts / "workflow.py").is_file():
        sys.path.insert(0, str(scripts))
    try:
        import workflow as wf  # type: ignore
        import _utils as u  # type: ignore
        st = wf.WorkflowState.load(root)
    except Exception:
        return

    if st.phase != "LOOP_FEATURES" or st.subphase != "executando":
        return
    f = st.feature or {}
    nnn = f.get("id", "")
    agent = f.get("agent_assigned", "")
    ok, _msg = wf.gate_execution_done(root, nnn, agent)
    if ok:
        st.set_subphase("validando", by="hook")
        print(f"[mad] {nnn}: executando → validando (report detectado).", file=sys.stderr)
    else:
        warn = f"Feature {nnn}: agente '{agent}' não decantou (sem report). Sub-fase travada."
        if warn not in st.data.get("warnings", []):
            st.data.setdefault("warnings", []).append(warn)
            st.save()
        # penaliza trust
        try:
            tp = root / "memory" / agent / "trust.json"
            if tp.is_file():
                u.apply_trust_outcome(tp, nnn, "decanting_skipped")
        except Exception:
            pass
        wf.log_event(root, "gate_check_failed", feature=nnn, reason="decanting ausente")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"[mad] hook post-decanting erro: {e}\n")
