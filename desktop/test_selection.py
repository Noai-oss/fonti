import pytest
from main import Library

from fonti.info import FailedScan, FontInfo
from fonti.install import InstallResult


def test_selection_is_bound_to_displayed_scan(tmp_path, monkeypatch):
    good = FontInfo(tmp_path / "ok.ttf", "Example (TrueType)", "TrueType")
    bad = FailedScan(tmp_path / "broken.ttf", ValueError("Invalid font"))
    monkeypatch.setattr("main.scan_fonts", lambda _: iter((bad, good)))
    calls = []

    def install(files, *, replace):
        calls.append((list(files), replace))
        yield InstallResult(good.path, good.name, "skipped")

    monkeypatch.setattr("main.install_files", install)
    library = Library()
    first = library.scan(tmp_path)
    assert first["fonts"][0] == {"path": "broken.ttf", "error": "Invalid font"}
    assert first["fonts"][1]["name"] == good.name
    second = library.scan(tmp_path)
    with pytest.raises(ValueError, match="folder has changed"):
        library.install({"scanId": first["scanId"], "selected": [1]})

    for indexes in ([1, 0], [1, 2], [-1], [True], [1, 1], ["elsewhere.ttf"]):
        with pytest.raises(ValueError):
            library.install({"scanId": second["scanId"], "selected": indexes})
    with pytest.raises(ValueError):
        library.install(
            {"scanId": second["scanId"], "selected": [1], "replace": "false"}
        )
    assert calls == []

    response = library.install({"scanId": second["scanId"], "selected": [1]})
    assert calls == [([good.path], False)]
    assert response == {"results": [{"index": 1, "status": "skipped", "message": ""}]}
