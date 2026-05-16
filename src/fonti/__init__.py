import sys

if sys.platform != "win32":
    raise RuntimeError("fonti is only supported on Windows.")

__version__ = "0.1.0"
