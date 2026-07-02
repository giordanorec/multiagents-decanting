"""MCP server (stdio JSON-RPC) — handshake, resources, tools."""
import json, subprocess, sys
from pathlib import Path
PLUGIN = Path(__file__).resolve().parent.parent


def _rpc(root, msgs):
    inp = "\n".join(json.dumps(m) for m in msgs) + "\n"
    r = subprocess.run([sys.executable, str(root / "scripts" / "mcp_server.py")],
                       input=inp, text=True, cwd=str(root), capture_output=True)
    return [json.loads(l) for l in r.stdout.splitlines() if l.strip()]


def test_mcp_handshake_and_tools(tmp_project):
    out = _rpc(tmp_project, [
        {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 1, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "mad_workflow_status", "arguments": {}}},
    ])
    by = {m["id"]: m for m in out}
    assert by[0]["result"]["serverInfo"]["name"] == "mad-decanting-state"
    assert len(by[1]["result"]["resources"]) > 0
    assert {t["name"] for t in by[2]["result"]["tools"]} >= {"mad_agent_state", "mad_workflow_status"}
    assert "DISCOVERY" in by[3]["result"]["content"][0]["text"]
