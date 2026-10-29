"""Main window: editor with a syllable/rhyme gutter, rhyme and issue panels."""

from __future__ import annotations

import queue
import tkinter as tk
import tkinter.font as tkfont
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from poet_core import LANGUAGES, Analyzer, Issue, IssueKind, Report
from poet_core.i18n import UI_LANGUAGES, t
from poet_core.samples import SAMPLES

from . import os_support
from .settings import Settings
from .tooltip import Tooltip

DEBOUNCE_MS = 250
POLL_MS = 40
EDITOR_SIZE = 13
GUTTER_SIZE_OFFSET = -3   # gutter font follows the editor, slightly smaller
MIN_SIZE, MAX_SIZE = 8, 48
SASH_MIN = 10  # px
UI_NAMED_FONTS = (
    "TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkCaptionFont",
    "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont", "TkFixedFont",
)

# Background tints for rhyme groups (cycled), with a matching strong colour for the gutter letter.
RHYME_COLORS = [
    ("#ffe3e3", "#c92a2a"), ("#dbe4ff", "#364fc7"), ("#d3f9d8", "#2b8a3e"),
    ("#fff3bf", "#e67700"), ("#f3d9fa", "#862e9c"), ("#c5f6fa", "#0b7285"),
    ("#ffe8cc", "#d9480f"), ("#e5dbff", "#5f3dc4"),
]
SPELLING_COLOR = "#e03131"
GRAMMAR_COLOR = "#1c7ed6"
FOCUS_COLOR = "#e4e6ea"
RIGHT_PANE_MIN = 380      # px at default zoom; the side panels start at least this wide
RIGHT_PANE_SHARE = 0.36


def _pick_font(candidates: tuple[str, ...], size: int, fallback: str) -> tkfont.Font:
    families = set(tkfont.families())
    family = next((f for f in candidates if f in families), None)
    if family is None:
        font = tkfont.nametofont(fallback).copy()
        font.configure(size=size)  # named fonts may be in pixels (negative); zoom expects points
        return font
    return tkfont.Font(family=family, size=size)


