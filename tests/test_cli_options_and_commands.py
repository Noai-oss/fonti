from __future__ import annotations

from pathlib import Path

import click
import pytest

import fonti.cli as cli_module


def test_parse_opts_accepts_commas_repeats_dots_and_case() -> None:
    assert cli_module.parse_opts(["TTF,.otf", "ttf", " otc "]) == [
        "ttf",
        "otf",
        "otc",
    ]


def test_parse_opts_returns_none_when_not_provided() -> None:
    assert cli_module.parse_opts(None) is None
    assert cli_module.parse_opts([]) is None


def test_parse_opts_rejects_invalid_or_empty_values() -> None:
    with pytest.raises(click.BadParameter, match="unsupported font format: woff"):
        cli_module.parse_opts(["ttf,woff"])

    with pytest.raises(click.BadParameter, match="expected at least one font format"):
        cli_module.parse_opts([",", "  "])


def test_install_cmd_forwards_cli_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_install(
        source: Path,
        *,
        is_global: bool,
        force: bool,
        name_regex: str | None,
        formats: list[str] | None,
    ) -> None:
        calls.append(
            {
                "source": source,
                "is_global": is_global,
                "force": force,
                "name_regex": name_regex,
                "formats": formats,
            }
        )

    monkeypatch.setattr(cli_module, "install", fake_install)

    source = Path("fonts")
    cli_module.install_cmd(
        source,
        is_global=True,
        force=True,
        name_regex="mono",
        formats=["ttf", "otf"],
    )

    assert calls == [
        {
            "source": source,
            "is_global": True,
            "force": True,
            "name_regex": "mono",
            "formats": ["ttf", "otf"],
        }
    ]


def test_inspect_and_list_commands_forward_to_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspect_calls: list[Path] = []
    list_calls: list[tuple[bool, str | None]] = []

    monkeypatch.setattr(
        cli_module, "inspect", lambda source: inspect_calls.append(source)
    )
    monkeypatch.setattr(
        cli_module,
        "list_installed_fonts",
        lambda is_global=False, name_regex=None: list_calls.append(
            (is_global, name_regex)
        ),
    )

    source = Path("fonts")
    cli_module.inspect_cmd(source)
    cli_module.list_cmd(name_regex="mono", is_global=True)

    assert inspect_calls == [source]
    assert list_calls == [(True, "mono")]


def test_uninstall_cmd_rejects_unsafe_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit, match="requires at least one target"):
        cli_module.uninstall_cmd(targets=None)

    with pytest.raises(
        SystemExit, match="Filtered uninstall can remove multiple fonts"
    ):
        cli_module.uninstall_cmd(targets=None, name_regex="mono")

    monkeypatch.setattr(cli_module, "is_admin", lambda: False)

    with pytest.raises(SystemExit, match="requires admin privileges"):
        cli_module.uninstall_cmd(targets=["Demo"], is_global=True)


def test_uninstall_cmd_resolves_targets_and_filters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = cli_module.UninstallTarget(
        "Demo Regular (TrueType)", tmp_path / "Demo.ttf"
    )
    filter_calls: list[tuple[str | None, bool]] = []
    uninstall_calls: list[tuple[list[cli_module.UninstallTarget], bool]] = []

    monkeypatch.setattr(cli_module, "is_admin", lambda: True)
    monkeypatch.setattr(
        cli_module,
        "resolve_uninstall_target",
        lambda token, is_global=False: [target] if token == "Demo.ttf" else [],
    )
    monkeypatch.setattr(
        cli_module,
        "uninstall_by_filters",
        lambda name_regex=None, is_global=False: filter_calls.append(
            (name_regex, is_global)
        ),
    )
    monkeypatch.setattr(
        cli_module,
        "uninstall_font_targets",
        lambda targets, is_global: uninstall_calls.append((list(targets), is_global)),
    )

    cli_module.uninstall_cmd(
        targets=["Demo.ttf"],
        is_global=True,
        yes=True,
        name_regex="mono",
    )

    assert filter_calls == [("mono", True)]
    assert uninstall_calls == [([target], True)]


def test_uninstall_cmd_fails_when_target_does_not_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "resolve_uninstall_target", lambda *args, **kw: [])

    with pytest.raises(SystemExit, match="No installed font matched 'Missing.ttf'"):
        cli_module.uninstall_cmd(targets=["Missing.ttf"])
