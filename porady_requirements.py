# -*- coding: utf-8 -*-

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk


class RequirementMixin:

    def show_requirement_overview(self):
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

        dialog, content = self.create_dialog("Přehled požadavků", 1180, 680, 900, 500)
        self.create_dialog_header(
            content,
            "Přehled požadavků z porad",
            "Požadavky jsou vedeny samostatně mimo úkoly, body programu a nařízení.",
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
            values=["Všichni"] + self.get_requirement_owner_filter_values(),
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

        columns = ("meeting_date", "status", "due_date", "owner", "meeting", "description")
        tree_frame = tk.Frame(content, bg=self.COLORS["panel"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("meeting_date", text="Porada dne")
        tree.heading("status", text="Stav")
        tree.heading("due_date", text="Termín")
        tree.heading("owner", text="Odpovědnost")
        tree.heading("meeting", text="Porada")
        tree.heading("description", text="Požadavek")
        tree.column("meeting_date", width=95, anchor="w", stretch=False)
        tree.column("status", width=90, anchor="w", stretch=False)
        tree.column("due_date", width=95, anchor="w", stretch=False)
        tree.column("owner", width=140, anchor="w", stretch=False)
        tree.column("meeting", width=220, anchor="w")
        tree.column("description", width=500, anchor="w")
        tree.tag_configure("resolved", foreground=self.COLORS["success"])
        tree.tag_configure("overdue", foreground=self.COLORS["danger"])
        tree.tag_configure("today", foreground=self.COLORS["warning"])
        tree.tag_configure("no_due", foreground=self.COLORS["muted"])

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(14, 0))

        refresh = lambda: self.populate_requirement_overview(
            tree,
            owner_var.get(),
            status_var.get(),
            search_var.get(),
            count_label,
        )
        owner_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        status_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        search_entry.bind("<KeyRelease>", lambda event: refresh())
        tree.bind("<Double-1>", lambda event: self.open_selected_requirement_dialog(tree, refresh))
        tree.bind("<Return>", lambda event: self.open_selected_requirement_dialog(tree, refresh))

        self.create_button(
            actions,
            text="Nový požadavek",
            command=lambda: self.show_requirement_dialog(refresh_callback=refresh),
            variant="primary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT)

        self.create_button(
            actions,
            text="Upravit vybrané",
            command=lambda: self.open_selected_requirement_dialog(tree, refresh),
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Smazat vybrané",
            command=lambda: self.delete_selected_requirement(tree, refresh),
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Otevřít poradu",
            command=lambda: self.open_selected_requirement_meeting(tree),
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(actions, text="Obnovit", command=refresh, variant="secondary").pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)

        refresh()


    def get_requirement_owner_filter_values(self):
        c = self.conn.cursor()
        c.execute(
            """SELECT DISTINCT owner FROM meeting_requirements
               WHERE owner IS NOT NULL AND TRIM(owner) <> ''
               ORDER BY owner"""
        )
        return [row[0] for row in c.fetchall()]


    def fetch_requirements(self, owner=None, status_filter="Všechna", search_text=""):
        c = self.conn.cursor()
        query = """
            SELECT
                meeting_requirements.id,
                meeting_requirements.description,
                meeting_requirements.owner,
                meeting_requirements.due_date,
                meeting_requirements.is_resolved,
                meeting_requirements.meeting_id,
                meetings.title,
                meetings.date
            FROM meeting_requirements
            LEFT JOIN meetings ON meetings.id = meeting_requirements.meeting_id
        """
        params = []
        if owner and owner != "Všichni":
            query += " WHERE meeting_requirements.owner = ?"
            params.append(owner)
        query += " ORDER BY meetings.date DESC, meeting_requirements.id DESC"
        c.execute(query, params)

        requirements = []
        today = datetime.now().date()
        search_text = (search_text or "").strip().lower()
        for row in c.fetchall():
            requirement_id, description, item_owner, due_date, is_resolved, meeting_id, meeting_title, meeting_date = row
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
                    item_owner or "",
                    due_date or "",
                    meeting_title or "",
                    meeting_date or "",
                    formatted_meeting_date,
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

            requirements.append(
                {
                    "requirement_id": requirement_id,
                    "description": description or "",
                    "owner": item_owner or "",
                    "due_date": due_date or "",
                    "parsed_due": parsed_due,
                    "is_resolved": is_resolved,
                    "status_text": status_text,
                    "tag": tag,
                    "meeting_id": meeting_id,
                    "meeting_title": meeting_title or "",
                    "meeting_date": meeting_date or "",
                    "formatted_meeting_date": formatted_meeting_date,
                }
            )
        max_date = datetime.max.date()
        requirements.sort(
            key=lambda item: (
                item["is_resolved"] == 1,
                item["parsed_due"] is None,
                item["parsed_due"] or max_date,
                item["meeting_date"] or "",
                item["meeting_title"].lower(),
            )
        )
        return requirements


    def populate_requirement_overview(self, tree, owner, status_filter, search_text, count_label):
        tree.delete(*tree.get_children())
        requirements = self.fetch_requirements(owner=owner, status_filter=status_filter, search_text=search_text)

        for item in requirements:
            tree.insert(
                "",
                tk.END,
                iid=str(item["requirement_id"]),
                values=(
                    item["formatted_meeting_date"] or "-",
                    item["status_text"],
                    item["due_date"] or "-",
                    item["owner"] or "-",
                    item["meeting_title"] or "-",
                    item["description"],
                ),
                tags=(item["tag"],) if item["tag"] else (),
            )

        if search_text.strip():
            suffix = " nalezených"
        elif status_filter != "Všechna":
            suffix = f" ({status_filter.lower()})"
        else:
            suffix = ""
        count_label.config(text=f"{len(requirements)} požadavků{suffix}")


    def fetch_requirement_detail(self, requirement_id):
        c = self.conn.cursor()
        c.execute(
            """SELECT id, meeting_id, description, owner, due_date, is_resolved
               FROM meeting_requirements
               WHERE id=?""",
            (requirement_id,),
        )
        return c.fetchone()


    def show_requirement_dialog(self, requirement_id=None, refresh_callback=None):
        if not self.require_admin():
            return

        choices, meeting_mapping = self.get_meeting_choices()
        if not choices:
            messagebox.showwarning("Požadavky", "Nejprve vytvořte poradu, ze které požadavek vychází.")
            return

        existing = self.fetch_requirement_detail(requirement_id) if requirement_id else None
        if requirement_id and not existing:
            messagebox.showwarning("Požadavky", "Vybraný požadavek už neexistuje.")
            if refresh_callback:
                refresh_callback()
            return

        title = "Upravit požadavek" if existing else "Nový požadavek"
        dialog, content = self.create_dialog(title, 760, 520, 640, 430, modal=True)
        self.create_dialog_header(
            content,
            title,
            "Požadavek se ukládá samostatně a není svázaný s úkoly, body programu ani nařízeními.",
        )
        form = tk.Frame(content, bg=self.COLORS["panel"])
        form.pack(fill=tk.BOTH, expand=True)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(1, weight=1)

        meeting_var = tk.StringVar()
        owner_var = tk.StringVar()
        due_date_var = tk.StringVar(value=self.get_today_due_date())
        resolved_var = tk.BooleanVar(value=False)

        if existing:
            _, meeting_id, description, owner, due_date, is_resolved = existing
            for label, mapped_id in meeting_mapping.items():
                if mapped_id == meeting_id:
                    meeting_var.set(label)
                    break
            owner_var.set(owner or "")
            due_date_var.set(due_date or "")
            resolved_var.set(is_resolved == 1)
        else:
            if self.current_id:
                for label, mapped_id in meeting_mapping.items():
                    if mapped_id == self.current_id:
                        meeting_var.set(label)
                        break
            if not meeting_var.get():
                meeting_var.set(choices[0])
            description = ""

        tk.Label(form, text="Porada", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).grid(
            row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 12)
        )
        meeting_entry = ttk.Combobox(form, textvariable=meeting_var, values=choices, state="readonly", font=(self.FONT, 10))
        meeting_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10), ipady=3)

        tk.Label(
            form,
            text="Požadavek",
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

        owner_entry = ttk.Combobox(field_row, textvariable=owner_var, values=self.get_requirement_owner_filter_values(), font=(self.FONT, 10))
        owner_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=3)

        due_entry = ttk.Combobox(
            field_row,
            textvariable=due_date_var,
            values=[(datetime.now().date() + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(0, 366)],
            font=(self.FONT, 10),
        )
        due_entry.grid(row=0, column=1, sticky="ew", ipady=3)

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

        actions = tk.Frame(form, bg=self.COLORS["panel"])
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        def save_requirement():
            selected_meeting = meeting_var.get()
            meeting_id = meeting_mapping.get(selected_meeting)
            description_value = description_text.get("1.0", tk.END).strip()
            owner_value = owner_var.get().strip()
            due_date_value = due_date_var.get().strip()
            parsed_due = self.parse_due_date(due_date_value)

            if not meeting_id:
                messagebox.showwarning("Požadavky", "Vyberte poradu.")
                meeting_entry.focus_set()
                return
            if not description_value:
                messagebox.showwarning("Požadavky", "Zadejte text požadavku.")
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
                c.execute(
                    """UPDATE meeting_requirements
                       SET meeting_id=?, description=?, owner=?, due_date=?, is_resolved=?, completed_at=?
                       WHERE id=?""",
                    (
                        meeting_id,
                        description_value,
                        owner_value,
                        due_date_value,
                        is_resolved,
                        completed_at,
                        requirement_id,
                    ),
                )
            else:
                c.execute(
                    """INSERT INTO meeting_requirements
                       (meeting_id, description, owner, due_date, is_resolved, created_at, completed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        meeting_id,
                        description_value,
                        owner_value,
                        due_date_value,
                        is_resolved,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        completed_at,
                    ),
                )
            self.commit_database()
            if refresh_callback:
                refresh_callback()
            dialog.destroy()

        self.create_button(actions, text="Uložit", command=save_requirement, variant="primary").pack(side=tk.LEFT)
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)
        description_text.focus_set()


    def open_selected_requirement_dialog(self, tree, refresh_callback=None):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled požadavků", "Nejprve vyberte požadavek.")
            return
        self.show_requirement_dialog(requirement_id=int(selection[0]), refresh_callback=refresh_callback)


    def delete_selected_requirement(self, tree, refresh_callback=None):
        if not self.require_admin():
            return

        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled požadavků", "Nejprve vyberte požadavek.")
            return
        if not messagebox.askyesno("Smazat požadavek", "Opravdu chcete vybraný požadavek smazat?"):
            return

        c = self.conn.cursor()
        c.execute("DELETE FROM meeting_requirements WHERE id=?", (int(selection[0]),))
        self.commit_database()
        if refresh_callback:
            refresh_callback()


    def open_selected_requirement_meeting(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Přehled požadavků", "Nejprve vyberte požadavek.")
            return

        row = self.fetch_requirement_detail(int(selection[0]))
        if not row or not row[1]:
            messagebox.showwarning("Přehled požadavků", "Porada pro vybraný požadavek už neexistuje.")
            return
        if self.current_id and self.notes_dirty:
            self.save_notes(show_message=False)
        self.current_id = row[1]
        self.show_open_only.set(False)
        self.load_meetings()
        self.load_meeting_details()
        self.root.lift()
        self.root.focus_force()