class PoetApp:
    def __init__(
        self,
        root: tk.Tk,
        poem_language: str = "en",
        ui_language: str = "en",
        dictionary_path: Callable[[str], Path | None] = lambda code: None,
        on_settings_changed: Callable[[str, str], None] | None = None,
    ):
        self.root = root
        self.ui_language = ui_language
        self._dictionary_path = dictionary_path
        self._on_settings_changed = on_settings_changed
        self.report: Report | None = None
        self.missing: list[str] = []
        self.path: Path | None = None
        self.dirty = False

        self._version = 0
        self._pending: str | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._results: queue.Queue[tuple[int, Report, list[str]]] = queue.Queue()
        self._analyzers: dict[str, Analyzer] = {}
        self.analyzer = self._get_analyzer(poem_language)

        self.editor_font = _pick_font(os_support.EDITOR_FONTS, EDITOR_SIZE, "TkTextFont")
        self.gutter_font = _pick_font(os_support.UI_MONO_FONTS, EDITOR_SIZE + GUTTER_SIZE_OFFSET, "TkFixedFont")
        self.gutter_bold = self.gutter_font.copy()
        self.gutter_bold.configure(weight="bold")

        self._ui_font_sizes = {
            name: tkfont.nametofont(name).cget("size")
            for name in UI_NAMED_FONTS if name in tkfont.names()
        }
        self.style = ttk.Style(self.root)
        self.poem_language_var = tk.StringVar(self.root, poem_language)
        self.ui_language_var = tk.StringVar(self.root, ui_language)
        self._menubar_widgets: list[tk.Widget] = []
        self._alt_keys: list[str] = []

        self._build_ui()
        self._apply_ui_scale()
        self._bind_keys()
        self._update_title()
        self.root.after(POLL_MS, self._poll_results)
        self._schedule_analysis(0)

    def tr(self, key: str, **kwargs: object) -> str:
        return t(key, self.ui_language, **kwargs)

    # ------------------------------------------------------------ languages

    def _get_analyzer(self, code: str) -> Analyzer:
        analyzer = self._analyzers.get(code)
        if analyzer is None:
            analyzer = Analyzer(code, self.ui_language, user_dictionary=self._dictionary_path(code))
            self._analyzers[code] = analyzer
            # Load dictionaries off the UI thread; analyses queue up behind it.
            self._executor.submit(analyzer.warm_up)
        return analyzer

    def set_poem_language(self, code: str) -> None:
        old = self.analyzer.code
        if code == old:
            return
        self.analyzer = self._get_analyzer(code)
        self.poem_language_var.set(code)
        # Swap the demo poem along with the language, but never touch the user's own text.
        if not self.dirty and self.path is None and self.text.get("1.0", "end-1c") == SAMPLES.get(old):
            self._set_text(SAMPLES.get(code, ""), None)
        self._settings_changed()
        self._schedule_analysis(0)

    def set_ui_language(self, code: str) -> None:
        if code == self.ui_language:
            return
        self.ui_language = code
        self.ui_language_var.set(code)
        for analyzer in self._analyzers.values():
            analyzer.ui_language = code
        self._retranslate()
        self._settings_changed()
        self._schedule_analysis(0)  # issue messages are rendered by the analyzer

    def _settings_changed(self) -> None:
        if self._on_settings_changed:
            self._on_settings_changed(self.analyzer.code, self.ui_language)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        self.root.geometry("1100x700")
        self.root.minsize(700, 400)
        self._build_menu()

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        self._paned = paned

        # Editor + gutter
        left = ttk.Frame(paned)
        self.gutter = tk.Canvas(left, width=self._gutter_x(13.5), highlightthickness=0, background="#f4f4f2")
        self.text = tk.Text(
            left, wrap="word", undo=True, font=self.editor_font, padx=10, pady=8,
            relief="flat", background="#fffefb", foreground="#222", insertbackground="#222",
            selectbackground="#b6d4fe", spacing1=2, spacing3=2,
        )
        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=lambda *a: (scroll.set(*a), self._redraw_gutter()))
        self.gutter.pack(side=tk.LEFT, fill=tk.Y)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        paned.add(left, weight=3)

        self._configure_tags()

        # Right side: rhymes over issues
        right = ttk.PanedWindow(paned, orient=tk.VERTICAL)
        paned.add(right, weight=1)

        self.rhyme_frame = ttk.LabelFrame(right)
        self.rhyme_tree = ttk.Treeview(self.rhyme_frame, columns=("words",), show="tree headings", height=8)
        self.rhyme_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.rhyme_tree.bind("<<TreeviewSelect>>", self._on_rhyme_select)
        right.add(self.rhyme_frame, weight=1)

        self.issue_frame = ttk.LabelFrame(right)
        self.issue_tree = ttk.Treeview(self.issue_frame, columns=("line", "msg"), show="headings", height=10)
        self.issue_tree.column("line", stretch=False, anchor=tk.E)
        self.issue_tree.tag_configure(IssueKind.SPELLING.value, foreground=SPELLING_COLOR)
        self.issue_tree.tag_configure(IssueKind.GRAMMAR.value, foreground=GRAMMAR_COLOR)
        self.issue_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.issue_tree.bind("<<TreeviewSelect>>", self._on_issue_select)
        self.issue_tree.bind("<Double-1>", self._on_issue_activate)
        right.add(self.issue_frame, weight=1)

        status_bar = ttk.Frame(self.root)
        # Packed ahead of the main area: when space runs short (e.g. zoomed in), pack shrinks
        # the last-packed widget, which must be the editor, not the status bar.
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, before=paned)
        self.status = ttk.Label(status_bar, anchor=tk.W, padding=(8, 2))
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.warning = ttk.Label(status_bar, anchor=tk.E, padding=(8, 2), foreground="#c2410c")
        self.warning.pack(side=tk.RIGHT)

        self.menu = tk.Menu(self.root, tearoff=False, font="TkMenuFont")
        self._label_widgets()

    def _label_widgets(self) -> None:
        self.rhyme_frame.configure(text=self.tr("panel.rhymes"))
        self.rhyme_tree.heading("#0", text=self.tr("panel.lines"))
        self.rhyme_tree.heading("words", text=self.tr("panel.words"))
        self.issue_frame.configure(text=self.tr("panel.issues"))
        self.issue_tree.heading("line", text=self.tr("panel.line"))
        self.issue_tree.heading("msg", text=self.tr("panel.issue"))

    def _retranslate(self) -> None:
        self._build_menu()
        self._label_widgets()
        if self.report:
            self._fill_rhymes(self.report)
        self._update_status()
        self._update_title()

    def _build_menu(self) -> None:
        m = os_support.MOD_LABEL
        tr = self.tr
        file_menu = tk.Menu(self.root, tearoff=False, font="TkMenuFont")
        file_menu.add_command(label=tr("menu.new"), accelerator=f"{m}+N", command=self.new_file)
        file_menu.add_command(label=tr("menu.open"), accelerator=f"{m}+O", command=self.open_file)
        file_menu.add_command(label=tr("menu.save"), accelerator=f"{m}+S", command=self.save_file)
        file_menu.add_command(label=tr("menu.save_as"), accelerator=f"{m}+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label=tr("menu.sample"), command=self.load_sample)
        file_menu.add_separator()
        file_menu.add_command(label=tr("menu.exit"), command=self.quit)

        edit_menu = tk.Menu(self.root, tearoff=False, font="TkMenuFont")
        edit_menu.add_command(label=tr("menu.undo"), accelerator=f"{m}+Z", command=lambda: self._edit("<<Undo>>"))
        edit_menu.add_command(label=tr("menu.redo"), accelerator=f"{m}+Y", command=lambda: self._edit("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label=tr("menu.next_issue"), accelerator="F8", command=lambda: self.goto_issue(+1))
        edit_menu.add_command(label=tr("menu.prev_issue"), accelerator="Shift+F8", command=lambda: self.goto_issue(-1))

        lang_menu = tk.Menu(self.root, tearoff=False, font="TkMenuFont")
        poem_menu = tk.Menu(lang_menu, tearoff=False, font="TkMenuFont")
        for code in LANGUAGES:
            poem_menu.add_radiobutton(label=tr(f"lang.{code}"), value=code, variable=self.poem_language_var,
                                      command=lambda c=code: self.set_poem_language(c))
        ui_menu = tk.Menu(lang_menu, tearoff=False, font="TkMenuFont")
        for code in UI_LANGUAGES:
            # Each interface language is listed in its own name so it can be found when lost.
            ui_menu.add_radiobutton(label=t(f"lang.{code}", code), value=code, variable=self.ui_language_var,
                                    command=lambda c=code: self.set_ui_language(c))
        lang_menu.add_cascade(label=tr("menu.poem_language"), menu=poem_menu)
        lang_menu.add_cascade(label=tr("menu.ui_language"), menu=ui_menu)

        menus = [(tr("menu.file"), file_menu), (tr("menu.edit"), edit_menu), (tr("menu.language"), lang_menu)]
        if os_support.NATIVE_MENUBAR:
            bar = tk.Menu(self.root)
            for label, menu in menus:
                bar.add_cascade(label=label, menu=menu)
            self.root.configure(menu=bar)
        else:
            self._build_window_menubar(menus)

    def _build_window_menubar(self, menus: list[tuple[str, tk.Menu]]) -> None:
        # Drawn by Tk (unlike the native Windows menubar), so it follows the zoom.
        self.style.layout("Menubar.TMenubutton", [("Menubutton.padding", {"sticky": "nswe", "children": [
            ("Menubutton.label", {"sticky": "nswe"})]})])
        self.style.configure("Menubar.TMenubutton", padding=(8, 2), font="TkMenuFont")
        self.style.map("Menubar.TMenubutton", background=[("active", "#dbe4ff")])
        for widget in self._menubar_widgets:
            widget.destroy()
        for key in self._alt_keys:
            self.root.unbind_all(key)
        self._alt_keys = []

        # On a rebuild (language change) the bar must go back above the main area.
        place = {"before": self._paned} if hasattr(self, "_paned") else {}
        bar = ttk.Frame(self.root)
        bar.pack(side=tk.TOP, fill=tk.X, **place)
        separator = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        separator.pack(side=tk.TOP, fill=tk.X, **place)
        self._menubar_widgets = [bar, separator]
        for label, menu in menus:
            button = ttk.Menubutton(bar, text=label, menu=menu, underline=0, style="Menubar.TMenubutton")
            button.pack(side=tk.LEFT)
            # Alt+<first letter> opens the menu like a native menubar.
            key = f"<Alt-{label[0].lower()}>"
            self.root.bind_all(key, lambda e, b=button: self._post_menu(b))
            self._alt_keys.append(key)

    @staticmethod
    def _post_menu(button: ttk.Menubutton) -> str:
        menu = button.nametowidget(button.cget("menu"))
        menu.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())
        return "break"

    def _configure_tags(self) -> None:
        t = self.text
        for i, (bg, _) in enumerate(RHYME_COLORS):
            t.tag_configure(f"rhyme{i}", background=bg)
        t.tag_configure("spelling", underline=True, foreground=SPELLING_COLOR)
        t.tag_configure("grammar", underline=True)
        try:  # underlinefg needs Tk >= 8.6.11
            t.tag_configure("grammar", underlinefg=GRAMMAR_COLOR)
            t.tag_configure("spelling", underlinefg=SPELLING_COLOR, foreground="")
        except tk.TclError:
            t.tag_configure("grammar", foreground=GRAMMAR_COLOR)
        # Highlight for the row selected in a side panel: neutral grey, none of the rhyme
        # tints, and drawn underneath them so the coloured rhyme words stay visible.
        t.tag_configure("focus", background=FOCUS_COLOR)
        t.tag_lower("focus")
        t.tag_raise("spelling")
        t.tag_raise("grammar")
        t.tag_raise("sel")

    def _bind_keys(self) -> None:
        mod = os_support.MOD
        self.root.bind_all(f"<{mod}-n>", lambda e: self.new_file())
        self.root.bind_all(f"<{mod}-o>", lambda e: self.open_file())
        self.root.bind_all(f"<{mod}-s>", lambda e: self.save_file())
        self.root.bind_all(f"<{mod}-S>", lambda e: self.save_file_as())
        self.root.bind_all("<F8>", lambda e: self.goto_issue(+1))
        self.root.bind_all("<Shift-F8>", lambda e: self.goto_issue(-1))
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<KeyRelease>", lambda e: self._update_status())
        self.text.bind("<ButtonRelease-1>", lambda e: self._update_status())
        self.text.bind("<Button-1>", lambda e: self.clear_focus(), add="+")
        self.text.bind("<Escape>", lambda e: self.clear_focus())
        for tree in (self.rhyme_tree, self.issue_tree):
            self._bind_deselect(tree)
            Tooltip(tree)
        self._paned.bind("<Configure>", self._initial_sash, add="+")
        self.text.bind("<Configure>", lambda e: self._redraw_gutter())
        for seq in os_support.CONTEXT_BUTTONS:
            self.text.bind(seq, self._on_context_menu)
        for seq in os_support.ZOOM_WHEEL_EVENTS:
            self.root.bind_all(seq, self._on_zoom_wheel)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def _edit(self, event: str) -> None:
        self.text.event_generate(event)

    def _on_zoom_wheel(self, event) -> str:
        self.zoom(os_support.wheel_direction(event))
        return "break"  # don't also scroll the text

    def zoom(self, step: int) -> None:
        size = max(MIN_SIZE, min(MAX_SIZE, self.editor_font.cget("size") + step))
        self.editor_font.configure(size=size)
        # Scale Tk's named fonts (used by ttk widgets, labels, menus) by the same factor.
        # Their sizes may be negative (pixels); multiplying keeps the sign.
        factor = size / EDITOR_SIZE
        for name, base in self._ui_font_sizes.items():
            scaled = round(base * factor)
            tkfont.nametofont(name).configure(size=scaled if abs(scaled) >= 6 else (6 if base > 0 else -6))
        self._apply_ui_scale()
        gutter_size = max(MIN_SIZE - 1, size + GUTTER_SIZE_OFFSET)
        self.gutter_font.configure(size=gutter_size)
        self.gutter_bold.configure(size=gutter_size)
        self.gutter.configure(width=self._gutter_x(13.5))
        self._redraw_gutter()

    def _apply_ui_scale(self) -> None:
        # Pixel sizes that don't follow the font by themselves: tree rows, columns, pane dividers.
        linespace = tkfont.nametofont("TkDefaultFont").metrics("linespace")
        self.style.configure("Treeview", rowheight=round(linespace * 1.35))
        # The default divider is ~5 px and hard to grab; keep it about two-thirds of a text line.
        self.style.configure("Sash", sashthickness=max(SASH_MIN, round(linespace * 0.65)))
        self._fit_columns()

    def _fit_columns(self) -> None:
        # Fixed columns are sized to their content (minwidth stops ttk from squeezing them);
        # the remaining column stretches to fill the panel.
        font = tkfont.nametofont("TkDefaultFont")
        pad = font.measure("00")
        tree = self.rhyme_tree
        labels = [self.tr("panel.lines")] + [tree.item(i, "text") for i in tree.get_children()]
        children = [tree.item(c, "text") for i in tree.get_children() for c in tree.get_children(i)]
        indent = font.metrics("linespace") + pad  # expander icon of top-level rows
        width = max([font.measure(t) + indent for t in labels] + [font.measure(t) + 2 * indent for t in children]) + pad
        tree.column("#0", width=width, minwidth=width, stretch=False)
        tree.column("words", minwidth=font.measure(self.tr("panel.words")) + pad)
        line_width = max(font.measure("000"), font.measure(self.tr("panel.line"))) + pad
        self.issue_tree.column("line", width=line_width, minwidth=line_width, stretch=False)

    def _initial_sash(self, event) -> None:
        # Once the window has its real size, give the side panels room for their columns.
        if getattr(self, "_sash_placed", False) or event.width < 200:
            return
        self._sash_placed = True
        right = max(RIGHT_PANE_MIN, round(event.width * RIGHT_PANE_SHARE))
        self._paned.sashpos(0, max(event.width // 2, event.width - right))

    def _gutter_x(self, chars: float) -> int:
        """Gutter positions are in monospace character widths so they scale with the font."""
        return round(self.gutter_font.measure("0") * chars)

    # ------------------------------------------------------------ analysis

    def _on_modified(self, _event=None) -> None:
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        if not self.dirty:
            self.dirty = True
            self._update_title()
        self._schedule_analysis(DEBOUNCE_MS)

    def _schedule_analysis(self, delay: int) -> None:
        if self._pending:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(delay, self._start_analysis)

    def _start_analysis(self) -> None:
        self._pending = None
        self._version += 1
        version, text, analyzer = self._version, self.text.get("1.0", "end-1c"), self.analyzer
        # missing_data is computed on the worker too: it may touch dictionaries still loading.
        future = self._executor.submit(lambda: (analyzer.analyze(text), analyzer.missing_data()))
        future.add_done_callback(lambda f: self._on_analysis_done(version, f))

    def _on_analysis_done(self, version: int, future) -> None:
        # Runs on the worker thread: hand over through the queue, never touch Tk here.
        if not future.cancelled() and future.exception() is None:
            report, missing = future.result()
            self._results.put((version, report, missing))

    def _poll_results(self) -> None:
        latest = None
        try:
            while True:
                latest = self._results.get_nowait()
        except queue.Empty:
            pass
        if latest and latest[0] == self._version:  # drop results for outdated text
            self.missing = latest[2]
            self._apply_report(latest[1])
            if latest[1].incomplete:
                self._schedule_analysis(0)  # fetch the spelling suggestions skipped for speed
        self.root.after(POLL_MS, self._poll_results)

    def _apply_report(self, report: Report) -> None:
        self.report = report
        t = self.text
        for tag in ["spelling", "grammar", "focus"] + [f"rhyme{i}" for i in range(len(RHYME_COLORS))]:
            t.tag_remove(tag, "1.0", tk.END)

        for line in report.lines:
            if line.rhymes_with and line.rhyme_group is not None and line.end_word_span:
                start, end = line.end_word_span
                tag = f"rhyme{line.rhyme_group % len(RHYME_COLORS)}"
                t.tag_add(tag, f"{line.index + 1}.{start}", f"{line.index + 1}.{end}")

        for issue in report.issues:
            t.tag_add(issue.kind.value, *self._issue_range(issue))

        self._fill_rhymes(report)
        self._fill_issues(report)
        self._redraw_gutter()
        self._update_status()

    @staticmethod
    def _issue_range(issue: Issue) -> tuple[str, str]:
        return f"{issue.line + 1}.{issue.start}", f"{issue.line + 1}.{issue.end}"

    # --------------------------------------------------------------- panels

    def _fill_rhymes(self, report: Report) -> None:
        tree = self.rhyme_tree
        open_state = {iid: tree.item(iid, "open") for iid in tree.get_children()}
        tree.delete(*tree.get_children())
        for st in report.stanzas:
            first, last = st.lines[0] + 1, st.lines[-1] + 1
            iid = f"s{st.index}"
            tree.insert("", tk.END, iid=iid, text=self.tr("rhyme.stanza", n=st.index + 1, scheme=st.scheme),
                        values=(self.tr("rhyme.stanza_lines", first=first, last=last),),
                        open=open_state.get(iid, True))
            if not st.pairs:
                tree.insert(iid, tk.END, text=self.tr("rhyme.none"), values=("",))
            for p in st.pairs:
                tree.insert(iid, tk.END, iid=f"p{p.first}_{p.second}",
                            text=self.tr("rhyme.pair", a=p.first + 1, b=p.second + 1),
                            values=(f"{p.first_word} / {p.second_word}",))
        self._fit_columns()

    def _fill_issues(self, report: Report) -> None:
        tree = self.issue_tree
        tree.delete(*tree.get_children())
        for n, issue in enumerate(report.issues):
            msg = issue.message
            if issue.suggestions:
                msg += "  → " + ", ".join(issue.suggestions[:3])
            tree.insert("", tk.END, iid=str(n), values=(issue.line + 1, msg), tags=(issue.kind.value,))

    def _on_rhyme_select(self, _event=None) -> None:
        sel = self.rhyme_tree.selection()
        if not sel or not self.report:
            self._clear_focus_from(self.rhyme_tree)
            return
        iid = sel[0]
        if iid.startswith("p"):
            a, b = (int(x) for x in iid[1:].split("_"))
            self._highlight_lines([a, b])
        elif iid.startswith("s"):
            st = self.report.stanzas[int(iid[1:])]
            self._highlight_lines(st.lines)
        else:
            return
        self._take_focus(self.rhyme_tree)

    def _highlight_lines(self, lines: list[int]) -> None:
        self.text.tag_remove("focus", "1.0", tk.END)
        for ln in lines:
            # "+1c" covers the newline, so the band spans the full editor width.
            self.text.tag_add("focus", f"{ln + 1}.0", f"{ln + 1}.end+1c")
        self.text.see(f"{lines[0] + 1}.0")
        self.text.mark_set(tk.INSERT, f"{lines[0] + 1}.0")
        self._update_status()

    # The editor highlight belongs to whichever panel selected it last; deselecting
    # there (or clicking into the text, or Esc) removes it.

    def _take_focus(self, tree: ttk.Treeview) -> None:
        self._focus_owner = tree
        for other in (self.rhyme_tree, self.issue_tree):
            if other is not tree and other.selection():
                other.selection_set(())

    def _clear_focus_from(self, tree: ttk.Treeview) -> None:
        # Selection events arrive asynchronously; only the current owner may clear.
        if getattr(self, "_focus_owner", None) is tree:
            self.clear_focus()

    def clear_focus(self) -> None:
        self._focus_owner = None
        self.text.tag_remove("focus", "1.0", tk.END)
        for tree in (self.rhyme_tree, self.issue_tree):
            if tree.selection():
                tree.selection_set(())

    def _bind_deselect(self, tree: ttk.Treeview) -> None:
        def on_click(event) -> str | None:
            if "indicator" in tree.identify_element(event.x, event.y):
                return None  # expand/collapse arrow keeps its normal behaviour
            row = tree.identify_row(event.y)
            if tree.identify_region(event.x, event.y) == "heading":
                return None
            if not row or row in tree.selection():
                # Clicking the selected row again, or empty space, deselects.
                tree.selection_set(())
                return "break"
            return None

        tree.bind("<Button-1>", on_click)
        tree.bind("<Escape>", lambda e: self.clear_focus())

    def _selected_issue(self) -> Issue | None:
        sel = self.issue_tree.selection()
        if not sel or not self.report:
            return None
        n = int(sel[0])
        return self.report.issues[n] if n < len(self.report.issues) else None

    def _on_issue_select(self, _event=None) -> None:
        issue = self._selected_issue()
        if issue:
            start, end = self._issue_range(issue)
            self.text.tag_remove("focus", "1.0", tk.END)
            self.text.tag_add("focus", start, end)
            self.text.see(start)
            self._take_focus(self.issue_tree)
        else:
            self._clear_focus_from(self.issue_tree)

    def _on_issue_activate(self, event=None) -> None:
        # The first click of a double-click on an already selected row deselects it
        # (toggle), so re-select the row under the pointer.
        row = self.issue_tree.identify_row(event.y) if event else ""
        if row:
            self.issue_tree.selection_set(row)
            self._on_issue_select()
        issue = self._selected_issue()
        if issue:
            start, _ = self._issue_range(issue)
            self.text.mark_set(tk.INSERT, start)
            self.text.focus_set()
            bbox = self.text.bbox(start)
            if bbox:
                self._show_issue_menu(issue, self.text.winfo_rootx() + bbox[0], self.text.winfo_rooty() + bbox[1] + bbox[3])

    def goto_issue(self, step: int) -> None:
        if not self.report or not self.report.issues:
            return
        cur_line, cur_col = (int(x) for x in self.text.index(tk.INSERT).split("."))
        pos = (cur_line - 1, cur_col)
        issues = self.report.issues
        if step > 0:
            idx = next((n for n, i in enumerate(issues) if (i.line, i.start) > pos), 0)
        else:
            idx = next((n for n in range(len(issues) - 1, -1, -1) if (issues[n].line, issues[n].start) < pos), len(issues) - 1)
        self.issue_tree.selection_set(str(idx))
        self.issue_tree.see(str(idx))
        start, _ = self._issue_range(issues[idx])
        self.text.mark_set(tk.INSERT, start)
        self.text.focus_set()

    # --------------------------------------------------------- context menu

    def _issue_at(self, index: str) -> Issue | None:
        if not self.report:
            return None
        line, col = (int(x) for x in self.text.index(index).split("."))
        for issue in self.report.issues:
            if issue.line == line - 1 and issue.start <= col < issue.end:
                return issue
        return None

    def _on_context_menu(self, event) -> str:
        index = f"@{event.x},{event.y}"
        issue = self._issue_at(index)
        if issue is None:
            menu = self.menu
            menu.delete(0, tk.END)
            for key, ev in (("menu.cut", "<<Cut>>"), ("menu.copy", "<<Copy>>"), ("menu.paste", "<<Paste>>")):
                menu.add_command(label=self.tr(key), command=lambda ev=ev: self._edit(ev))
            menu.tk_popup(event.x_root, event.y_root)
        else:
            self._show_issue_menu(issue, event.x_root, event.y_root)
        return "break"

    def _show_issue_menu(self, issue: Issue, x: int, y: int) -> None:
        menu = self.menu
        menu.delete(0, tk.END)
        menu.add_command(label=issue.message, state=tk.DISABLED)
        menu.add_separator()
        for s in issue.suggestions:
            menu.add_command(label=s if s.strip() else repr(s), command=lambda s=s: self._replace(issue, s))
        if not issue.suggestions:
            menu.add_command(label=self.tr("ctx.no_suggestions"), state=tk.DISABLED)
        if issue.kind is IssueKind.SPELLING:
            word = self.report.lines[issue.line].text[issue.start:issue.end] if self.report else ""
            menu.add_separator()
            menu.add_command(label=self.tr("ctx.add_word", word=word), command=lambda: self._learn(word, permanent=True))
            menu.add_command(label=self.tr("ctx.ignore"), command=lambda: self._learn(word, permanent=False))
        menu.tk_popup(x, y)

    def _replace(self, issue: Issue, replacement: str) -> None:
        start, end = self._issue_range(issue)
        expected = self.report.lines[issue.line].text[issue.start:issue.end] if self.report else None
        if self.text.get(start, end) != expected:
            return  # text changed since the analysis; ignore stale action
        self.text.edit_separator()
        self.text.delete(start, end)
        self.text.insert(start, replacement)
        self.text.edit_separator()

    def _learn(self, word: str, permanent: bool) -> None:
        if permanent:
            self.analyzer.spelling.add_to_dictionary(word)
        else:
            self.analyzer.spelling.ignore(word)
        self._schedule_analysis(0)

    # --------------------------------------------------------------- gutter

    def _redraw_gutter(self) -> None:
        g = self.gutter
        g.delete("all")
        width = int(g.cget("width"))
        g.create_line(width - 1, 0, width - 1, g.winfo_height(), fill="#ddd")
        lines = self.report.lines if self.report else []
        index = self.text.index("@0,0")
        while True:
            info = self.text.dlineinfo(index)
            if info is None:
                break
            ln = int(index.split(".")[0])
            y = info[1] + info[4]  # baseline
            g.create_text(self._gutter_x(3.7), y, anchor="se", text=str(ln), fill="#aaa", font=self.gutter_font)
            li = lines[ln - 1] if ln - 1 < len(lines) else None
            if li and not li.is_blank:
                g.create_text(self._gutter_x(8.9), y, anchor="se", text=li.syllables_text, fill="#444", font=self.gutter_font)
                if li.rhyme_label:
                    color = RHYME_COLORS[li.rhyme_group % len(RHYME_COLORS)][1] if li.rhymes_with else "#999"
                    g.create_text(self._gutter_x(10), y, anchor="sw", text=li.rhyme_label, fill=color, font=self.gutter_bold)
            nxt = self.text.index(f"{index}+1line linestart")
            if nxt == index:
                break
            index = nxt

    # --------------------------------------------------------------- status

    def _update_status(self) -> None:
        r = self.report
        if r is None:
            self.status.configure(text=self.tr("status.loading"))
            return
        line_no = int(self.text.index(tk.INSERT).split(".")[0]) - 1
        parts = []
        if 0 <= line_no < len(r.lines) and not r.lines[line_no].is_blank:
            li = r.lines[line_no]
            parts.append(self.tr("status.line", n=line_no + 1, syllables=li.syllables_text))
            if li.rhymes_with:
                parts.append(self.tr("status.rhymes_with", lines=", ".join(str(x + 1) for x in li.rhymes_with)))
            elif li.end_word:
                parts.append(self.tr("status.no_rhyme", word=li.end_word))
        spelling = sum(i.kind is IssueKind.SPELLING for i in r.issues)
        grammar = len(r.issues) - spelling
        parts.append(self.tr("status.totals", stanzas=len(r.stanzas), lines=sum(not l.is_blank for l in r.lines)))
        parts.append(self.tr("status.issues", spelling=spelling, grammar=grammar))
        self.status.configure(text="   ·   ".join(parts))
        self.warning.configure(
            text="⚠ " + "; ".join(self.missing) + " — " + self.tr("install_hint") if self.missing else ""
        )

    def _update_title(self) -> None:
        name = self.path.name if self.path else self.tr("title.untitled")
        self.root.title(f"{'*' if self.dirty else ''}{name} — Poet")

    # ---------------------------------------------------------------- files

    def _filetypes(self) -> list[tuple[str, str]]:
        return [(self.tr("dlg.text_files"), "*.txt"), (self.tr("dlg.all_files"), "*.*")]

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel("Poet", self.tr("dlg.save_changes"))
        if answer is None:
            return False
        return self.save_file() if answer else True

    def _set_text(self, content: str, path: Path | None) -> None:
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.mark_set(tk.INSERT, "1.0")
        self.path, self.dirty = path, False
        self.text.edit_modified(False)
        self._update_title()
        self._schedule_analysis(0)

    def new_file(self) -> None:
        if self._confirm_discard():
            self._set_text("", None)

    def load_sample(self) -> None:
        if self._confirm_discard():
            self._set_text(SAMPLES.get(self.analyzer.code, ""), None)

    def open_file(self, path: str | Path | None = None) -> None:
        if not self._confirm_discard():
            return
        path = path or filedialog.askopenfilename(filetypes=self._filetypes())
        if path:
            try:
                content = Path(path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                messagebox.showerror("Poet", self.tr("dlg.open_failed", error=e))
                return
            self._set_text(content, Path(path))

    def save_file(self) -> bool:
        if self.path is None:
            return self.save_file_as()
        try:
            self.path.write_text(self.text.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Poet", self.tr("dlg.save_failed", error=e))
            return False
        self.dirty = False
        self._update_title()
        return True

    def save_file_as(self) -> bool:
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=self._filetypes())
        if not path:
            return False
        self.path = Path(path)
        return self.save_file()

    def quit(self) -> None:
        if self._confirm_discard():
            self._executor.shutdown(wait=False, cancel_futures=True)
            self.root.destroy()


def run(path: str | None = None) -> None:
    root = tk.Tk()
    settings = Settings.load()

    def save_settings(poem_language: str, ui_language: str) -> None:
        settings.poem_language, settings.ui_language = poem_language, ui_language
        settings.save()

    app = PoetApp(root, settings.poem_language, settings.ui_language,
                  dictionary_path=os_support.user_dictionary_path, on_settings_changed=save_settings)
    if path:
        app.open_file(path)
    else:
        app._set_text(SAMPLES.get(settings.poem_language, ""), None)
    root.mainloop()
