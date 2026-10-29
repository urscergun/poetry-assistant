"""Rhyme-scheme detection within a stanza."""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Protocol


class RhymeKeys(Protocol):
    def rhyme_keys(self, word: str) -> frozenset[str]: ...


@dataclass
class StanzaRhymes:
    labels: dict[int, str]          # line index -> letter
    groups: dict[int, int]          # line index -> group number (0-based, in order of first appearance)
    partners: dict[int, list[int]]  # line index -> other lines in the same group


def _label(n: int) -> str:
    letters = string.ascii_uppercase
    return letters[n] if n < 26 else letters[n // 26 - 1] + letters[n % 26]


def rhyme_stanza(end_words: dict[int, str | None], pron: RhymeKeys) -> StanzaRhymes:
    """Assign rhyme letters to lines (in order) based on their last word.

    A line joins the first earlier group containing a line it rhymes with;
    otherwise it starts a new group. Lines without a word get no letter.
    """
    group_members: list[list[int]] = []
    group_keys: list[set[str]] = []
    labels: dict[int, str] = {}
    groups: dict[int, int] = {}

    for line, word in end_words.items():
        if not word:
            continue
        keys = pron.rhyme_keys(word)
        for g, gkeys in enumerate(group_keys):
            if keys & gkeys:
                group_members[g].append(line)
                gkeys |= keys
                break
        else:
            g = len(group_members)
            group_members.append([line])
            group_keys.append(set(keys))
        groups[line] = g
        labels[line] = _label(g)

    partners = {
        line: [other for other in group_members[g] if other != line]
        for line, g in groups.items()
    }
    return StanzaRhymes(labels, groups, partners)
