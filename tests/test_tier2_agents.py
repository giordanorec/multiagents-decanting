"""Tier 2 — CA-200: agentes dba, frontend-dev, devops-installer, docs-writer."""
import sys
from pathlib import Path

import _utils as u

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# palavra distintiva esperada no prompt real de cada agente Tier 2
TIER2 = {
    "dba": ("migration", "sonnet"),
    "frontend-dev": ("UI", "sonnet"),
    "devops-installer": ("instala", "haiku"),
    "docs-writer": ("README", "sonnet"),
}


def test_tier2_agent_files_exist():
    for role in TIER2:
        f = PLUGIN_ROOT / "agents" / f"{role}.md"
        assert f.is_file(), f"falta agents/{role}.md"


def test_tier2_frontmatter_model():
    for role, (_kw, model) in TIER2.items():
        text = u.read_text(PLUGIN_ROOT / "agents" / f"{role}.md")
        assert f"model: {model}" in text, f"{role} deveria ser model: {model}"
        assert f"name: {role}" in text


def test_tier2_self_contained_no_spec_refs():
    # prompts não podem referenciar _spec/ (cliente não tem essa pasta)
    for role in TIER2:
        text = u.read_text(PLUGIN_ROOT / "agents" / f"{role}.md")
        assert "_spec/" not in text, f"{role} referencia _spec/ (deve ser inline)"


def test_enable_tier2_registers_real_prompt(tmp_path, monkeypatch):
    import init
    monkeypatch.chdir(tmp_path)
    init.run(name="x", project_type="outro", target=tmp_path)
    for role, (kw, _model) in TIER2.items():
        rc = init.enable_agent(role, target=tmp_path)
        assert rc == 0
        reg = tmp_path / ".claude" / "agents" / f"{role}.md"
        assert reg.is_file()
        # o prompt real (não o template genérico) tem a palavra distintiva do papel
        assert kw.lower() in u.read_text(reg).lower(), \
            f".claude/agents/{role}.md não parece ser o prompt real de {role}"


def test_web_project_includes_frontend_dev(tmp_path, monkeypatch):
    import init
    monkeypatch.chdir(tmp_path)
    init.run(name="w", project_type="web", target=tmp_path)
    assert (tmp_path / "memory" / "frontend-dev").is_dir()
    assert (tmp_path / ".claude" / "agents" / "frontend-dev.md").is_file()
