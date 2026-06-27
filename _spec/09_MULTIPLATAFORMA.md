# 09 — Multiplataforma e Portabilidade

## 9.1 Objetivo

Rodar com **igual qualidade** em:

- Windows 11 nativo (sem WSL), bash via Git ou PowerShell.
- macOS (Intel + Apple Silicon).
- Linux (qualquer distro com Python 3.9+).
- WSL2 (se o usuário tiver).
- GitHub Codespaces, Replit, Cursor remote.
- Docker container (roadmap V2.0).
- Roadmap: ARM (Raspberry Pi 4+).

## 9.2 Princípios de portabilidade

1. **Python 3.9+ como linguagem do CLI.** Sem deps externas além de `websockets` (pip install).
2. **Sem `jq`, sem `uuidgen`, sem `tmux`, sem `Tilix`, sem ferramentas Unix-only.** Tudo em Python stdlib + pathlib.
3. **Paths via `pathlib.Path`.** Nunca string concatenation com `/`. Resolve diferenças Windows vs Unix.
4. **HOME directory via `Path.home()`.** Nunca `~` hardcoded.
5. **Encoding UTF-8 explícito** em toda I/O. Default do Python 3.9+ Windows ainda é cp1252 — passar `encoding="utf-8"` em todo `open()`.
6. **Newlines:** `open(path, "w", newline="\n")` para arquivos versionados (consistência git).
7. **Comandos shell via `subprocess.run([...], ...)`** com lista de argumentos, nunca string. Evita injection e diferenças de shell.
8. **`shutil` para operações de arquivo cross-platform.**
9. **`webbrowser.open()`** para abrir URL no browser default (cross-platform).

## 9.3 Wrappers shell

Para conveniência (usuário não precisa lembrar `python scripts/decanting.py ...`):

**Windows (PowerShell):** `bin/decanting.ps1`
```powershell
#!/usr/bin/env pwsh
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Project = Split-Path -Parent $ScriptDir
python "$Project\scripts\decanting.py" @args
```

**Windows (cmd):** `bin/decanting.bat`
```bat
@echo off
python "%~dp0\..\scripts\decanting.py" %*
```

**Bash (Linux/macOS/Git Bash):** `bin/decanting`
```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/../scripts/decanting.py" "$@"
```

Usuário pode adicionar `bin/` ao PATH para chamar só `decanting doctor` etc.

## 9.4 Detecção de plataforma

`scripts/_utils.py`:

```python
import sys
import platform
from pathlib import Path

def get_platform():
    """Returns 'windows', 'macos', 'linux', or 'unknown'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    return "unknown"

def is_wsl():
    """Detect if running under WSL."""
    if get_platform() != "linux":
        return False
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False

def get_open_command():
    """Cross-platform 'open file/url' command."""
    p = get_platform()
    if p == "windows": return ["cmd", "/c", "start", ""]
    if p == "macos":   return ["open"]
    if p == "linux":   return ["xdg-open"]
    return None
```

## 9.5 Dependências externas (mínimas)

Apenas:

| Dep | Tamanho | Função | Alternativa stdlib |
|---|---|---|---|
| `websockets` | ~1MB | WebSocket server pro dashboard | n/a (asyncio sozinho não cobre WS) |
| (opcional) `textual` | ~10MB | TUI fallback | n/a — só ativa se usuário quer TUI |
| (opcional) `tomli` | ~50KB | Ler `multiagents-decanting.toml` em Python < 3.11 | stdlib `tomllib` em 3.11+ |

Instalação:

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
websockets>=12.0
tomli>=2.0; python_version<"3.11"
```

`requirements-tui.txt` (opcional):
```
textual>=0.50
```

## 9.6 Compatibilidade com Claude Code

Plugin **detecta versão** do Claude Code instalado:

```python
def get_claude_code_version():
    """Returns tuple (major, minor, patch) or None."""
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
        # parse semver de saída tipo "claude 2.1.77"
        ...
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

def supports_sendmessage():
    """Claude Code 2.1.77+ com env var habilitada."""
    v = get_claude_code_version()
    if v is None or v < (2, 1, 77):
        return False
    return os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"
```

Comportamento adaptativo:
- **Claude Code < 2.1.77:** sem `SendMessage`. Multi-turn Arquiteto ↔ Especialista usa nova call do `Agent` tool a cada interação; especialista relê `handoff.md` no boot. Funciona, ligeiramente menos fluido.
- **Claude Code ≥ 2.1.77 sem env var:** mesmo comportamento. Doctor sugere `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
- **Claude Code ≥ 2.1.77 com env var:** usa `SendMessage` para retomar sessão interna do subagent em multi-turn. Fluência máxima dentro da feature.

