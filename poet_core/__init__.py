"""Portable poetry-analysis core.

This package has no GUI or OS-specific dependencies: it takes plain text in
and returns plain data (see ``model``). Any frontend (Tk, Qt, web, CLI, a
mobile port...) only needs to call ``Analyzer.analyze`` and render the
``Report``; ``i18n`` provides translated labels for it.
"""

from .analyzer import Analyzer
from .lang import LANGUAGES
from .model import Issue, IssueKind, LineInfo, Report, RhymePair, Stanza

__all__ = [
    "Analyzer",
    "Issue",
    "IssueKind",
    "LANGUAGES",
    "LineInfo",
    "Report",
    "RhymePair",
    "Stanza",
]
