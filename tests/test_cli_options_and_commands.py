from pathlib import Path

import pytest

import fonti.cli as cli
from fonti.__main__ import main


def test_help_exposes_the_four_commands(capsys):
    assert main(["--help"]) == 0
    help_text = capsys.readouterr().out
    for command in ("install", "list", "remove", "info"):
        assert command in help_text


@pytest.mark.parametrize(
    "args", [["install"], ["remove"], ["info"], ["install", "--unknown"]]
)
def test_invalid_usage_fails_on_stderr(args, capsys):
    assert main(args) == 2
    assert capsys.readouterr().err


def test_multiple_install_paths_and_flags(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "install", lambda path, **kw: calls.append((path, kw)))
    assert main(["install", "a.ttf", "fonts", "--replace", "--system"]) == 0
    assert calls == [
        (Path(p), {"force": True, "is_global": True}) for p in ("a.ttf", "fonts")
    ]


def test_list_accepts_literal_keyword_and_scope(monkeypatch, capsys):
    import fonti.ls as listing

    entries = [("Display Name", "A.B.ttf", 1), ("AaB Regular", "Other.ttf", 1)]
    monkeypatch.setattr(
        listing, "iter_font_registry_values", lambda system: entries if system else []
    )
    assert main(["list", "a.b", "--system"]) == 0
    assert capsys.readouterr().out == "Display Name\tA.B.ttf\n"
    assert main(["list", "DISPLAY", "--system"]) == 0
    assert capsys.readouterr().out == "Display Name\tA.B.ttf\n"
    assert main(["list", "Display"]) == 0
    assert capsys.readouterr().out == ""


def test_info_delegates_the_path(monkeypatch):
    paths = []
    monkeypatch.setattr(cli, "show_info", paths.append)
    assert main(["info", "Demo.ttf"]) == 0
    assert paths == [Path("Demo.ttf")]