Em todos os casos: plugin NÃO usa `claude -p` em momento algum. Sessão viva durante a feature é sempre via primitivas nativas do Claude Code (`Agent` tool + opcional `SendMessage`).

## 9.7 Docker (roadmap V2.0)

Imagem oficial `giordanorec/multiagents-decanting:latest`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ scripts/
COPY templates/ templates/
COPY agents/ agents/
COPY dashboard/ dashboard/
ENTRYPOINT ["python", "scripts/decanting.py"]
```

Uso:
```bash
docker run -v $(pwd):/project -p 8765:8765 \
  giordanorec/multiagents-decanting:latest init
```

Útil em:
- CI pipelines.
- Ambientes locked-down (banco, governo).
- "Leve seu plugin pra qualquer Codespace".

Cross-arch via Docker Buildx (amd64 + arm64).

## 9.8 Codespaces / Cloud IDEs

Plugin deve funcionar out-of-the-box em:

- **GitHub Codespaces:** Python pré-instalado; `pip install -r requirements.txt`; rodar normal. Dashboard em porta 8765 com forwarding automático do Codespaces (URL pública temporária).
- **Replit:** similar; Python disponível.
- **Cursor / VS Code Remote:** se o agente roda na máquina remota, dashboard fica na porta remota e o IDE forward.

`devcontainer.json` template incluído para Codespaces:

```json
{
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/anthropics/devcontainer-features/claude-code:1": {}
  },
  "postCreateCommand": "pip install -r requirements.txt && decanting doctor",
  "forwardPorts": [8765],
  "portsAttributes": {
    "8765": {"label": "Multiagente Dashboard", "onAutoForward": "openBrowser"}
  }
}
```

## 9.9 Encoding e i18n

Padrão UTF-8 em tudo. Para mensagens do usuário:

`locale/pt-BR.json`:
```json
{
  "init.welcome": "Bem-vindo ao multiagents-decanting. Vou conduzir um Discovery breve. Uma pergunta por vez.",
  "init.q1_objetivo": "Qual é o objetivo principal do projeto, em uma frase?",
  ...
  "doctor.healthy": "Tudo verde. Projeto saudável.",
  "doctor.warning": "Atenção: {issue}",
  ...
}
```

`locale/en.json`: equivalente em inglês.

Plugin carrega locale baseado em `multiagents-decanting.toml[i18n].default_locale` ou env var `LANG`.

## 9.10 Testes cross-platform

CI no GitHub Actions roda matrix:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python: ["3.9", "3.10", "3.11", "3.12"]
```

Testes principais:
- `test_init.py`: estrutura criada corretamente.
- `test_paths.py`: paths funcionam em Win/Mac/Linux.
- `test_agent_call.py`: simula call do Agent tool (mock) e verifica boot + decanting.
- `test_decanting.py`: protocolo executado.
- `test_dashboard.py`: WebSocket conecta, messages chegam.
- `test_doctor.py`: detecta projeto saudável vs problemas.

## 9.11 Quirks conhecidos por plataforma

### Windows
- Caminhos com espaço ou OneDrive: testar `C:\Users\X\OneDrive - Org\Projetos\`. Plugin lida via `pathlib`, mas testar.
- `cmd.exe` codepage pode mostrar caracteres errados — emit ASCII-safe em fallback.
- Locks de arquivo (`File in use`): tentar `os.replace()` em vez de `os.rename()` quando sobrescrevendo.

### macOS
- Gatekeeper pode pedir permissão na primeira execução de script Python externo. Documentar.

### Linux
- `xdg-open` pode não estar disponível em servidores headless. Fallback: imprimir URL.

### WSL
- `webbrowser.open()` no WSL pode tentar abrir browser do Linux que não existe. Detectar WSL e usar `wslview` ou imprimir URL.

### Codespaces
- Porta 8765 já em uso? Tentar 8766-8775 sequencial.

## 9.12 Auto-update

`decanting upgrade`:

1. Verifica versão atual em `multiagents-decanting.toml`.
2. Busca última release no GitHub: `gh release view ...` ou HTTP `api.github.com/repos/.../releases/latest`.
3. Compara semver.
4. Se patch (X.Y.Z+1): aplica auto, sem confirmação.
5. Se minor (X.Y+1.0): mostra changelog, pede confirmação.
6. Se major (X+1.0.0): mostra changelog + nota de breaking change, pede confirmação dupla.
7. Atualiza apenas `scripts/`, `templates/`, `agents/`, `dashboard/`, `commands/`, `skills/`.
8. **Nunca** sobrescreve `memory/`, `docs/`, `specs/`, `reports/`, `CLAUDE.md`, `multiagents-decanting.toml`.
9. Roda `decanting doctor` ao fim.
