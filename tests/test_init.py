"""Testes do scaffold (init) — CA-001, CA-005, CA-010, CA-091."""
import sys
import tomllib

import _utils as u


def test_init_creates_layout(tmp_project):
    p = tmp_project
    for d in ["docs", "specs", "reports", "memory", "logs/otel",
              ".claude/agents", ".claude/hooks", "dashboard", "scripts"]:
        assert (p / d).is_dir(), f"faltou diretório {d}"
    assert (p / u.CONFIG_FILENAME).is_file()
    assert (p / "CLAUDE.md").is_file()


def test_init_toml_valid_and_budget(tmp_path, monkeypatch):
    import init
    monkeypatch.chdir(tmp_path)
    init.run(name="x", project_type="web", budget_usd=33.0, target=tmp_path)
    with open(tmp_path / u.CONFIG_FILENAME, "rb") as f:
        cfg = tomllib.load(f)
    assert cfg["budget"]["max_cost_per_day_usd"] == 33.0
    assert "max_tokens_per_feature" in cfg["budget"]
    assert "max_tokens_per_session" not in cfg["budget"]


def test_init_memory_seven_files(tmp_project):
    # ml => arquiteto, pipeline-dev, qa-tester, dba
    for ag in ["arquiteto", "pipeline-dev", "qa-tester", "dba"]:
        d = tmp_project / "memory" / ag
        assert d.is_dir()
        for f in ["identity.md", "dossier.md", "decisions.md", "handoff.md",
                  "state.md", "lessons.md", "trust.json"]:
            assert (d / f).is_file(), f"faltou memory/{ag}/{f}"
        assert (d / "playbooks").is_dir()
        tj = u.read_json(d / "trust.json", {})
        assert tj.get("score") == 50


def test_init_substitutes_agente_var(tmp_project):
    idy = u.read_text(tmp_project / "memory" / "pipeline-dev" / "identity.md")
    assert "{{agente}}" not in idy
    assert "pipeline-dev" in idy


def test_init_idempotent_guard(tmp_project, monkeypatch):
    import init
    monkeypatch.chdir(tmp_project)
    rc = init.run(name="proj-teste", target=tmp_project)
    assert rc == 1  # recusa reinit


def test_enable_agent(tmp_project, monkeypatch):
    import init
    monkeypatch.chdir(tmp_project)
    rc = init.enable_agent("docs-writer", target=tmp_project)
    assert rc == 0
    assert (tmp_project / "memory" / "docs-writer" / "trust.json").is_file()
    # re-enable recusa
    assert init.enable_agent("docs-writer", target=tmp_project) == 1


def test_agents_registered_in_claude(tmp_project):
    # arquiteto tem template específico -> deve ir pra .claude/agents
    assert (tmp_project / ".claude" / "agents" / "arquiteto.md").is_file()
