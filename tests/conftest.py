"""Fixtures comuns dos testes do plugin."""
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Cria um projeto inicializado num diretório temporário e cd nele."""
    import init

    monkeypatch.chdir(tmp_path)
    init.run(name="proj-teste", project_type="ml", target=tmp_path)
    return tmp_path
