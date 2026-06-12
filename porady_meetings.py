# -*- coding: utf-8 -*-

import calendar
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk


class MeetingMixin:

    def format_czech_date(self, date_text):
        try:
            return datetime.strptime(date_text, "%Y-%m-%d").strftime("%d.%m.%Y")
        except (TypeError, ValueError):
            return date_text


    def is_planned_meeting(self, date_text):
        parsed_date = self.parse_due_date(date_text)
        return bool(parsed_date and parsed_date > datetime.now().date())


    def parse_czech_date(self, date_text):
        parsed = self.parse_due_date(date_text)
        return datetime.combine(parsed, datetime.min.time()) if parsed else datetime.now()


    def parse_due_date(self, date_text):
        if not date_text or date_text == "Termín":
            return None

        for date_format in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_text.strip(), date_format).date()
            except (TypeError, ValueError):
                continue
        return None


    def refresh_owner_choices(self):
        if not hasattr(self, "entry_new_owner"):
            return

        people = self.get_people_values()
        if people:
            self.entry_new_owner.configure(values=people)
            return

        c = self.conn.cursor()
        c.execute(
            """SELECT DISTINCT owner FROM agenda_items
               WHERE owner IS NOT NULL AND TRIM(owner) <> ''
               ORDER BY owner"""
        )
        owners = [row[0] for row in c.fetchall()]
        self.entry_new_owner.configure(values=owners)


    def refresh_item_description_choices(self):
        if not hasattr(self, "entry_new_item"):
            return

        c = self.conn.cursor()
        c.execute(
            """SELECT description, MAX(agenda_items.id) AS last_used
               FROM agenda_items
               WHERE description IS NOT NULL AND TRIM(description) <> ''
               GROUP BY description
               ORDER BY last_used DESC
               LIMIT 100"""
        )
        descriptions = [row[0] for row in c.fetchall()]
        self.entry_new_item.configure(values=descriptions)


    def refresh_due_date_choices(self):
        if not hasattr(self, "entry_new_due_date"):
            return
        if not isinstance(self.entry_new_due_date, ttk.Combobox):
            return

        today = datetime.now().date()
        future_dates = [(today + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(0, 366)]
        past_dates = [(today + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(-30, 0)]
        dates = future_dates + past_dates
        self.entry_new_due_date.configure(values=dates)


    def get_today_due_date(self):
        return datetime.now().date().strftime("%d.%m.%Y")


    def open_due_date_picker(self, event=None):
        self.ensure_active_agenda_point()
        return self.open_date_picker_for_widget(self.entry_new_due_date)


    def get_date_target_value(self, target):
        if hasattr(target, "get"):
            return target.get()
        return ""


    def set_date_target_value(self, target, value):
        if hasattr(target, "set"):
            target.set(value)
            return
        target.delete(0, tk.END)
        target.insert(0, value)


    def open_date_picker_for_widget(self, widget):
        self.open_date_picker(widget, anchor_widget=widget)
        return "break"


    def open_date_picker_for_variable(self, variable, anchor_widget=None):
        self.open_date_picker(variable, anchor_widget=anchor_widget)
        return "break"


    def open_date_picker(self, target, anchor_widget=None):
        current_text = self.get_date_target_value(target).strip()
        selected_date = self.parse_due_date(current_text) or datetime.now().date()
        month_state = {"year": selected_date.year, "month": selected_date.month}

        picker = tk.Toplevel(self.root)
        picker.title("Vybrat termín")
        picker.resizable(False, False)
        picker.configure(bg=self.COLORS["panel"])
        picker.transient(self.root)
        picker.grab_set()

        body = tk.Frame(picker, bg=self.COLORS["panel"], padx=14, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(body, bg=self.COLORS["panel"])
        header.pack(fill=tk.X, pady=(0, 10))

        def close_picker():
            picker.destroy()
            if anchor_widget is not None:
                anchor_widget.focus_set()

        def select_date(date_value):
            self.set_date_target_value(target, date_value.strftime("%d.%m.%Y"))
            close_picker()

        def change_month(delta):
            month = month_state["month"] + delta
            year = month_state["year"]
            if month < 1:
                month = 12
                year -= 1
            elif month > 12:
                month = 1
                year += 1
            month_state["year"] = year
            month_state["month"] = month
            draw_month()

        prev_button = self.create_button(header, text="<", command=lambda: change_month(-1), variant="secondary")
        prev_button.pack(side=tk.LEFT, padx=(0, 8))

        month_label = tk.Label(
            header,
            text="",
            font=(self.FONT, 12, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            width=18,
        )
        month_label.pack(side=tk.LEFT, expand=True)

        next_button = self.create_button(header, text=">", command=lambda: change_month(1), variant="secondary")
        next_button.pack(side=tk.RIGHT, padx=(8, 0))

        calendar_grid = tk.Frame(body, bg=self.COLORS["panel"])
        calendar_grid.pack(fill=tk.BOTH, expand=True)

        def draw_month():
            for child in calendar_grid.winfo_children():
                child.destroy()

            year = month_state["year"]
            month = month_state["month"]
            month_label.config(text=f"{self.CZECH_MONTHS[month]} {year}")

            for column, weekday in enumerate(("Po", "Út", "St", "Čt", "Pá", "So", "Ne")):
                tk.Label(
                    calendar_grid,
                    text=weekday,
                    font=(self.FONT, 9, "bold"),
                    bg=self.COLORS["panel"],
                    fg=self.COLORS["muted"],
                    width=4,
                ).grid(row=0, column=column, padx=2, pady=(0, 4))

            first_weekday, days_in_month = calendar.monthrange(year, month)
            today = datetime.now().date()
            for day in range(1, days_in_month + 1):
                date_value = datetime(year, month, day).date()
                offset = first_weekday + day - 1
                row = 1 + offset // 7
                column = offset % 7
                is_selected = date_value == selected_date
                is_today = date_value == today
                button = tk.Button(
                    calendar_grid,
                    text=str(day),
                    command=lambda value=date_value: select_date(value),
                    bg=self.COLORS["primary"] if is_selected else ("#e6edf7" if is_today else self.COLORS["panel_soft"]),
                    fg="white" if is_selected else self.COLORS["text"],
                    activebackground=self.COLORS["primary_dark"],
                    activeforeground="white",
                    font=(self.FONT, 10, "bold" if is_selected or is_today else "normal"),
                    relief=tk.FLAT,
                    borderwidth=0,
                    width=4,
                    padx=4,
                    pady=7,
                    cursor="hand2",
                )
                button.grid(row=row, column=column, padx=2, pady=2)

        footer = tk.Frame(body, bg=self.COLORS["panel"])
        footer.pack(fill=tk.X, pady=(12, 0))
        self.create_button(footer, text="Dnes", command=lambda: select_date(datetime.now().date()), variant="secondary").pack(side=tk.LEFT)
        self.create_button(footer, text="Vymazat", command=lambda: (self.set_date_target_value(target, ""), close_picker()), variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(footer, text="Zavřít", command=close_picker, variant="secondary").pack(side=tk.RIGHT)

        draw_month()
        picker.update_idletasks()
        if anchor_widget is not None:
            x = anchor_widget.winfo_rootx()
            y = anchor_widget.winfo_rooty() - picker.winfo_height() - 4
            x = min(max(x, 0), max(picker.winfo_screenwidth() - picker.winfo_width(), 0))
            y = max(y, 0)
        else:
            x = self.root.winfo_rootx() + max((self.root.winfo_width() - picker.winfo_width()) // 2, 0)
            y = self.root.winfo_rooty() + max((self.root.winfo_height() - picker.winfo_height()) // 2, 0)
        picker.geometry(f"+{x}+{y}")
        picker.bind("<Escape>", lambda event: close_picker())


    def load_meetings(self):
        self.meeting_listbox.delete(0, tk.END)
        c = self.conn.cursor()
        if self.show_archived_meetings.get():
            c.execute("SELECT id, title, date, COALESCE(archived, 0) FROM meetings ORDER BY date DESC")
        else:
            c.execute("SELECT id, title, date, COALESCE(archived, 0) FROM meetings WHERE COALESCE(archived, 0)=0 ORDER BY date DESC")
        all_meetings = c.fetchall()
        search_text = self.meeting_search_var.get().strip().lower()
        if search_text:
            self.meetings_data = [
                meeting
                for meeting in all_meetings
                for status_text in ("plánovaná" if self.is_planned_meeting(meeting[2]) else "proběhlá",)
                if search_text in (meeting[1] or "").lower()
                or search_text in (meeting[2] or "").lower()
                or search_text in self.format_czech_date(meeting[2]).lower()
                or search_text in status_text
            ]
        else:
            self.meetings_data = all_meetings

        for meeting in self.meetings_data:
            meeting_id, title, date = meeting[:3]
            archived = meeting[3] == 1 if len(meeting) > 3 else False
            prefix = " ARCHIV " if archived else ("  PLÁN  " if self.is_planned_meeting(date) else "        ")
            self.meeting_listbox.insert(tk.END, f"{prefix}{self.format_czech_date(date)}  |  {title}")

        if hasattr(self, "lbl_meeting_count"):
            if search_text:
                self.lbl_meeting_count.config(text=f"Zobrazeno {len(self.meetings_data)} z {len(all_meetings)} porad")
            else:
                self.lbl_meeting_count.config(text=f"Celkem {len(all_meetings)} porad")

        if not self.current_id and self.meetings_data and not search_text:
            self.current_id = self.meetings_data[0][0]
            self.select_current_meeting()
            self.load_meeting_details()
        elif not self.current_id:
            self.clear_right_panel()
        else:
            self.select_current_meeting()


    def select_current_meeting(self):
        for index, meeting in enumerate(self.meetings_data):
            if meeting[0] == self.current_id:
                self.meeting_listbox.selection_clear(0, tk.END)
                self.meeting_listbox.selection_set(index)
                self.meeting_listbox.activate(index)
                self.meeting_listbox.see(index)
                return


    def clear_right_panel(self):
        self.notes_dirty = False
        self.general_info_tree.delete(*self.general_info_tree.get_children())
        self.agenda_listbox.delete(0, tk.END)
        self.current_agenda_data = []
        self.all_agenda_data = []
        self.progress_data = []
        self.owner_progress_data = []
        self.progress_total = {"done": 0, "total": 0}
        self.active_point_id = None
        if hasattr(self, "dashboard_labels"):
            self.refresh_dashboard_summary()
        self.lbl_title.config(text="Vyberte poradu ze seznamu")
        self.lbl_subtitle.config(text="Zápis a agenda se zobrazí po výběru porady.")
        self.lbl_agenda_count.config(text="Dvojklikem označíte bod jako vyřešený.")
        self.lbl_progress_summary.config(text="Bez bodů programu.")
        self.draw_progress_overview()
        self.draw_owner_progress_overview()
        self.draw_lotus_calendar()
        self.btn_delete.config(state=tk.DISABLED)
        self.btn_edit_date.config(state=tk.DISABLED)
        self.btn_export.config(state=tk.DISABLED)
        self.btn_delete_agenda.config(state=tk.DISABLED)
        if hasattr(self, "btn_archive"):
            self.btn_archive.config(state=tk.DISABLED)
        if hasattr(self, "btn_history"):
            self.btn_history.config(state=tk.DISABLED)
        self.apply_permission_state()


    def add_meeting(self):
        if not self.require_admin():
            return

        dialog, content = self.create_dialog("Nová porada", 560, 360, 500, 330, modal=True)
        self.create_dialog_header(
            content,
            "Nová porada",
            "Zadejte název a datum plánované porady.",
        )

        form = tk.Frame(content, bg=self.COLORS["panel"])
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        title_var = tk.StringVar(value=self.get_next_meeting_number())
        date_var = tk.StringVar(value=self.get_today_due_date())

        tk.Label(
            form,
            text="Název",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 10))
        title_entry = ttk.Entry(form, textvariable=title_var, font=(self.FONT, 10))
        title_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10), ipady=3)

        tk.Label(
            form,
            text="Datum",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).grid(row=1, column=0, sticky="w", padx=(0, 12))
        date_entry = ttk.Combobox(
            form,
            textvariable=date_var,
            values=[(datetime.now().date() + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(0, 366)],
            font=(self.FONT, 10),
        )
        date_entry.grid(row=1, column=1, sticky="ew", ipady=3)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(18, 0))

        def save_new_meeting():
            title = title_var.get().strip()
            parsed_date = self.parse_due_date(date_var.get())
            if not title:
                messagebox.showwarning("Nová porada", "Zadejte název porady.")
                title_entry.focus_set()
                return
            if not parsed_date:
                messagebox.showwarning("Nová porada", "Zadejte platné datum, například 13.05.2026.")
                date_entry.focus_set()
                return

            c = self.conn.cursor()
            c.execute(
                "INSERT INTO meetings (title, date, notes, general_info) VALUES (?, ?, ?, ?)",
                (title, parsed_date.strftime("%Y-%m-%d"), "", ""),
            )
            self.current_id = c.lastrowid
            self.commit_database()
            dialog.destroy()
            self.load_meetings()
            self.load_meeting_details()

        self.create_button(actions, text="Přidat", command=save_new_meeting, variant="primary").pack(side=tk.LEFT)
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)

        title_entry.bind("<Return>", lambda event: save_new_meeting())
        date_entry.bind("<Return>", lambda event: save_new_meeting())
        title_entry.focus_set()


    def edit_meeting_date(self):
        if not self.require_admin():
            return

        if not self.current_id:
            return

        c = self.conn.cursor()
        c.execute("SELECT date FROM meetings WHERE id=?", (self.current_id,))
        row = c.fetchone()
        current_date = self.format_czech_date(row[0]) if row else self.get_today_due_date()

        dialog, content = self.create_dialog("Datum porady", 460, 260, 420, 240, modal=True)
        self.create_dialog_header(
            content,
            "Datum porady",
            "Vyberte nebo zadejte datum vybrané porady.",
        )

        form = tk.Frame(content, bg=self.COLORS["panel"])
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        date_var = tk.StringVar(value=current_date)
        tk.Label(
            form,
            text="Datum",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        date_entry = ttk.Entry(form, textvariable=date_var, font=(self.FONT, 10))
        date_entry.grid(row=0, column=1, sticky="ew", ipady=3)

        def open_picker(event=None):
            return self.open_date_picker_for_variable(date_var, date_entry)

        def save_date():
            parsed_date = self.parse_due_date(date_var.get())
            if not parsed_date:
                messagebox.showwarning("Datum porady", "Zadejte platné datum, například 13.05.2026.")
                date_entry.focus_set()
                return

            c.execute("UPDATE meetings SET date=? WHERE id=?", (parsed_date.strftime("%Y-%m-%d"), self.current_id))
            self.commit_database()
            dialog.destroy()
            self.load_meetings()
            self.load_meeting_details()

        date_entry.bind("<Button-1>", open_picker)
        date_entry.bind("<Up>", open_picker)
        date_entry.bind("<Return>", lambda event: save_date())

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(18, 0))
        self.create_button(actions, text="Uložit", command=save_date, variant="primary").pack(side=tk.LEFT)
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)

        date_entry.focus_set()


    def on_select_meeting(self, event):
        selection = self.meeting_listbox.curselection()
        if selection:
            index = selection[0]
            if self.current_id and self.notes_dirty:
                self.save_notes(show_message=False)
            self.current_id = self.meetings_data[index][0]
            self.active_point_id = None
            self.load_meeting_details()


    def load_meeting_details(self):
        if not self.current_id:
            return

        c = self.conn.cursor()

        # Načtení základních dat porady
        c.execute("SELECT title, date FROM meetings WHERE id=?", (self.current_id,))
        meeting = c.fetchone()
        if not meeting:
            messagebox.showwarning("Porada", "Vybraná porada už neexistuje. Seznam bude obnoven.")
            self.current_id = None
            self.clear_right_panel()
            self.load_meetings()
            return
        czech_date = self.format_czech_date(meeting[1])
        meeting_date = self.parse_due_date(meeting[1])
        if meeting_date:
            self.lotus_calendar_month = meeting_date.replace(day=1)
        self.lbl_title.config(text=f"{meeting[0]} - {czech_date}")
        self.lbl_subtitle.config(text="Datum je součástí názvu porady.")
        c.execute("SELECT COALESCE(archived, 0) FROM meetings WHERE id=?", (self.current_id,))
        archived_row = c.fetchone()
        if hasattr(self, "btn_archive"):
            self.btn_archive.config(text="Vrátit z archivu" if archived_row and archived_row[0] == 1 else "Archiv")

        self.notes_dirty = False

        self.load_general_info_entries()

        # Načtení bodů programu a jejich položek
        self.agenda_listbox.delete(0, tk.END)
        self.current_agenda_data = []
        self.all_agenda_data = []
        self.progress_data = []
        self.owner_progress_data = []
        owner_progress = {}

        def add_owner_progress(owner, is_resolved):
            owner_key = (owner or "").strip() or "Bez odpovědnosti"
            if owner_key not in owner_progress:
                owner_progress[owner_key] = {"owner": owner_key, "done": 0, "total": 0}
            owner_progress[owner_key]["total"] += 1
            owner_progress[owner_key]["done"] += int(is_resolved == 1)

        c.execute("SELECT id, title FROM agenda_points WHERE meeting_id=? ORDER BY id", (self.current_id,))
        points = c.fetchall()

        resolved_count = 0
        total = 0
        for point_id, title in points:
            point_row = {"type": "point", "id": point_id, "title": title}
            self.all_agenda_data.append(point_row)

            c.execute(
                """SELECT id, description, is_resolved, owner, due_date, due_date_reason
                   FROM agenda_items WHERE point_id=? ORDER BY id""",
                (point_id,),
            )
            items = c.fetchall()
            point_total = len(items)
            point_done = sum(1 for item in items if item[2] == 1)
            visible_items = [item for item in items if not self.show_open_only.get() or item[2] == 0]
            self.progress_data.append(
                {
                    "title": title,
                    "done": point_done,
                    "total": point_total,
                }
            )

            if visible_items or not self.show_open_only.get():
                self.add_agenda_display_row(point_row, f" ▸ {title}", self.COLORS["primary"])

            for item_id, description, is_resolved, owner, due_date, due_date_reason in items:
                is_done = is_resolved == 1
                resolved_count += int(is_done)
                total += 1
                add_owner_progress(owner, is_resolved)
                status = "✓" if is_done else "○"
                meta = self.format_item_meta(owner, due_date, due_date_reason)
                item_row = {
                    "type": "item",
                    "id": item_id,
                    "point_id": point_id,
                    "description": description,
                    "is_resolved": is_resolved,
                    "owner": owner or "",
                    "due_date": due_date or "",
                    "due_date_reason": due_date_reason or "",
                }
                self.all_agenda_data.append(item_row)
                if not self.show_open_only.get() or not is_done:
                    if self.is_item_overdue(due_date, is_resolved):
                        color = self.COLORS["danger"]
                        background = "#fee2e2"
                    elif self.is_item_due_today(due_date, is_resolved):
                        color = "#b45309"
                        background = "#ffedd5"
                    else:
                        color = self.COLORS["muted"] if is_done else self.COLORS["text"]
                        background = self.COLORS["panel_soft"]
                    self.add_agenda_display_row(item_row, f"    {status}  {description}{meta}", color, background)

        for table_name in ("meeting_orders", "meeting_requirements"):
            c.execute(
                f"""SELECT owner, is_resolved
                    FROM {table_name}
                    WHERE meeting_id=?""",
                (self.current_id,),
            )
            for owner, is_resolved in c.fetchall():
                add_owner_progress(owner, is_resolved)

        open_count = total - resolved_count
        self.progress_total = {"done": resolved_count, "total": total}
        self.owner_progress_data = sorted(
            owner_progress.values(),
            key=lambda row: (row["owner"] == "Bez odpovědnosti", row["owner"].lower()),
        )
        if self.show_open_only.get():
            self.lbl_agenda_count.config(text=f"Zobrazeno jen otevřené: {open_count} / {total}")
            if not self.current_agenda_data:
                self.agenda_listbox.insert(tk.END, "    Žádné otevřené položky")
                self.agenda_listbox.itemconfig(tk.END, {"fg": self.COLORS["muted"]})
        else:
            self.lbl_agenda_count.config(text=f"{open_count} otevřené / {total} celkem")
        if total:
            percent = round((resolved_count / total) * 100)
            self.lbl_progress_summary.config(text=f"Celkem splněno {percent} %")
        elif points:
            self.lbl_progress_summary.config(text="Body zatím nemají položky.")
        else:
            self.lbl_progress_summary.config(text="Bez bodů programu.")
        self.draw_progress_overview()
        self.draw_owner_progress_overview()
        self.draw_lotus_calendar()
        self.refresh_dashboard_summary()
        self.ensure_active_agenda_point()

        self.btn_delete.config(state=tk.NORMAL)
        self.btn_edit_date.config(state=tk.NORMAL)
        self.btn_export.config(state=tk.NORMAL)
        self.btn_delete_agenda.config(state=tk.NORMAL)
        if hasattr(self, "btn_archive"):
            self.btn_archive.config(state=tk.NORMAL)
        if hasattr(self, "btn_history"):
            self.btn_history.config(state=tk.NORMAL)
        self.apply_permission_state()


    def add_agenda_display_row(self, row, text, color, background=None):
        self.current_agenda_data.append(row)
        self.agenda_listbox.insert(tk.END, text)
        self.agenda_listbox.itemconfig(tk.END, {"fg": color})
        if background:
            self.agenda_listbox.itemconfig(tk.END, {"bg": background})


    def on_notes_modified(self, event=None):
        if self.text_notes is None:
            return
        if not self.can_edit():
            self.text_notes.edit_modified(False)
            return

        if self.text_notes.edit_modified():
            self.notes_dirty = True
            self.text_notes.edit_modified(False)


    def save_notes(self, show_message=True):
        if not self.require_admin():
            return

        if self.current_id:
            if self.text_notes is None:
                self.notes_dirty = False
                return
            notes = self.text_notes.get(1.0, tk.END).strip()
            c = self.conn.cursor()
            c.execute("UPDATE meetings SET notes=? WHERE id=?", (notes, self.current_id))
            self.commit_database()
            self.notes_dirty = False
            self.text_notes.edit_modified(False)
            if show_message:
                messagebox.showinfo("Uloženo", "Zápis byl úspěšně uložen.")


    def load_general_info_entries(self):
        if not hasattr(self, "general_info_tree"):
            return

        self.general_info_tree.delete(*self.general_info_tree.get_children())
        if not self.current_id:
            return

        c = self.conn.cursor()
        c.execute(
            """SELECT id, info_text, created_at, is_invalid
               FROM meeting_general_info
               WHERE meeting_id=?
               ORDER BY datetime(created_at) DESC, id DESC""",
            (self.current_id,),
        )
        for info_id, info_text, created_at, is_invalid in c.fetchall():
            tag = "invalid" if is_invalid == 1 else "valid"
            self.general_info_tree.insert(
                "",
                tk.END,
                iid=str(info_id),
                values=(self.format_general_info_timestamp(created_at), info_text or ""),
                tags=(tag,),
            )


    def format_general_info_timestamp(self, timestamp):
        if not timestamp:
            return ""
        for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(timestamp, date_format).strftime("%d.%m.%Y %H:%M")
            except (TypeError, ValueError):
                continue
        return timestamp


    def fetch_general_info_detail(self, info_id):
        c = self.conn.cursor()
        c.execute(
            """SELECT id, info_text, is_invalid
               FROM meeting_general_info
               WHERE id=? AND meeting_id=?""",
            (info_id, self.current_id),
        )
        return c.fetchone()


    def get_selected_general_info_id(self):
        selection = self.general_info_tree.selection()
        return int(selection[0]) if selection else None


    def show_general_info_dialog(self, info_id=None):
        if not self.require_admin():
            return

        if not self.current_id:
            return

        existing = self.fetch_general_info_detail(info_id) if info_id else None
        title = "Upravit informaci" if existing else "Nová informace"
        dialog, content = self.create_dialog(title, 700, 390, 560, 330, modal=True)
        self.create_dialog_header(content, title, "Zadejte všeobecnou informaci k vybrané poradě.")

        text = tk.Text(content, height=9, wrap=tk.WORD, font=(self.FONT, 10), relief=tk.SOLID, borderwidth=1)
        text.pack(fill=tk.BOTH, expand=True)
        if existing:
            text.insert("1.0", existing[1] or "")

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(18, 0))

        def save_info():
            info_text = text.get("1.0", tk.END).strip()
            if not info_text:
                messagebox.showwarning("Všeobecné informace", "Zadejte text informace.")
                text.focus_set()
                return

            c = self.conn.cursor()
            if existing:
                c.execute(
                    "UPDATE meeting_general_info SET info_text=? WHERE id=? AND meeting_id=?",
                    (info_text, existing[0], self.current_id),
                )
            else:
                c.execute(
                    """INSERT INTO meeting_general_info
                       (meeting_id, info_text, created_at, is_invalid, invalidated_at)
                       VALUES (?, ?, ?, 0, '')""",
                    (self.current_id, info_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
            self.commit_database()
            self.load_general_info_entries()
            dialog.destroy()

        self.create_button(actions, text="Uložit", command=save_info, variant="primary").pack(side=tk.LEFT)
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)
        text.focus_set()


    def edit_selected_general_info(self):
        info_id = self.get_selected_general_info_id()
        if not info_id:
            messagebox.showwarning("Všeobecné informace", "Nejprve vyberte informaci.")
            return
        self.show_general_info_dialog(info_id)


    def invalidate_selected_general_info(self):
        if not self.require_admin():
            return

        info_id = self.get_selected_general_info_id()
        if not info_id:
            messagebox.showwarning("Všeobecné informace", "Nejprve vyberte informaci.")
            return

        row = self.fetch_general_info_detail(info_id)
        if not row:
            messagebox.showwarning("Všeobecné informace", "Vybraná informace už neexistuje.")
            self.load_general_info_entries()
            return
        if row[2] == 1:
            messagebox.showinfo("Všeobecné informace", "Vybraná informace už je zneplatněná.")
            return
        if not messagebox.askyesno("Zneplatnit informaci", "Opravdu chcete vybranou informaci zneplatnit?"):
            return

        c = self.conn.cursor()
        c.execute(
            """UPDATE meeting_general_info
               SET is_invalid=1, invalidated_at=?
               WHERE id=? AND meeting_id=?""",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), info_id, self.current_id),
        )
        self.commit_database()
        self.load_general_info_entries()


    def delete_meeting(self):
        if not self.require_admin():
            return

        if self.current_id:
            if messagebox.askyesno("Smazat poradu", "Opravdu chcete tuto poradu smazat?"):
                if not self.backup_before_delete("delete_meeting"):
                    return
                c = self.conn.cursor()
                c.execute("SELECT id FROM agenda_points WHERE meeting_id=?", (self.current_id,))
                point_ids = [row[0] for row in c.fetchall()]
                for point_id in point_ids:
                    c.execute("DELETE FROM agenda_items WHERE point_id=?", (point_id,))
                c.execute("DELETE FROM agenda_points WHERE meeting_id=?", (self.current_id,))
                c.execute("DELETE FROM agenda WHERE meeting_id=?", (self.current_id,))
                c.execute("DELETE FROM meeting_orders WHERE meeting_id=?", (self.current_id,))
                c.execute("DELETE FROM meeting_requirements WHERE meeting_id=?", (self.current_id,))
                c.execute("DELETE FROM meeting_general_info WHERE meeting_id=?", (self.current_id,))
                self.log_audit("smazání porady", str(self.current_id), self.current_id)
                c.execute("DELETE FROM meetings WHERE id=?", (self.current_id,))
                self.commit_database()
                self.current_id = None
                self.load_meetings()


