"""Plain data returned by the analyzer. Frontends consume only these types.

All positions are 0-based: ``line`` is the line index in the input text and
``start``/``end`` are character offsets within that line (end exclusive).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IssueKind(str, Enum):
    SPELLING = "spelling"
    GRAMMAR = "grammar"


@dataclass(frozen=True)
class Issue:
    kind: IssueKind
    line: int
    start: int
    end: int
    code: str                                   # message id in ``i18n``, e.g. "repeated_word"
    args: tuple[tuple[str, str], ...] = ()      # message parameters, e.g. (("word", "the"),)
    suggestions: tuple[str, ...] = ()
    message: str = ""                           # filled by Analyzer in the UI language


@dataclass
class LineInfo:
    index: int
    text: str
    syllables: int = 0                 # minimum count
    syllables_max: int = 0             # differs from ``syllables`` when words have variant pronunciations
    stanza: int | None = None          # None for blank lines
    end_word: str | None = None
    end_word_span: tuple[int, int] | None = None  # (start, end) of end_word within the line
    rhyme_label: str | None = None     # "A", "B", ... within the stanza
    rhyme_group: int | None = None     # global id, stable across stanzas; useful for colouring
    rhymes_with: list[int] = field(default_factory=list)  # other line indices in the same stanza

    @property
    def is_blank(self) -> bool:
        return self.stanza is None

    @property
    def syllables_text(self) -> str:
        if self.syllables == self.syllables_max:
            return str(self.syllables)
        return f"{self.syllables}-{self.syllables_max}"


@dataclass(frozen=True)
class RhymePair:
    first: int
    second: int
    first_word: str
    second_word: str


@dataclass
class Stanza:
    index: int
    lines: list[int]
    scheme: str            # e.g. "ABAB"
    pairs: list[RhymePair]


@dataclass
class Report:
    lines: list[LineInfo]
    stanzas: list[Stanza]
    issues: list[Issue]
    # True when some spelling suggestions were skipped to keep this pass fast;
    # analysing the same text again fills them in from cache.
    incomplete: bool = False

    @property
    def total_syllables(self) -> int:
        return sum(l.syllables for l in self.lines)
