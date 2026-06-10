# -*- coding: utf-8 -*-

import html
import os
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk


class ProblemMixin:
    PROBLEM_PRIORITY_VALUES = ("Nízká", "Normální", "Vysoká", "Kritická")
    PROBLEM_STATUS_VALUES = ("Nový", "V řešení", "Ověření účinnosti", "Uzavřeno")

    def show_problem_overview(self, standalone=False, close_callback=None):
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

        dialog, content = self.create_dialog("Problémy a nápravná opatření", 1220, 700, 940, 520)

        def close_overview():
            dialog.destroy()
            if close_callback:
                close_callback()

        if standalone:
            dialog.protocol("WM_DELETE_WINDOW", close_overview)

        self.create_dialog_header(
            content,
            "Problémy a nápravná opatření",
            "Samostatná evidence problémů, příčin, opatření, odpovědností a termínů.",
            right_widget=add_count_label,
            accent=self.COLORS["page_problems_accent"],
        )
        count_label = count_label_holder["label"]

        filters = tk.Frame(content, bg=self.COLORS["panel"])
        filters.pack(fill=tk.X, pady=(0, 12))

        tk.Label(filters, text="Odpovědnost", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).pack(side=tk.LEFT, padx=(0, 8))
        owner_var = tk.StringVar(value="Všichni")
        owner_filter = ttk.Combobox(filters, textvariable=owner_var, state="readonly", width=20, font=(self.FONT, 10), values=["Všichni"] + self.get_people_values())
        owner_filter.pack(side=tk.LEFT, padx=(0, 16), ipady=3)

        tk.Label(filters, text="Stav", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).pack(side=tk.LEFT, padx=(0, 8))
        status_var = tk.StringVar(value="Všechny")
        status_filter = ttk.Combobox(
            filters,
            textvariable=status_var,
            state="readonly",
            width=18,
            font=(self.FONT, 10),
            values=["Všechny", "Otevřené", "Po termínu", "Dnes"] + list(self.PROBLEM_STATUS_VALUES),
        )
        status_filter.pack(side=tk.LEFT, padx=(0, 16), ipady=3)

        tk.Label(filters, text="Zdroj", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).pack(side=tk.LEFT, padx=(0, 8))
        source_var = tk.StringVar(value="Vše")
        source_filter = ttk.Combobox(
            filters,
            textvariable=source_var,
            state="readonly",
            width=13,
            font=(self.FONT, 10),
            values=["Vše", "Z požadavku", "Ručně"],
        )
        source_filter.pack(side=tk.LEFT, padx=(0, 16), ipady=3)

        tk.Label(filters, text="Hledat", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).pack(side=tk.LEFT, padx=(0, 8))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filters, textvariable=search_var, font=(self.FONT, 10), width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        quick_filters = tk.Frame(content, bg=self.COLORS["panel"])
        quick_filters.pack(fill=tk.X, pady=(0, 12))

        columns = ("created_at", "status", "priority", "due_date", "owner", "meeting", "requirement", "problem", "action")
        tree_frame = tk.Frame(content, bg=self.COLORS["panel"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("created_at", text="Zadáno")
        tree.heading("status", text="Stav")
        tree.heading("priority", text="Priorita")
        tree.heading("due_date", text="Termín")
        tree.heading("owner", text="Odpovědnost")
        tree.heading("meeting", text="Porada")
        tree.heading("requirement", text="Požadavek")
        tree.heading("problem", text="Problém")
        tree.heading("action", text="Nápravné opatření")
        tree.column("created_at", width=95, anchor="w", stretch=False)
        tree.column("status", width=130, anchor="w", stretch=False)
        tree.column("priority", width=85, anchor="w", stretch=False)
        tree.column("due_date", width=95, anchor="w", stretch=False)
        tree.column("owner", width=135, anchor="w", stretch=False)
        tree.column("meeting", width=180, anchor="w")
        tree.column("requirement", width=95, anchor="w", stretch=False)
        tree.column("problem", width=280, anchor="w")
        tree.column("action", width=340, anchor="w")
        self.configure_status_tags(tree)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(14, 0))

        refresh = lambda: self.populate_problem_overview(
            tree,
            owner_var.get(),
            status_var.get(),
            source_var.get(),
            search_var.get(),
            count_label,
        )
        owner_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        status_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        source_filter.bind("<<ComboboxSelected>>", lambda event: refresh())
        search_entry.bind("<KeyRelease>", lambda event: refresh())
        tree.bind("<Double-1>", lambda event: self.open_selected_problem_dialog(tree, refresh))
        tree.bind("<Return>", lambda event: self.open_selected_problem_dialog(tree, refresh))

        def set_my_problems():
            owner = self.get_my_owner_value()
            if not owner:
                messagebox.showwarning("Moje položky", "Uživatelské jméno Windows není v seznamu odpovědných osob.")
                return
            owner_var.set(owner)
            status_var.set("Otevřené")
            refresh()

        self.create_button(quick_filters, text="Moje", command=set_my_problems, variant="secondary").pack(side=tk.LEFT)
        self.create_button(quick_filters, text="Otevřené", command=lambda: (status_var.set("Otevřené"), refresh()), variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(quick_filters, text="Dnes", command=lambda: (status_var.set("Dnes"), refresh()), variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(quick_filters, text="Po termínu", command=lambda: (status_var.set("Po termínu"), refresh()), variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(
            quick_filters,
            text="Reset",
            command=lambda: (owner_var.set("Všichni"), status_var.set("Všechny"), source_var.set("Vše"), search_var.set(""), refresh()),
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.create_button(
            actions,
            text="Nový problém",
            command=lambda: self.show_problem_dialog(refresh_callback=refresh),
            variant="primary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT)
        self.create_button(
            actions,
            text="Upravit vybrané",
            command=lambda: self.open_selected_problem_dialog(tree, refresh),
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            actions,
            text="Smazat vybrané",
            command=lambda: self.delete_selected_problem(tree, refresh),
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            actions,
            text="Otevřít požadavek",
            command=lambda: self.open_selected_problem_requirement(tree, refresh),
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            actions,
            text="Otevřít poradu",
            command=lambda: self.open_selected_problem_meeting(tree),
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            actions,
            text="Export",
            command=lambda: self.export_problem_overview(
                owner_var.get(),
                status_var.get(),
                source_var.get(),
                search_var.get(),
            ),
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(actions, text="Obnovit", command=refresh, variant="secondary").pack(side=tk.LEFT, padx=(10, 0))

        if standalone:
            self.create_button(actions, text="Rozcestník", command=close_overview, variant="secondary").pack(side=tk.RIGHT)
        else:
            self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)

        def toggle_admin_from_problems():
            self.toggle_admin_login()
            dialog.destroy()
            self.show_problem_overview(standalone=standalone, close_callback=close_callback)

        self.create_button(
            actions,
            text="Odhlásit admina" if self.can_edit() else "Admin",
            command=toggle_admin_from_problems,
            variant="secondary",
        ).pack(side=tk.RIGHT, padx=(0, 10))

        refresh()

    def fetch_problems(self, owner=None, status_filter="Všechny", source_filter="Vše", search_text=""):
        c = self.conn.cursor()
        c.execute(
            """SELECT corrective_actions.id, corrective_actions.meeting_id, corrective_actions.problem_title,
                      corrective_actions.problem_description, corrective_actions.root_cause,
                      corrective_actions.corrective_action, corrective_actions.owner,
                      corrective_actions.due_date, corrective_actions.status,
                      COALESCE(corrective_actions.priority, 'Normální'),
                      corrective_actions.created_at, corrective_actions.completed_at,
                      corrective_actions.source_requirement_id,
                      meetings.title, meetings.date
               FROM corrective_actions
               LEFT JOIN meetings ON meetings.id = corrective_actions.meeting_id"""
        )
        today = datetime.now().date()
        search_text = (search_text or "").strip().lower()
        problems = []
        for row in c.fetchall():
            (
                problem_id,
                meeting_id,
                title,
                description,
                root_cause,
                action,
                item_owner,
                due_date,
                status,
                priority,
                created_at,
                completed_at,
                source_requirement_id,
                meeting_title,
                meeting_date,
            ) = row
            status = status or "Nový"
            is_closed = status == "Uzavřeno"
            parsed_due = self.parse_due_date(due_date)
            is_overdue = bool(parsed_due and parsed_due < today and not is_closed)
            is_today = bool(parsed_due and parsed_due == today and not is_closed)

            if owner and owner != "Všichni" and item_owner != owner:
                continue
            if status_filter == "Otevřené" and is_closed:
                continue
            if status_filter == "Po termínu" and not is_overdue:
                continue
            if status_filter == "Dnes" and not is_today:
                continue
            if status_filter in self.PROBLEM_STATUS_VALUES and status != status_filter:
                continue
            if source_filter == "Z požadavku" and not source_requirement_id:
                continue
            if source_filter == "Ručně" and source_requirement_id:
                continue

            formatted_meeting_date = self.format_czech_date(meeting_date) if meeting_date else ""
            source_requirement_text = f"#{source_requirement_id}" if source_requirement_id else ""
            haystack = " ".join(
                (
                    title or "",
                    description or "",
                    root_cause or "",
                    action or "",
                    item_owner or "",
                    due_date or "",
                    status or "",
                    meeting_title or "",
                    formatted_meeting_date,
                    str(source_requirement_id or ""),
                    source_requirement_text,
                )
            ).lower()
            if search_text and search_text not in haystack:
                continue

            status_text, tag = self.get_record_status(due_date, 1 if is_closed else 0)
            if status:
                status_text = status
                if status == "Nový":
                    tag = "problem_new"
                elif status == "V řešení":
                    tag = "problem_in_progress"
                elif status == "Ověření účinnosti":
                    tag = "problem_verify"
                elif status == "Uzavřeno":
                    tag = "problem_closed"

            problems.append(
                {
                    "id": problem_id,
                    "meeting_id": meeting_id,
                    "title": title or "",
                    "description": description or "",
                    "root_cause": root_cause or "",
                    "action": action or "",
                    "owner": item_owner or "",
                    "due_date": due_date or "",
                    "parsed_due": parsed_due,
                    "status": status,
                    "priority": priority or "Normální",
                    "created_at": created_at or "",
                    "completed_at": completed_at or "",
                    "source_requirement_id": source_requirement_id,
                    "meeting_title": meeting_title or "",
                    "meeting_date": meeting_date or "",
                    "formatted_meeting_date": formatted_meeting_date,
                    "status_text": status_text,
                    "tag": tag,
                }
            )
        max_date = datetime.max.date()
        problems.sort(
            key=lambda item: (
                item["status"] == "Uzavřeno",
                item["parsed_due"] is None,
                item["parsed_due"] or max_date,
                item["created_at"],
            )
        )
        return problems

    def populate_problem_overview(self, tree, owner, status_filter, source_filter, search_text, count_label):
        tree.delete(*tree.get_children())
        problems = self.fetch_problems(
            owner=owner,
            status_filter=status_filter,
            source_filter=source_filter,
            search_text=search_text,
        )
        for item in problems:
            created = item["created_at"][:10] if item["created_at"] else "-"
            tree.insert(
                "",
                tk.END,
                iid=str(item["id"]),
                values=(
                    created,
                    item["status_text"],
                    item["priority"],
                    item["due_date"] or "-",
                    item["owner"] or "-",
                    item["meeting_title"] or "-",
                    f"#{item['source_requirement_id']}" if item["source_requirement_id"] else "-",
                    item["title"],
                    item["action"],
                ),
                tags=(item["tag"],) if item["tag"] else (),
            )
        suffix = ""
        if search_text.strip():
            suffix = " nalezených"
        elif source_filter != "Vše":
            suffix = f" ({source_filter.lower()})"
        elif status_filter != "Všechny":
            suffix = f" ({status_filter.lower()})"
        count_label.config(text=f"{len(problems)} problémů{suffix}")

    def export_problem_overview(self, owner=None, status_filter="Všechny", source_filter="Vše", search_text=""):
        problems = self.fetch_problems(
            owner=owner,
            status_filter=status_filter,
            source_filter=source_filter,
            search_text=search_text,
        )
        if not problems:
            messagebox.showwarning("Export problémů", "Není co exportovat.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            initialfile=f"Problemy_a_opatreni_{datetime.now().strftime('%Y-%m-%d')}.html",
            filetypes=[("Tiskový HTML přehled", "*.html")],
        )
        if not filepath:
            return

        rows = []
        for item in problems:
            rows.append(
                "<tr>"
                f"<td>{html.escape(item['status_text'])}</td>"
                f"<td>{html.escape(item['priority'])}</td>"
                f"<td>{html.escape(item['due_date'] or '-')}</td>"
                f"<td>{html.escape(item['owner'] or '-')}</td>"
                f"<td>{html.escape(item['meeting_title'] or '-')}</td>"
                f"<td>{html.escape('#' + str(item['source_requirement_id']) if item['source_requirement_id'] else '-')}</td>"
                f"<td>{html.escape(item['title'])}</td>"
                f"<td>{html.escape(item['root_cause'] or '-')}</td>"
                f"<td>{html.escape(item['action'])}</td>"
                "</tr>"
            )

        document = f"""<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>Problémy a nápravná opatření</title>
  <style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 32px; color: #17202a; }}
    h1 {{ margin: 0 0 6px; }}
    .meta {{ color: #667085; margin-bottom: 22px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #d7dee8; padding: 8px 10px; vertical-align: top; }}
    th {{ background: #f1f5f9; text-align: left; }}
    tr:nth-child(even) td {{ background: #f8fafc; }}
    @media print {{ body {{ margin: 16mm; }} }}
  </style>
</head>
<body>
  <h1>Problémy a nápravná opatření</h1>
  <div class="meta">Exportováno {html.escape(datetime.now().strftime('%d.%m.%Y %H:%M'))} | počet záznamů: {len(problems)}</div>
  <table>
    <thead>
      <tr>
        <th>Stav</th>
        <th>Priorita</th>
        <th>Termín</th>
        <th>Odpovědnost</th>
        <th>Porada</th>
        <th>Požadavek</th>
        <th>Problém</th>
        <th>Příčina</th>
        <th>Nápravné opatření</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>"""
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(document)

        if messagebox.askyesno("Export problémů", "Přehled byl exportován. Chcete ho otevřít pro tisk?"):
            try:
                os.startfile(filepath)
            except OSError:
                messagebox.showwarning("Export problémů", "Soubor se nepodařilo automaticky otevřít.")
        messagebox.showinfo("Export problémů", "Přehled problémů byl úspěšně exportován.")

    def fetch_problem_detail(self, problem_id):
        c = self.conn.cursor()
        c.execute(
            """SELECT id, meeting_id, problem_title, problem_description, root_cause,
                      corrective_action, owner, due_date, status, priority, source_requirement_id
               FROM corrective_actions
               WHERE id=?""",
            (problem_id,),
        )
        return c.fetchone()

    def show_problem_dialog(self, problem_id=None, refresh_callback=None, initial_values=None, after_save_callback=None):
        if not self.require_admin():
            return

        initial_values = initial_values or {}
        choices, meeting_mapping = self.get_meeting_choices()
        existing = self.fetch_problem_detail(problem_id) if problem_id else None
        if problem_id and not existing:
            messagebox.showwarning("Problémy", "Vybraný problém už neexistuje.")
            if refresh_callback:
                refresh_callback()
            return

        title = "Upravit problém" if existing else "Nový problém"
        dialog, content = self.create_dialog(title, 820, 650, 700, 540, modal=True)
        self.create_dialog_header(
            content,
            title,
            "Zapište problém, příčinu a nápravné opatření včetně odpovědnosti a termínu.",
            accent=self.COLORS["page_problems_accent"],
        )
        source_requirement_id = existing[10] if existing else initial_values.get("source_requirement_id")
        if source_requirement_id:
            tk.Label(
                content,
                text=f"Vznikl z požadavku #{source_requirement_id}",
                font=(self.FONT, 10, "bold"),
                bg=self.COLORS["selection"],
                fg=self.COLORS["primary"],
                padx=10,
                pady=6,
                anchor="w",
            ).pack(fill=tk.X, pady=(0, 10))

        form = tk.Frame(content, bg=self.COLORS["panel"])
        form.pack(fill=tk.BOTH, expand=True)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(2, weight=1)
        form.rowconfigure(3, weight=1)
        form.rowconfigure(4, weight=1)

        meeting_var = tk.StringVar()
        title_var = tk.StringVar()
        owner_var = tk.StringVar()
        due_date_var = tk.StringVar(value=self.get_today_due_date())
        status_var = tk.StringVar(value="Nový")
        priority_var = tk.StringVar(value="Normální")

        description = ""
        root_cause = ""
        action = ""
        original_status = ""
        if existing:
            _, meeting_id, problem_title, description, root_cause, action, owner, due_date, status, priority, source_requirement_id = existing
            original_status = status or "Nový"
            for label, mapped_id in meeting_mapping.items():
                if mapped_id == meeting_id:
                    meeting_var.set(label)
                    break
            title_var.set(problem_title or "")
            owner_var.set(owner or "")
            due_date_var.set(due_date or "")
            status_var.set(status or "Nový")
            priority_var.set(priority or "Normální")
        else:
            initial_meeting_id = initial_values.get("meeting_id") or self.current_id
            if initial_meeting_id:
                for label, mapped_id in meeting_mapping.items():
                    if mapped_id == initial_meeting_id:
                        meeting_var.set(label)
                        break
            title_var.set(initial_values.get("problem_title", ""))
            owner_var.set(initial_values.get("owner", ""))
            due_date_var.set(initial_values.get("due_date", self.get_today_due_date()))
            status_var.set(initial_values.get("status", "Nový"))
            priority_var.set(initial_values.get("priority", "Normální"))
            description = initial_values.get("problem_description", "")
            root_cause = initial_values.get("root_cause", "")
            action = initial_values.get("corrective_action", "")

        tk.Label(form, text="Porada", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        meeting_entry = ttk.Combobox(form, textvariable=meeting_var, values=[""] + choices, state="readonly", font=(self.FONT, 10))
        meeting_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10), ipady=3)

        tk.Label(form, text="Problém", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).grid(row=1, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        title_entry = ttk.Entry(form, textvariable=title_var, font=(self.FONT, 10))
        title_entry.grid(row=1, column=1, sticky="ew", pady=(0, 10), ipady=3)

        description_text = self.create_problem_text_row(form, "Popis", 2, description or "")
        cause_text = self.create_problem_text_row(form, "Příčina", 3, root_cause or "")
        action_text = self.create_problem_text_row(form, "Opatření", 4, action or "")

        tk.Label(form, text="Řízení", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).grid(row=5, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        fields = tk.Frame(form, bg=self.COLORS["panel"])
        fields.grid(row=5, column=1, sticky="ew", pady=(0, 10))
        for column in range(4):
            fields.columnconfigure(column, weight=1)

        ttk.Combobox(fields, textvariable=owner_var, values=self.get_people_values(), font=(self.FONT, 10)).grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=3)
        due_entry = ttk.Combobox(
            fields,
            textvariable=due_date_var,
            values=[(datetime.now().date() + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(0, 366)],
            font=(self.FONT, 10),
        )
        due_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), ipady=3)
        due_entry.bind("<Button-1>", lambda event: self.open_date_picker_for_variable(due_date_var, due_entry))
        ttk.Combobox(fields, textvariable=status_var, values=self.PROBLEM_STATUS_VALUES, state="readonly", font=(self.FONT, 10)).grid(row=0, column=2, sticky="ew", padx=(0, 8), ipady=3)
        ttk.Combobox(fields, textvariable=priority_var, values=self.PROBLEM_PRIORITY_VALUES, state="readonly", font=(self.FONT, 10)).grid(row=0, column=3, sticky="ew", ipady=3)

        actions = tk.Frame(form, bg=self.COLORS["panel"])
        actions.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        def save_problem():
            problem_title = title_var.get().strip()
            description_value = description_text.get("1.0", tk.END).strip()
            cause_value = cause_text.get("1.0", tk.END).strip()
            action_value = action_text.get("1.0", tk.END).strip()
            owner_value = owner_var.get().strip()
            due_date_value = due_date_var.get().strip()
            parsed_due = self.parse_due_date(due_date_value)
            meeting_id = meeting_mapping.get(meeting_var.get()) if meeting_var.get() else None

            if not problem_title:
                messagebox.showwarning("Problémy", "Zadejte název problému.")
                title_entry.focus_set()
                return
            if not action_value:
                messagebox.showwarning("Problémy", "Zadejte nápravné opatření.")
                action_text.focus_set()
                return
            if due_date_value and not parsed_due:
                messagebox.showwarning("Termín", "Zadejte platný termín, například 13.05.2026, nebo pole vymažte.")
                due_entry.focus_set()
                return
            if parsed_due:
                due_date_value = parsed_due.strftime("%d.%m.%Y")

            completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status_var.get() == "Uzavřeno" else ""
            c = self.conn.cursor()
            saved_problem_id = problem_id
            if existing:
                c.execute(
                    """UPDATE corrective_actions
                       SET meeting_id=?, problem_title=?, problem_description=?, root_cause=?,
                           corrective_action=?, owner=?, due_date=?, status=?, priority=?, completed_at=?
                       WHERE id=?""",
                    (
                        meeting_id,
                        problem_title,
                        description_value,
                        cause_value,
                        action_value,
                        owner_value,
                        due_date_value,
                        status_var.get(),
                        priority_var.get(),
                        completed_at,
                        problem_id,
                    ),
                )
                self.log_change("problém", problem_id, meeting_id, "upraveno", "", problem_title)
                if original_status != status_var.get():
                    if status_var.get() == "Ověření účinnosti":
                        self.log_change("problém", problem_id, meeting_id, "opatření ověřeno", original_status, status_var.get())
                    elif status_var.get() == "Uzavřeno":
                        self.log_change("problém", problem_id, meeting_id, "problém uzavřen", original_status, status_var.get())
            else:
                c.execute(
                    """INSERT INTO corrective_actions
                       (meeting_id, problem_title, problem_description, root_cause, corrective_action,
                        owner, due_date, status, priority, created_at, completed_at, source_requirement_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        meeting_id,
                        problem_title,
                        description_value,
                        cause_value,
                        action_value,
                        owner_value,
                        due_date_value,
                        status_var.get(),
                        priority_var.get(),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        completed_at,
                        initial_values.get("source_requirement_id"),
                    ),
                )
                saved_problem_id = c.lastrowid
                self.log_change("problém", saved_problem_id, meeting_id, "vytvořeno", "", problem_title)
                if initial_values.get("source_requirement_id"):
                    self.log_change(
                        "problém",
                        saved_problem_id,
                        meeting_id,
                        "problém vytvořen z požadavku",
                        "",
                        str(initial_values.get("source_requirement_id")),
                    )
            self.commit_database()
            dialog.destroy()
            if after_save_callback:
                after_save_callback(saved_problem_id)
            if refresh_callback:
                refresh_callback()

        self.create_button(actions, text="Uložit", command=save_problem, variant="primary").pack(side=tk.LEFT)
        if source_requirement_id:
            self.create_button(
                actions,
                text="Otevřít zdrojový požadavek",
                command=lambda: self.show_requirement_dialog(requirement_id=source_requirement_id, refresh_callback=refresh_callback),
                variant="secondary",
            ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)
        title_entry.focus_set()

    def create_problem_text_row(self, parent, label, row, value):
        tk.Label(
            parent,
            text=label,
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="nw",
        ).grid(row=row, column=0, sticky="nw", pady=(0, 10), padx=(0, 12))
        text = tk.Text(parent, height=4, wrap=tk.WORD, font=(self.FONT, 10), relief=tk.SOLID, borderwidth=1)
        text.insert("1.0", value)
        text.grid(row=row, column=1, sticky="nsew", pady=(0, 10))
        return text

    def open_selected_problem_dialog(self, tree, refresh_callback=None):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Problémy", "Nejprve vyberte problém.")
            return
        self.show_problem_dialog(problem_id=int(selection[0]), refresh_callback=refresh_callback)

    def delete_selected_problem(self, tree, refresh_callback=None):
        if not self.require_admin():
            return
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Problémy", "Nejprve vyberte problém.")
            return
        if not messagebox.askyesno("Smazat problém", "Opravdu chcete vybraný problém smazat?"):
            return
        c = self.conn.cursor()
        self.log_audit("smazání problému", selection[0])
        c.execute("UPDATE meeting_requirements SET linked_problem_id=NULL WHERE linked_problem_id=?", (int(selection[0]),))
        c.execute("DELETE FROM corrective_actions WHERE id=?", (int(selection[0]),))
        self.commit_database()
        if refresh_callback:
            refresh_callback()

    def open_selected_problem_requirement(self, tree, refresh_callback=None):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Problémy", "Nejprve vyberte problém.")
            return

        row = self.fetch_problem_detail(int(selection[0]))
        if not row or not row[10]:
            messagebox.showwarning("Problémy", "Vybraný problém nemá vazbu na požadavek.")
            return

        self.show_requirement_dialog(requirement_id=row[10], refresh_callback=refresh_callback)

    def open_selected_problem_meeting(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Problémy", "Nejprve vyberte problém.")
            return
        row = self.fetch_problem_detail(int(selection[0]))
        if not row or not row[1]:
            messagebox.showwarning("Problémy", "Problém není propojený s poradou.")
            return
        if self.current_id and self.notes_dirty:
            self.save_notes(show_message=False)
        self.current_id = row[1]
        self.show_open_only.set(False)
        self.show_porady_workspace()
        self.load_meetings()
        self.load_meeting_details()
        self.root.lift()
        self.root.focus_force()
