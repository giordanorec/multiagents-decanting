"""Testes da lógica do dashboard — snapshot e inferência de status (CA-061/063)."""
from datetime import datetime, timezone

import _utils as u
import dashboard_server as ds


def test_snapshot_shape(tmp_project):
    snap = ds.snapshot(tmp_project)
    assert snap["type"] == "snapshot"
    assert snap["project"] == tmp_project.name
    names = {a["agente"] for a in snap["agents"]}
    assert {"arquiteto", "pipeline-dev", "qa-tester", "dba"} <= names
    for a in snap["agents"]:
        assert set(a) >= {"agente", "status", "bubble", "trust", "note"}
    assert "tokens_today" in snap["metrics"]


def test_status_sleeping_without_spans(tmp_project):
    snap = ds.snapshot(tmp_project)
    # sem spans, todos sleeping
    assert all(a["status"] == "sleeping" for a in snap["agents"])


def test_status_working_after_recent_span(tmp_project):
    u.emit_span("tool.use", {"agent.name": "pipeline-dev", "tool.name": "Edit"},
                root=tmp_project)
    snap = ds.snapshot(tmp_project)
    pd = next(a for a in snap["agents"] if a["agente"] == "pipeline-dev")
    assert pd["status"] == "working"
    assert "Edit" in pd["bubble"]


def test_metrics_accumulate_tokens(tmp_project):
    u.emit_span("model.call", {
        "agent.name": "pipeline-dev",
        "gen_ai.usage.input_tokens": 1000,
        "gen_ai.usage.output_tokens": 500,
        "gen_ai.cost.estimate": 0.01,
    }, root=tmp_project)
    snap = ds.snapshot(tmp_project)
    assert snap["metrics"]["tokens_today"] >= 1500


def test_infer_decanting_status(tmp_project):
    u.emit_span("decanting.start", {"agent.name": "qa-tester"}, root=tmp_project)
    snap = ds.snapshot(tmp_project)
    qa = next(a for a in snap["agents"] if a["agente"] == "qa-tester")
    assert qa["status"] == "decanting"


def test_pick_port_returns_int():
    port = ds._pick_port(None, "127.0.0.1")
    assert port is None or isinstance(port, int)
