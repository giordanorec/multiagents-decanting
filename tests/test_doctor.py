"""Testes do doctor — CA-096 e invariantes de saúde."""
import doctor


def test_doctor_no_project(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = doctor.run(root=None)
    assert rc == 2  # sem projeto


def test_doctor_fresh_project_runs(tmp_project, capsys):
    rc = doctor.run(root=tmp_project)
    out = capsys.readouterr().out
    assert "doctor" in out
    # projeto recém-criado: agentes nunca invocados => amarelo (warnings), não vermelho
    assert rc == 0
    assert "Estrutura" in out
    assert "Trust scores" in out


def test_doctor_json_mode(tmp_project, capsys):
    doctor.run(root=tmp_project, as_json=True)
    import json
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] in {"verde", "amarelo", "vermelho"}
    titles = [s["title"] for s in out["sections"]]
    assert "Versões" in titles and "Budget (hoje)" in titles


def test_doctor_detects_incomplete_memory(tmp_project):
    # remove um arquivo mandatório -> deve virar problema (vermelho)
    (tmp_project / "memory" / "qa-tester" / "identity.md").unlink()
    rc = doctor.run(root=tmp_project)
    assert rc == 1  # problema detectado
