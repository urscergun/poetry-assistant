"""Hover tooltip showing a Treeview cell's full text when the column cuts it off."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

DELAY_MS = 400


class Tooltip:
    def __init__(self, tree: ttk.Treeview):
        self.tree = tree
        self._cell: tuple[str, str] | None = None
        self._after: str | None = None
        self._tip: tk.Toplevel | None = None
        tree.bind("<Motion>", self._on_motion, add="+")
        tree.bind("<Leave>", lambda e: self._hide(), add="+")
        tree.bind("<ButtonPress>", lambda e: self._hide(), add="+")
        tree.bind("<MouseWheel>", lambda e: self._hide(), add="+")

    def _on_motion(self, event) -> None:
        row, column = self.tree.identify_row(event.y), self.tree.identify_column(event.x)
        cell = (row, column) if row else None
        if cell == self._cell:
            return
        self._hide()
        self._cell = cell
        if cell:
            self._after = self.tree.after(DELAY_MS, lambda: self._show(event.x_root, event.y_root))

    def _cell_text(self, row: str, column: str) -> str:
        if column == "#0":
            return self.tree.item(row, "text")
        index = int(column[1:]) - 1
        values = self.tree.item(row, "values")
        return str(values[index]) if 0 <= index < len(values) else ""

    def _is_cut_off(self, row: str, column: str, text: str) -> bool:
        bbox = self.tree.bbox(row, column)
        if not bbox:
            return False
        font = tkfont.nametofont("TkDefaultFont")
        # Tree-column text is indented by its depth; leave room for that and cell padding.
        depth = 0
        parent = self.tree.parent(row)
        while parent:
            depth, parent = depth + 1, self.tree.parent(parent)
        indent = (depth + 1) * font.metrics("linespace") if column == "#0" else 0
        return font.measure(text) + indent + font.measure("0") > bbox[2]

    def _show(self, x: int, y: int) -> None:
        self._after = None
        if not self._cell:
            return
        row, column = self._cell
        if not self.tree.exists(row):
            return
        text = self._cell_text(row, column)
        if not text or not self._is_cut_off(row, column, text):
            return
        tip = tk.Toplevel(self.tree)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x + 12}+{y + 16}")
        tk.Label(tip, text=text, font="TkDefaultFont", background="#ffffe8", foreground="#222",
                 relief="solid", borderwidth=1, padx=6, pady=2).pack()
        self._tip = tip

    def _hide(self) -> None:
        self._cell = None
        if self._after:
            self.tree.after_cancel(self._after)
            self._after = None
        if self._tip:
            self._tip.destroy()
            self._tip = None
