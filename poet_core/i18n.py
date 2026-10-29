"""Translated strings for analysis messages and frontend labels.

Kept in the portable core so every frontend shares one catalog. Keys missing
in a language fall back to English. Placeholders use ``str.format`` syntax.
"""

from __future__ import annotations

UI_LANGUAGES = ("en", "ro")

CATALOG: dict[str, dict[str, str]] = {
    "en": {
        # language names (shown in each language's own menu)
        "lang.en": "English",
        "lang.ro": "Romanian",

        # spelling / grammar messages
        "unknown_word": "Unknown word '{word}'.",
        "repeated_word": "Repeated word '{word}'.",
        "no_space_before": "No space before '{p}'.",
        "space_after": "Add a space after '{p}'.",
        "capitalize_sentence": "Capitalise the first word of a sentence.",
        "en_use_an": "Use 'an' before '{word}'.",
        "en_use_a": "Use 'a' before '{word}'.",
        "en_capital_i": "The pronoun 'I' is capitalised.",
        "en_modal_have": "Use 'have' after modal verbs.",
        "en_doesnt": "Subject-verb agreement: use 'doesn't'.",
        "en_agree_am": "Subject-verb agreement: use 'am'.",
        "en_agree_are": "Subject-verb agreement: use 'are'.",
        "en_agree_were": "Subject-verb agreement: use 'were'.",
        "en_agree_is": "Subject-verb agreement: use 'is'.",
        "en_a_lot": "'A lot' is two words.",
        "en_its_contraction": "Did you mean \"it's\" (it is / it has)?",
        "en_its_possessive": "Possessive 'its' has no apostrophe.",
        "en_youre": "Did you mean \"you're\" (you are)?",
        "en_than": "Use 'than' for comparisons.",
        "ro_fi": "After an auxiliary verb the infinitive is 'fi' (one i).",
        "ro_placea": "The infinitive is 'plăcea'.",
        "ro_subjunctive": "Incorrect subjunctive form.",
        "ro_pleonasm": "Pleonasm: '{word}' is already a superlative.",

        # degraded-feature notes
        "missing_cmudict": "cmudict missing: syllables and rhymes are approximate",
        "missing_en_wordlist": "no English word list: spell-check is off",
        "missing_spylls": "spylls missing: Romanian spell-check is off",
        "missing_ro_dictionary": "Romanian dictionary files missing: spell-check is off",
        "install_hint": "run: python -m pip install -r requirements.txt",

        # menus
        "menu.file": "File",
        "menu.new": "New",
        "menu.open": "Open...",
        "menu.save": "Save",
        "menu.save_as": "Save As...",
        "menu.sample": "Load sample poem",
        "menu.exit": "Exit",
        "menu.edit": "Edit",
        "menu.undo": "Undo",
        "menu.redo": "Redo",
        "menu.next_issue": "Next issue",
        "menu.prev_issue": "Previous issue",
        "menu.cut": "Cut",
        "menu.copy": "Copy",
        "menu.paste": "Paste",
        "menu.language": "Language",
        "menu.poem_language": "Poem language",
        "menu.ui_language": "Interface language",

        # panels
        "panel.rhymes": "Rhymes",
        "panel.lines": "Lines",
        "panel.words": "Words",
        "panel.issues": "Spelling & grammar",
        "panel.line": "Line",
        "panel.issue": "Issue",
        "rhyme.stanza": "Stanza {n}  ({scheme})",
        "rhyme.stanza_lines": "lines {first}-{last}",
        "rhyme.none": "no rhymes",
        "rhyme.pair": "line {a} ↔ line {b}",

        # status bar
        "status.loading": "Loading dictionaries…",
        "status.line": "Line {n}: {syllables} syllables",
        "status.rhymes_with": "rhymes with line {lines}",
        "status.no_rhyme": "no rhyme for “{word}” in stanza",
        "status.totals": "{stanzas} stanza(s), {lines} lines",
        "status.issues": "{spelling} spelling, {grammar} grammar",

        # context menu, dialogs, title
        "ctx.no_suggestions": "(no suggestions)",
        "ctx.add_word": "Add “{word}” to dictionary",
        "ctx.ignore": "Ignore this session",
        "dlg.save_changes": "Save changes before continuing?",
        "dlg.open_failed": "Could not open file:\n{error}",
        "dlg.save_failed": "Could not save file:\n{error}",
        "dlg.text_files": "Text files",
        "dlg.all_files": "All files",
        "title.untitled": "Untitled",
    },
    "ro": {
        "lang.en": "Engleză",
        "lang.ro": "Română",

        "unknown_word": "Cuvânt necunoscut: „{word}”.",
        "repeated_word": "Cuvânt repetat: „{word}”.",
        "no_space_before": "Fără spațiu înainte de „{p}”.",
        "space_after": "Adăugați un spațiu după „{p}”.",
        "capitalize_sentence": "Propoziția începe cu majusculă.",
        "en_use_an": "Folosiți „an” înainte de „{word}”.",
        "en_use_a": "Folosiți „a” înainte de „{word}”.",
        "en_capital_i": "Pronumele „I” se scrie cu majusculă.",
        "en_modal_have": "După verbele modale se folosește „have”.",
        "en_doesnt": "Acord subiect-predicat: folosiți „doesn't”.",
        "en_agree_am": "Acord subiect-predicat: folosiți „am”.",
        "en_agree_are": "Acord subiect-predicat: folosiți „are”.",
        "en_agree_were": "Acord subiect-predicat: folosiți „were”.",
        "en_agree_is": "Acord subiect-predicat: folosiți „is”.",
        "en_a_lot": "„A lot” se scrie în două cuvinte.",
        "en_its_contraction": "Ați vrut să scrieți „it's” (it is / it has)?",
        "en_its_possessive": "Posesivul „its” nu are apostrof.",
        "en_youre": "Ați vrut să scrieți „you're” (you are)?",
        "en_than": "La comparații se folosește „than”.",
        "ro_fi": "După verbul auxiliar, infinitivul este „fi” (cu un singur i).",
        "ro_placea": "Infinitivul corect este „plăcea”.",
        "ro_subjunctive": "Formă incorectă de conjunctiv.",
        "ro_pleonasm": "Pleonasm: „{word}” este deja un superlativ.",

        "missing_cmudict": "lipsește cmudict: silabele și rimele sunt aproximative",
        "missing_en_wordlist": "lipsește lista de cuvinte englezești: corectura ortografică e oprită",
        "missing_spylls": "lipsește spylls: corectura ortografică în română e oprită",
        "missing_ro_dictionary": "lipsesc fișierele dicționarului român: corectura ortografică e oprită",
        "install_hint": "rulați: python -m pip install -r requirements.txt",

        "menu.file": "Fișier",
        "menu.new": "Nou",
        "menu.open": "Deschide...",
        "menu.save": "Salvează",
        "menu.save_as": "Salvează ca...",
        "menu.sample": "Încarcă poezia exemplu",
        "menu.exit": "Ieșire",
        "menu.edit": "Editare",
        "menu.undo": "Anulează",
        "menu.redo": "Refă",
        "menu.next_issue": "Problema următoare",
        "menu.prev_issue": "Problema anterioară",
        "menu.cut": "Taie",
        "menu.copy": "Copiază",
        "menu.paste": "Lipește",
        "menu.language": "Limbă",
        "menu.poem_language": "Limba poeziei",
        "menu.ui_language": "Limba interfeței",

        "panel.rhymes": "Rime",
        "panel.lines": "Versuri",
        "panel.words": "Cuvinte",
        "panel.issues": "Ortografie și gramatică",
        "panel.line": "Vers",
        "panel.issue": "Problemă",
        "rhyme.stanza": "Strofa {n}  ({scheme})",
        "rhyme.stanza_lines": "versurile {first}-{last}",
        "rhyme.none": "fără rime",
        "rhyme.pair": "versul {a} ↔ versul {b}",

        "status.loading": "Se încarcă dicționarele…",
        "status.line": "Versul {n}: {syllables} silabe",
        "status.rhymes_with": "rimează cu versul {lines}",
        "status.no_rhyme": "nicio rimă pentru „{word}” în strofă",
        "status.totals": "{stanzas} strofe, {lines} versuri",
        "status.issues": "{spelling} ortografie, {grammar} gramatică",

        "ctx.no_suggestions": "(nicio sugestie)",
        "ctx.add_word": "Adaugă „{word}” în dicționar",
        "ctx.ignore": "Ignoră în această sesiune",
        "dlg.save_changes": "Salvați modificările înainte de a continua?",
        "dlg.open_failed": "Fișierul nu a putut fi deschis:\n{error}",
        "dlg.save_failed": "Fișierul nu a putut fi salvat:\n{error}",
        "dlg.text_files": "Fișiere text",
        "dlg.all_files": "Toate fișierele",
        "title.untitled": "Fără titlu",
    },
}


def t(key: str, lang: str = "en", **kwargs: object) -> str:
    text = CATALOG.get(lang, {}).get(key) or CATALOG["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
