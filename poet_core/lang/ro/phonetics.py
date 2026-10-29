"""Romanian syllables and rhymes from spelling.

Romanian orthography is close to phonemic, so syllable nuclei can be found
from letters: runs of vowels are split into diphthongs/triphthongs (one
syllable each) or vowels in hiatus, and a word-final "i" after a consonant
is non-syllabic ("pomi", "dormi", "dă-mi").

Stress (which starts the rhyme) is not marked in writing. The heuristic:
words ending in a single vowel are stressed on the next-to-last syllable
("floare", "adună"), others on the last ("pământ", "cafea", "copaci").
A trailing definite article does not move stress ("cerul", "codrului").
Accented letters typed by the poet ("fáce") mark stress explicitly.
"""

from __future__ import annotations

import unicodedata
from typing import NamedTuple

VOWELS = set("aăâeiîouy")

# Triphthongs: one syllable; value = offset of the vowel that carries the syllable.
TRIPHTHONGS = {"eoa": 2, "ioa": 2, "iea": 2, "eau": 1, "iau": 1, "eai": 1, "oai": 1, "uai": 1, "iai": 1}
# Diphthongs: rising (semivowel first) -> 1, falling (semivowel last) -> 0.
DIPHTHONGS = {
    "ea": 1, "oa": 1, "ia": 1, "ie": 1, "io": 1, "ua": 1, "uă": 1,
    "ai": 0, "ei": 0, "oi": 0, "ui": 0, "ăi": 0, "âi": 0, "îi": 0,
    "au": 0, "ou": 0, "eu": 0, "ău": 0, "âu": 0, "îu": 0, "iu": 0,
}
ARTICLE_SUFFIXES = ("ului", "lor", "ul")

_CEDILLA = str.maketrans({"ş": "ș", "ţ": "ț", "Ş": "Ș", "Ţ": "Ț"})
_STRESS_MARKS = {"́", "̀"}  # combining acute / grave


class Nucleus(NamedTuple):
    start: int   # first letter of the vowel group
    end: int     # one past its last letter
    main: int    # index of the syllable-carrying vowel
    stressed: bool = False


def normalize_ro(word: str) -> str:
    """Lowercase, comma-below ș/ț, curly apostrophe -> straight."""
    return word.translate(_CEDILLA).replace("’", "'").lower()


def _strip_stress(word: str) -> tuple[str, set[int]]:
    """Remove acute/grave accents, returning the letters and which were accented."""
    letters, marked = [], set()
    for ch in unicodedata.normalize("NFD", word):
        if ch in _STRESS_MARKS:
            if letters:
                marked.add(len(letters) - 1)
        else:
            letters.append(ch)
    return unicodedata.normalize("NFC", "".join(letters)), marked


def _phonetic_letters(word: str) -> tuple[str, set[int]]:
    w, marked = _strip_stress(normalize_ro(word))
    # Hyphens and apostrophes join clitics without adding sounds: "s-a" -> "sa".
    keep = [(i, c) for i, c in enumerate(w) if c not in "-'"]
    remap = {old: new for new, (old, _) in enumerate(keep)}
    return "".join(c for _, c in keep), {remap[i] for i in marked if i in remap}


def nuclei(word: str) -> tuple[str, list[Nucleus]]:
    """Letters (lowercase, no hyphens/accents) and their syllable nuclei."""
    w, marked = _phonetic_letters(word)
    found: list[Nucleus] = []
    i = 0
    while i < len(w):
        if w[i] not in VOWELS:
            i += 1
            continue
        j = i
        while j < len(w) and w[j] in VOWELS:
            j += 1
        found.extend(_split_run(w, i, j))
        i = j
    # Word-final "i" after a consonant is non-syllabic when another nucleus exists.
    if len(found) > 1:
        last = found[-1]
        if last.end == len(w) and w[last.start:last.end] == "i" and last.start > 0 and w[last.start - 1] not in VOWELS:
            found.pop()
    if marked:
        found = [n._replace(stressed=any(n.start <= m < n.end for m in marked)) for n in found]
    return w, found


def _split_run(w: str, start: int, end: int) -> list[Nucleus]:
    out = []
    i = start
    after_consonant = start > 0
    while i < end:
        tri, di = w[i:i + 3], w[i:i + 2]
        if i + 3 <= end and tri in TRIPHTHONGS:
            out.append(Nucleus(i, i + 3, i + TRIPHTHONGS[tri]))
            i += 3
            continue
        if i + 2 <= end and di in DIPHTHONGS and not _is_hiatus(w, i, end, after_consonant and i == start):
            out.append(Nucleus(i, i + 2, i + DIPHTHONGS[di]))
            i += 2
            continue
        if i + 2 == end == len(w) and di == "ii":  # "copii", "fii"
            out.append(Nucleus(i, i + 2, i))
            i += 2
            continue
        out.append(Nucleus(i, i + 1, i))
        i += 1
    return out


def _is_hiatus(w: str, i: int, run_end: int, after_consonant: bool) -> bool:
    # Word-final "-ie"/"-ia" after a consonant are two syllables: "poe-zi-e", "fa-mi-li-a".
    # After c/g/ch/gh the "i" only marks pronunciation ("ce-ai-ul" aside), so it stays one.
    pair = w[i:i + 2]
    if pair in ("ie", "ia") and after_consonant and i + 2 == run_end == len(w):
        return w[i - 1] not in "cgh"
    return False


def syllable_count(word: str) -> int:
    w, found = nuclei(word)
    return max(1, len(found)) if w else 0


def _stressed_index(w: str, found: list[Nucleus]) -> int:
    for k, n in enumerate(found):
        if n.stressed:
            return k
    if len(found) == 1:
        return 0
    last = found[-1]
    ends_in_single_vowel = last.end == len(w) and last.end - last.start == 1
    return len(found) - 2 if ends_in_single_vowel else len(found) - 1


def rhyme_key(word: str) -> str:
    w, found = nuclei(word)
    if not found:
        return "~" + w
    base_found, base = found, w
    if not any(n.stressed for n in found):
        for suffix in ARTICLE_SUFFIXES:
            if w.endswith(suffix):
                cand_w, cand = nuclei(w[: -len(suffix)])
                if cand:
                    base, base_found = cand_w, cand
                break
    k = _stressed_index(base, base_found)
    # Rhyme runs from the syllable-carrying vowel of the stressed nucleus to the end,
    # so "soare" and "mare" share "are". "â" and "î" are the same sound.
    return w[base_found[k].main:].replace("â", "î")


class RomanianPhonetics:
    available = True

    def warm_up(self) -> None:
        pass

    def syllable_range(self, word: str) -> tuple[int, int]:
        n = syllable_count(word)
        return n, n

    def syllables(self, word: str) -> int:
        return syllable_count(word)

    def rhyme_keys(self, word: str) -> frozenset[str]:
        return frozenset({rhyme_key(word)})
