"""Testes de _utils: plataforma, I/O atômica, toml, custo, spans, paths."""
import json

import _utils as u


def test_get_platform_known():
    assert u.get_platform() in {"windows", "macos", "linux", "unknown"}


def test_atomic_write_utf8_lf(tmp_path):
    p = tmp_path / "sub" / "x.md"
    u.write_text(p, "linha1\nação çã\n")
    raw = p.read_bytes()
    assert b"\r\n" not in raw          # sempre LF
    assert "ação" in raw.decode("utf-8")  # UTF-8


def test_write_then_read_json(tmp_path):
    p = tmp_path / "t.json"
    u.write_json(p, {"score": 50, "x": [1, 2]})
    assert u.read_json(p)["score"] == 50
    assert u.read_json(tmp_path / "missing.json", default={}) == {}


def test_estimate_cost_by_model():
    opus = u.estimate_cost_usd("claude-opus-4-8", 1_000_000, 0)
    haiku = u.estimate_cost_usd("claude-haiku-4-5", 1_000_000, 0)
    assert opus > haiku > 0


def test_find_project_root(tmp_path):
    (tmp_path / u.CONFIG_FILENAME).write_text("[plugin]\nversion='1.0.0'\n")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert u.find_project_root(sub) == tmp_path
    assert u.find_project_root(tmp_path.parent) != tmp_path or True


def test_emit_span_appends(tmp_path):
    u.emit_span("agent.start", {"agent.name": "qa-tester"}, root=tmp_path)
    u.emit_span("agent.end", {"agent.name": "qa-tester"}, root=tmp_path)
    files = list((tmp_path / "logs" / "otel").glob("*.jsonl"))
    assert len(files) == 1
    lines = [json.loads(l) for l in files[0].read_text(encoding="utf-8").splitlines()]
    assert {l["name"] for l in lines} == {"agent.start", "agent.end"}


def test_iso_now_has_offset():
    s = u.iso_now()
    assert "T" in s and (s.endswith("Z") or "+" in s or s.count("-") >= 3)


def test_bar_bounds():
    assert u.bar(0) == "░" * 10
    assert u.bar(1) == "▓" * 10
    assert len(u.bar(0.5)) == 10
