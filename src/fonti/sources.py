from __future__ import annotations

import os
import stat
from collections.abc import Generator
from contextlib import contextmanager
from http.client import HTTPException
from lzma import LZMAError
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import IO, TypeGuard
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
from zipfile import BadZipFile, ZipFile
from zlib import error as ZlibError

from fonti.scan import SUPPORTED_FONT_EXTENSIONS

MAX_DOWNLOAD = 256 * 1024 * 1024
MAX_EXTRACTED = 512 * 1024 * 1024
MAX_ENTRIES = 4096
DOWNLOAD_EXTENSIONS = SUPPORTED_FONT_EXTENSIONS | {".zip"}


class HTTPSRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme.lower() != "https":
            raise ValueError("Font downloads require HTTPS on every redirect.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def is_https(source: str | Path) -> TypeGuard[str]:
    return isinstance(source, str) and source.lower().startswith("https://")


def _check_name(name: str) -> None:
    if (
        not name
        or name in {".", ".."}
        or Path(name).name != name
        or os.path.isreserved(name)
    ):
        raise ValueError(f"Invalid Windows filename: {name!r}")


def _url_filename(url: str) -> str:
    return unquote(urlsplit(url).path.rsplit("/", 1)[-1])


def _copy_limited(reader: IO[bytes], writer: IO[bytes], limit: int) -> int:
    written = 0
    while chunk := reader.read(1024 * 1024):
        written += len(chunk)
        if written > limit:
            raise ValueError("Font download or expanded ZIP exceeds the size limit.")
        writer.write(chunk)
    return written


def _download(url: str, directory: Path) -> Path:
    opener = build_opener(HTTPSRedirectHandler())
    try:
        with opener.open(url, timeout=30) as response:
            if response.headers.get_content_type() == "text/html":
                raise ValueError(
                    "Expected a direct font or ZIP download, received HTML."
                )
            names = (
                _url_filename(url),
                response.headers.get_filename(),
                _url_filename(response.geturl()),
            )
            for name in names:
                if name and Path(name).suffix.lower() in DOWNLOAD_EXTENSIONS:
                    _check_name(name)
                    target = directory / name
                    break
            else:
                raise ValueError(
                    "Expected a direct link to a supported font file or ZIP."
                )

            length = response.headers.get("Content-Length")
            expected = int(length) if length is not None else None
            if expected is not None and expected > MAX_DOWNLOAD:
                raise ValueError("Font download exceeds the size limit.")
            with target.open("xb") as output:
                written = _copy_limited(response, output, MAX_DOWNLOAD)
            if expected is not None and written != expected:
                raise ValueError("Incomplete font download.")
            return target
    except (HTTPException, OSError) as exc:
        raise ValueError(f"Could not download font: {exc}") from exc


def _extract_fonts(archive: Path, directory: Path) -> None:
    remaining = MAX_EXTRACTED
    found = False
    try:
        with ZipFile(archive) as package:
            if len(package.infolist()) > MAX_ENTRIES:
                raise ValueError("Font ZIP contains too many entries.")
            for member in package.infolist():
                path = PurePosixPath(member.filename)
                if (
                    member.is_dir()
                    or path.suffix.lower() not in SUPPORTED_FONT_EXTENSIONS
                ):
                    continue
                if stat.S_ISLNK(member.external_attr >> 16):
                    continue
                for part in path.parts:
                    _check_name(part)
                if member.file_size > remaining:
                    raise ValueError("Expanded font ZIP exceeds the size limit.")
                target = directory.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(member) as source, target.open("xb") as output:
                    remaining -= _copy_limited(source, output, remaining)
                found = True
    except (BadZipFile, EOFError, RuntimeError, ZlibError, LZMAError) as exc:
        raise ValueError(f"Could not read font ZIP '{archive.name}': {exc}") from exc
    if not found:
        raise ValueError(f"No supported fonts in '{archive.name}'.")


@contextmanager
def local_source(source: str | Path) -> Generator[Path]:
    """Keep a remote file or expanded font tree alive while its consumer runs."""
    if isinstance(source, str) and source.lower().startswith("http://"):
        raise ValueError("Use an HTTPS URL to download fonts.")
    if not is_https(source):
        yield Path(source)
        return

    with TemporaryDirectory(prefix="fonti-") as temp:
        root = Path(temp)
        downloaded = _download(source, root)
        if downloaded.suffix.lower() == ".zip":
            directory = root / "fonts"
            _extract_fonts(downloaded, directory)
            yield directory
        else:
            yield downloaded
