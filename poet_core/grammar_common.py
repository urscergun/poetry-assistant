"""Grammar-checker scaffolding and language-neutral rules.

Poetry bends grammar on purpose, so rules target unambiguous slips rather than
style. Each language builds a ``GrammarChecker`` from the common rules plus its
own. Any other engine can be plugged into ``Analyzer`` as long as it provides
``check(lines: list[str]) -> list[Issue]``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterator

from .model import Issue, IssueKind
from .text import WORD_RE, normalize, words

Rule = Callable[[int, str], Iterator[Issue]]


def grammar_issue(line: int, start: int, end: int, code: str, suggestions: tuple[str, ...] = (), **args: str) -> Issue:
    return Issue(IssueKind.GRAMMAR, line, start, end, code, tuple(args.items()), suggestions)


def same_case(original: str, replacement: str) -> str:
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


@dataclass(frozen=True)
class PhraseRule:
    """A regex whose every match is an issue; ``fix`` builds the replacement."""
    pattern: re.Pattern[str]
    code: str
    fix: Callable[[re.Match[str]], str]

    def __call__(self, i: int, line: str) -> Iterator[Issue]:
        for m in self.pattern.finditer(line):
            yield grammar_issue(i, m.start(), m.end(), self.code, (same_case(m.group(), self.fix(m)),))


def phrase(pattern: str, code: str, fix: Callable[[re.Match[str]], str]) -> PhraseRule:
    return PhraseRule(re.compile(pattern, re.I), code, fix)


def repeated_words(allowed: set[str], word_re: re.Pattern[str] = WORD_RE) -> Rule:
    def rule(i: int, line: str) -> Iterator[Issue]:
        prev = None
        for tok in words(line, word_re):
            gap = line[prev.end:tok.start] if prev else ""
            # Only flag when separated by whitespace: "so, so" or "no! no!" are deliberate.
            if prev and normalize(prev.text) == normalize(tok.text) and gap.strip() == "" \
                    and normalize(tok.text) not in allowed:
                yield grammar_issue(i, prev.start, tok.end, "repeated_word", (prev.text,), word=tok.text)
            prev = tok
    return rule


def punctuation_spacing(i: int, line: str) -> Iterator[Issue]:
    for m in re.finditer(r"(?<=\w)\s+([,;:!?.])(?!\.)", line):
        yield grammar_issue(i, m.start(), m.end(), "no_space_before", (m.group(1),), p=m.group(1))
    for m in re.finditer(r"(?<=[^\W\d_])([,;!?])(?=[^\W\d_])", line):
        yield grammar_issue(i, m.start(), m.end(), "space_after", (m.group(1) + " ",), p=m.group(1))


def capital_after_sentence(i: int, line: str) -> Iterator[Issue]:
    # Within a line only; many poems deliberately run sentences across lowercase lines.
    for m in re.finditer(r"(?<!\.)[.!?]\s+([^\W\d_]\w*)", line):
        w = m.group(1)
        if w[0].islower():
            yield grammar_issue(i, m.start(1), m.end(1), "capitalize_sentence", (w[0].upper() + w[1:],))


class GrammarChecker:
    def __init__(self, rules: list[Rule]):
        self.rules = rules

    def check(self, lines: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        for i, line in enumerate(lines):
            if line.strip():
                for rule in self.rules:
                    issues.extend(rule(i, line))
        return issues
