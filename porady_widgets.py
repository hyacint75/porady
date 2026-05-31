# -*- coding: utf-8 -*-

import tkinter as tk


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
