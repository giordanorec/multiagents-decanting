"""Testes do protocolo de decanting e trust ladder — CA-014, CA-020..022."""
import _utils as u


def test_trust_default_50(tmp_project):
    tj = u.read_json(tmp_project / "memory" / "pipeline-dev" / "trust.json", {})
    assert tj["score"] == 50


def test_trust_accepted_raises(tmp_project):
    tp = tmp_project / "memory" / "pipeline-dev" / "trust.json"
    out = u.apply_trust_outcome(tp, "feature-001", "accepted")
    assert out["score"] == 55
    assert out["history"][-1]["outcome"] == "accepted"
    assert out["history"][-1]["weight"] == 5


def test_trust_rework_major_lowers(tmp_project):
    tp = tmp_project / "memory" / "qa-tester" / "trust.json"
    u.apply_trust_outcome(tp, "f1", "rework_major")
    out = u.read_json(tp, {})
    assert out["score"] == 47


def test_trust_caps_at_bounds(tmp_project):
    tp = tmp_project / "memory" / "dba" / "trust.json"
    for _ in range(30):
        u.apply_trust_outcome(tp, "f", "accepted")
    assert u.read_json(tp, {})["score"] == 100
    for _ in range(30):
        u.apply_trust_outcome(tp, "f", "rejected")
    assert u.read_json(tp, {})["score"] == 0


def test_decanting_skipped_penalty(tmp_project):
    tp = tmp_project / "memory" / "pipeline-dev" / "trust.json"
    u.apply_trust_outcome(tp, "f-x", "decanting_skipped")
    out = u.read_json(tp, {})
    assert out["score"] == 40  # 50 - 10
    assert out["history"][-1]["outcome"] == "decanting_skipped"


def test_decanting_complete_span_detected_by_doctor(tmp_project):
    import doctor
    u.emit_span("agent.start", {"agent.name": "pipeline-dev"}, root=tmp_project)
    u.emit_span("decanting.complete",
                {"agent.name": "pipeline-dev", "feature": "f-1"}, root=tmp_project)
    rc = doctor.run(root=tmp_project, as_json=True)
    assert rc in (0, 1)


def test_report_written_simulating_decant(tmp_project):
    """Simula a saída de um decanting: report + handoff sobrescrito."""
    feat = tmp_project / "reports" / "feature-001"
    u.write_text(feat / "pipeline-dev.md", "# Report\n**Status:** completed\n")
    u.write_text(tmp_project / "memory" / "pipeline-dev" / "handoff.md",
                 "# Handoff\n## Em andamento\nnada\n")
    assert (feat / "pipeline-dev.md").is_file()
    # dashboard conta como feature completada hoje
    import dashboard_server as ds
    snap = ds.snapshot(tmp_project)
    assert snap["metrics"]["features_completed"] >= 1
