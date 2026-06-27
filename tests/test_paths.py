"""Testes de portabilidade de paths — CA-083, CA-084."""
import _utils as u


def test_no_crlf_in_versioned_text(tmp_path):
    p = tmp_path / "doc.md"
    u.write_text(p, "a\nb\nc\n")
    assert b"\r\n" not in p.read_bytes()


def test_paths_are_pathlib(tmp_project):
    # find_project_root devolve Path, não str
    from pathlib import Path
    root = u.find_project_root(tmp_project)
    assert isinstance(root, Path)


def test_utf8_roundtrip(tmp_path):
    p = tmp_path / "acentos.md"
    txt = "ações, decantação, café, ñ, 中文"
    u.write_text(p, txt)
    assert u.read_text(p) == txt


def test_open_command_per_platform():
    cmd = u.get_open_command()
    assert cmd is None or isinstance(cmd, list)
