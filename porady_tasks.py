# -*- coding: utf-8 -*-

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk


class TaskOverviewMixin:

    def show_order_overview(self):
        count_label_holder = {}

        def add_count_label(parent):
            count_label_holder["label"] = tk.Label(
                parent,
                text="",
                font=(self.FONT, 10),
                bg=self.COLORS["panel"],
                fg=self.COLORS["muted"],
            )
            count_label_holder["label"].pack(side=tk.RIGHT, padx=(18, 0))

        dialog, content = self.create_dialog("Přehled nařízení", 1180, 680, 900, 500)
        self.create_dialog_header(
            content,
            "Přehled nařízení z porad",
            "Dvojklikem otevřete detail nařízení v samostatném okně.",
            right_widget=add_count_label,
        )
        count_label = count_label_holder["label"]

        filters = tk.Frame(content, bg=self.COLORS["panel"])
        filters.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            filters,
            text="Odpovědnost",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).pack(side=tk.LEFT, padx=(0, 8))

        owner_var = tk.StringVar(value="Všichni")
        owner_filter = ttk.Combobox(
            filters,
            textvariable=owner_var,
            state="readonly",
            width=20,
            font=(self.FONT, 10),
            values=["Všichni"] + self.get_owner_filter_values(),
        )
        owner_filter.pack(side=tk.LEFT, padx=(0, 16), ipady=3)

        tk.Label(
            filters,
            text="Stav",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).pack(side=tk.LEFT, padx=(0, 8))

        status_var = tk.StringVar(value="Všechna")
        status_filter = ttk.Combobox(
            filters,
            textvariable=status_var,
            state="readonly",
            width=14,
            font=(self.FONT, 10),
            values=["Všechna", "Otevřená", "Splněná", "Po termínu", "Dnes"],
        )
        status_filter.pack(side=tk.LEFT, padx=(0, 16), ipady=3)

        tk.Label(
            filters,
            text="Hledat",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).pack(side=tk.LEFT, padx=(0, 8))

        search_var = tk.StringVar()
        search_entry = ttk.Entry(filters, textvariable=search_var, font=(self.FONT, 10), width=28)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        columns = ("meeting_date", "status", "due_date", "owner", "meeting", "point", "description")
        tree_frame = tk.Frame(content, bg=self.COLORS["panel"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("meeting_date", text="Porada dne")
        tree.heading("status", text="Stav")
        tree.heading("due_date", text="Termín")
        tree.heading("owner", text="Odpovědnost")
        tree.heading("meeting", text="Porada")
        tree.heading("point", text="Bod")
        tree.heading("description", text="Nařízení")
        tree.column("meeting_date", width=95, anchor="w", stretch=False)
        tree.column("status", width=90, anchor="w", stretch=False)
        tree.column("due_date", width=95, anchor="w", stretch=False)
        tree.column("owner", width=130, anchor="w", stretch=False)
        tree.column("meeting", width=190, anchor="w")
        tree.column("point", width=150, anchor="w")
        tree.column("description", width=390, anchor="w")
        self.configure_status_tags(tree)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(14, 0))

        refresh = lambda: self.populate_order_overview(
            tree,
            owner_var.get(),
            status_var.get(),
            search_var.get(),
            count_label,
        )
        owner_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        status_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        search_entry.bind("<KeyRelease>", lambda event: refresh())
        tree.bind("<Double-1>", lambda event: self.open_selected_order(tree, refresh))
        tree.bind("<Return>", lambda event: self.open_selected_order(tree, refresh))

        self.create_button(
            actions,
            text="Zobrazit vybrané nařízení",
            command=lambda: self.open_selected_order(tree, refresh),
            variant="primary",
        ).pack(side=tk.LEFT)

        self.create_button(
            actions,
            text="Obnovit",
            command=refresh,
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Zavřít",
            command=dialog.destroy,
            variant="secondary",
        ).pack(side=tk.RIGHT)

        refresh()


    def show_task_overview(self):
        count_label_holder = {}

        def add_count_label(parent):
            count_label_holder["label"] = tk.Label(
                parent,
                text="",
                font=(self.FONT, 10),
                bg=self.COLORS["panel"],
                fg=self.COLORS["muted"],
            )
            count_label_holder["label"].pack(side=tk.RIGHT, padx=(18, 0))

        dialog, content = self.create_dialog("Přehled úkolů", 1080, 650, 840, 460)
        self.create_dialog_header(
            content,
            "Přehled otevřených úkolů",
            "Dvojklikem otevřete detail úkolu v samostatném okně.",
            right_widget=add_count_label,
            accent=self.COLORS["page_tasks_accent"],
        )
        count_label = count_label_holder["label"]

        filters = tk.Frame(content, bg=self.COLORS["panel"])
        filters.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            filters,
            text="Odpovědnost",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).pack(side=tk.LEFT, padx=(0, 8))

        owner_var = tk.StringVar(value="Všichni")
        owner_filter = ttk.Combobox(
            filters,
            textvariable=owner_var,
            state="readonly",
            width=22,
            font=(self.FONT, 10),
            values=["Všichni"] + self.get_owner_filter_values(),
        )
        owner_filter.pack(side=tk.LEFT, padx=(0, 18), ipady=3)

        overdue_only = tk.BooleanVar(value=False)
        overdue_check = tk.Checkbutton(
            filters,
            text="Jen po termínu",
            variable=overdue_only,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["panel"],
            activeforeground=self.COLORS["text"],
            selectcolor=self.COLORS["panel"],
            font=(self.FONT, 10),
            relief=tk.FLAT,
            borderwidth=0,
        )
        overdue_check.pack(side=tk.LEFT, padx=(0, 18))

        tk.Label(
            filters,
            text="Hledat",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).pack(side=tk.LEFT, padx=(0, 8))

        task_search_var = tk.StringVar()
        task_search = ttk.Entry(filters, textvariable=task_search_var, font=(self.FONT, 10), width=28)
        task_search.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        columns = ("due_date", "status", "owner", "meeting", "point", "description")
        tree_frame = tk.Frame(content, bg=self.COLORS["panel"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("due_date", text="Termín")
        tree.heading("status", text="Stav")
        tree.heading("owner", text="Odpovědnost")
        tree.heading("meeting", text="Porada")
        tree.heading("point", text="Bod")
        tree.heading("description", text="Úkol")
        tree.column("due_date", width=95, anchor="w", stretch=False)
        tree.column("status", width=95, anchor="w", stretch=False)
        tree.column("owner", width=130, anchor="w", stretch=False)
        tree.column("meeting", width=190, anchor="w")
        tree.column("point", width=150, anchor="w")
        tree.column("description", width=360, anchor="w")
        self.configure_status_tags(tree)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(14, 0))

        refresh = lambda: self.populate_task_overview(
            tree,
            owner_var.get(),
            overdue_only.get(),
            count_label,
            task_search_var.get(),
        )
        owner_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        overdue_check.configure(command=refresh)
        task_search.bind("<KeyRelease>", lambda event: refresh())
        tree.bind("<Double-1>", lambda event: self.open_selected_task(tree, dialog, refresh))
        tree.bind("<Return>", lambda event: self.open_selected_task(tree, dialog, refresh))

        self.create_button(
            actions,
            text="Zobrazit vybraný úkol",
            command=lambda: self.open_selected_task(tree, dialog, refresh),
            variant="primary",
        ).pack(side=tk.LEFT)

        self.create_button(
            actions,
            text="Obnovit",
            command=refresh,
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Zavřít",
            command=dialog.destroy,
            variant="secondary",
        ).pack(side=tk.RIGHT)

        refresh()


    def get_owner_filter_values(self):
        c = self.conn.cursor()
        c.execute(
            """SELECT DISTINCT owner FROM agenda_items
               WHERE owner IS NOT NULL AND TRIM(owner) <> ''
               ORDER BY owner"""
        )
        return [row[0] for row in c.fetchall()]


    def fetch_orders(self, owner=None, status_filter="Všechna", search_text=""):
        c = self.conn.cursor()
        query = """
            SELECT
                agenda_items.id,
                agenda_items.description,
                agenda_items.owner,
                agenda_items.due_date,
                agenda_items.is_resolved,
                agenda_points.id,
                agenda_points.title,
                meetings.id,
                meetings.title,
                meetings.date
            FROM agenda_items
            JOIN agenda_points ON agenda_points.id = agenda_items.point_id
            JOIN meetings ON meetings.id = agenda_points.meeting_id
        """
        params = []
        if owner and owner != "Všichni":
            query += " WHERE agenda_items.owner = ?"
            params.append(owner)
        query += " ORDER BY meetings.date DESC, agenda_points.id, agenda_items.id"
        c.execute(query, params)

        orders = []
        today = datetime.now().date()
        search_text = (search_text or "").strip().lower()
        for item_id, description, order_owner, due_date, is_resolved, point_id, point_title, meeting_id, meeting_title, meeting_date in c.fetchall():
            parsed_due = self.parse_due_date(due_date)
            is_done = is_resolved == 1
            is_overdue = bool(parsed_due and parsed_due < today and not is_done)
            is_today = bool(parsed_due and parsed_due == today and not is_done)

            if status_filter == "Otevřená" and is_done:
                continue
            if status_filter == "Splněná" and not is_done:
                continue
            if status_filter == "Po termínu" and not is_overdue:
                continue
            if status_filter == "Dnes" and not is_today:
                continue

            haystack = " ".join(
                (
                    description or "",
                    order_owner or "",
                    due_date or "",
                    point_title or "",
                    meeting_title or "",
                    meeting_date or "",
                    self.format_czech_date(meeting_date),
                )
            ).lower()
            if search_text and search_text not in haystack:
                continue

            if is_done:
                status_text = "Splněno"
                tag = "resolved"
            elif is_overdue:
                status_text = "Po termínu"
                tag = "overdue"
            elif is_today:
                status_text = "Dnes"
                tag = "today"
            elif not parsed_due:
                status_text = "Bez termínu"
                tag = "no_due"
            else:
                status_text = "Otevřeno"
                tag = ""

            orders.append(
                {
                    "item_id": item_id,
                    "description": description or "",
                    "owner": order_owner or "",
                    "due_date": due_date or "",
                    "parsed_due": parsed_due,
                    "is_resolved": is_resolved,
                    "status_text": status_text,
                    "tag": tag,
                    "point_id": point_id,
                    "point_title": point_title,
                    "meeting_id": meeting_id,
                    "meeting_title": meeting_title,
                    "meeting_date": meeting_date,
                }
            )

        max_date = datetime.max.date()
        orders.sort(
            key=lambda order: (
                order["is_resolved"] == 1,
                order["parsed_due"] is None,
                order["parsed_due"] or max_date,
                order["meeting_date"] or "",
                order["meeting_title"].lower(),
            )
        )
        return orders


    def populate_order_overview(self, tree, owner, status_filter, search_text, count_label):
        tree.delete(*tree.get_children())
        orders = self.fetch_orders(owner=owner, status_filter=status_filter, search_text=search_text)

        for order in orders:
            tree.insert(
                "",
                tk.END,
                iid=str(order["item_id"]),
                values=(
                    self.format_czech_date(order["meeting_date"]),
                    order["status_text"],
                    order["due_date"] or "-",
                    order["owner"] or "-",
                    order["meeting_title"],
                    order["point_title"],
                    order["description"],
                ),
                tags=(order["tag"],) if order["tag"] else (),
            )

        if search_text.strip():
            suffix = " nalezených"
        elif status_filter != "Všechna":
            suffix = f" ({status_filter.lower()})"
        else:
            suffix = ""
        count_label.config(text=f"{len(orders)} nařízení{suffix}")


    def open_selected_order(self, tree, refresh_callback=None):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled nařízení", "Nejprve vyberte nařízení.")
            return

        item_id = int(selection[0])
        self.show_task_popup(item_id, refresh_callback=refresh_callback)


    def fetch_open_tasks(self, owner=None, overdue_only=False, search_text=""):
        c = self.conn.cursor()
        query = """
            SELECT
                agenda_items.id,
                agenda_items.description,
                agenda_items.owner,
                agenda_items.due_date,
                agenda_points.id,
                agenda_points.title,
                meetings.id,
                meetings.title,
                meetings.date
            FROM agenda_items
            JOIN agenda_points ON agenda_points.id = agenda_items.point_id
            JOIN meetings ON meetings.id = agenda_points.meeting_id
            WHERE agenda_items.is_resolved = 0
        """
        params = []
        if owner and owner != "Všichni":
            query += " AND agenda_items.owner = ?"
            params.append(owner)
        query += " ORDER BY meetings.date DESC, agenda_points.id, agenda_items.id"
        c.execute(query, params)

        tasks = []
        today = datetime.now().date()
        search_text = (search_text or "").strip().lower()
        for item_id, description, task_owner, due_date, point_id, point_title, meeting_id, meeting_title, meeting_date in c.fetchall():
            parsed_due = self.parse_due_date(due_date)
            if overdue_only and not (parsed_due and parsed_due < today):
                continue
            haystack = " ".join(
                (
                    description or "",
                    task_owner or "",
                    due_date or "",
                    point_title or "",
                    meeting_title or "",
                    meeting_date or "",
                    self.format_czech_date(meeting_date),
                )
            ).lower()
            if search_text and search_text not in haystack:
                continue
            tasks.append(
                {
                    "item_id": item_id,
                    "description": description,
                    "owner": task_owner or "",
                    "due_date": due_date or "",
                    "parsed_due": parsed_due,
                    "point_id": point_id,
                    "point_title": point_title,
                    "meeting_id": meeting_id,
                    "meeting_title": meeting_title,
                    "meeting_date": meeting_date,
                }
            )

        max_date = datetime.max.date()
        tasks.sort(
            key=lambda task: (
                task["parsed_due"] is None,
                task["parsed_due"] or max_date,
                (task["owner"] or "").lower(),
                task["meeting_title"].lower(),
            )
        )
        return tasks


    def get_task_status(self, parsed_due):
        if not parsed_due:
            return "Bez termínu", "no_due"

        today = datetime.now().date()
        if parsed_due < today:
            return "Po termínu", "overdue"
        if parsed_due == today:
            return "Dnes", "today"
        return "Otevřeno", "open"


    def populate_task_overview(self, tree, owner, overdue_only, count_label, search_text=""):
        tree.delete(*tree.get_children())
        tasks = self.fetch_open_tasks(owner=owner, overdue_only=overdue_only, search_text=search_text)

        for task in tasks:
            status, tag = self.get_task_status(task["parsed_due"])
            tree.insert(
                "",
                tk.END,
                iid=str(task["item_id"]),
                values=(
                    task["due_date"] or "-",
                    status,
                    task["owner"] or "-",
                    f"{self.format_czech_date(task['meeting_date'])} | {task['meeting_title']}",
                    task["point_title"],
                    task["description"],
                ),
                tags=(tag,) if tag else (),
            )

        suffix = " nalezených" if search_text.strip() else " otevřených"
        count_label.config(text=f"{len(tasks)}{suffix} úkolů")


    def open_selected_task(self, tree, dialog, refresh_callback=None):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled úkolů", "Nejprve vyberte úkol.")
            return

        item_id = int(selection[0])
        self.show_task_popup(item_id, refresh_callback=refresh_callback)


    def fetch_task_detail(self, item_id):
        c = self.conn.cursor()
        c.execute(
            """SELECT
                   agenda_items.id,
                   agenda_items.description,
                   agenda_items.owner,
                   agenda_items.due_date,
                   agenda_items.due_date_reason,
                   agenda_items.is_resolved,
                   agenda_points.id,
                   agenda_points.title,
                   meetings.id,
                   meetings.title,
                   meetings.date
               FROM agenda_items
               JOIN agenda_points ON agenda_points.id = agenda_items.point_id
               JOIN meetings ON meetings.id = agenda_points.meeting_id
               WHERE agenda_items.id = ?""",
            (item_id,),
        )
        return c.fetchone()


    def show_task_popup(self, item_id, refresh_callback=None):
        row = self.fetch_task_detail(item_id)
        if not row:
            messagebox.showwarning("Přehled úkolů", "Vybraný úkol už neexistuje.")
            return

        (
            task_id,
            description,
            owner,
            due_date,
            due_date_reason,
            is_resolved,
            point_id,
            point_title,
            meeting_id,
            meeting_title,
            meeting_date,
        ) = row

        popup, content = self.create_dialog("Detail úkolu", 740, 540, 600, 430, modal=True)
        content.columnconfigure(1, weight=1)

        tk.Label(
            content,
            text="Detail úkolu",
            font=(self.FONT, 18, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew")

        meta = f"{self.format_czech_date(meeting_date)} | {meeting_title} | {point_title}"
        tk.Label(
            content,
            text=meta,
            font=(self.FONT, 10),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 18))

        tk.Label(
            content,
            text="Úkol",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="nw",
        ).grid(row=2, column=0, sticky="nw", pady=(0, 12), padx=(0, 12))

        description_text = tk.Text(content, height=5, wrap=tk.WORD, font=(self.FONT, 10), relief=tk.SOLID, borderwidth=1)
        description_text.insert("1.0", description or "")
        description_text.grid(row=2, column=1, sticky="nsew", pady=(0, 12))

        owner_var = tk.StringVar(value=owner or "")
        due_date_var = tk.StringVar(value=due_date or "")
        resolved_var = tk.BooleanVar(value=bool(is_resolved))

        tk.Label(
            content,
            text="Odpovědnost",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).grid(row=3, column=0, sticky="w", pady=(0, 8), padx=(0, 12))

        fields = tk.Frame(content, bg=self.COLORS["panel"])
        fields.grid(row=3, column=1, sticky="ew", pady=(0, 8))
        fields.columnconfigure(0, weight=1)
        fields.columnconfigure(1, weight=1)

        owner_entry = ttk.Combobox(fields, textvariable=owner_var, values=self.get_owner_filter_values(), font=(self.FONT, 10))
        owner_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=3)

        today = datetime.now().date()
        due_entry = ttk.Combobox(
            fields,
            textvariable=due_date_var,
            values=[(today + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(0, 366)],
            font=(self.FONT, 10),
        )
        due_entry.grid(row=0, column=1, sticky="ew", ipady=3)

        resolved_check = tk.Checkbutton(
            fields,
            text="Splněno",
            variable=resolved_var,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["panel"],
            activeforeground=self.COLORS["text"],
            selectcolor=self.COLORS["panel"],
            font=(self.FONT, 10),
            relief=tk.FLAT,
            borderwidth=0,
        )
        resolved_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        tk.Label(
            content,
            text="Důvod prodloužení",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="nw",
        ).grid(row=4, column=0, sticky="nw", pady=(8, 0), padx=(0, 12))

        reason_text = tk.Text(content, height=3, wrap=tk.WORD, font=(self.FONT, 10), relief=tk.SOLID, borderwidth=1)
        reason_text.insert("1.0", due_date_reason or "")
        reason_text.grid(row=4, column=1, sticky="ew", pady=(8, 0))

        if not self.can_edit():
            description_text.config(state=tk.DISABLED)
            owner_entry.config(state="disabled")
            due_entry.config(state="disabled")
            resolved_check.config(state=tk.DISABLED)
            reason_text.config(state=tk.DISABLED)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(20, 0))

        def save_popup_task():
            if not self.require_admin():
                return

            new_description = description_text.get("1.0", tk.END).strip()
            if not new_description:
                messagebox.showwarning("Detail úkolu", "Zadejte text úkolu.")
                return
            new_due_date = due_date_var.get().strip()
            new_reason = reason_text.get("1.0", tk.END).strip()
            old_due = self.parse_due_date(due_date)
            parsed_new_due = self.parse_due_date(new_due_date)
            if new_due_date and not parsed_new_due:
                messagebox.showwarning("Detail úkolu", "Zadejte platný termín, například 13.05.2026, nebo pole vymažte.")
                due_entry.focus_set()
                return
            if parsed_new_due:
                new_due_date = parsed_new_due.strftime("%d.%m.%Y")
            if old_due and parsed_new_due and parsed_new_due > old_due and not new_reason:
                messagebox.showwarning(
                    "Důvod prodloužení",
                    "Termín byl prodloužen. Doplňte prosím důvod prodloužení termínu.",
                )
                reason_text.focus_set()
                return

            c = self.conn.cursor()
            c.execute(
                """UPDATE agenda_items
                   SET description=?, owner=?, due_date=?, due_date_reason=?, is_resolved=?
                   WHERE id=?""",
                (
                    new_description,
                    owner_var.get().strip(),
                    new_due_date,
                    new_reason,
                    1 if resolved_var.get() else 0,
                    task_id,
                ),
            )
            self.commit_database()
            self.refresh_dashboard_summary()
            self.refresh_item_description_choices()
            self.refresh_owner_choices()
            if self.current_id == meeting_id:
                self.load_meeting_details()
                self.select_agenda_item(task_id)
            if refresh_callback:
                refresh_callback()
            popup.destroy()

        def open_meeting_from_popup():
            if self.current_id and self.notes_dirty:
                self.save_notes(show_message=False)
            self.current_id = meeting_id
            self.show_open_only.set(False)
            self.load_meetings()
            self.load_meeting_details()
            self.select_agenda_item(task_id)
            popup.destroy()
            self.root.lift()
            self.root.focus_force()

        self.create_button(
            actions,
            text="Uložit",
            command=save_popup_task,
            variant="primary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT)
        self.create_button(actions, text="Otevřít poradu", command=open_meeting_from_popup, variant="secondary").pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(actions, text="Zavřít", command=popup.destroy, variant="secondary").pack(side=tk.RIGHT)

        if self.can_edit():
            description_text.focus_set()

