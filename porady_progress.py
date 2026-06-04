# -*- coding: utf-8 -*-

import calendar
import tkinter as tk
from datetime import datetime


class ProgressMixin:

    def show_lotus_calendar_today(self):
        self.lotus_calendar_month = datetime.now().date().replace(day=1)
        self.draw_lotus_calendar()


    def shift_lotus_calendar_month(self, delta):
        current = getattr(self, "lotus_calendar_month", None) or datetime.now().date().replace(day=1)
        month = current.month + delta
        year = current.year
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        self.lotus_calendar_month = current.replace(year=year, month=month, day=1)
        self.draw_lotus_calendar()


    def scroll_lotus_calendar(self, event):
        if hasattr(self, "lotus_calendar_canvas"):
            canvas = self.lotus_calendar_canvas
            current_tags = canvas.gettags("current")
            day_tag = next((tag for tag in current_tags if tag.startswith("lotus_day_")), "")
            if day_tag:
                self.scroll_lotus_calendar_day(day_tag.replace("lotus_day_", ""), event.delta)
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"


    def scroll_lotus_calendar_day(self, day_key, delta):
        offsets = getattr(self, "lotus_calendar_day_offsets", {})
        offsets[day_key] = max(0, offsets.get(day_key, 0) + (-1 if delta > 0 else 1))
        self.lotus_calendar_day_offsets = offsets
        self.draw_lotus_calendar()


    def shorten_lotus_text(self, text, cell_width):
        max_chars = max(10, int((cell_width - 28) / 6.2))
        text = " ".join((text or "").split())
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 1].rstrip() + "…"


    def open_lotus_calendar_item(self, item_id):
        if hasattr(self, "show_open_only") and self.show_open_only.get():
            self.show_open_only.set(False)
            self.load_meeting_details()

        if hasattr(self, "detail_tabs") and hasattr(self, "meeting_tab"):
            self.detail_tabs.select(self.meeting_tab)

        self.select_agenda_item(item_id)
        row = next(
            (
                agenda_row
                for agenda_row in getattr(self, "all_agenda_data", [])
                if agenda_row.get("type") == "item" and agenda_row.get("id") == item_id
            ),
            None,
        )
        if row:
            self.active_point_id = row.get("point_id")
            if self.can_edit():
                self.start_edit_item(row)


    def draw_lotus_calendar(self):
        if not hasattr(self, "lotus_calendar_canvas"):
            return

        canvas = self.lotus_calendar_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        today = datetime.now().date()
        month_anchor = getattr(self, "lotus_calendar_month", None) or today.replace(day=1)
        self.lotus_calendar_month = month_anchor

        if hasattr(self, "lbl_lotus_calendar_month"):
            self.lbl_lotus_calendar_month.config(text=f"{self.CZECH_MONTHS[month_anchor.month]} {month_anchor.year}")

        items_by_date = {}
        point_titles = {
            row.get("id"): row.get("title", "")
            for row in getattr(self, "all_agenda_data", [])
            if row.get("type") == "point"
        }
        for row in getattr(self, "all_agenda_data", []):
            if row.get("type") != "item":
                continue
            parsed_due = self.parse_due_date(row.get("due_date", ""))
            if not parsed_due:
                continue
            items_by_date.setdefault(parsed_due, []).append(
                {
                    "id": row.get("id"),
                    "description": row.get("description", ""),
                    "point": point_titles.get(row.get("point_id"), ""),
                    "done": row.get("is_resolved") == 1,
                }
            )

        top = 46
        left = 10
        right = 10
        gap = 4
        header_height = 28
        rows = calendar.monthcalendar(month_anchor.year, month_anchor.month)
        while len(rows) < 6:
            rows.append([0] * 7)

        visible_width = max(width - 18, 1)
        cell_width = max((visible_width - left - right - gap * 6) / 7, 64)
        cell_height = 126
        content_height = int(top + header_height + 6 * cell_height + 6 * gap + 14)
        day_offsets = getattr(self, "lotus_calendar_day_offsets", {})

        canvas.create_rectangle(0, 0, width, top - 10, fill="#233b6e", outline="")
        canvas.create_text(
            16,
            18,
            text=f"LOTUS kalendář | {self.CZECH_MONTHS[month_anchor.month]} {month_anchor.year}",
            anchor="w",
            fill="white",
            font=(self.FONT, 12, "bold"),
        )
        canvas.create_text(
            width - 16,
            18,
            text="termíny položek vybrané porady",
            anchor="e",
            fill="#dbeafe",
            font=(self.FONT, 9),
        )

        weekdays = ("Po", "Út", "St", "Čt", "Pá", "So", "Ne")
        for column, weekday in enumerate(weekdays):
            x = left + column * (cell_width + gap)
            y = top
            is_weekend = column >= 5
            canvas.create_rectangle(
                x,
                y,
                x + cell_width,
                y + header_height,
                fill="#facc15" if not is_weekend else "#94a3b8",
                outline="#64748b",
            )
            canvas.create_text(
                x + 8,
                y + header_height / 2,
                text=weekday,
                anchor="w",
                fill="#111827",
                font=(self.FONT, 9, "bold"),
            )

        for row_index, week in enumerate(rows):
            for column, day in enumerate(week):
                x = left + column * (cell_width + gap)
                y = top + header_height + gap + row_index * (cell_height + gap)
                is_weekend = column >= 5
                bg = "#f8fafc" if not is_weekend else "#e2e8f0"
                outline = "#93a4bb"
                if day:
                    date_value = datetime(month_anchor.year, month_anchor.month, day).date()
                    day_items = items_by_date.get(date_value, [])
                    day_key = date_value.isoformat().replace("-", "_")
                    day_tag = f"lotus_day_{day_key}"
                    if day_items:
                        bg = "#fff7ed"
                    if date_value == today:
                        bg = "#dbeafe"
                        outline = self.COLORS["primary"]
                else:
                    date_value = None
                    day_items = []
                    day_key = ""
                    day_tag = ""
                    bg = "#d8dee8"

                cell_tags = (day_tag,) if day_tag else ()
                canvas.create_rectangle(x, y, x + cell_width, y + cell_height, fill=bg, outline=outline, tags=cell_tags)
                if not day:
                    continue

                canvas.create_text(
                    x + 7,
                    y + 8,
                    text=str(day),
                    anchor="nw",
                    fill=self.COLORS["text"],
                    font=(self.FONT, 10, "bold"),
                    tags=cell_tags,
                )

                item_top = y + 26
                max_visible = max(1, int((cell_height - 42) // 20))
                max_offset = max(0, len(day_items) - max_visible)
                offset = min(day_offsets.get(day_key, 0), max_offset)
                if offset != day_offsets.get(day_key, 0):
                    day_offsets[day_key] = offset
                    self.lotus_calendar_day_offsets = day_offsets

                if len(day_items) > max_visible:
                    up_tag = f"{day_tag}_up"
                    down_tag = f"{day_tag}_down"
                    canvas.create_rectangle(
                        x + cell_width - 18,
                        y + 6,
                        x + cell_width - 5,
                        y + 22,
                        fill="#f8fafc",
                        outline="#cbd5e1",
                        tags=(day_tag, up_tag),
                    )
                    canvas.create_text(
                        x + cell_width - 11,
                        y + 14,
                        text="^",
                        anchor="center",
                        fill=self.COLORS["muted"] if offset == 0 else self.COLORS["primary"],
                        font=(self.FONT, 8, "bold"),
                        tags=(day_tag, up_tag),
                    )
                    canvas.create_rectangle(
                        x + cell_width - 18,
                        y + cell_height - 22,
                        x + cell_width - 5,
                        y + cell_height - 6,
                        fill="#f8fafc",
                        outline="#cbd5e1",
                        tags=(day_tag, down_tag),
                    )
                    canvas.create_text(
                        x + cell_width - 11,
                        y + cell_height - 14,
                        text="v",
                        anchor="center",
                        fill=self.COLORS["muted"] if offset >= max_offset else self.COLORS["primary"],
                        font=(self.FONT, 8, "bold"),
                        tags=(day_tag, down_tag),
                    )
                    canvas.tag_bind(up_tag, "<Button-1>", lambda event, selected_day=day_key: self.scroll_lotus_calendar_day(selected_day, 120))
                    canvas.tag_bind(down_tag, "<Button-1>", lambda event, selected_day=day_key: self.scroll_lotus_calendar_day(selected_day, -120))
                    canvas.tag_bind(up_tag, "<Enter>", lambda event: canvas.config(cursor="hand2"))
                    canvas.tag_bind(down_tag, "<Enter>", lambda event: canvas.config(cursor="hand2"))

                for index, item in enumerate(day_items[offset:offset + max_visible]):
                    item_y = item_top + index * 20
                    overdue = date_value < today and not item["done"]
                    item_bg = "#dcfce7" if item["done"] else ("#fee2e2" if overdue else "#e0f2fe")
                    item_fg = "#166534" if item["done"] else ("#991b1b" if overdue else "#075985")
                    item_tag = f"lotus_item_{item['id']}"
                    canvas.create_rectangle(
                        x + 5,
                        item_y,
                        x + cell_width - 5,
                        item_y + 16,
                        fill=item_bg,
                        outline="",
                        tags=(item_tag, "lotus_item_link", day_tag),
                    )
                    prefix = "✓" if item["done"] else "○"
                    detail = item["description"] or item["point"] or "Položka"
                    canvas.create_text(
                        x + 9,
                        item_y + 8,
                        text=self.shorten_lotus_text(f"{prefix} {detail}", cell_width),
                        anchor="w",
                        fill=item_fg,
                        font=(self.FONT, 8, "bold" if overdue else "normal"),
                        tags=(item_tag, "lotus_item_link", day_tag),
                    )
                    canvas.tag_bind(item_tag, "<Button-1>", lambda event, selected_id=item["id"]: self.open_lotus_calendar_item(selected_id))
                    canvas.tag_bind(item_tag, "<Enter>", lambda event: canvas.config(cursor="hand2"))
                    canvas.tag_bind(item_tag, "<Leave>", lambda event: canvas.config(cursor=""))

                hidden_count = max(0, len(day_items) - offset - max_visible)
                if hidden_count > 0:
                    canvas.create_text(
                        x + 8,
                        y + cell_height - 13,
                        text=f"+ {hidden_count} další",
                        anchor="w",
                        fill=self.COLORS["muted"],
                        font=(self.FONT, 8, "bold"),
                        tags=(day_tag,),
                    )
                canvas.tag_bind(day_tag, "<Enter>", lambda event: canvas.config(cursor="sb_v_double_arrow"))
                canvas.tag_bind(day_tag, "<Leave>", lambda event: canvas.config(cursor=""))

        if not items_by_date:
            canvas.create_text(
                width / 2,
                content_height / 2,
                text="Vybraná porada zatím nemá položky s termínem.",
                anchor="center",
                fill=self.COLORS["muted"],
                font=(self.FONT, 11, "bold"),
            )

        canvas.configure(scrollregion=(0, 0, int(left + 7 * cell_width + 6 * gap + right), content_height))

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

