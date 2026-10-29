"""Tokenising helpers shared by the analysers."""

from __future__ import annotations

import re
from typing import Iterator, NamedTuple

# Words may contain inner apostrophes (don't, o'er); hyphens are separators, so
# "well-known" yields two words.
WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
# Languages that join clitics with hyphens (Romanian "s-a", "într-o", "florile-n")
# keep them as one token.
HYPHENATED_WORD_RE = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)


class Token(NamedTuple):
    text: str
    start: int
    end: int


def normalize(word: str) -> str:
    """Lowercase and unify curly apostrophes so dictionary lookups match."""
    return word.replace("’", "'").lower()


def words(line: str, word_re: re.Pattern[str] = WORD_RE) -> Iterator[Token]:
    for m in word_re.finditer(line):
        yield Token(m.group(), m.start(), m.end())


def last_word(line: str, word_re: re.Pattern[str] = WORD_RE) -> Token | None:
    tok = None
    for tok in words(line, word_re):
        pass
    return tok


def split_stanzas(lines: list[str]) -> list[list[int]]:
    """Group line indices into stanzas separated by blank lines."""
    stanzas: list[list[int]] = []
    current: list[int] = []
    for i, line in enumerate(lines):
        if line.strip():
            current.append(i)
        elif current:
            stanzas.append(current)
            current = []
    if current:
        stanzas.append(current)
    return stanzas
