"""Facade that turns raw text into a ``Report``."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from . import i18n
from .lang import Grammar, create_language
from .model import Issue, IssueKind, LineInfo, Report, RhymePair, Stanza
from .rhyme import rhyme_stanza
from .text import last_word, split_stanzas, words

# Uncached spelling suggestions can take ~0.5 s each (Romanian Hunspell); a pass spends at
# most this long on them and marks the report incomplete so the caller re-runs it.
SUGGESTION_BUDGET_S = 0.3


class Analyzer:
    """Analyses poems in one language; messages come out in ``ui_language``.

    Stateless per call and safe to run from a worker thread. Spelling
    suggestions are cached, so re-analysing on every keystroke only pays for
    words that changed.
    """

    def __init__(
        self,
        language: str = "en",
        ui_language: str = "en",
        user_dictionary: Path | None = None,
        grammar: Grammar | None = None,
    ):
        self.language = create_language(language, user_dictionary)
        self.ui_language = ui_language
        self.phonetics = self.language.phonetics
        self.spelling = self.language.speller
        self.grammar = grammar or self.language.grammar

    @property
    def code(self) -> str:
        return self.language.code

    def warm_up(self) -> None:
        """Load dictionaries up front (about a second); optional."""
        self.language.warm_up()

    def missing_data(self) -> list[str]:
        """Notes on degraded features in the UI language, empty when fully equipped."""
        return [i18n.t(code, self.ui_language) for code in self.language.missing_data()]

    def analyze(self, text: str) -> Report:
        word_re = self.language.word_re
        raw_lines = text.split("\n")
        lines = [LineInfo(index=i, text=t) for i, t in enumerate(raw_lines)]

        for info in lines:
            ranges = [self.phonetics.syllable_range(t.text) for t in words(info.text, word_re)]
            info.syllables = sum(lo for lo, _ in ranges)
            info.syllables_max = sum(hi for _, hi in ranges)
            tok = last_word(info.text, word_re)
            if tok:
                info.end_word, info.end_word_span = tok.text, (tok.start, tok.end)

        stanzas: list[Stanza] = []
        group_offset = 0
        for s_idx, members in enumerate(split_stanzas(raw_lines)):
            rhymes = rhyme_stanza({i: lines[i].end_word for i in members}, self.phonetics)
            for i in members:
                info = lines[i]
                info.stanza = s_idx
                info.rhyme_label = rhymes.labels.get(i)
                if i in rhymes.groups:
                    info.rhyme_group = group_offset + rhymes.groups[i]
                info.rhymes_with = rhymes.partners.get(i, [])
            group_offset += len(set(rhymes.groups.values()))

            pairs = [
                RhymePair(a, b, lines[a].end_word or "", lines[b].end_word or "")
                for a in members for b in rhymes.partners.get(a, []) if a < b
            ]
            scheme = "".join(rhymes.labels.get(i, "-") for i in members)
            stanzas.append(Stanza(s_idx, members, scheme, pairs))

        spelling, incomplete = self._spelling_issues(raw_lines)
        issues = [self._render(x) for x in spelling + self.grammar.check(raw_lines)]
        issues.sort(key=lambda x: (x.line, x.start, x.kind.value))
        return Report(lines, stanzas, issues, incomplete)

    def _render(self, issue: Issue) -> Issue:
        return replace(issue, message=i18n.t(issue.code, self.ui_language, **dict(issue.args)))

    def _spelling_issues(self, lines: list[str]) -> tuple[list[Issue], bool]:
        out: list[Issue] = []
        speller = self.spelling
        if not speller.available:
            return out, False
        deadline = time.monotonic() + SUGGESTION_BUDGET_S
        incomplete = False
        for i, line in enumerate(lines):
            first = True
            prev_end = 0
            for tok in words(line, self.language.word_re):
                # A capital after sentence punctuation is not a proper-noun hint either.
                at_start = first or line[prev_end:tok.start].strip()[-1:] in (".", "!", "?")
                first, prev_end = False, tok.end
                if not speller.should_check(tok.text, at_start) or speller.is_correct(tok.text):
                    continue
                suggestions = speller.cached_suggestions(tok.text)
                if suggestions is None:
                    if time.monotonic() < deadline:
                        suggestions = speller.suggest(tok.text)
                    else:
                        suggestions, incomplete = (), True
                out.append(Issue(
                    IssueKind.SPELLING, i, tok.start, tok.end,
                    "unknown_word", (("word", tok.text),), suggestions,
                ))
        return out, incomplete
