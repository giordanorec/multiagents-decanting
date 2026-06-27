"""
_utils.py — fundação cross-platform do multiagents-decanting.

Tudo aqui é stdlib + pathlib. Sem deps externas. UTF-8 explícito em toda I/O,
newline="\\n" em arquivos versionados, os.replace() para sobrescrita atômica
(seguro contra locks do Windows). Nenhuma versão de Claude Code é hardcodada:
capacidades são detectadas em runtime e degradadas com graça.
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# TOML — tomllib (stdlib 3.11+) com fallback tomli (<3.11)
# ---------------------------------------------------------------------------
try:
    import tomllib as _toml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - só em <3.11
    try:
        import tomli as _toml  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        _toml = None


# ---------------------------------------------------------------------------
# Plataforma
# ---------------------------------------------------------------------------
def get_platform() -> str:
    """Retorna 'windows', 'macos', 'linux' ou 'unknown'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return "unknown"


def is_wsl() -> bool:
    """Detecta execução sob WSL."""
    if get_platform() != "linux":
        return False
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except (FileNotFoundError, OSError):
        return False


def python_cmd() -> str:
    """Nome do executável python disponível ('python3' preferido)."""
    # Em runtime já sabemos: estamos rodando, então sys.executable é a verdade.
    return sys.executable or "python3"


def get_open_command() -> list[str] | None:
    """Comando cross-platform para abrir arquivo/URL no app default."""
    p = get_platform()
    if p == "windows":
        return ["cmd", "/c", "start", ""]
    if p == "macos":
        return ["open"]
    if is_wsl():
        # webbrowser no WSL falha; wslview se existir.
        return ["wslview"]
    if p == "linux":
        return ["xdg-open"]
    return None


def open_url(url: str) -> bool:
    """Abre URL no browser default. Retorna True se conseguiu disparar."""
    import webbrowser

    if is_wsl():
        cmd = get_open_command()
        if cmd:
            try:
                subprocess.Popen(cmd + [url])
                return True
            except (FileNotFoundError, OSError):
                pass
        print(f"Abra manualmente no browser: {url}")
        return False
    try:
        return webbrowser.open(url)
    except Exception:
        print(f"Abra manualmente no browser: {url}")
        return False


# ---------------------------------------------------------------------------
# Detecção de Claude Code (feature-detect, nunca hardcode de versão)
# ---------------------------------------------------------------------------
def get_claude_code_version() -> tuple[int, int, int] | None:
    """Retorna (major, minor, patch) ou None se indisponível."""
    try:
        r = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", (r.stdout or "") + (r.stderr or ""))
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def supports_sendmessage() -> bool:
    """
    SendMessage (multi-turn com subagent) está ativo?

    Detecta por env var de habilitação, não por número de versão — a feature
    é experimental e o gate real é a env var. Se a Anthropic estabilizar isso,
    revisitar (ver docs/DECISOES.md #1).
    """
    return os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"


# ---------------------------------------------------------------------------
# Projeto: raiz, config, paths
# ---------------------------------------------------------------------------
CONFIG_FILENAME = "multiagents-decanting.toml"


def find_project_root(start: Path | None = None) -> Path | None:
    """Sobe a árvore procurando multiagents-decanting.toml."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / CONFIG_FILENAME).is_file():
            return candidate
    return None


def project_root_or_cwd() -> Path:
    return find_project_root() or Path.cwd()


def load_config(root: Path | None = None) -> dict:
    """Lê multiagents-decanting.toml como dict. {} se ausente/sem parser."""
    root = root or find_project_root()
    if root is None:
        return {}
    cfg_path = root / CONFIG_FILENAME
    if not cfg_path.is_file() or _toml is None:
        return {}
    with open(cfg_path, "rb") as f:
        return _toml.load(f)


# ---------------------------------------------------------------------------
# I/O UTF-8 / atômica / append
# ---------------------------------------------------------------------------
def read_text(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: Path | str, content: str) -> None:
    """Escrita atômica UTF-8 com newline LF. Seguro contra lock do Windows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp, path)  # atômico, sobrescreve mesmo em Windows


def append_text(path: Path | str, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(content)


def read_json(path: Path | str, default=None):
    p = Path(path)
    if not p.is_file():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path | str, obj) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------
