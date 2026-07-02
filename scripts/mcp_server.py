"""
mcp_server.py — servidor MCP (stdio, JSON-RPC 2.0) que expõe o ESTADO DECANTADO do
mad para outras ferramentas (Cursor, IDEs, outros agentes). Stdlib puro, zero dep.

Expõe:
- resources: memory/<agente>/*.md, docs/DECISOES.md, docs/STATE.md, workflow_state.
- tools: mad_agent_state, mad_recent_decisions, mad_workflow_status.

Transporte: mensagens JSON-RPC delimitadas por newline no stdin/stdout (MCP stdio).
Nunca derruba: erro vira resposta JSON-RPC de erro.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

PROTOCOL = "2024-11-05"


def _root() -> Path | None:
    return u.find_project_root()


def _resources(root: Path) -> list[dict]:
    res = []
    mem = root / "memory"
    if mem.is_dir():
        for ag in sorted(p for p in mem.iterdir() if p.is_dir()):
            for f in sorted(ag.glob("*.md")):
                res.append({"uri": f"mad://memory/{ag.name}/{f.name}",
                            "name": f"memória: {ag.name}/{f.name}", "mimeType": "text/markdown"})
    for rel in ("docs/DECISOES.md", "docs/STATE.md", "docs/CONSTITUICAO.md"):
        if (root / rel).is_file():
            res.append({"uri": f"mad://{rel}", "name": rel, "mimeType": "text/markdown"})
    if (root / ".mad" / "workflow_state.json").is_file():
        res.append({"uri": "mad://workflow_state", "name": "estado do workflow",
                    "mimeType": "application/json"})
    return res


def _read_resource(root: Path, uri: str) -> str:
    if uri == "mad://workflow_state":
        return json.dumps(u.read_json(root / ".mad" / "workflow_state.json", {}),
                          ensure_ascii=False, indent=1)
    rel = uri.replace("mad://", "", 1)
    if rel.startswith("memory/"):
        p = root / rel
    else:
        p = root / rel
    p = p.resolve()
    if root.resolve() not in p.parents and p != root.resolve():
        raise ValueError("fora do projeto")  # não vaza fora da raiz
    if not p.is_file():
        raise ValueError("recurso inexistente")
    return u.read_text(p)


TOOLS = [
    {"name": "mad_agent_state",
     "description": "Estado/memória decantada de um agente (identity, handoff, lessons, trust).",
     "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}},
                     "required": ["agent"]}},
    {"name": "mad_recent_decisions",
     "description": "Últimas N decisões do projeto (docs/DECISOES.md).",
     "inputSchema": {"type": "object", "properties": {"n": {"type": "integer"}}}},
    {"name": "mad_workflow_status",
     "description": "Fase atual, feature(s) ativa(s) e próximo passo do workflow.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def _tool_call(root: Path, name: str, args: dict) -> str:
    if name == "mad_agent_state":
        ag = args.get("agent", "")
        d = root / "memory" / ag
        if not d.is_dir():
            return f"agente '{ag}' não encontrado."
        out = [f"# {ag}"]
        for f in sorted(d.glob("*")):
            if f.is_file():
                out.append(f"\n## {f.name}\n" + u.read_text(f)[:4000])
        return "\n".join(out)
    if name == "mad_recent_decisions":
        n = int(args.get("n", 5) or 5)
        dec = root / "docs" / "DECISOES.md"
        if not dec.is_file():
            return "sem DECISOES.md"
        blocks = u.read_text(dec).split("\n## ")
        return "## " + "\n## ".join(blocks[-n:]) if len(blocks) > 1 else u.read_text(dec)
    if name == "mad_workflow_status":
        wd = u.read_json(root / ".mad" / "workflow_state.json", {})
        af = wd.get("active_feature") or {}
        par = wd.get("active_features") or []
        return json.dumps({"phase": wd.get("current_phase"),
                           "active_feature": af.get("id"),
                           "parallel": [p.get("id") for p in par]}, ensure_ascii=False)
    return f"tool desconhecida: {name}"


def _handle(msg: dict) -> dict | None:
    mid = msg.get("id")
    method = msg.get("method")
    root = _root()

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({"protocolVersion": PROTOCOL,
                   "capabilities": {"resources": {}, "tools": {}},
                   "serverInfo": {"name": "mad-decanting-state", "version": "1.0.0"}})
    if method in ("notifications/initialized", "initialized"):
        return None  # notificação, sem resposta
    if root is None:
        return err(-32000, "projeto mad não encontrado (sem multiagents-decanting.toml)")
    if method == "resources/list":
        return ok({"resources": _resources(root)})
    if method == "resources/read":
        uri = (msg.get("params") or {}).get("uri", "")
        try:
            text = _read_resource(root, uri)
        except Exception as e:  # noqa: BLE001
            return err(-32001, str(e))
        return ok({"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        p = msg.get("params") or {}
        try:
            text = _tool_call(root, p.get("name", ""), p.get("arguments") or {})
        except Exception as e:  # noqa: BLE001
            return err(-32002, str(e))
        return ok({"content": [{"type": "text", "text": text}]})
    if mid is not None:
        return err(-32601, f"método não suportado: {method}")
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
