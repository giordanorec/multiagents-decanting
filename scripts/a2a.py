"""
a2a.py — gera um Agent Card compatível com A2A (Linux Foundation) a partir da
identidade de um agente do mad.

Tier 3 (CA-307). O `identity.md` + o frontmatter do agente já carregam nome,
descrição e papel; aqui isso vira um Agent Card JSON que um agente externo (Google,
Microsoft, etc.) consegue ler para descobrir capabilities. V1: gera o card. Servir
via HTTP é roadmap (o card pode ser publicado em /.well-known/agent.json).

Uso: python scripts/mad.py a2a <agente> [--write]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

A2A_VERSION = "0.1"


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    fm = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def build_card(agent: str, root: Path | None = None) -> dict | None:
    root = root or u.find_project_root()
    if root is None:
        return None
    agent_md = root / ".claude" / "agents" / f"{agent}.md"
    identity = root / "memory" / agent / "identity.md"
    if not agent_md.is_file() and not identity.is_file():
        return None

    name = agent
    description = ""
    model = ""
    if agent_md.is_file():
        fm = _frontmatter(u.read_text(agent_md))
        name = fm.get("name", agent)
        description = fm.get("description", "")
        model = fm.get("model", "")
    # primeira linha não-vazia do identity como sumário do papel
    role = ""
    if identity.is_file():
        for line in u.read_text(identity).splitlines():
            s = line.strip().lstrip("# ").strip()
            if s and not s.startswith("---"):
                role = s
                break

    proj = root.name
    return {
        "a2a_version": A2A_VERSION,
        "name": name,
        "displayName": f"{name} ({proj})",
        "description": (description or role or f"Especialista {name} do projeto {proj}.").strip(),
        "provider": {"organization": "mad (MultiAgent Decanting)", "project": proj},
        "model": model,
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True
        },
        "skills": [
            {
                "id": f"{name}-work",
                "name": f"{name}",
                "description": role or description or f"Trabalho de especialista {name}.",
                "tags": [name, "mad", "decanting"]
            }
        ],
        "memory": {
            "convention": f"memory/{name}/",
            "files": ["identity.md", "dossier.md", "decisions.md", "handoff.md",
                      "state.md", "lessons.md", "trust.json"]
        },
        "endpoints": {"note": "Servir via HTTP em /.well-known/agent.json é roadmap (V2)."}
    }


def cli(agent: str, write: bool = False) -> int:
    import json
    card = build_card(agent)
    if card is None:
        print(u.c(f"✗ Não foi possível montar o Agent Card de '{agent}' "
                  f"(agente/identity inexistente?).", "red"))
        return 1
    out = json.dumps(card, ensure_ascii=False, indent=2)
    if write:
        root = u.find_project_root() or Path.cwd()
        path = root / "memory" / agent / "agent-card.json"
        u.write_text(path, out + "\n")
        print(u.c(f"✓ Agent Card escrito em memory/{agent}/agent-card.json", "green"))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: a2a.py <agente> [--write]")
        sys.exit(2)
    sys.exit(cli(sys.argv[1], "--write" in sys.argv))
