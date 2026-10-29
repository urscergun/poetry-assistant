"""English grammar rules: doubled words, a/an, "could of", "he don't"..."""

from __future__ import annotations

import re
from typing import Iterator

from ...grammar_common import (
    GrammarChecker, capital_after_sentence, grammar_issue, phrase, punctuation_spacing,
    repeated_words, same_case,
)
from ...model import Issue
from ...text import words
from .phonetics import Pronouncer

# Doubled words that are usually deliberate.
ALLOWED_REPEATS = {"had", "that", "very", "far", "on", "round", "bye", "ha", "no", "ho"}

PHRASE_RULES = [
    phrase(r"\b(could|should|would|must|might)\s+of\b", "en_modal_have", lambda m: f"{m.group(1)} have"),
    phrase(r"\b(he|she|it)\s+don't\b", "en_doesnt", lambda m: f"{m.group(1)} doesn't"),
    phrase(r"\bI\s+is\b", "en_agree_am", lambda m: "I am"),
    phrase(r"\b(you|we|they)\s+is\b", "en_agree_are", lambda m: f"{m.group(1)} are"),
    phrase(r"\b(you|we|they)\s+was\b", "en_agree_were", lambda m: f"{m.group(1)} were"),
    # Only "are": "if it were" is a valid subjunctive.
    phrase(r"\b(he|she|it)\s+are\b", "en_agree_is", lambda m: f"{m.group(1)} is"),
    phrase(r"\balot\b", "en_a_lot", lambda m: "a lot"),
    phrase(r"\bits\s+(a|an|the|been|not|so|too|very)\b", "en_its_contraction", lambda m: f"it's {m.group(1)}"),
    phrase(r"\bit's\s+(own)\b", "en_its_possessive", lambda m: "its own"),
    phrase(r"\byour\s+(welcome|a|an|the|not|so|too|very|going)\b", "en_youre", lambda m: f"you're {m.group(1)}"),
    phrase(r"\b(more|less|better|worse|rather|other)\s+then\b", "en_than", lambda m: f"{m.group(1)} than"),
]


def english_grammar(pronouncer: Pronouncer) -> GrammarChecker:
    def a_an(i: int, line: str) -> Iterator[Issue]:
        toks = list(words(line))
        for art, nxt in zip(toks, toks[1:]):
            a = art.text.lower()
            if a not in ("a", "an") or line[art.end:nxt.start].strip():
                continue
            vowel = pronouncer.starts_with_vowel_sound(nxt.text)
            if vowel is None:
                continue
            if a == "a" and vowel:
                yield grammar_issue(i, art.start, art.end, "en_use_an", (same_case(art.text, "an"),), word=nxt.text)
            elif a == "an" and not vowel:
                yield grammar_issue(i, art.start, art.end, "en_use_a", (same_case(art.text, "a"),), word=nxt.text)

    def lowercase_i(i: int, line: str) -> Iterator[Issue]:
        for m in re.finditer(r"(?<![\w'’])i(?=$|[\s,.;:!?'’])", line):
            yield grammar_issue(i, m.start(), m.end(), "en_capital_i", ("I",))

    return GrammarChecker([
        repeated_words(ALLOWED_REPEATS),
        a_an,
        lowercase_i,
        punctuation_spacing,
        capital_after_sentence,
        *PHRASE_RULES,
    ])
