"""Spell-checker base: user dictionary, session ignore list, suggestion cache."""

from __future__ import annotations

import threading
from pathlib import Path


class BaseSpeller:
    """Subclasses implement ``available``, ``_known`` and ``_compute_suggestions``."""

    def __init__(self, user_dictionary: Path | None = None):
        self._user_path = user_dictionary
        self._user: set[str] = set()
        self._ignored: set[str] = set()
        self._suggestions: dict[str, tuple[str, ...]] = {}
        self._lock = threading.Lock()
        if user_dictionary and user_dictionary.exists():
            self._user = {self.normalize(w) for w in user_dictionary.read_text(encoding="utf-8").split() if w}

    # -- per-language hooks ------------------------------------------------

    @property
    def available(self) -> bool:
        raise NotImplementedError

    def warm_up(self) -> None:
        pass

    def normalize(self, word: str) -> str:
        return word.replace("’", "'").lower()

    def _known(self, word: str) -> bool:
        """``word`` is already normalised."""
        raise NotImplementedError

    def _compute_suggestions(self, word: str, limit: int) -> list[str]:
        raise NotImplementedError

    def proper_noun_exception(self, word: str) -> bool:
        """Capitalised words that are not names even mid-line (English "I")."""
        return False

    # -- public API --------------------------------------------------------

    def add_to_dictionary(self, word: str) -> None:
        self._user.add(self.normalize(word))
        if self._user_path:
            self._user_path.parent.mkdir(parents=True, exist_ok=True)
            self._user_path.write_text("\n".join(sorted(self._user)) + "\n", encoding="utf-8")

    def ignore(self, word: str) -> None:
        """Ignore for this session only."""
        self._ignored.add(self.normalize(word))

    def is_correct(self, word: str) -> bool:
        w = self.normalize(word)
        if len(w) <= 1 or w in self._user or w in self._ignored:
            return True
        return self._known(w)

    def cached_suggestions(self, word: str) -> tuple[str, ...] | None:
        return self._suggestions.get(word)

    def suggest(self, word: str, limit: int = 5) -> tuple[str, ...]:
        cached = self._suggestions.get(word)
        if cached is not None:
            return cached
        w = self.normalize(word)
        # A lowercase word is rarely a misspelt proper noun, so skip "Topești" for "topeștte".
        lowercase = word[:1].islower()
        out = [c for c in self._compute_suggestions(w, limit + 3)
               if c.lower() != w and not (lowercase and c[:1].isupper())][:limit]
        result = tuple(match_case(word, c) for c in out)
        with self._lock:
            self._suggestions[word] = result
        return result

    def should_check(self, word: str, at_line_start: bool) -> bool:
        """Skip acronyms and capitalised words mid-line (likely proper nouns)."""
        if word.isupper() and len(word) > 1:
            return False
        if word[:1].isupper() and not at_line_start and not self.proper_noun_exception(word):
            return False
        return True


def match_case(original: str, suggestion: str) -> str:
    if original.isupper() and len(original) > 1:
        return suggestion.upper()
    if original[:1].isupper():
        return suggestion[:1].upper() + suggestion[1:]
    return suggestion
