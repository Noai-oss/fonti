"""Build the Windows desktop executable from the repository checkout."""

import argparse
import hashlib
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

DESKTOP = Path(__file__).resolve().parent
ROOT = DESKTOP.parent
TAG = "v3.0.0-beta.6"
ASSET = f"JadeView_win_x64_{TAG}.26K02.zip"
RELEASE = f"https://github.com/JadeViewDocs/JadeView/releases/download/{TAG}/{ASSET}"
SHA256 = "2402d7523617fabb085e7186dc5ac36f42cf691c178531c9cb7e71d25b0679a8"
DLL = "JadeView_x64.dll"


def prepare_runtime(archive: Path, stage: Path) -> None:
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != SHA256:
            raise SystemExit(f"SHA-256 mismatch for {archive}. Expected {SHA256}.")
        with ZipFile(stream) as sdk:
            sdk.extract(DLL, stage)
            sdk.extract("README.txt", stage / "JadeView")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sdk-zip", type=Path, help="use a local copy of the JadeView release ZIP"
    )
    args = parser.parse_args()
    if sysconfig.get_platform() != "win-amd64":
        parser.error("the desktop release requires x64 Python on Windows")

    stage = ROOT / "build" / "desktop"
    stage.mkdir(parents=True, exist_ok=True)
    archive = args.sdk_zip
    if archive is None:
        archive = stage / ASSET
        with urlopen(RELEASE, timeout=60) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
    prepare_runtime(archive, stage)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--noupx",
            "--name=Fonti",
            f"--specpath={stage}",
            f"--workpath={stage / 'pyi'}",
            f"--distpath={ROOT / 'dist'}",
            f"--paths={ROOT / 'src'}",
            "--hidden-import=fontTools.ttLib.tables._n_a_m_e",
            "--copy-metadata=fonttools",  # Includes the FontTools license files.
            f"--add-binary={stage / DLL}:.",
            f"--add-data={DESKTOP / 'ui'}:ui",
            f"--add-data={stage / 'JadeView'}:notices/JadeView",
            f"--add-data={Path(sys.base_prefix) / 'LICENSE.txt'}:notices/Python",
            str(DESKTOP / "main.py"),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
