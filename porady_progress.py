# -*- coding: utf-8 -*-

import tkinter as tk


class ProgressMixin:

    def draw_progress_overview(self):
        if not hasattr(self, "progress_canvas"):
            return

        canvas = self.progress_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)

        if not self.progress_data:
            if int(canvas.cget("height")) != 118:
                canvas.configure(height=118)
            canvas.create_text(
                16,
                58,
                text="Zatím nejsou vytvořené žádné body programu.",
                anchor="w",
                fill=self.COLORS["muted"],
                font=(self.FONT, 10),
            )
            return

        row_height = 24
        top = 12
        desired_height = top + 34 + len(self.progress_data) * row_height + 12
        if int(canvas.cget("height")) != desired_height:
            canvas.configure(height=desired_height)

        label_width = min(170, max(105, width // 4))
        value_width = 96
        value_gap = 24
        bar_left = label_width + 22
        bar_right = max(bar_left + 80, width - value_width - value_gap)
        bar_width = bar_right - bar_left
        value_x = width - 12

        total_done = self.progress_total["done"]
        total_count = self.progress_total["total"]
        total_ratio = total_done / total_count if total_count else 0
        total_percent = round(total_ratio * 100)

        self.draw_progress_row(
            canvas=canvas,
            label="Celkem",
            done=total_done,
            total=total_count,
            percent=total_percent,
            ratio=total_ratio,
            y=top,
            bar_left=bar_left,
            bar_right=bar_right,
            bar_width=bar_width,
            value_x=value_x,
            emphasized=True,
        )

        divider_y = top + row_height
        canvas.create_line(12, divider_y + 2, width - 12, divider_y + 2, fill=self.COLORS["border"])

        visible_rows = self.progress_data
        for index, point in enumerate(self.progress_data):
            y = top + 34 + index * row_height
            total = point["total"]
            done = point["done"]
            ratio = done / total if total else 0
            percent = round(ratio * 100)

            title = point["title"]
            if len(title) > 22:
                title = title[:21] + "…"

            self.draw_progress_row(
                canvas=canvas,
                label=title,
                done=done,
                total=total,
                percent=percent,
                ratio=ratio,
                y=y,
                bar_left=bar_left,
                bar_right=bar_right,
                bar_width=bar_width,
                value_x=value_x,
                emphasized=False,
            )

        hidden_count = len(self.progress_data) - len(visible_rows)
        if hidden_count > 0:
            canvas.create_text(
                12,
                top + 34 + len(visible_rows) * row_height + 7,
                text=f"+ další body: {hidden_count}",
                anchor="w",
                fill=self.COLORS["muted"],
                font=(self.FONT, 9),
            )


    def draw_owner_progress_overview(self):
        if not hasattr(self, "owner_progress_canvas"):
            return

        canvas = self.owner_progress_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)

        if not self.owner_progress_data:
            if int(canvas.cget("height")) != 118:
                canvas.configure(height=118)
            canvas.create_text(
                16,
                58,
                text="Zatím nejsou zadané žádné odpovědnosti.",
                anchor="w",
                fill=self.COLORS["muted"],
                font=(self.FONT, 10),
            )
            return

        row_height = 24
        top = 12
        desired_height = top + len(self.owner_progress_data) * row_height + 12
        if int(canvas.cget("height")) != desired_height:
            canvas.configure(height=desired_height)

        label_width = min(190, max(120, width // 4))
        value_width = 96
        value_gap = 24
        bar_left = label_width + 22
        bar_right = max(bar_left + 80, width - value_width - value_gap)
        bar_width = bar_right - bar_left
        value_x = width - 12

        for index, owner_row in enumerate(self.owner_progress_data):
            y = top + index * row_height
            total = owner_row["total"]
            done = owner_row["done"]
            ratio = done / total if total else 0
            percent = round(ratio * 100)
            label = owner_row["owner"]
            if len(label) > 24:
                label = label[:23] + "…"
            self.draw_progress_row(
                canvas=canvas,
                label=label,
                done=done,
                total=total,
                percent=percent,
                ratio=ratio,
                y=y,
                bar_left=bar_left,
                bar_right=bar_right,
                bar_width=bar_width,
                value_x=value_x,
            )


    def draw_progress_row(
        self,
        canvas,
        label,
        done,
        total,
        percent,
        ratio,
        y,
        bar_left,
        bar_right,
        bar_width,
        value_x,
        emphasized=False,
    ):
        bar_color = self.COLORS["success"] if percent == 100 and total else self.COLORS["warning"]
        if percent == 0:
            bar_color = self.COLORS["muted"]

        font = (self.FONT, 9, "bold") if emphasized else (self.FONT, 9)
        label_color = self.COLORS["text"] if emphasized else self.COLORS["muted"]
        bar_height = 14 if emphasized else 12
        bar_top = y + 3

        canvas.create_text(
            12,
            y + 9,
            text=label,
            anchor="w",
            fill=label_color,
            font=font,
        )
        canvas.create_rectangle(
            bar_left,
            bar_top,
            bar_right,
            bar_top + bar_height,
            fill="#e5eaf1",
            outline="",
        )
        canvas.create_rectangle(
            bar_left,
            bar_top,
            bar_left + int(bar_width * ratio),
            bar_top + bar_height,
            fill=bar_color,
            outline="",
        )
        canvas.create_text(
            value_x,
            y + 9,
            text=f"{done}/{total} ({percent}%)",
            anchor="e",
            fill=self.COLORS["text"] if emphasized else self.COLORS["muted"],
            font=font,
        )

