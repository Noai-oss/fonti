from email.message import Message
from io import BytesIO
from urllib.request import OpenerDirector
from urllib.response import addinfourl
from zipfile import ZIP_DEFLATED, ZipFile

import pytest


@pytest.fixture
def serve_download(monkeypatch):
    """Supply a fresh HTTP response for each request, including repeat installs."""

    def serve(body, *, headers=None, final_url=None, status=200):
        def open_response(opener, url, timeout):
            metadata = Message()
            for key, value in (headers or {}).items():
                metadata[key] = value
            return addinfourl(BytesIO(body), metadata, final_url or url, status)

        monkeypatch.setattr(OpenerDirector, "open", open_response)

    return serve


@pytest.fixture
def font_zip():
    def pack(files, compression=ZIP_DEFLATED):
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return buffer.getvalue()

    return pack
