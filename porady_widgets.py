# -*- coding: utf-8 -*-

import tkinter as tk
from datetime import datetime


def bind_mousewheel_to_canvas(canvas, *containers):
    def on_mousewheel(event):
        if event.num == 4:
            units = -1
        elif event.num == 5:
            units = 1
        else:
            units = int(-1 * (event.delta / 120)) if event.delta else 0
        if units:
            canvas.yview_scroll(units, "units")
            return "break"
        return None

    def bind_widget(widget):
        widget.bind("<MouseWheel>", on_mousewheel, add="+")
        widget.bind("<Button-4>", on_mousewheel, add="+")
        widget.bind("<Button-5>", on_mousewheel, add="+")
        for child in widget.winfo_children():
            bind_widget(child)

    bind_widget(canvas)
    for container in containers:
        bind_widget(container)


def _treeview_sort_value(value, value_type):
    text = str(value or "").strip()
    if not text or text == "-":
        return None

    if value_type == "date":
        for date_format in ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return (0, datetime.strptime(text, date_format))
            except ValueError:
                continue
        return (1, text.casefold())

    if value_type == "number":
        try:
            return (0, float(text.replace(" ", "").replace(",", ".")))
        except ValueError:
            return (1, text.casefold())

    return (0, text.casefold())


def sort_treeview(tree, column=None, descending=None):
    if column is None:
        column = getattr(tree, "_sort_column", None)
        if column is None:
            return

    current_column = getattr(tree, "_sort_column", None)
    current_descending = getattr(tree, "_sort_descending", False)
    if descending is None:
        descending = not current_descending if column == current_column else False

    value_type = getattr(tree, "_sort_column_types", {}).get(column, "text")
    populated = []
    empty = []
    for item_id in tree.get_children(""):
        value = _treeview_sort_value(tree.set(item_id, column), value_type)
        if value is None:
            empty.append(item_id)
        else:
            populated.append((value, item_id))

    populated.sort(key=lambda item: item[0], reverse=descending)
    ordered_items = [item_id for _, item_id in populated] + empty
    for index, item_id in enumerate(ordered_items):
        tree.move(item_id, "", index)

    tree._sort_column = column
    tree._sort_descending = descending
    for column_id, title in getattr(tree, "_sort_titles", {}).items():
        marker = " ▼" if column_id == column and descending else " ▲" if column_id == column else ""
        tree.heading(column_id, text=title + marker)


def configure_treeview_sorting(tree, column_types=None):
    tree._sort_column_types = column_types or {}
    tree._sort_titles = {
        column: tree.heading(column, "text")
        for column in tree["columns"]
    }
    tree._sort_column = None
    tree._sort_descending = False
    for column in tree["columns"]:
        tree.heading(
            column,
            command=lambda selected_column=column: sort_treeview(tree, selected_column),
        )


def reapply_treeview_sorting(tree):
    column = getattr(tree, "_sort_column", None)
    if column is not None:
        sort_treeview(
            tree,
            column=column,
            descending=getattr(tree, "_sort_descending", False),
        )


class RoundedFrame(tk.Canvas):
    def __init__(
        self,
        parent,
        radius=14,
        background="#ffffff",
        border="#d7dee8",
        border_width=1,
        padding=0,
        **kwargs,
    ):
        super().__init__(
            parent,
            bg=kwargs.pop("bg", parent.cget("bg")),
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.radius = radius
        self.panel_bg = background
        self.border = border
        self.border_width = border_width
        self.padding = padding
        self.inner = tk.Frame(self, bg=background)
        self._window_id = self.create_window(
            padding,
            padding,
            anchor="nw",
            window=self.inner,
        )
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event=None):
        width = max(self.winfo_width(), 2)
        height = max(self.winfo_height(), 2)
        self.delete("rounded_bg")
        self._draw_rounded_rect(
            self.border_width,
            self.border_width,
            width - self.border_width,
            height - self.border_width,
            self.radius,
            fill=self.panel_bg,
            outline=self.border,
            width=self.border_width,
            tags="rounded_bg",
        )
        inner_width = max(width - (self.padding * 2), 1)
        inner_height = max(height - (self.padding * 2), 1)
        self.coords(self._window_id, self.padding, self.padding)
        self.itemconfigure(self._window_id, width=inner_width, height=inner_height)
        self.tag_lower("rounded_bg")

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        radius = min(radius, max((x2 - x1) / 2, 0), max((y2 - y1) / 2, 0))
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=16, **kwargs)
