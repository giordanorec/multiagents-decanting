"""OTel: store SQLite (ingest/trace/percentiles) + envelope OTLP padrão."""
import _utils as u
import otel_store as ost


def test_sqlite_ingest_and_trace(tmp_project):
    for i in range(3):
        u.emit_span("tool.use", {"agent.name": "pipeline-dev", "tool.name": "Edit",
                                 "tool.outcome": "ok"}, root=tmp_project)
    u.emit_span("tool.use", {"agent.name": "qa-tester", "tool.name": "Bash",
                             "tool.outcome": "error"}, root=tmp_project)
    n = ost.ingest(tmp_project)
    assert n >= 4
    assert (tmp_project / "logs" / "otel.db").is_file()  # SQLite local, sem install
    pcts = {r["tool"]: r for r in ost.percentiles(tmp_project)}
    assert pcts["Edit"]["n"] == 3 and pcts["Bash"]["errors"] == 1
    tr = ost.trace(tmp_project)  # trace mais recente
    assert len(tr["spans"]) >= 1


def test_otlp_envelope_standard(tmp_project):
    span = u.emit_span("tool.use", {"agent.name": "x", "tool.name": "Read",
                                    "gen_ai.usage.input_tokens": 10}, root=tmp_project)
    env = u._to_otlp(span)
    rs = env["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert len(rs["traceId"]) == 32 and len(rs["spanId"]) == 16  # hex OTLP
    keys = {a["key"] for a in rs["attributes"]}
    assert "gen_ai.agent.name" in keys and "gen_ai.tool.name" in keys  # semconv
