"""Pronunciation lookups: syllable counts, rhyme keys, vowel-initial words.

Uses the CMU Pronouncing Dictionary (``cmudict`` package) when installed and
falls back to spelling heuristics for unknown words or when it is missing.
"""

from __future__ import annotations

import re
import threading
from functools import lru_cache

from ...text import normalize

Phones = tuple[str, ...]

_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def _is_vowel(phone: str) -> bool:
    return phone[-1].isdigit()


def heuristic_syllables(word: str) -> int:
    w = normalize(word).replace("'", "")
    n = len(_VOWEL_GROUP_RE.findall(w))
    # Silent final e ("stone", "fire"), but keep "-le" ("candle") and "-ee".
    if n > 1 and w.endswith("e") and not w.endswith(("le", "ee", "ye")):
        n -= 1
    # "-es"/"-ed" endings that do not add a syllable ("stones", "loved").
    elif n > 1 and re.search(r"[^aeiouy][^aeioulydt]e[sd]$", w) and not w.endswith(("ces", "ses", "zes", "ges", "shes", "ches")):
        n -= 1
    return max(1, n)


def heuristic_rhyme_key(word: str) -> str:
    """Spelling-based rhyme key: the last vowel group and everything after it."""
    w = normalize(word).replace("'", "")
    # Treat a silent final e as part of the preceding vowel ("love" -> "ove").
    core = w[:-1] if len(w) > 2 and w.endswith("e") and w[-2] not in "aeiouy" else w
    matches = list(_VOWEL_GROUP_RE.finditer(core))
    if not matches:
        return "~" + w
    return "~" + w[matches[-1].start():]


class Pronouncer:
    """Lazy CMU dictionary wrapper. Thread-safe to warm up in the background."""

    def __init__(self, cmu: dict[str, list[list[str]]] | None = None):
        self._cmu = cmu
        self._lock = threading.Lock()

    # -- dictionary ------------------------------------------------------

    @property
    def available(self) -> bool:
        return bool(self._dict())

    def _dict(self) -> dict[str, list[list[str]]]:
        if self._cmu is None:
            with self._lock:
                if self._cmu is None:
                    try:
                        import cmudict  # type: ignore
                        self._cmu = cmudict.dict()
                    except Exception:
                        self._cmu = {}
        return self._cmu

    def warm_up(self) -> None:
        self._dict()

    def known(self, word: str) -> bool:
        return normalize(word) in self._dict()

    def words(self):
        return self._dict().keys()

    @lru_cache(maxsize=20000)
    def phones(self, word: str) -> tuple[Phones, ...]:
        """All known pronunciations, deriving simple inflections if needed."""
        w = normalize(word)
        d = self._dict()
        if w in d:
            return tuple(tuple(p) for p in d[w])
        # Poetic elisions and simple suffixes: lov'd, o'er-less words, cats, walked.
        for suffix, extra in (("'s", "Z"), ("'d", "D"), ("s", "Z"), ("ed", "D"), ("d", "D")):
            if w.endswith(suffix) and w[: -len(suffix)] in d:
                return tuple(tuple(p) + (extra,) for p in d[w[: -len(suffix)]])
        if "'" in w and w.replace("'", "") in d:
            return tuple(tuple(p) for p in d[w.replace("'", "")])
        return ()

    # -- derived queries -------------------------------------------------

    def syllable_range(self, word: str) -> tuple[int, int]:
        """(min, max) over known pronunciations: "fire" -> (1, 2), "temperate" -> (2, 3)."""
        prons = self.phones(word)
        if prons:
            counts = [max(1, sum(_is_vowel(p) for p in pron)) for pron in prons]
            return min(counts), max(counts)
        n = heuristic_syllables(word)
        return n, n

    def syllables(self, word: str) -> int:
        return self.syllable_range(word)[0]

    def rhyme_keys(self, word: str) -> frozenset[str]:
        """Keys that are equal for words forming a perfect rhyme."""
        prons = self.phones(word)
        if not prons:
            return frozenset({heuristic_rhyme_key(word)})
        keys = set()
        for pron in prons:
            idx = _rhyme_start(pron)
            if idx is None:
                continue
            tail = [pron[idx][:-1]] + [p.rstrip("012") for p in pron[idx + 1:]]
            keys.add(" ".join(tail))
        return frozenset(keys) or frozenset({heuristic_rhyme_key(word)})

    def starts_with_vowel_sound(self, word: str) -> bool | None:
        """True/False if known, None when we cannot tell (used for a/an)."""
        prons = self.phones(word)
        if prons:
            return _is_vowel(prons[0][0])
        if not word:
            return None
        if word.isupper() and len(word) <= 5:
            return None  # acronyms: "an FBI agent" vs "a NATO plan"; don't guess
        return normalize(word)[0] in "aeiou"


def _rhyme_start(pron: Phones) -> int | None:
    """Index of the last primary-stressed vowel (or secondary, or any vowel)."""
    for stress in ("1", "2", "0"):
        for i in range(len(pron) - 1, -1, -1):
            if pron[i].endswith(stress):
                return i
    return None
