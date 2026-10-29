"""Romanian grammar rules: common, unambiguous slips only."""

from __future__ import annotations

from ...grammar_common import (
    GrammarChecker, capital_after_sentence, phrase, punctuation_spacing, repeated_words,
)
from ...text import HYPHENATED_WORD_RE

# Doubled words that are idiomatic: "încet încet", "abia abia", "tot tot".
ALLOWED_REPEATS = {"încet", "ușor", "abia", "tot", "mereu", "când", "pas", "hai", "da", "nu", "ba", "of", "vai"}

_FUTURE_COND = r"(aș|ar|vei|va|vom|veți|vor|voi)"

PHRASE_RULES = [
    # "ar fii" -> "ar fi": the infinitive after auxiliaries has one i ("să fii" is correct).
    phrase(rf"\b{_FUTURE_COND}\s+fii\b", "ro_fi", lambda m: f"{m.group(1)} fi"),
    phrase(r"\ba\s+fii\b", "ro_fi", lambda m: "a fi"),
    # "mi-ar place" -> "mi-ar plăcea"
    phrase(rf"\b{_FUTURE_COND}\s+place\b", "ro_placea", lambda m: f"{m.group(1)} plăcea"),
    phrase(r"\bsă\s+aibe\b", "ro_subjunctive", lambda m: "să aibă"),
    phrase(r"\bsă\s+deie\b", "ro_subjunctive", lambda m: "să dea"),
    phrase(r"\bsă\s+steie\b", "ro_subjunctive", lambda m: "să stea"),
    # Pleonasms: superlatives of absolute adjectives.
    phrase(r"\bcel\s+mai\s+(optim|maxim|minim)\b", "ro_pleonasm", lambda m: m.group(1)),
]


def romanian_grammar() -> GrammarChecker:
    return GrammarChecker([
        repeated_words(ALLOWED_REPEATS, HYPHENATED_WORD_RE),
        punctuation_spacing,
        capital_after_sentence,
        *PHRASE_RULES,
    ])
