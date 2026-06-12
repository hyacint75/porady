# -*- coding: utf-8 -*-

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from porady_widgets import configure_treeview_sorting, reapply_treeview_sorting


class OrderMixin:

    def show_order_overview(self, parent=None):
        embedded = parent is not None
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

        if embedded:
            dialog = None
            content = parent
        else:
            dialog, content = self.create_dialog("Přehled nařízení", 1180, 680, 900, 500)
        self.create_dialog_header(
            content,
            "Přehled nařízení z porad",
            "Nařízení jsou vedena samostatně mimo úkoly a body programu.",
            right_widget=add_count_label,
            accent=self.COLORS["page_orders_accent"],
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
            values=["Všichni"] + self.get_people_values(),
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

        quick_filters = tk.Frame(content, bg=self.COLORS["panel"])
        quick_filters.pack(fill=tk.X, pady=(0, 12))

        columns = ("meeting_date", "status", "priority", "due_date", "owner", "meeting", "description")
        tree_frame = tk.Frame(content, bg=self.COLORS["panel"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("meeting_date", text="Porada dne")
        tree.heading("status", text="Stav")
        tree.heading("priority", text="Priorita")
        tree.heading("due_date", text="Termín")
        tree.heading("owner", text="Odpovědnost")
        tree.heading("meeting", text="Porada")
        tree.heading("description", text="Nařízení")
        configure_treeview_sorting(
            tree,
            column_types={"meeting_date": "date", "due_date": "date"},
        )
        tree.column("meeting_date", width=95, anchor="w", stretch=False)
        tree.column("status", width=90, anchor="w", stretch=False)
        tree.column("priority", width=85, anchor="w", stretch=False)
        tree.column("due_date", width=95, anchor="w", stretch=False)
        tree.column("owner", width=140, anchor="w", stretch=False)
        tree.column("meeting", width=220, anchor="w")
        tree.column("description", width=500, anchor="w")
        self.configure_status_tags(tree)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(14, 0))
        edit_buttons = []

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
        tree.bind("<Double-1>", lambda event: self.open_selected_order_dialog(tree, refresh))
        tree.bind("<Return>", lambda event: self.open_selected_order_dialog(tree, refresh))

        def set_my_orders():
            owner = self.get_my_owner_value()
            if not owner:
                messagebox.showwarning("Moje položky", "Uživatelské jméno Windows není v seznamu odpovědných osob.")
                return
            owner_var.set(owner)
            status_var.set("Otevřená")
            refresh()

        self.create_button(quick_filters, text="Moje", command=set_my_orders, variant="secondary").pack(side=tk.LEFT)
        self.create_button(quick_filters, text="Otevřené", command=lambda: (status_var.set("Otevřená"), refresh()), variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(quick_filters, text="Dnes", command=lambda: (status_var.set("Dnes"), refresh()), variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(quick_filters, text="Po termínu", command=lambda: (status_var.set("Po termínu"), refresh()), variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(
            quick_filters,
            text="Reset",
            command=lambda: (owner_var.set("Všichni"), status_var.set("Všechna"), search_var.set(""), refresh()),
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(8, 0))

        button = self.create_button(
            actions,
            text="Nové nařízení",
            command=lambda: self.show_order_dialog(refresh_callback=refresh),
            variant="primary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        )
        button.pack(side=tk.LEFT)
        edit_buttons.append(button)

        button = self.create_button(
            actions,
            text="Upravit vybrané",
            command=lambda: self.open_selected_order_dialog(tree, refresh),
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        )
        button.pack(side=tk.LEFT, padx=(10, 0))
        edit_buttons.append(button)

        button = self.create_button(
            actions,
            text="Smazat vybrané",
            command=lambda: self.delete_selected_order(tree, refresh),
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        )
        button.pack(side=tk.LEFT, padx=(10, 0))
        edit_buttons.append(button)

        self.create_button(
            actions,
            text="Otevřít poradu",
            command=lambda: self.open_selected_order_meeting(tree),
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Obnovit",
            command=refresh,
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))

        if not embedded:
            self.create_button(
                actions,
                text="Zavřít",
                command=dialog.destroy,
                variant="secondary",
            ).pack(side=tk.RIGHT)

        if embedded:
            self.order_tab_refresh = refresh
            self.order_tab_edit_buttons = edit_buttons
        refresh()


    def get_order_owner_filter_values(self):
        c = self.conn.cursor()
        c.execute(
            """SELECT DISTINCT owner FROM meeting_orders
               WHERE owner IS NOT NULL AND TRIM(owner) <> ''
               ORDER BY owner"""
        )
        return [row[0] for row in c.fetchall()]


    def get_meeting_choices(self):
        c = self.conn.cursor()
        c.execute("SELECT id, title, date FROM meetings ORDER BY date DESC, id DESC")
        meetings = c.fetchall()
        choices = []
        mapping = {}
        for meeting_id, title, meeting_date in meetings:
            label = f"{self.format_czech_date(meeting_date)} | {title}"
            choices.append(label)
            mapping[label] = meeting_id
        return choices, mapping


    def fetch_orders(self, owner=None, status_filter="Všechna", search_text=""):
        c = self.conn.cursor()
        query = """
            SELECT
                meeting_orders.id,
                meeting_orders.description,
                meeting_orders.owner,
                meeting_orders.due_date,
                meeting_orders.is_resolved,
                COALESCE(meeting_orders.priority, 'Normální'),
                meeting_orders.meeting_id,
                meetings.title,
                meetings.date
            FROM meeting_orders
            LEFT JOIN meetings ON meetings.id = meeting_orders.meeting_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM meeting_orders AS copied_order
                WHERE copied_order.copied_from_order_id = meeting_orders.id
            )
        """
        params = []
        if owner and owner != "Všichni":
            query += " AND meeting_orders.owner = ?"
            params.append(owner)
        query += " ORDER BY meetings.date DESC, meeting_orders.id DESC"
        c.execute(query, params)

        orders = []
        today = datetime.now().date()
        search_text = (search_text or "").strip().lower()
        for order_id, description, order_owner, due_date, is_resolved, priority, meeting_id, meeting_title, meeting_date in c.fetchall():
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

            formatted_meeting_date = self.format_czech_date(meeting_date) if meeting_date else ""
            haystack = " ".join(
                (
                    description or "",
                    order_owner or "",
                    due_date or "",
                    meeting_title or "",
                    meeting_date or "",
                    formatted_meeting_date,
                )
            ).lower()
            if search_text and search_text not in haystack:
                continue

            status_text, tag = self.get_record_status(due_date, is_resolved)

            orders.append(
                {
                    "order_id": order_id,
                    "description": description or "",
                    "owner": order_owner or "",
                    "due_date": due_date or "",
                    "parsed_due": parsed_due,
                    "is_resolved": is_resolved,
                    "priority": priority or "Normální",
                    "status_text": status_text,
                    "tag": tag,
                    "meeting_id": meeting_id,
                    "meeting_title": meeting_title or "",
                    "meeting_date": meeting_date or "",
                    "formatted_meeting_date": formatted_meeting_date,
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
                iid=str(order["order_id"]),
                values=(
                    order["formatted_meeting_date"] or "-",
                    order["status_text"],
                    order["priority"],
                    order["due_date"] or "-",
                    order["owner"] or "-",
                    order["meeting_title"] or "-",
                    order["description"],
                ),
                tags=(order["tag"],) if order["tag"] else (),
            )

        reapply_treeview_sorting(tree)
        if search_text.strip():
            suffix = " nalezených"
        elif status_filter != "Všechna":
            suffix = f" ({status_filter.lower()})"
        else:
            suffix = ""
        count_label.config(text=f"{len(orders)} nařízení{suffix}")


    def fetch_order_detail(self, order_id):
        c = self.conn.cursor()
        c.execute(
            """SELECT id, meeting_id, description, owner, due_date, is_resolved, COALESCE(priority, 'Normální')
               FROM meeting_orders
               WHERE id=?""",
            (order_id,),
        )
        return c.fetchone()


    def show_order_dialog(self, order_id=None, refresh_callback=None):
        if not self.require_admin():
            return

        choices, meeting_mapping = self.get_meeting_choices()
        if not choices:
            messagebox.showwarning("Nařízení", "Nejprve vytvořte poradu, ze které nařízení vychází.")
            return

        existing = self.fetch_order_detail(order_id) if order_id else None
        if order_id and not existing:
            messagebox.showwarning("Nařízení", "Vybrané nařízení už neexistuje.")
            if refresh_callback:
                refresh_callback()
            return

        title = "Upravit nařízení" if existing else "Nové nařízení"
        dialog, content = self.create_dialog(title, 760, 520, 640, 430, modal=True)
        self.create_dialog_header(
            content,
            title,
            "Nařízení se ukládá samostatně a není svázané s úkoly ani body programu.",
            accent=self.COLORS["page_orders_accent"],
        )
        form = tk.Frame(content, bg=self.COLORS["panel"])
        form.pack(fill=tk.BOTH, expand=True)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(1, weight=1)

        meeting_var = tk.StringVar()
        owner_var = tk.StringVar()
        due_date_var = tk.StringVar(value=self.get_today_due_date())
        resolved_var = tk.BooleanVar(value=False)
        priority_var = tk.StringVar(value="Normální")

        if existing:
            _, meeting_id, description, owner, due_date, is_resolved, priority = existing
            for label, mapped_id in meeting_mapping.items():
                if mapped_id == meeting_id:
                    meeting_var.set(label)
                    break
            owner_var.set(owner or "")
            due_date_var.set(due_date or "")
            resolved_var.set(is_resolved == 1)
            priority_var.set(priority or "Normální")
        else:
            if self.current_id:
                for label, mapped_id in meeting_mapping.items():
                    if mapped_id == self.current_id:
                        meeting_var.set(label)
                        break
            if not meeting_var.get():
                meeting_var.set(choices[0])
            description = ""

        tk.Label(
            form,
            text="Porada",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        meeting_entry = ttk.Combobox(
            form,
            textvariable=meeting_var,
            values=choices,
            state="readonly",
            font=(self.FONT, 10),
        )
        meeting_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10), ipady=3)

        tk.Label(
            form,
            text="Nařízení",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="nw",
        ).grid(row=1, column=0, sticky="nw", pady=(0, 10), padx=(0, 12))
        description_text = tk.Text(form, height=6, wrap=tk.WORD, font=(self.FONT, 10), relief=tk.SOLID, borderwidth=1)
        description_text.insert("1.0", description or "")
        description_text.grid(row=1, column=1, sticky="nsew", pady=(0, 10))

        tk.Label(
            form,
            text="Odpovědnost",
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        ).grid(row=2, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        field_row = tk.Frame(form, bg=self.COLORS["panel"])
        field_row.grid(row=2, column=1, sticky="ew", pady=(0, 10))
        field_row.columnconfigure(0, weight=1)
        field_row.columnconfigure(1, weight=1)

        owner_entry = ttk.Combobox(
            field_row,
            textvariable=owner_var,
            values=self.get_people_values(),
            font=(self.FONT, 10),
        )
        owner_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=3)

        due_entry = ttk.Combobox(
            field_row,
            textvariable=due_date_var,
            values=[(datetime.now().date() + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(0, 366)],
            font=(self.FONT, 10),
        )
        due_entry.grid(row=0, column=1, sticky="ew", ipady=3)
        due_entry.bind("<Button-1>", lambda event: self.open_date_picker_for_variable(due_date_var, due_entry))

        resolved_check = tk.Checkbutton(
            field_row,
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

        priority_entry = ttk.Combobox(
            field_row,
            textvariable=priority_var,
            values=self.PRIORITY_VALUES,
            state="readonly",
            font=(self.FONT, 10),
        )
        priority_entry.grid(row=1, column=1, sticky="ew", pady=(10, 0), ipady=3)

        actions = tk.Frame(form, bg=self.COLORS["panel"])
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        def save_order():
            selected_meeting = meeting_var.get()
            meeting_id = meeting_mapping.get(selected_meeting)
            description_value = description_text.get("1.0", tk.END).strip()
            owner_value = owner_var.get().strip()
            due_date_value = due_date_var.get().strip()
            parsed_due = self.parse_due_date(due_date_value)

            if not meeting_id:
                messagebox.showwarning("Nařízení", "Vyberte poradu.")
                meeting_entry.focus_set()
                return
            if not description_value:
                messagebox.showwarning("Nařízení", "Zadejte text nařízení.")
                description_text.focus_set()
                return
            if due_date_value and not parsed_due:
                messagebox.showwarning("Termín", "Zadejte platný termín, například 13.05.2026, nebo pole vymažte.")
                due_entry.focus_set()
                return
            if parsed_due:
                due_date_value = parsed_due.strftime("%d.%m.%Y")

            is_resolved = 1 if resolved_var.get() else 0
            completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if is_resolved else ""
            c = self.conn.cursor()
            if existing:
                previous = {
                    "porada": existing[1],
                    "text": existing[2],
                    "odpovědnost": existing[3],
                    "termín": existing[4],
                    "stav": "splněno" if existing[5] == 1 else "otevřeno",
                    "priorita": existing[6],
                }
                c.execute(
                    """UPDATE meeting_orders
                       SET meeting_id=?, description=?, owner=?, due_date=?, is_resolved=?, completed_at=?, priority=?
                       WHERE id=?""",
                    (
                        meeting_id,
                        description_value,
                        owner_value,
                        due_date_value,
                        is_resolved,
                        completed_at,
                        priority_var.get(),
                        order_id,
                    ),
                )
                self.log_field_changes(
                    "nařízení",
                    order_id,
                    meeting_id,
                    previous,
                    {
                        "porada": meeting_id,
                        "text": description_value,
                        "odpovědnost": owner_value,
                        "termín": due_date_value,
                        "stav": "splněno" if is_resolved else "otevřeno",
                        "priorita": priority_var.get(),
                    },
                )
            else:
                c.execute(
                    """INSERT INTO meeting_orders
                       (meeting_id, description, owner, due_date, is_resolved, created_at, completed_at, priority)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        meeting_id,
                        description_value,
                        owner_value,
                        due_date_value,
                        is_resolved,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        completed_at,
                        priority_var.get(),
                    ),
                )
                self.log_change("nařízení", c.lastrowid, meeting_id, "vytvořeno", "", description_value)
            self.commit_database()
            self.refresh_dashboard_summary()
            if refresh_callback:
                refresh_callback()
            dialog.destroy()

        self.create_button(actions, text="Uložit", command=save_order, variant="primary").pack(side=tk.LEFT)
        if existing:
            self.create_button(
                actions,
                text="Historie",
                command=lambda: self.show_history_dialog("nařízení", order_id, existing[1]),
                variant="secondary",
            ).pack(side=tk.LEFT, padx=(10, 0))
            self.create_button(
                actions,
                text="Komentáře",
                command=lambda: self.show_comments_dialog("nařízení", order_id, existing[1]),
                variant="secondary",
            ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)
        description_text.focus_set()


    def open_selected_order_dialog(self, tree, refresh_callback=None):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled nařízení", "Nejprve vyberte nařízení.")
            return
        self.show_order_dialog(order_id=int(selection[0]), refresh_callback=refresh_callback)


    def delete_selected_order(self, tree, refresh_callback=None):
        if not self.require_admin():
            return

        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled nařízení", "Nejprve vyberte nařízení.")
            return
        if not messagebox.askyesno("Smazat nařízení", "Opravdu chcete vybrané nařízení smazat?"):
            return

        c = self.conn.cursor()
        self.log_audit("smazání nařízení", selection[0])
        c.execute("DELETE FROM meeting_orders WHERE id=?", (int(selection[0]),))
        self.commit_database()
        self.refresh_dashboard_summary()
        if refresh_callback:
            refresh_callback()


    def open_selected_order_meeting(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled nařízení", "Nejprve vyberte nařízení.")
            return

        row = self.fetch_order_detail(int(selection[0]))
        if not row or not row[1]:
            messagebox.showwarning("Přehled nařízení", "Porada pro vybrané nařízení už neexistuje.")
            return
        if self.current_id and self.notes_dirty:
            self.save_notes(show_message=False)
        self.current_id = row[1]
        self.show_open_only.set(False)
        self.load_meetings()
        self.load_meeting_details()
        self.root.lift()
        self.root.focus_force()
