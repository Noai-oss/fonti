from __future__ import annotations

import pytest
import typer

import fonti.__main__ as main_module


def test_main_returns_zero_when_app_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str] | None, bool]] = []

    def fake_app(
        *,
        prog_name: str,
        args: list[str] | None,
        standalone_mode: bool,
    ) -> None:
        calls.append((prog_name, args, standalone_mode))

    monkeypatch.setattr(main_module, "app", fake_app)

    assert main_module.main(["list"]) == 0
    assert calls == [("fonti", ["list"], True)]


def test_main_maps_typer_exit_to_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_app(**kwargs: object) -> None:
        raise typer.Exit(7)

    monkeypatch.setattr(main_module, "app", fake_app)

    assert main_module.main(["--help"]) == 7


def test_main_reports_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main_module.main(["unknown-command"]) == 2
    assert "unknown-command" in capsys.readouterr().err


def test_main_maps_abort_or_keyboard_interrupt_to_130(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_app(**kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "app", fake_app)

    assert main_module.main(["install"]) == 130
    assert "Interrupted." in capsys.readouterr().err


def test_main_maps_system_exit_none_and_int(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exits = iter([SystemExit(None), SystemExit(9)])

    def fake_app(**kwargs: object) -> None:
        raise next(exits)

    monkeypatch.setattr(main_module, "app", fake_app)

    assert main_module.main(["ok"]) == 0
    assert main_module.main(["bad"]) == 9


def test_main_maps_system_exit_strings_to_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_app(**kwargs: object) -> None:
        raise SystemExit("boom")

    monkeypatch.setattr(main_module, "app", fake_app)

    assert main_module.main(["bad"]) == 1
    assert "boom" in capsys.readouterr().err
