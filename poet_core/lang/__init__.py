"""Language registry: everything the analyzer needs for one poem language.

To add a language, create ``lang/<code>/`` with phonetics, spelling and
grammar, register a factory in ``_FACTORIES``, add its strings to ``i18n``
and (optionally) a sample poem in ``samples``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from ..model import Issue
from ..spelling_common import BaseSpeller
from ..text import HYPHENATED_WORD_RE, WORD_RE


class Phonetics(Protocol):
    @property
    def available(self) -> bool: ...
    def warm_up(self) -> None: ...
    def syllable_range(self, word: str) -> tuple[int, int]: ...
    def rhyme_keys(self, word: str) -> frozenset[str]: ...


class Grammar(Protocol):
    def check(self, lines: list[str]) -> list[Issue]: ...


@dataclass
class Language:
    code: str
    phonetics: Phonetics
    speller: BaseSpeller
    grammar: Grammar
    word_re: re.Pattern[str] = field(default=WORD_RE)

    def warm_up(self) -> None:
        self.phonetics.warm_up()
        self.speller.warm_up()

    def missing_data(self) -> list[str]:
        """Message codes for degraded features; empty when fully equipped."""
        codes = [] if self.phonetics.available else ["missing_cmudict"]
        return codes + self.speller.missing_data()


def _english(user_dictionary: Path | None) -> Language:
    from .en.grammar import english_grammar
    from .en.phonetics import Pronouncer
    from .en.spelling import SpellChecker
    pron = Pronouncer()
    return Language("en", pron, SpellChecker(pron, user_dictionary), english_grammar(pron))


def _romanian(user_dictionary: Path | None) -> Language:
    from .ro.grammar import romanian_grammar
    from .ro.phonetics import RomanianPhonetics
    from .ro.spelling import RomanianSpeller
    return Language("ro", RomanianPhonetics(), RomanianSpeller(user_dictionary), romanian_grammar(), HYPHENATED_WORD_RE)


_FACTORIES: dict[str, Callable[[Path | None], Language]] = {"en": _english, "ro": _romanian}

LANGUAGES = tuple(_FACTORIES)  # poem languages, in menu order


def create_language(code: str, user_dictionary: Path | None = None) -> Language:
    try:
        return _FACTORIES[code](user_dictionary)
    except KeyError:
        raise ValueError(f"unsupported language {code!r}; available: {', '.join(LANGUAGES)}") from None
