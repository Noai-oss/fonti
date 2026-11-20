from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import OpenerDirector, Request

import pytest
from fontTools.ttLib import TTFont, newTable

from fonti import sources
from fonti.__main__ import main


def font_bytes(name):
    buffer = BytesIO()
    with TTFont() as font:
        font["name"] = newTable("name")
        font["name"].setName(name, 4, 3, 1, 0x409)
        font.save(buffer)
    return buffer.getvalue()


def test_remote_info_reads_nested_fonts_and_prints_relative_names(
    serve_download, font_zip, capsys
):
    files = {
        "nested/Regular.ttf": font_bytes("Demo Regular"),
        "Bold.otf": font_bytes("Demo Bold"),
        "LICENSE.txt": b"text",
    }
    serve_download(font_zip(files))
    assert main(["info", "https://fonts.example/family.zip"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "Bold.otf",
        "  Registry name: Demo Bold (TrueType)",
        "  Kind: TrueType",
        str(Path("nested/Regular.ttf")),
        "  Registry name: Demo Regular (TrueType)",
        "  Kind: TrueType",
    ]


@pytest.mark.parametrize(
    ("url", "headers", "final", "expected"),
    [
        (
            "https://fonts.example/A%20B.ttf?v=1",
            {},
            "https://cdn.example/id",
            "A B.ttf",
        ),
        (
            "https://fonts.example/asset",
            {"Content-Disposition": 'attachment; filename="Book.otc"'},
            None,
            "Book.otc",
        ),
        (
            "https://fonts.example/asset",
            {},
            "https://cdn.example/Family.TTC?t=1",
            "Family.TTC",
        ),
    ],
)
def test_remote_filename_is_stable_and_temporary(
    serve_download, url, headers, final, expected
):
    serve_download(b"download", headers=headers, final_url=final)
    with sources.local_source(url) as path:
        assert path.name == expected
        assert path.read_bytes() == b"download"
    assert not path.parent.exists()


def test_redirects_require_https():
    handler = sources.HTTPSRedirectHandler()
    req = Request("https://fonts.example/asset")
    url = "https://cdn.example/file.ttf"
    assert handler.redirect_request(req, None, 302, "", {}, url).full_url == url
    with pytest.raises(ValueError, match="HTTPS"):
        handler.redirect_request(req, None, 302, "", {}, "http://cdn.example/file.ttf")


@pytest.mark.parametrize(
    ("filename", "headers", "data", "error"),
    [
        ("font.ttf", {"Content-Type": "text/html"}, b"page", "received HTML"),
        ("asset", {}, b"file", "direct link"),
        ("font.ttf", {"Content-Length": "9"}, b"short", "Incomplete"),
        ("font.ttf", {"Content-Length": "99"}, b"", "size limit"),
        ("font.ttf", {}, b"x" * 40, "size limit"),
        ("bad.zip", {}, b"bad archive", "font ZIP"),
        ("broken.ttf", {}, b"bad font", "font metadata"),
        ("CON.ttf", {}, b"x", "Invalid Windows filename"),
    ],
)
def test_invalid_inputs_fail_cleanly_and_remove_temp_files(
    monkeypatch, tmp_path, serve_download, filename, headers, data, error, capsys
):
    monkeypatch.setattr(sources, "MAX_DOWNLOAD", 32)
    monkeypatch.setattr(
        sources,
        "TemporaryDirectory",
        lambda **kw: TemporaryDirectory(dir=tmp_path, **kw),
    )
    serve_download(data, headers=headers)
    assert main(["info", f"https://fonts.example/{filename}"]) == 1
    assert error in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("files", "error"),
    [
        ({"doc.txt": b"x"}, "No supported fonts"),
        ({"Demo.ttf": b"123", "Other.otf": b"12"}, "size limit"),
        ({"a.txt": b"", "b.txt": b"", "c.txt": b""}, "too many entries"),
        ({"AUX/Demo.ttf": b""}, "Invalid Windows filename"),
    ],
)
def test_archive_limits_and_invalid_members(
    monkeypatch, serve_download, font_zip, files, error, capsys
):
    monkeypatch.setattr(sources, "MAX_EXTRACTED", 4)
    monkeypatch.setattr(sources, "MAX_ENTRIES", 2)
    serve_download(font_zip(files))
    assert main(["info", "https://fonts.example/demo.zip"]) == 1
    assert error in capsys.readouterr().err


def test_network_failure_and_http_input(monkeypatch, capsys):
    def offline(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr(OpenerDirector, "open", offline)
    assert main(["info", "http://fonts.example/Demo.ttf"]) == 1
    assert "Use an HTTPS URL" in capsys.readouterr().err
    assert main(["info", "https://fonts.example/Demo.ttf"]) == 1
    assert "offline" in capsys.readouterr().err
