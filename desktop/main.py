"""Fonti's Windows desktop entry point. The CLI has no JadeView dependency."""

import ctypes as C
import json
import os
import sys
from pathlib import Path
from queue import SimpleQueue
from threading import Event, Lock
from urllib.parse import urlsplit

from fonti.info import FailedScan, FontInfo, scan_fonts
from fonti.install import install_files
from fonti.ls import find_installed_fonts


class Library:
    def __init__(self):
        self.fonts: tuple[FontInfo | FailedScan, ...] = ()
        self.scan_id = 0

    def scan(self, directory: Path):
        folder = directory.resolve(strict=True)
        if not folder.is_dir():
            raise ValueError(f"Please choose a folder: {folder}")
        fonts = tuple(scan_fonts(folder))
        rows = []
        for font in fonts:
            row = {"path": str(font.path.relative_to(folder))}
            if isinstance(font, FailedScan):
                row["error"] = str(font.error)
            else:
                row.update(kind=font.kind, name=font.name)
            rows.append(row)
        self.fonts = fonts
        self.scan_id += 1
        return {"folder": str(folder), "fonts": rows, "scanId": self.scan_id}

    def install(self, request):
        scan_id = request.get("scanId")
        if type(scan_id) is not int or scan_id != self.scan_id:
            raise ValueError("The folder has changed. Choose the folder again.")
        indexes = request.get("selected")
        replace = request.get("replace", False)
        if not isinstance(indexes, list) or not indexes or type(replace) is not bool:
            raise ValueError("Invalid font selection.")
        paths = []
        for i in indexes:
            if type(i) is not int or not 0 <= i < len(self.fonts):
                raise ValueError("Unknown font selection.")
            font = self.fonts[i]
            if isinstance(font, FailedScan):
                raise font.error
            paths.append(font.path)
        if len(set(indexes)) != len(indexes):
            raise ValueError("A font was selected twice.")
        results = [
            {"index": indexes[i], "status": outcome.status, "message": outcome.message}
            for i, outcome in enumerate(install_files(paths, replace=replace))
        ]
        return {"results": results}


# Layout from the Windows v3.0.0-beta.6 release header, JadeView.h.
class WebViewSettings(C.Structure):
    _fields_ = [
        ("struct_size", C.c_uint32),
        ("abi_version", C.c_uint32),
        ("autoplay", C.c_int32),
        ("background_throttling", C.c_int32),
        ("allow_right_click", C.c_int32),
        ("user_agent", C.c_char_p),
        ("preload_js", C.c_char_p),
        ("allow_fullscreen", C.c_int32),
        ("postmessage_allowed_origins", C.c_char_p),
        ("cors_allowed_origins", C.c_char_p),
        ("password_autofill", C.c_int32),
        ("form_autofill", C.c_int32),
        ("incognito", C.c_int32),
        ("disable_clipboard", C.c_int32),
        ("proxy_url", C.c_char_p),
        ("focused", C.c_int32),
        ("profile_name", C.c_char_p),
        ("devtools", C.c_int32),
        ("zoom_factor", C.c_double),
        ("background_color", C.c_char_p),
    ]


class FileDialog(C.Structure):
    _fields_ = [
        ("window_id", C.c_uint32),
        ("title", C.c_char_p),
        ("default_path", C.c_char_p),
        ("button_label", C.c_char_p),
        ("filters", C.c_char_p),
        ("properties", C.c_char_p),
    ]


def load_jade(path: Path):
    dll = C.WinDLL(str(path))
    text, ptr, integer, uid = C.c_char_p, C.c_void_p, C.c_int32, C.c_uint32
    callback = C.WINFUNCTYPE(ptr, uid, text)
    signatures = {
        "JadeView_init": (integer, integer, text, text, text, text, integer),
        "get_webview_version": (integer, C.POINTER(C.c_char), C.c_size_t),
        "jadeview_exit": (integer,),
        "jade_on": (uid, text, callback),
        "register_ipc_handler": (integer, text, callback),
        "set_protocol_service_path": (
            integer,
            text,
            C.POINTER(C.c_char),
            C.c_size_t,
            integer,
        ),
        "webview_settings_default": (integer, C.POINTER(WebViewSettings), C.c_size_t),
        "create_webview_window": (uid, text, uid, ptr, C.POINTER(WebViewSettings), ptr),
        "set_window_title": (integer, uid, text),
        "set_window_size": (integer, uid, integer, integer),
        "jade_dialog_show_open_dialog": (ptr, C.POINTER(FileDialog)),
        "jade_text_create": (ptr, text),
        "jade_text_free": (None, ptr),
        "jade_last_error_message": (ptr,),
    }
    for name, (result, *args) in signatures.items():
        function = getattr(dll, name)
        function.restype, function.argtypes = result, args
    return dll, callback


