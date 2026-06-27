# Installation

## Requirements

- **Claude Code** v2.1.172 or later (`claude --version` to check).
- **Python 3.10+** on PATH (for the MCP server). Test: `python --version`.
- **uv** (modern Python package manager, used to run the MCP server in isolation). Install:
  - Windows: `winget install astral-sh.uv` or `pip install uv`
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
- A modern browser for the dashboard.

## Quick install (local)

Clone the repository, then from inside Claude Code:

```
/plugin install file:///absolute/path/to/claude-brainstorm-multiagent
```

On Windows, use forward slashes in the path: `file:///C:/Users/you/.../plugin`.

## From a marketplace

If the marketplace is hosted on GitHub:

```
/plugin marketplace add <your-user>/claude-brainstorm-multiagent
/plugin install claude-brainstorm-multiagent
```

## Verify

Run:

```
/brainstorm instant
Topic: anything you want.
```

You should see:
1. The orchestrator running through Phase 0 → 1 → 2 → 3.
2. A directory created at `./brainstorm-runs/<timestamp>-<slug>/`.
3. A dashboard URL printed: `http://localhost:8765/dashboard/index.html`.
4. A final report at `./brainstorm-runs/<id>/FINAL_REPORT.md`.

If the dashboard doesn't auto-launch, open it manually.

## Troubleshooting

### `uvx` not found
The MCP server uses `uvx`. Install `uv` (see above). On Windows, after install, restart the terminal so PATH updates.

### MCP server fails to start
Check `claude mcp list` — `brainstorm-tools` should appear. If not:
```
claude mcp restart brainstorm-tools
```

If it still fails, the plugin will run in **degraded mode** without MAP-Elites (verbal approximation). You'll lose archive precision but the pipeline still works.

### Dashboard shows "Waiting for first ideas..." forever
Check `./brainstorm-runs/<id>/state/status.json` exists. If not, the skill failed to bootstrap — check Claude's error output.

### Port 8765 already in use
Edit `start.bat` / `start.sh` in the run dir to use a different port, or kill the existing process.

## Uninstall

```
/plugin uninstall claude-brainstorm-multiagent
```

Run directories under `./brainstorm-runs/` are NOT deleted — they're your data. Remove manually if desired.
