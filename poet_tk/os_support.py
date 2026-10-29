"""OS-specific details: where to keep user data, which fonts to prefer."""

from __future__ import annotations

import locale
import os
import sys
from pathlib import Path

APP_NAME = "Poet"


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME.lower()


def user_dictionary_path(language: str) -> Path:
    return config_dir() / f"dictionary-{language}.txt"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def default_ui_language(supported: tuple[str, ...]) -> str:
    """The OS display language if supported, else English."""
    code = None
    if sys.platform == "win32":
        try:
            import ctypes
            code = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage())
        except (AttributeError, OSError):
            code = None
    if not code:
        code = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") \
            or locale.getlocale()[0] or ""
    code = code.lower()
    for lang in supported:
        if code.startswith(lang) or code.startswith({"ro": "romanian", "en": "english"}.get(lang, "?")):
            return lang
    return "en"


# First installed family wins.
EDITOR_FONTS = ("Georgia", "Cambria", "Palatino Linotype", "Palatino", "DejaVu Serif", "Liberation Serif", "Times")
UI_MONO_FONTS = ("Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Courier")

# macOS apps use the system menubar at the top of the screen. Elsewhere the menubar is drawn
# inside the window so it zooms with the UI (the native Windows menubar ignores Tk fonts).
NATIVE_MENUBAR = sys.platform == "darwin"

MOD = "Command" if sys.platform == "darwin" else "Control"
MOD_LABEL = "Cmd" if sys.platform == "darwin" else "Ctrl"
# Ctrl+wheel: Windows/macOS send <MouseWheel> with a signed delta; X11 sends buttons 4 (up) and 5 (down).
ZOOM_WHEEL_EVENTS = ("<Control-MouseWheel>",) if sys.platform in ("win32", "darwin") else ("<Control-Button-4>", "<Control-Button-5>")


def wheel_direction(event) -> int:
    """+1 for wheel up/away, -1 for down/towards the user."""
    if getattr(event, "num", None) in (4, 5):
        return 1 if event.num == 4 else -1
    return 1 if event.delta > 0 else -1


# Right-click is Button-2 on macOS Tk, Button-3 elsewhere.
CONTEXT_BUTTONS = ("<Button-2>", "<Control-Button-1>") if sys.platform == "darwin" else ("<Button-3>",)
