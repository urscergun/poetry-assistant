"""Core tests (no GUI). Run: python -m unittest discover tests"""

import unittest

from poet_core import Analyzer, IssueKind
from poet_core.i18n import CATALOG
from poet_core.lang.en.phonetics import Pronouncer, heuristic_rhyme_key, heuristic_syllables
from poet_core.lang.ro.phonetics import rhyme_key as ro_rhyme_key, syllable_count as ro_syllables

ANALYZER = Analyzer("en")
RO = Analyzer("ro")
EMINESCU = """Somnoroase păsărele
Pe la cuiburi se adună,
Se ascund în rămurele -
Noapte bună!"""


def kinds(text):
    return [(i.kind, i.line, i.message) for i in ANALYZER.analyze(text).issues]


class SyllableTests(unittest.TestCase):
    def test_dictionary_words(self):
        p = ANALYZER.phonetics
        self.assertEqual(p.syllables("cat"), 1)
        self.assertEqual(p.syllables("poetry"), 3)
        self.assertEqual(p.syllable_range("fire"), (1, 2))

    def test_line_count(self):
        r = ANALYZER.analyze("Shall I compare thee to a summer's day?")
        self.assertEqual(r.lines[0].syllables_text, "10")

    def test_variant_range(self):
        r = ANALYZER.analyze("Thou art more lovely and more temperate")
        self.assertEqual(r.lines[0].syllables_text, "9-10")

    def test_heuristic(self):
        self.assertEqual(heuristic_syllables("glimmerous"), 3)
        self.assertEqual(heuristic_syllables("stone"), 1)
        self.assertEqual(heuristic_syllables("candle"), 2)

    def test_works_without_cmudict(self):
        p = Pronouncer(cmu={})
        self.assertEqual(p.syllables("window"), 2)
        self.assertEqual(p.rhyme_keys("night"), p.rhyme_keys("light"))


class RhymeTests(unittest.TestCase):
    def test_abab(self):
        r = ANALYZER.analyze("The sun is bright\nUpon the sea\nIt fades to night\nAnd sets me free")
        self.assertEqual(r.stanzas[0].scheme, "ABAB")
        self.assertEqual(r.lines[0].rhymes_with, [2])
        self.assertEqual([(p.first, p.second) for p in r.stanzas[0].pairs], [(0, 2), (1, 3)])

    def test_stanzas_are_independent(self):
        r = ANALYZER.analyze("a day\nthe sea\n\nthe bay\nits key")
        self.assertEqual([s.scheme for s in r.stanzas], ["AB", "AB"])
        self.assertEqual(r.lines[0].rhymes_with, [])
        self.assertIsNone(r.lines[2].stanza)
        self.assertNotEqual(r.lines[0].rhyme_group, r.lines[3].rhyme_group)

    def test_multisyllable_and_punctuation(self):
        r = ANALYZER.analyze("so happy,\nand snappy!")
        self.assertEqual(r.stanzas[0].scheme, "AA")

    def test_unknown_words_fall_back_to_spelling(self):
        self.assertEqual(heuristic_rhyme_key("glove"), heuristic_rhyme_key("shove"))


class SpellingTests(unittest.TestCase):
    def test_misspelling_with_suggestion(self):
        issues = [i for i in ANALYZER.analyze("my true loev").issues if i.kind is IssueKind.SPELLING]
        self.assertEqual(len(issues), 1)
        self.assertEqual((issues[0].start, issues[0].end), (8, 12))
        self.assertIn("love", issues[0].suggestions)

    def test_poetic_and_contracted_words_accepted(self):
        text = "Thou art o'er the hill, 'tis thy night's song; I don't know"
        self.assertEqual([i for i in ANALYZER.analyze(text).issues if i.kind is IssueKind.SPELLING], [])

    def test_proper_nouns_midline_skipped(self):
        self.assertEqual(kinds("we walked with Zyxandra"), [])

    def test_no_word_list_disables_spelling(self):
        a = Analyzer("en")
        a.spelling._pron = a.phonetics = a.language.phonetics = Pronouncer(cmu={})
        a.spelling._backend = None  # simulate pyspellchecker not installed
        self.assertFalse(a.spelling.available)
        self.assertEqual([i for i in a.analyze("Shall I compare thee").issues if i.kind is IssueKind.SPELLING], [])
        self.assertEqual(len(a.missing_data()), 2)
        self.assertEqual(ANALYZER.missing_data(), [])

    def test_ignore(self):
        a = Analyzer()
        a.spelling.ignore("blorft")
        self.assertEqual(a.analyze("a blorft day").issues, [])


