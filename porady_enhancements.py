# -*- coding: utf-8 -*-

import html
import os
import tempfile
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk


class EnhancementMixin:

    def normalize_person_name(self, name):
        return " ".join((name or "").strip().split()).lower()


    def log_change(self, record_type, record_id, meeting_id, field_name, old_value, new_value):
        old_text = "" if old_value is None else str(old_value)
        new_text = "" if new_value is None else str(new_value)
        if old_text == new_text:
            return

        c = self.conn.cursor()
        c.execute(
            """INSERT INTO change_history
               (record_type, record_id, meeting_id, field_name, old_value, new_value, changed_at, changed_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_type,
                record_id,
                meeting_id,
                field_name,
                old_text,
                new_text,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admin" if self.can_edit() else "uživatel",
            ),
        )


    def log_field_changes(self, record_type, record_id, meeting_id, previous, current):
        for field_name, old_value in previous.items():
            self.log_change(record_type, record_id, meeting_id, field_name, old_value, current.get(field_name, ""))


    def seed_people_from_existing_data(self):
        c = self.conn.cursor()
        names = set()
        for table_name in ("agenda_items", "meeting_orders", "meeting_requirements"):
            c.execute(f"SELECT DISTINCT owner FROM {table_name} WHERE owner IS NOT NULL AND TRIM(owner) <> ''")
            names.update(row[0].strip() for row in c.fetchall() if row[0].strip())
        for name in sorted(names):
            c.execute(
                "INSERT OR IGNORE INTO people (name, normalized_name, is_active) VALUES (?, ?, 1)",
                (name, self.normalize_person_name(name)),
            )
        self.commit_database()


    def get_people_values(self, active_only=True):
        c = self.conn.cursor()
        query = "SELECT name FROM people"
        if active_only:
            query += " WHERE COALESCE(is_active, 1)=1"
        query += " ORDER BY name"
        c.execute(query)
        values = [row[0] for row in c.fetchall()]
        if values:
            return values

        fallback = set()
        for getter in (self.get_owner_filter_values, self.get_order_owner_filter_values, self.get_requirement_owner_filter_values):
            try:
                fallback.update(getter())
            except Exception:
                continue
        return sorted(fallback)


    def show_people_manager(self):
        if not self.require_admin():
            return

        self.seed_people_from_existing_data()
        dialog, content = self.create_dialog("Odpovědnosti", 760, 560, 620, 440, modal=True)
        self.create_dialog_header(
            content,
            "Správa odpovědností",
            "Sjednoťte názvy osob nebo oddělení používaných v úkolech, nařízeních a požadavcích.",
            accent=self.COLORS["page_tasks_accent"],
        )

        columns = ("name", "active")
        tree = ttk.Treeview(content, columns=columns, show="headings", selectmode="browse")
        tree.heading("name", text="Odpovědnost")
        tree.heading("active", text="Aktivní")
        tree.column("name", width=480, anchor="w")
        tree.column("active", width=80, anchor="w", stretch=False)
        tree.pack(fill=tk.BOTH, expand=True)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(14, 0))

        name_var = tk.StringVar()
        name_entry = ttk.Entry(actions, textvariable=name_var, font=(self.FONT, 10))
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3, padx=(0, 8))

        def refresh():
            tree.delete(*tree.get_children())
            c = self.conn.cursor()
            c.execute("SELECT id, name, is_active FROM people ORDER BY name")
            for person_id, name, is_active in c.fetchall():
                tree.insert("", tk.END, iid=str(person_id), values=(name, "ano" if is_active else "ne"))

        def save_person():
            name = name_var.get().strip()
            if not name:
                return
            c = self.conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO people (name, normalized_name, is_active) VALUES (?, ?, 1)",
                (name, self.normalize_person_name(name)),
            )
            self.commit_database()
            name_var.set("")
            refresh()
            self.refresh_owner_choices()

        def rename_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Odpovědnosti", "Nejprve vyberte záznam.")
                return
            old_name = tree.item(selection[0], "values")[0]
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("Odpovědnosti", "Zadejte nový název odpovědnosti.")
                return
            c = self.conn.cursor()
            c.execute("UPDATE people SET name=?, normalized_name=? WHERE id=?", (new_name, self.normalize_person_name(new_name), int(selection[0])))
            for table_name in ("agenda_items", "meeting_orders", "meeting_requirements"):
                c.execute(f"UPDATE {table_name} SET owner=? WHERE owner=?", (new_name, old_name))
            self.commit_database()
            self.refresh_owner_choices()
            self.load_meeting_details()
            name_var.set("")
            refresh()

        def toggle_active():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Odpovědnosti", "Nejprve vyberte záznam.")
                return
            c = self.conn.cursor()
            c.execute("UPDATE people SET is_active=CASE WHEN COALESCE(is_active, 1)=1 THEN 0 ELSE 1 END WHERE id=?", (int(selection[0]),))
            self.commit_database()
            refresh()

        self.create_button(actions, text="Přidat", command=save_person, variant="primary").pack(side=tk.LEFT, padx=(0, 8))
        self.create_button(actions, text="Přejmenovat", command=rename_selected, variant="secondary").pack(side=tk.LEFT, padx=(0, 8))
        self.create_button(actions, text="Aktivní/neaktivní", command=toggle_active, variant="secondary").pack(side=tk.LEFT, padx=(0, 8))
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)
        tree.bind("<<TreeviewSelect>>", lambda event: name_var.set(tree.item(tree.selection()[0], "values")[0]) if tree.selection() else None)
        name_entry.bind("<Return>", lambda event: save_person())
        refresh()


    def collect_open_records(self, filter_type="all"):
        today = datetime.now().date()
        week_end = today + timedelta(days=7)
        records = []

        def include_record(due_date, owner):
            parsed_due = self.parse_due_date(due_date)
            if filter_type == "today":
                return parsed_due == today
            if filter_type == "week":
                return bool(parsed_due and today <= parsed_due <= week_end)
            if filter_type == "overdue":
                return bool(parsed_due and parsed_due < today)
            if filter_type == "no_owner":
                return not (owner or "").strip()
            return True

        c = self.conn.cursor()
        c.execute(
            """SELECT agenda_items.id, agenda_items.description, agenda_items.owner, agenda_items.due_date,
                      agenda_points.title, meetings.id, meetings.title, meetings.date
               FROM agenda_items
               JOIN agenda_points ON agenda_points.id = agenda_items.point_id
               JOIN meetings ON meetings.id = agenda_points.meeting_id
               WHERE COALESCE(agenda_items.is_resolved, 0)=0"""
        )
        for item_id, description, owner, due_date, point_title, meeting_id, meeting_title, meeting_date in c.fetchall():
            if filter_type in ("all", "today", "week", "overdue", "no_owner", "tasks") and include_record(due_date, owner):
                status, tag = self.get_record_status(due_date, 0)
                records.append(("Úkol", item_id, meeting_id, meeting_title, meeting_date, point_title, description, owner, due_date, status, tag))

        for label, table_name, type_filter in (
            ("Nařízení", "meeting_orders", "orders"),
            ("Požadavek", "meeting_requirements", "requirements"),
        ):
            c.execute(
                f"""SELECT {table_name}.id, {table_name}.description, {table_name}.owner, {table_name}.due_date,
                           meetings.id, meetings.title, meetings.date
                    FROM {table_name}
                    LEFT JOIN meetings ON meetings.id = {table_name}.meeting_id
                    WHERE COALESCE({table_name}.is_resolved, 0)=0"""
            )
            for record_id, description, owner, due_date, meeting_id, meeting_title, meeting_date in c.fetchall():
                if filter_type in ("all", "today", "week", "overdue", "no_owner", type_filter) and include_record(due_date, owner):
                    status, tag = self.get_record_status(due_date, 0)
                    records.append((label, record_id, meeting_id, meeting_title or "", meeting_date or "", "", description, owner, due_date, status, tag))

        max_date = datetime.max.date()
        records.sort(key=lambda row: (self.parse_due_date(row[8]) is None, self.parse_due_date(row[8]) or max_date, row[0], row[6].lower()))
        return records


    def show_open_items_overview(self, filter_type="all"):
        titles = {
            "today": "Položky s termínem dnes",
            "week": "Položky na tento týden",
            "overdue": "Položky po termínu",
            "no_owner": "Položky bez odpovědnosti",
            "tasks": "Aktivní úkoly",
            "orders": "Aktivní nařízení",
            "requirements": "Aktivní požadavky",
            "all": "Otevřené položky",
        }
        dialog, content = self.create_dialog(titles.get(filter_type, "Otevřené položky"), 1180, 680, 900, 500)
        self.create_dialog_header(content, titles.get(filter_type, "Otevřené položky"), "Souhrn úkolů, nařízení a požadavků napříč poradami.", accent=self.COLORS["primary"])

        columns = ("type", "due", "status", "owner", "meeting", "point", "description")
        tree = ttk.Treeview(content, columns=columns, show="headings", selectmode="browse")
        for key, title, width in (
            ("type", "Typ", 90),
            ("due", "Termín", 95),
            ("status", "Stav", 95),
            ("owner", "Odpovědnost", 140),
            ("meeting", "Porada", 230),
            ("point", "Bod", 150),
            ("description", "Popis", 420),
        ):
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w", stretch=key in ("meeting", "description"))
        self.configure_status_tags(tree)
        scrollbar = ttk.Scrollbar(content, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for index, record in enumerate(self.collect_open_records(filter_type)):
            record_type, record_id, meeting_id, meeting_title, meeting_date, point_title, description, owner, due_date, status, tag = record
            tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(record_type, due_date or "-", status, owner or "-", f"{self.format_czech_date(meeting_date)} | {meeting_title}", point_title or "-", description or ""),
                tags=(tag,),
            )
            tree.item(str(index), tags=(tag, f"meeting:{meeting_id or 0}"))

        def open_selected():
            selection = tree.selection()
            if not selection:
                return
            record = self.collect_open_records(filter_type)[int(selection[0])]
            meeting_id = record[2]
            if meeting_id:
                self.current_id = meeting_id
                self.show_open_only.set(False)
                self.load_meetings()
                self.load_meeting_details()
                dialog.destroy()
                self.root.lift()

        tree.bind("<Double-1>", lambda event: open_selected())


    def export_open_items_overview(self):
        records = self.collect_open_records("all")
        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            initialfile=f"Prehled_otevrenych_polozek_{datetime.now().strftime('%Y-%m-%d')}.html",
            filetypes=[("HTML přehled", "*.html"), ("Textové soubory", "*.txt")],
        )
        if not filepath:
            return

        if filepath.lower().endswith(".txt"):
            with open(filepath, "w", encoding="utf-8") as handle:
                handle.write("PŘEHLED OTEVŘENÝCH POLOŽEK\n")
                handle.write("=" * 40 + "\n\n")
                for record in records:
                    record_type, _, _, meeting_title, meeting_date, point_title, description, owner, due_date, status, _ = record
                    handle.write(f"- {record_type}: {description}\n")
                    handle.write(f"  Porada: {self.format_czech_date(meeting_date)} | {meeting_title}\n")
                    if point_title:
                        handle.write(f"  Bod: {point_title}\n")
                    handle.write(f"  Stav: {status}, termín: {due_date or '-'}, odpovědnost: {owner or '-'}\n\n")
        else:
            rows = []
            for record in records:
                record_type, _, _, meeting_title, meeting_date, point_title, description, owner, due_date, status, tag = record
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(record_type)}</td>"
                    f"<td>{html.escape(due_date or '-')}</td>"
                    f"<td class='{tag}'>{html.escape(status)}</td>"
                    f"<td>{html.escape(owner or '-')}</td>"
                    f"<td>{html.escape(self.format_czech_date(meeting_date))} | {html.escape(meeting_title)}</td>"
                    f"<td>{html.escape(point_title or '-')}</td>"
                    f"<td>{html.escape(description or '')}</td>"
                    "</tr>"
                )
            document = f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><title>Přehled otevřených položek</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#eef2f6;color:#17202a;margin:0;padding:28px}}
main{{background:white;max-width:1180px;margin:auto;padding:28px;border:1px solid #d7dee8}}
table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{border-bottom:1px solid #e5eaf1;padding:8px;text-align:left;vertical-align:top}}
th{{background:#f8fafc}} .overdue{{color:#dc2626;font-weight:700}} .today{{color:#f59e0b;font-weight:700}} .no_due{{color:#667085}}
.print-button{{position:fixed;right:24px;top:18px;border:0;background:#2563eb;color:white;padding:10px 14px;font-weight:700;cursor:pointer}}
@media print{{body{{background:white;padding:0}}main{{border:0}}.print-button{{display:none}}}}
</style></head><body><button class="print-button" onclick="window.print()">Tisk</button><main>
<h1>Přehled otevřených položek</h1><p>Vygenerováno {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
<table><thead><tr><th>Typ</th><th>Termín</th><th>Stav</th><th>Odpovědnost</th><th>Porada</th><th>Bod</th><th>Popis</th></tr></thead>
<tbody>{''.join(rows) if rows else '<tr><td colspan="7">Žádné otevřené položky.</td></tr>'}</tbody></table></main></body></html>"""
            with open(filepath, "w", encoding="utf-8") as handle:
                handle.write(document)

        if filepath.lower().endswith(".html") and messagebox.askyesno("Export", "Přehled byl exportován. Chcete ho otevřít pro tisk?"):
            try:
                os.startfile(filepath)
            except OSError:
                messagebox.showwarning("Export", "Soubor se nepodařilo automaticky otevřít.")


    def show_global_search(self):
        dialog, content = self.create_dialog("Globální hledání", 1180, 680, 900, 500)
        self.create_dialog_header(content, "Globální hledání", "Vyhledávání přes porady, zápisy, úkoly, nařízení, požadavky a všeobecné informace.", accent=self.COLORS["primary"])
        search_var = tk.StringVar()
        search_entry = ttk.Entry(content, textvariable=search_var, font=(self.FONT, 11))
        search_entry.pack(fill=tk.X, ipady=4, pady=(0, 12))

        columns = ("type", "date", "meeting", "text")
        tree = ttk.Treeview(content, columns=columns, show="headings", selectmode="browse")
        for key, title, width in (("type", "Typ", 130), ("date", "Datum", 95), ("meeting", "Porada", 250), ("text", "Text", 620)):
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w", stretch=key == "text")
        tree.pack(fill=tk.BOTH, expand=True)
        results = []

        def add_result(record_type, meeting_id, meeting_title, meeting_date, text):
            results.append((meeting_id, record_type, meeting_title or "", meeting_date or "", text or ""))

        def refresh():
            tree.delete(*tree.get_children())
            results.clear()
            query = search_var.get().strip().lower()
            if len(query) < 2:
                return
            c = self.conn.cursor()
            c.execute("SELECT id, title, date FROM meetings")
            for meeting_id, title, meeting_date in c.fetchall():
                if query in " ".join((title or "", meeting_date or "")).lower():
                    add_result("Porada", meeting_id, title, meeting_date, title)
            c.execute(
                """SELECT meetings.id, meetings.title, meetings.date, agenda_points.title, agenda_items.description
                   FROM agenda_items JOIN agenda_points ON agenda_points.id=agenda_items.point_id
                   JOIN meetings ON meetings.id=agenda_points.meeting_id"""
            )
            for meeting_id, title, meeting_date, point_title, description in c.fetchall():
                if query in " ".join((point_title or "", description or "")).lower():
                    add_result("Úkol", meeting_id, title, meeting_date, f"{point_title}: {description}")
            for record_type, table_name in (("Nařízení", "meeting_orders"), ("Požadavek", "meeting_requirements")):
                c.execute(f"""SELECT meetings.id, meetings.title, meetings.date, {table_name}.description
                              FROM {table_name} LEFT JOIN meetings ON meetings.id={table_name}.meeting_id""")
                for meeting_id, title, meeting_date, description in c.fetchall():
                    if query in (description or "").lower():
                        add_result(record_type, meeting_id, title, meeting_date, description)
            c.execute(
                """SELECT meetings.id, meetings.title, meetings.date, meeting_general_info.info_text
                   FROM meeting_general_info LEFT JOIN meetings ON meetings.id=meeting_general_info.meeting_id"""
            )
            for meeting_id, title, meeting_date, info_text in c.fetchall():
                if query in (info_text or "").lower():
                    add_result("Všeobecná informace", meeting_id, title, meeting_date, info_text)
            for index, row in enumerate(results):
                meeting_id, record_type, meeting_title, meeting_date, text = row
                tree.insert("", tk.END, iid=str(index), values=(record_type, self.format_czech_date(meeting_date), meeting_title, text[:500]))

        def open_selected():
            selection = tree.selection()
            if not selection:
                return
            meeting_id = results[int(selection[0])][0]
            if meeting_id:
                self.current_id = meeting_id
                self.show_open_only.set(False)
                self.load_meetings()
                self.load_meeting_details()
                dialog.destroy()
                self.root.lift()

        search_entry.bind("<KeyRelease>", lambda event: refresh())
        tree.bind("<Double-1>", lambda event: open_selected())
        self.create_button(content, text="Zavřít", command=dialog.destroy, variant="secondary").pack(anchor="e", pady=(12, 0))
        search_entry.focus_set()


    def archive_current_meeting(self):
        if not self.require_admin() or not self.current_id:
            return
        c = self.conn.cursor()
        c.execute("SELECT archived FROM meetings WHERE id=?", (self.current_id,))
        row = c.fetchone()
        archived = row and row[0] == 1
        prompt = "Vrátit poradu z archivu?" if archived else "Archivovat vybranou poradu?"
        if not messagebox.askyesno("Archiv porad", prompt):
            return
        c.execute("UPDATE meetings SET archived=? WHERE id=?", (0 if archived else 1, self.current_id))
        self.commit_database()
        if not archived and not self.show_archived_meetings.get():
            self.current_id = None
        self.load_meetings()


    def show_history_dialog(self, record_type=None, record_id=None, meeting_id=None):
        dialog, content = self.create_dialog("Historie změn", 900, 540, 720, 420)
        self.create_dialog_header(content, "Historie změn", "Přehled evidovaných změn položek.", accent=self.COLORS["muted"])
        columns = ("when", "type", "field", "old", "new", "by")
        tree = ttk.Treeview(content, columns=columns, show="headings")
        for key, title, width in (("when", "Kdy", 135), ("type", "Typ", 90), ("field", "Pole", 120), ("old", "Původně", 210), ("new", "Nově", 210), ("by", "Kdo", 80)):
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w", stretch=key in ("old", "new"))
        tree.pack(fill=tk.BOTH, expand=True)
        query = "SELECT changed_at, record_type, field_name, old_value, new_value, changed_by FROM change_history"
        params = []
        clauses = []
        if record_type and record_id:
            clauses.append("record_type=? AND record_id=?")
            params.extend([record_type, record_id])
        elif meeting_id:
            clauses.append("meeting_id=?")
            params.append(meeting_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY datetime(changed_at) DESC, id DESC LIMIT 400"
        c = self.conn.cursor()
        c.execute(query, params)
        for row in c.fetchall():
            tree.insert("", tk.END, values=row)
        self.create_button(content, text="Zavřít", command=dialog.destroy, variant="secondary").pack(anchor="e", pady=(12, 0))


    def show_startup_reminders(self):
        records = self.collect_open_records("today") + self.collect_open_records("overdue")
        if not records:
            return
        dialog, content = self.create_dialog("Připomenutí termínů", 900, 520, 720, 400)
        self.create_dialog_header(content, "Připomenutí termínů", "Položky s termínem dnes a položky po termínu.", accent=self.COLORS["warning"])
        columns = ("type", "due", "status", "owner", "meeting", "description")
        tree = ttk.Treeview(content, columns=columns, show="headings")
        for key, title, width in (("type", "Typ", 90), ("due", "Termín", 95), ("status", "Stav", 95), ("owner", "Odpovědnost", 130), ("meeting", "Porada", 230), ("description", "Popis", 300)):
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w", stretch=key in ("meeting", "description"))
        self.configure_status_tags(tree)
        tree.pack(fill=tk.BOTH, expand=True)
        for index, record in enumerate(records[:200]):
            record_type, _, _, meeting_title, meeting_date, _, description, owner, due_date, status, tag = record
            tree.insert("", tk.END, iid=str(index), values=(record_type, due_date or "-", status, owner or "-", f"{self.format_czech_date(meeting_date)} | {meeting_title}", description), tags=(tag,))
        self.create_button(content, text="Zavřít", command=dialog.destroy, variant="primary").pack(anchor="e", pady=(12, 0))
