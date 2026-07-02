"""Tier 3 — agentes (CA-310), A2A (CA-307), notify (CA-302/304), voice (CA-300)."""
from pathlib import Path

import _utils as u

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

TIER3 = {
    "llm-prompt": "sonnet",
    "mobile-dev": "sonnet",
    "asset-designer": "sonnet",
    "security-auditor": "opus",
}


# ---- agentes ----
def test_tier3_agents_exist_with_models():
    for role, model in TIER3.items():
        f = PLUGIN_ROOT / "agents" / f"{role}.md"
        assert f.is_file(), f"falta agents/{role}.md"
        text = u.read_text(f)
        assert f"model: {model}" in text, f"{role} deveria ser {model}"
        assert "_spec/" not in text


# ---- A2A agent card ----
def test_a2a_card(tmp_project):
    import a2a
    card = a2a.build_card("pipeline-dev", root=tmp_project)
    assert card is not None
    assert card["name"] == "pipeline-dev"
    assert card["protocolVersion"] == "1.0"           # A2A v1.0
    assert card["preferredTransport"] == "JSONRPC"
    assert "capabilities" in card and "skills" in card
    assert card["capabilities"]["streaming"] is True   # mad transmite estado ao vivo
    assert card["_mad"]["memory_convention"] == "memory/pipeline-dev/"


def test_a2a_card_missing_agent(tmp_project):
    import a2a
    assert a2a.build_card("inexistente", root=tmp_project) is None


def test_a2a_write(tmp_project):
    import a2a
    rc = a2a.cli  # noqa
    card = a2a.build_card("qa-tester", root=tmp_project)
    u.write_json(tmp_project / "memory" / "qa-tester" / "agent-card.json", card)
    assert (tmp_project / "memory" / "qa-tester" / "agent-card.json").is_file()


# ---- notify ----
def test_notify_no_config_sends_nothing(tmp_project):
    import notify
    # sem token configurado: não bate na rede, retorna tudo False
    res = notify.notify("oi", root=tmp_project)
    assert res["telegram"] is False and res["slack"] is False


def test_notify_env_override(tmp_project, monkeypatch):
    import notify
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.invalid/hook")
    cfg = notify._cfg(tmp_project)
    assert cfg["slack_webhook_url"] == "https://example.invalid/hook"


def test_notify_send_helpers_guard():
    import notify
    # sem token/url, helpers retornam False sem tentar rede
    assert notify.send_telegram("", "", "x") is False
    assert notify.send_slack("", "x") is False


# ---- voice ----
def test_voice_available_is_bool():
    import voice
    assert isinstance(voice.available(), bool)


def test_voice_cli_without_dep(monkeypatch, capsys):
    import voice
    monkeypatch.setattr(voice, "available", lambda: False)
    import argparse
    rc = voice.cli(argparse.Namespace(audio="x.wav", model=None))
    assert rc == 1
    assert "faster-whisper" in capsys.readouterr().out