def read_text(jade, pointer):
    try:
        return C.string_at(pointer).decode("utf-8")
    finally:
        jade.jade_text_free(pointer)


def native_error(jade, operation):
    pointer = jade.jade_last_error_message()
    message = read_text(jade, pointer) if pointer else ""
    return RuntimeError(f"{operation}: {message}" if message else operation)


def choose_directory(jade, window):
    params = FileDialog(
        window_id=window, title=b"Choose a font folder", properties=b"openDirectory"
    )
    pointer = jade.jade_dialog_show_open_dialog(C.byref(params))
    if not pointer:
        raise native_error(jade, "Could not open the folder picker")
    result = json.loads(read_text(jade, pointer))
    if result.get("error"):
        raise RuntimeError(result["error"])
    return None if result["canceled"] else Path(result["filePaths"][0])


def installed_fonts(_):
    return {
        "installed": [
            {"name": font.name, "filename": font.path.name}
            for font in find_installed_fonts()
        ]
    }


def ipc_handler(jade, lock, action):
    def handle(_, data):
        try:
            payload = json.loads(data)
            if not isinstance(payload, dict):
                raise TypeError("Expected an object.")
            with lock:
                response = {"data": action(payload)}
        # A ctypes callback must always return a Jade-owned JSON reply.
        except Exception as exc:  # noqa: BLE001
            response = {"error": str(exc)}
        return jade.jade_text_create(json.dumps(response).encode())

    return handle


def run(runtime: Path, ui: Path):
    jade, callback = load_jade(runtime)
    version = C.create_string_buffer(256)
    if not jade.get_webview_version(version, len(version)):
        raise RuntimeError("Install Microsoft Edge WebView2 Runtime to open Fonti.")
    callbacks = []  # The DLL borrows these pointers until jadeview_exit completes.

    def register(register_fn, name, handler):
        wrapped = callback(handler)
        if not register_fn(name.encode(), wrapped):
            raise native_error(jade, f"Could not register {name}")
        callbacks.append(wrapped)

    ready = SimpleQueue()
    closed = Event()
    register(jade.jade_on, "app-ready", lambda _, data: ready.put(data))
    register(jade.jade_on, "window-all-closed", lambda *_: closed.set())
    profile = Path(os.environ["LOCALAPPDATA"]) / "Fonti" / "WebView2"
    if not jade.JadeView_init(
        0, None, str(profile).encode(), b"Fonti", b"org.noai.fonti", 0
    ):
        raise native_error(jade, "Could not start JadeView")

    try:
        notice = ready.get().decode()
        if not notice.startswith("{") or not json.loads(notice).get("ok"):
            raise RuntimeError(f"JadeView failed to start: {notice}")
        url = C.create_string_buffer(1024)
        if not jade.set_protocol_service_path(str(ui).encode(), url, len(url), 0):
            raise native_error(jade, "Could not open Fonti's interface")
        origin = b"https://jade." + urlsplit(url.value).netloc
        settings = WebViewSettings()
        if jade.webview_settings_default(C.byref(settings), C.sizeof(settings)) != 0:
            raise native_error(jade, "Could not configure JadeView")
        settings.cors_allowed_origins = settings.postmessage_allowed_origins = origin

        library = Library()
        operations = Lock()

        def pick_folder(_):
            folder = choose_directory(jade, window)
            return library.scan(folder) if folder is not None else None

        for name, action in (
            ("pick_folder", pick_folder),
            ("list", installed_fonts),
            ("install", library.install),
        ):
            register(
                jade.register_ipc_handler, name, ipc_handler(jade, operations, action)
            )
        entry = url.value.rstrip(b"/") + b"/index.html"
        allowed = {entry.decode(), (origin + b"/index.html").decode()}
        register(
            jade.jade_on,
            "webview-will-navigate",
            lambda _, data: int(json.loads(data)["url"] not in allowed),
        )
        register(jade.jade_on, "webview-new-window", lambda *_: 1)
        window = jade.create_webview_window(entry, 0, None, C.byref(settings), None)
        if not window:
            raise native_error(jade, "Could not open the Fonti window")
        jade.set_window_title(window, b"Fonti")
        jade.set_window_size(window, 1024, 740)
        closed.wait()
    finally:
        jade.jadeview_exit()


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    try:
        run(base / "JadeView_x64.dll", base / "ui")
    except (OSError, RuntimeError, ValueError) as exc:
        C.windll.user32.MessageBoxW(None, str(exc), "Fonti", 0x10)
        sys.exit(1)
