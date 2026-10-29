"""English spell checking.

Backed by ``pyspellchecker`` when installed (word frequencies give good
suggestions); words from the CMU dictionary and a user dictionary are also
accepted. Without pyspellchecker, the CMU word list is used with a plain
edit-distance suggester.
"""

from __future__ import annotations

from pathlib import Path

from ...spelling_common import BaseSpeller
from .phonetics import Pronouncer

# Archaic / poetic forms that general dictionaries tend to miss.
POETIC_WORDS = {
    "thee", "thou", "thy", "thine", "ye", "hath", "doth", "art", "wilt", "shalt",
    "ere", "o'er", "e'er", "ne'er", "e'en", "oft", "nigh", "whence", "thence",
    "hither", "thither", "yon", "yonder", "anon", "'tis", "'twas", "tis", "twas",
    "methinks", "alas", "betwixt", "amongst", "whilst", "lo", "mayhap", "perchance",
    "wherefore", "hast", "dost", "canst", "didst", "wouldst", "couldst", "shouldst",
}


class SpellChecker(BaseSpeller):
    def __init__(self, pronouncer: Pronouncer | None = None, user_dictionary: Path | None = None):
        super().__init__(user_dictionary)
        self._pron = pronouncer or Pronouncer()
        self._backend = None
        try:
            from spellchecker import SpellChecker as _Backend  # type: ignore
            self._backend = _Backend(distance=2)
        except Exception:
            self._backend = None

    @property
    def available(self) -> bool:
        """False when no word list is installed; checking would flag every word."""
        return self._backend is not None or self._pron.available

    def warm_up(self) -> None:
        self._pron.warm_up()

    def missing_data(self) -> list[str]:
        return [] if self.available else ["missing_en_wordlist"]

    def proper_noun_exception(self, word: str) -> bool:
        return word == "I" or word.startswith(("I'", "I’"))

    def _known(self, w: str) -> bool:
        if w in POETIC_WORDS:
            return True
        if self._backend is not None and w in self._backend:
            return True
        if self._pron.known(w):
            return True
        # Possessives and elided past tenses: "night's", "lov'd".
        for suffix in ("'s", "'d", "'ll", "'re", "'ve"):
            if w.endswith(suffix) and self.is_correct(w[: -len(suffix)]):
                return True
        return False

    def _compute_suggestions(self, w: str, limit: int) -> list[str]:
        if self._backend is not None:
            cands = self._backend.candidates(w) or set()
            return sorted(cands, key=lambda c: -self._backend.word_usage_frequency(c))[:limit]
        return sorted(_edits1(w) & set(self._pron.words()))[:limit]


def _edits1(word: str) -> set[str]:
    letters = "abcdefghijklmnopqrstuvwxyz'"
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = {a + b[1:] for a, b in splits if b}
    transposes = {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
    replaces = {a + c + b[1:] for a, b in splits if b for c in letters}
    inserts = {a + c + b for a, b in splits for c in letters}
    return deletes | transposes | replaces | inserts