class GrammarTests(unittest.TestCase):
    def grammar(self, text):
        return [i for i in ANALYZER.analyze(text).issues if i.kind is IssueKind.GRAMMAR]

    def test_rules(self):
        cases = {
            "the the moon": "the",
            "a apple": "an",
            "an tree": "a",
            "and i went": "I",
            "it could of been": "could have",
            "he don't care": "he doesn't",
            "they was here": "they were",
            "more then ever": "more than",
            "it's own way": "its own",
            "hello , world": ",",
        }
        for text, fix in cases.items():
            with self.subTest(text=text):
                issues = self.grammar(text)
                self.assertEqual(len(issues), 1, issues)
                self.assertEqual(issues[0].suggestions[0], fix)

    def test_no_false_positives(self):
        for text in ("an hour", "a unicorn", "I was there", "if it were so", "so, so tired", "its time had come", "an FBI man"):
            with self.subTest(text=text):
                self.assertEqual(self.grammar(text), [])


class RomanianSyllableTests(unittest.TestCase):
    def test_words(self):
        cases = {
            "somnoroase": 4, "păsărele": 4, "cuiburi": 2, "noapte": 2, "izvoarele": 4, "dormi": 1,
            "poezie": 4, "idee": 3, "copii": 2, "pomi": 1, "oameni": 2, "două": 2, "ziua": 2,
            "aripioară": 4, "chiar": 1, "istorie": 4, "aer": 2, "luceafărul": 4, "fereastră": 3,
            "s-a": 1, "mi-ar": 1, "într-o": 2, "dă-mi": 1, "florile-n": 3,
        }
        for word, n in cases.items():
            with self.subTest(word=word):
                self.assertEqual(ro_syllables(word), n)

    def test_eminescu_lines(self):
        r = RO.analyze(EMINESCU)
        self.assertEqual([l.syllables_text for l in r.lines], ["8", "8", "8", "4"])


class RomanianRhymeTests(unittest.TestCase):
    def test_pairs(self):
        rhyme = [("păsărele", "rămurele"), ("adună", "bună"), ("floare", "soare"), ("mare", "soare"),
                 ("deal", "val"), ("copaci", "săraci"), ("cafea", "stea"), ("pământ", "cuvânt"),
                 ("codrului", "modrului"), ("fáce", "pace")]
        for a, b in rhyme:
            with self.subTest(pair=(a, b)):
                self.assertEqual(ro_rhyme_key(a), ro_rhyme_key(b))
        for a, b in [("mare", "pace"), ("floare", "noapte"), ("dor", "dar"), ("cerul", "mister")]:
            with self.subTest(pair=(a, b)):
                self.assertNotEqual(ro_rhyme_key(a), ro_rhyme_key(b))

    def test_scheme(self):
        r = RO.analyze(EMINESCU)
        self.assertEqual(r.stanzas[0].scheme, "ABAB")


class RomanianSpellingGrammarTests(unittest.TestCase):
    def issues(self, text, kind):
        return [i for i in RO.analyze(text).issues if i.kind is kind]

    def test_correct_text_has_no_spelling_issues(self):
        text = "Și noaptea vine lin pe deal, s-a dus într-o zare, florile-n grădină; ş-a şi ţara"
        self.assertEqual(self.issues(text, IssueKind.SPELLING), [])

    def test_misspelling(self):
        issues = self.issues("ce-n zare se topeștte", IssueKind.SPELLING)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].suggestions[0], "topește")

    def test_rules(self):
        cases = {"ar fii bine": "ar fi", "mi-ar place": "ar plăcea", "să aibe": "să aibă",
                 "luna luna": "luna", "cel mai optim": "optim"}
        for text, fix in cases.items():
            with self.subTest(text=text):
                issues = self.issues(text, IssueKind.GRAMMAR)
                self.assertEqual(len(issues), 1, issues)
                self.assertEqual(issues[0].suggestions[0], fix)

    def test_no_false_positives(self):
        for text in ("să fii fericit", "încet încet", "îi place marea", "ai fii frumoși"):
            with self.subTest(text=text):
                self.assertEqual(self.issues(text, IssueKind.GRAMMAR), [])


class TranslationTests(unittest.TestCase):
    def test_catalogs_have_same_keys(self):
        self.assertEqual(set(CATALOG["en"]), set(CATALOG["ro"]))

    def test_messages_follow_ui_language(self):
        a = Analyzer("en", ui_language="ro")
        self.assertEqual(a.analyze("my true loev").issues[0].message, "Cuvânt necunoscut: „loev”.")


if __name__ == "__main__":
    unittest.main()
