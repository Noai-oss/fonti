from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import OpenerDirector, Request
from zipfile import ZIP_BZIP2, ZIP_STORED

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
        "__MACOSX/._Bold.otf": b"Finder metadata",
        "nested/._Regular.ttf": b"\x00\x05\x16\x07",
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
    response = BytesIO(b"Link moved")
    assert handler.redirect_request(req, response, 302, "", {}, url).full_url == url
    assert response.closed
    response = BytesIO()
    with pytest.raises(ValueError, match="HTTPS"):
        handler.redirect_request(
            req, response, 302, "", {}, "http://cdn.example/file.ttf"
        )
    assert response.closed


def test_partial_response_is_rejected(serve_download, capsys):
    data = font_bytes("Demo Regular")
    serve_download(data, status=206, headers={"Content-Length": str(len(data))})
    assert main(["info", "https://fonts.example/Demo.ttf"]) == 1
    assert "partial" in capsys.readouterr().err.lower()


def test_limit_zip_directory_before_reading_entries(
    monkeypatch, serve_download, font_zip, capsys
):
    monkeypatch.setattr(sources, "MAX_ZIP_DIRECTORY", 100)
    serve_download(font_zip({"First.ttf": b"one", "Second.ttf": b"two"}))
    assert main(["info", "https://fonts.example/fonts.zip"]) == 1
    assert "ZIP directory" in capsys.readouterr().err


def test_limit_archive_depth_before_creating_directories(
    monkeypatch, serve_download, font_zip, capsys
):
    monkeypatch.setattr(sources, "MAX_ZIP_DEPTH", 1)
    serve_download(font_zip({"family/regular/Demo.ttf": b"one"}))
    assert main(["info", "https://fonts.example/fonts.zip"]) == 1
    assert "nested" in capsys.readouterr().err


def test_zip_compression_methods(serve_download, font_zip, capsys):
    files = {"Demo.ttf": font_bytes("Demo Regular")}
    serve_download(font_zip(files, ZIP_STORED))
    assert main(["info", "https://fonts.example/fonts.zip"]) == 0
    serve_download(font_zip(files, ZIP_BZIP2))
    assert main(["info", "https://fonts.example/fonts.zip"]) == 1
    assert "compression" in capsys.readouterr().err


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
