"""User preferences persisted as JSON in the per-OS config directory."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from poet_core import LANGUAGES
from poet_core.i18n import UI_LANGUAGES

from . import os_support


@dataclass
class Settings:
    poem_language: str
    ui_language: str

    @classmethod
    def load(cls) -> "Settings":
        default_ui = os_support.default_ui_language(UI_LANGUAGES)
        try:
            data = json.loads(os_support.settings_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        poem = data.get("poem_language")
        ui = data.get("ui_language")
        return cls(
            poem_language=poem if poem in LANGUAGES else (default_ui if default_ui in LANGUAGES else "en"),
            ui_language=ui if ui in UI_LANGUAGES else default_ui,
        )

    def save(self) -> None:
        path = os_support.settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except OSError:
            pass  # preferences are a convenience; never block editing over them