def iso_now() -> str:
    """Timestamp ISO-8601 local com offset (ex: 2026-06-27T14:32:00-03:00)."""
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def today_str() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Preço por modelo (estimativa de custo; USD por 1M tokens)
# Valores aproximados públicos jun/2026. Tabela editável; é só estimativa.
# ---------------------------------------------------------------------------
PRICING_USD_PER_MTOK = {
    # modelo (substring) : (input, output)
    "opus":   (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku":  (0.80, 4.0),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    key = "sonnet"
    ml = (model or "").lower()
    for k in PRICING_USD_PER_MTOK:
        if k in ml:
            key = k
            break
    pin, pout = PRICING_USD_PER_MTOK[key]
    return (input_tokens / 1_000_000) * pin + (output_tokens / 1_000_000) * pout


# ---------------------------------------------------------------------------
# OTel — append de span GenAI em logs/otel/<date>.jsonl
# ---------------------------------------------------------------------------
def otel_dir(root: Path | None = None) -> Path:
    root = root or project_root_or_cwd()
    d = root / "logs" / "otel"
    d.mkdir(parents=True, exist_ok=True)
    return d


def emit_span(name: str, attributes: dict | None = None, root: Path | None = None) -> dict:
    """
    Grava um span OTel GenAI-compatível (subset) em logs/otel/<date>.jsonl.
    Se OTEL_EXPORTER_OTLP_ENDPOINT estiver setado, tenta exportar via OTLP HTTP
    (best-effort, silencioso em falha — telemetria nunca derruba o fluxo).
    """
    span = {
        "name": name,
        "timestamp": iso_now(),
        "attributes": attributes or {},
    }
    path = otel_dir(root) / f"{today_str()}.jsonl"
    append_text(path, json.dumps(span, ensure_ascii=False) + "\n")
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        _try_otlp_export(endpoint, span)
    return span


def _try_otlp_export(endpoint: str, span: dict) -> None:  # pragma: no cover
    """Export best-effort via urllib (stdlib). Falha em silêncio."""
    import urllib.request

    try:
        data = json.dumps(span).encode("utf-8")
        req = urllib.request.Request(
            endpoint.rstrip("/") + "/v1/traces",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Trust ladder — pesos canônicos e aplicação de outcome
# ---------------------------------------------------------------------------
TRUST_WEIGHTS = {
    "accepted": 5,
    "accepted_with_minor_note": 3,
    "rework_minor": 1,
    "rework_major": -3,
    "rejected": -7,
    "decanting_skipped": -10,
}
TRUST_DEFAULT = 50
TRUST_MIN, TRUST_MAX = 0, 100


def apply_trust_outcome(trust_path: Path | str, feature: str, outcome: str) -> dict:
    """
    Aplica um outcome ao trust.json de um agente (cap [0,100]), apenda ao
    histórico e persiste. Fonte única dos pesos — hook e Arquiteto chamam isto.
    """
    trust_path = Path(trust_path)
    tj = read_json(trust_path, {}) or {}
    tj.setdefault("agente", trust_path.parent.name)
    tj.setdefault("score", TRUST_DEFAULT)
    tj.setdefault("history", [])
    tj.setdefault("version", 1)
    weight = TRUST_WEIGHTS.get(outcome, 0)
    tj["score"] = max(TRUST_MIN, min(TRUST_MAX, int(tj["score"]) + weight))
    tj["history"].append({
        "feature": feature, "outcome": outcome,
        "weight": weight, "timestamp": iso_now(),
    })
    tj["last_updated"] = iso_now()
    write_json(trust_path, tj)
    return tj


# ---------------------------------------------------------------------------
# ANSI (saída de terminal legível; degrada se NO_COLOR ou não-tty)
# ---------------------------------------------------------------------------
def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


_C = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "blue": "\033[34m", "magenta": "\033[35m", "cyan": "\033[36m",
}


def c(text: str, *styles: str) -> str:
    if not _color_enabled():
        return text
    pre = "".join(_C.get(s, "") for s in styles)
    return f"{pre}{text}{_C['reset']}" if pre else text


def bar(pct: float, width: int = 10) -> str:
    """Barra de progresso textual: ▓▓▓▓░░░░░░."""
    pct = max(0.0, min(1.0, pct))
    filled = round(pct * width)
    return "▓" * filled + "░" * (width - filled)
