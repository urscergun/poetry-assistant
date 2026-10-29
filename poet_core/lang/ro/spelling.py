"""Romanian spell checking with the rospell Hunspell dictionary (via ``spylls``).

The dictionary is bundled in ``data/`` (GPL/LGPL/MPL, see data/LICENSE).
``spylls`` is a pure-Python Hunspell implementation; without it spell
checking is reported as unavailable.
"""

from __future__ import annotations

import itertools
import threading
from pathlib import Path

from ...spelling_common import BaseSpeller
from .phonetics import normalize_ro

DICTIONARY = Path(__file__).parent / "data" / "ro_RO"


class RomanianSpeller(BaseSpeller):
    def __init__(self, user_dictionary: Path | None = None, dictionary: Path = DICTIONARY):
        super().__init__(user_dictionary)
        self._path = dictionary
        self._dict = None
        self._loaded = False
        self._load_lock = threading.Lock()
        self._missing: list[str] = []

    def _hunspell(self):
        if not self._loaded:
            with self._load_lock:
                if not self._loaded:
                    try:
                        from spylls.hunspell import Dictionary  # type: ignore
                    except ImportError:
                        self._missing = ["missing_spylls"]
                    else:
                        try:
                            self._dict = Dictionary.from_files(str(self._path))
                        except OSError:
                            self._missing = ["missing_ro_dictionary"]
                    self._loaded = True
        return self._dict

    @property
    def available(self) -> bool:
        return self._hunspell() is not None

    def warm_up(self) -> None:
        self._hunspell()

    def missing_data(self) -> list[str]:
        self._hunspell()
        return list(self._missing)

    def normalize(self, word: str) -> str:
        # Lowercasing loses nothing here: Hunspell accepts lowercase forms of
        # capitalised entries, and proper nouns mid-line are skipped anyway.
        return normalize_ro(word)

    def _known(self, w: str) -> bool:
        d = self._hunspell()
        return d is not None and d.lookup(w)

    def _compute_suggestions(self, w: str, limit: int) -> list[str]:
        d = self._hunspell()
        if d is None:
            return []
        return list(itertools.islice(d.suggest(w), limit))
