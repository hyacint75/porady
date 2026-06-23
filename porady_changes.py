# -*- coding: utf-8 -*-

import csv
import html
import os
import tempfile
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from porady_widgets import bind_mousewheel_to_canvas, configure_treeview_sorting, reapply_treeview_sorting


APP_NAME = "Změnové řízení"

CHANGE_AREAS = (
    "Metodika kapacitního plánování",
    "ERP Helios Nephrite",
    "Prioritizace zakázek",
    "Kapacitní plánování",
    "Výrobní data (VP, Nh)",
    "Reporting a KPI",
    "Jiné",
)

IMPACTS = (
    "Bez dopadu na procesy",
    "Dopad na plánování výroby",
    "Dopad na ERP systém",
    "Dopad na organizaci práce",
    "Dopad na ostatní útvary",
)

STATUSES = (
    "Nový",
    "K posouzení",
    "Vráceno k doplnění",
    "Schváleno",
    "Schváleno s úpravou",
    "Zamítnuto",
    "Odloženo",
    "Realizováno",
)

DECISIONS = ("", "Schváleno", "Zamítnuto", "Odloženo")


class ChangeManagementApp(tk.Toplevel):
    def __init__(
        self,
        parent,
        *,
        connection,
        commit_callback,
        can_edit_callback,
        require_admin_callback,
        toggle_admin_callback=None,
        on_home=None,
        colors=None,
        font="Segoe UI",
    ):
        super().__init__(parent)
        self.parent = parent
        self.conn = connection
        self.commit_database = commit_callback
        self.can_edit = can_edit_callback
        self.require_admin = require_admin_callback
        self.toggle_admin_login = toggle_admin_callback
        self.on_home = on_home
        self.COLORS = colors or {}
        self.FONT = font
        self.edit_buttons = []
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Všechny")
        self.area_var = tk.StringVar(value="Všechny")
        self.count_var = tk.StringVar(value="")

        self.title(APP_NAME)
        self.geometry("1180x720")
        self.minsize(980, 620)
        self.configure(bg=self.color("app_bg", "#eef2f6"))
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.configure_styles()
        self.create_layout()
        self.refresh()
        self.after(1, self.center_on_parent)

    def color(self, key, fallback):
        return self.COLORS.get(key, fallback)

    def configure_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure(
            "Change.Treeview",
            rowheight=28,
            font=(self.FONT, 10),
            fieldbackground="white",
            background="white",
            foreground=self.color("text", "#17202a"),
        )
        self.style.configure(
            "Change.Treeview.Heading",
            font=(self.FONT, 10, "bold"),
            background="#f1f5f9",
            foreground=self.color("text", "#17202a"),
        )

    def center_on_parent(self):
        self.update_idletasks()
        parent = self.parent.winfo_toplevel()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def close(self):
        self.destroy()
        if self.on_home:
            self.on_home()

    def create_button(self, parent, text, command, variant="secondary", state=tk.NORMAL):
        variants = {
            "primary": ("#2563eb", "white", "#1d4ed8", (self.FONT, 10, "bold")),
            "secondary": ("#e6edf7", self.color("text", "#17202a"), "#d7e3f3", (self.FONT, 10)),
            "danger": ("#fee2e2", "#dc2626", "#fecaca", (self.FONT, 10, "bold")),
        }
        bg, fg, active_bg, font = variants[variant]
        return tk.Button(
            parent,
            text=text,
            command=command,
            state=state,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            disabledforeground="#667085",
            font=font,
            relief=tk.FLAT,
            borderwidth=0,
            padx=14,
            pady=8,
            cursor="hand2",
        )

    def create_layout(self):
        shell = tk.Frame(self, bg=self.color("app_bg", "#eef2f6"), padx=22, pady=22)
        shell.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(shell, bg=self.color("app_bg", "#eef2f6"))
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=APP_NAME,
            font=(self.FONT, 22, "bold"),
            bg=self.color("app_bg", "#eef2f6"),
            fg=self.color("text", "#17202a"),
        ).pack(side=tk.LEFT)
        self.create_button(header, "← Rozcestník", self.close, "secondary").pack(side=tk.RIGHT)
        if self.toggle_admin_login:
            self.btn_admin = self.create_button(
                header,
                self.admin_button_text(),
                self.toggle_admin_from_window,
                "secondary",
            )
            self.btn_admin.pack(side=tk.RIGHT, padx=(0, 8))

        panel = tk.Frame(
            shell,
            bg="white",
            padx=18,
            pady=18,
            highlightthickness=1,
            highlightbackground=self.color("border", "#d7dee8"),
        )
        panel.pack(fill=tk.BOTH, expand=True, pady=(18, 0))

        filters = tk.Frame(panel, bg="white")
        filters.pack(fill=tk.X, pady=(0, 12))
        self._label(filters, "Stav").pack(side=tk.LEFT, padx=(0, 8))
        status = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            state="readonly",
            width=20,
            values=("Všechny",) + STATUSES,
            font=(self.FONT, 10),
        )
        status.pack(side=tk.LEFT, padx=(0, 14), ipady=3)

        self._label(filters, "Oblast").pack(side=tk.LEFT, padx=(0, 8))
        area = ttk.Combobox(
            filters,
            textvariable=self.area_var,
            state="readonly",
            width=28,
            values=("Všechny",) + CHANGE_AREAS,
            font=(self.FONT, 10),
        )
        area.pack(side=tk.LEFT, padx=(0, 14), ipady=3)

        self._label(filters, "Hledat").pack(side=tk.LEFT, padx=(0, 8))
        search_entry = ttk.Entry(filters, textvariable=self.search_var, font=(self.FONT, 10))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        tk.Label(
            filters,
            textvariable=self.count_var,
            font=(self.FONT, 10),
            bg="white",
            fg=self.color("muted", "#667085"),
        ).pack(side=tk.RIGHT, padx=(14, 0))

        quick = tk.Frame(panel, bg="white")
        quick.pack(fill=tk.X, pady=(0, 12))
        for text, value in (
            ("Nové", "Nový"),
            ("K posouzení", "K posouzení"),
            ("Schválené", "Schváleno"),
            ("Reset", "Všechny"),
        ):
            self.create_button(
                quick,
                text,
                lambda selected=value: self.set_status_filter(selected),
                "secondary",
            ).pack(side=tk.LEFT, padx=(0, 8))

        table_frame = tk.Frame(panel, bg="white")
        table_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("number", "date", "status", "area", "proposer", "department", "title", "decision")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Change.Treeview",
        )
        headings = {
            "number": ("Číslo", 110),
            "date": ("Datum", 95),
            "status": ("Stav", 135),
            "area": ("Oblast", 190),
            "proposer": ("Navrhovatel", 140),
            "department": ("Útvar", 120),
            "title": ("Návrh změny", 340),
            "decision": ("Rozhodnutí", 120),
        }
        for key, (label, width) in headings.items():
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w", stretch=key == "title")
        configure_treeview_sorting(self.tree, column_types={"date": "date"})
        self.tree.tag_configure("approved", background="#dcfce7")
        self.tree.tag_configure("rejected", background="#fee2e2")
        self.tree.tag_configure("review", background="#fef3c7")
        self.tree.tag_configure("done", background="#e0f2fe")
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(panel, bg="white")
        actions.pack(fill=tk.X, pady=(14, 0))
        edit_state = tk.NORMAL if self.can_edit() else tk.DISABLED
        self.btn_new = self.create_button(actions, "Nový podnět", lambda: self.open_form(), "primary", edit_state)
        self.btn_new.pack(side=tk.LEFT)
        self.edit_buttons.append(self.btn_new)
        self.btn_edit = self.create_button(actions, "Upravit", self.open_selected, "secondary", edit_state)
        self.btn_edit.pack(side=tk.LEFT, padx=(8, 0))
        self.edit_buttons.append(self.btn_edit)
        self.btn_delete = self.create_button(actions, "Smazat", self.delete_selected, "danger", edit_state)
        self.btn_delete.pack(side=tk.LEFT, padx=(8, 0))
        self.edit_buttons.append(self.btn_delete)
        self.create_button(actions, "Detail", self.show_detail, "secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(actions, "Export HTML", self.export_html, "secondary").pack(side=tk.RIGHT)
        self.create_button(actions, "Export CSV", self.export_csv, "secondary").pack(side=tk.RIGHT, padx=(0, 8))

        status.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        area.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh())
        self.tree.bind("<Double-1>", lambda _event: self.open_selected() if self.can_edit() else self.show_detail())
        self.tree.bind("<Return>", lambda _event: self.open_selected() if self.can_edit() else self.show_detail())

    def admin_button_text(self):
        return "Odhlásit admina" if self.can_edit() else "Admin"

    def toggle_admin_from_window(self):
        if not self.toggle_admin_login:
            return
        self.toggle_admin_login()
        self.update_permission_state()

    def update_permission_state(self):
        state = tk.NORMAL if self.can_edit() else tk.DISABLED
        for button in self.edit_buttons:
            button.configure(state=state)
        if hasattr(self, "btn_admin"):
            self.btn_admin.configure(text=self.admin_button_text())

    def _label(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            font=(self.FONT, 10, "bold"),
            bg="white",
            fg=self.color("text", "#17202a"),
        )

    def set_status_filter(self, status):
        self.status_var.set(status)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = self.fetch_rows()
        for row in rows:
            tag = self.tag_for_status(row["process_status"])
            self.tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(
                    row["request_number"],
                    row["submitted_date"],
                    row["process_status"],
                    row["area_display"],
                    row["proposer"],
                    row["department"],
                    self.short_text(row["proposed_change"], 90),
                    row["decision"],
                ),
                tags=(tag,) if tag else (),
            )
        self.count_var.set(f"Záznamů: {len(rows)}")
        reapply_treeview_sorting(self.tree)

    def fetch_rows(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, request_number, submitted_date, proposer, department, contact,
                      area, area_other, current_state, proposed_change, justification,
                      impacts, impact_comment, owner_review_date, reviewed_by,
                      process_status, owner_reasoning, decision, decision_date,
                      method_revision, revision_number, process_owner, signature,
                      created_at, updated_at, closed_at
               FROM change_requests
               ORDER BY id DESC"""
        )
        rows = []
        query = self.search_var.get().strip().casefold()
        status_filter = self.status_var.get()
        area_filter = self.area_var.get()
        for values in cursor.fetchall():
            row = self.row_to_dict(values)
            if status_filter != "Všechny" and row["process_status"] != status_filter:
                continue
            if area_filter != "Všechny" and row["area"] != area_filter:
                continue
            haystack = " ".join(str(value or "") for value in row.values()).casefold()
            if query and query not in haystack:
                continue
            rows.append(row)
        return rows

    def row_to_dict(self, values):
        keys = (
            "id", "request_number", "submitted_date", "proposer", "department", "contact",
            "area", "area_other", "current_state", "proposed_change", "justification",
            "impacts", "impact_comment", "owner_review_date", "reviewed_by",
            "process_status", "owner_reasoning", "decision", "decision_date",
            "method_revision", "revision_number", "process_owner", "signature",
            "created_at", "updated_at", "closed_at",
        )
        row = dict(zip(keys, values))
        row["area_display"] = row["area_other"] if row["area"] == "Jiné" and row["area_other"] else row["area"]
        return row

    @staticmethod
    def short_text(value, max_length):
        text = " ".join(str(value or "").split())
        return text if len(text) <= max_length else text[: max_length - 1] + "…"

    @staticmethod
    def tag_for_status(status):
        if status in ("Schváleno", "Schváleno s úpravou"):
            return "approved"
        if status == "Zamítnuto":
            return "rejected"
        if status in ("K posouzení", "Vráceno k doplnění", "Odloženo"):
            return "review"
        if status == "Realizováno":
            return "done"
        return ""

    def selected_id(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(APP_NAME, "Vyberte podnět ze seznamu.", parent=self)
            return None
        return int(selection[0])

    def get_record(self, record_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, request_number, submitted_date, proposer, department, contact,
                      area, area_other, current_state, proposed_change, justification,
                      impacts, impact_comment, owner_review_date, reviewed_by,
                      process_status, owner_reasoning, decision, decision_date,
                      method_revision, revision_number, process_owner, signature,
                      created_at, updated_at, closed_at
               FROM change_requests
               WHERE id=?""",
            (record_id,),
        )
        row = cursor.fetchone()
        return self.row_to_dict(row) if row else None

    def open_selected(self):
        if not self.can_edit():
            self.require_admin()
            return
        record_id = self.selected_id()
        if record_id:
            self.open_form(record_id)

    def show_detail(self):
        record_id = self.selected_id()
        if not record_id:
            return
        record = self.get_record(record_id)
        if not record:
            return
        dialog = tk.Toplevel(self)
        dialog.title(record["request_number"] or APP_NAME)
        dialog.geometry("780x640")
        dialog.minsize(640, 480)
        dialog.configure(bg=self.color("app_bg", "#eef2f6"))
        text = tk.Text(dialog, wrap="word", font=(self.FONT, 10), padx=16, pady=16)
        text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        text.insert("1.0", self.format_detail(record))
        text.configure(state="disabled")
        actions = tk.Frame(dialog, bg=self.color("app_bg", "#eef2f6"))
        actions.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.create_button(actions, "Zavřít", dialog.destroy, "secondary").pack(side=tk.RIGHT)
        dialog.transient(self)
        dialog.lift()

    def format_detail(self, record):
        sections = [
            ("Číslo podnětu", record["request_number"]),
            ("Datum podání", record["submitted_date"]),
            ("Navrhovatel", record["proposer"]),
            ("Útvar", record["department"]),
            ("Kontakt", record["contact"]),
            ("Oblast změny", record["area_display"]),
            ("Popis současného stavu", record["current_state"]),
            ("Návrh změny", record["proposed_change"]),
            ("Zdůvodnění návrhu", record["justification"]),
            ("Předpokládané dopady", record["impacts"]),
            ("Komentář k dopadům", record["impact_comment"]),
            ("Stav", record["process_status"]),
            ("Datum posouzení", record["owner_review_date"]),
            ("Posoudil", record["reviewed_by"]),
            ("Odůvodnění", record["owner_reasoning"]),
            ("Rozhodnutí", record["decision"]),
            ("Datum rozhodnutí", record["decision_date"]),
            ("Vazba na revizi metodiky", record["method_revision"]),
            ("Číslo revize", record["revision_number"]),
            ("Vlastník procesu", record["process_owner"]),
            ("Podpis", record["signature"]),
        ]
        return "\n\n".join(f"{label}:\n{value or '-'}" for label, value in sections)

    def open_form(self, record_id=None):
        if not self.can_edit():
            self.require_admin()
            return
        record = self.get_record(record_id) if record_id else {}
        dialog = tk.Toplevel(self)
        dialog.title("Upravit podnět" if record_id else "Nový podnět ke změně")
        dialog.geometry("940x760")
        dialog.minsize(820, 620)
        dialog.configure(bg=self.color("app_bg", "#eef2f6"))
        dialog.transient(self)
        dialog.grab_set()

        panel = tk.Frame(dialog, bg="white", padx=18, pady=18)
        panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        canvas = tk.Canvas(panel, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=canvas.yview)
        form = tk.Frame(canvas, bg="white")
        form.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        values = self.default_form_values(record)
        variables = {key: tk.StringVar(value=value) for key, value in values.items() if key not in ("current_state", "proposed_change", "justification", "impact_comment", "owner_reasoning")}
        texts = {}

        tk.Label(
            form,
            text="Podnět ke změně",
            font=(self.FONT, 18, "bold"),
            bg="white",
            fg=self.color("text", "#17202a"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 16))

        row = 1
        row = self.add_entry(form, row, "Číslo podnětu", variables["request_number"], 0, readonly=True)
        row = self.add_entry(form, row, "Datum podání", variables["submitted_date"], 2)
        row = self.add_entry(form, row, "Navrhovatel", variables["proposer"], 0)
        row = self.add_entry(form, row, "Útvar", variables["department"], 2)
        row = self.add_entry(form, row, "Kontakt", variables["contact"], 0, columnspan=3)

        self.section_label(form, "Oblast změny", row)
        row += 1
        area = ttk.Combobox(form, textvariable=variables["area"], values=CHANGE_AREAS, state="readonly", font=(self.FONT, 10))
        area.grid(row=row, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(0, 10), ipady=3)
        ttk.Entry(form, textvariable=variables["area_other"], font=(self.FONT, 10)).grid(row=row, column=2, columnspan=2, sticky="ew", pady=(0, 10), ipady=3)
        row += 1

        for key, label, height in (
            ("current_state", "Popis současného stavu", 4),
            ("proposed_change", "Návrh změny", 5),
            ("justification", "Zdůvodnění návrhu", 4),
        ):
            texts[key] = self.add_text(form, row, label, record.get(key, ""), height)
            row += 2

        self.section_label(form, "Předpokládané dopady", row)
        row += 1
        selected_impacts = set((record.get("impacts") or "").split("; "))
        impact_vars = {}
        for index, impact in enumerate(IMPACTS):
            impact_vars[impact] = tk.BooleanVar(value=impact in selected_impacts)
            check = tk.Checkbutton(
                form,
                text=impact,
                variable=impact_vars[impact],
                bg="white",
                fg=self.color("text", "#17202a"),
                selectcolor="white",
                activebackground="white",
                font=(self.FONT, 10),
            )
            check.grid(row=row + index // 2, column=(index % 2) * 2, columnspan=2, sticky="w", pady=2)
        row += 3
        texts["impact_comment"] = self.add_text(form, row, "Komentář", record.get("impact_comment", ""), 3)
        row += 2

        self.section_label(form, "Stanovisko vlastníka procesu", row)
        row += 1
        row = self.add_entry(form, row, "Datum posouzení", variables["owner_review_date"], 0)
        row = self.add_entry(form, row, "Posoudil", variables["reviewed_by"], 2)
        self.add_combo(form, row, "Stav", variables["process_status"], STATUSES, 0)
        self.add_combo(form, row, "Rozhodnutí", variables["decision"], DECISIONS, 2)
        row += 1
        texts["owner_reasoning"] = self.add_text(form, row, "Odůvodnění", record.get("owner_reasoning", ""), 4)
        row += 2
        row = self.add_entry(form, row, "Datum rozhodnutí", variables["decision_date"], 0)
        self.add_combo(form, row, "Vazba na revizi metodiky", variables["method_revision"], ("Ne", "Ano"), 2)
        row += 1
        row = self.add_entry(form, row, "Číslo revize", variables["revision_number"], 0)
        row = self.add_entry(form, row, "Jméno vlastníka procesu", variables["process_owner"], 2)
        row = self.add_entry(form, row, "Podpis", variables["signature"], 0, columnspan=3)

        bind_mousewheel_to_canvas(canvas, panel, form)

        for column in range(4):
            form.columnconfigure(column, weight=1)

        actions = tk.Frame(dialog, bg=self.color("app_bg", "#eef2f6"))
        actions.pack(fill=tk.X, padx=12, pady=(0, 12))

        def save():
            payload = {key: var.get().strip() for key, var in variables.items()}
            for key, widget in texts.items():
                payload[key] = widget.get("1.0", "end-1c").strip()
            payload["impacts"] = "; ".join(impact for impact, var in impact_vars.items() if var.get())
            if not payload["proposed_change"]:
                messagebox.showwarning(APP_NAME, "Vyplňte návrh změny.", parent=dialog)
                return
            if not payload["request_number"]:
                payload["request_number"] = self.next_request_number()
            now = datetime.now().isoformat(timespec="seconds")
            closed_at = record.get("closed_at") if record else ""
            if payload["process_status"] in ("Zamítnuto", "Realizováno") and not closed_at:
                closed_at = now
            self.save_record(record_id, payload, now, closed_at)
            self.refresh()
            dialog.destroy()

        self.create_button(actions, "Uložit", save, "primary").pack(side=tk.RIGHT)
        self.create_button(actions, "Zrušit", dialog.destroy, "secondary").pack(side=tk.RIGHT, padx=(0, 8))
        dialog.bind("<Control-s>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.after(1, lambda: self.center_child(dialog, 940, 760))

    def default_form_values(self, record):
        request_number = record.get("request_number") or self.next_request_number()
        return {
            "request_number": request_number,
            "submitted_date": record.get("submitted_date", datetime.now().strftime("%d.%m.%Y")),
            "proposer": record.get("proposer", ""),
            "department": record.get("department", ""),
            "contact": record.get("contact", ""),
            "area": record.get("area", CHANGE_AREAS[0]),
            "area_other": record.get("area_other", ""),
            "owner_review_date": record.get("owner_review_date", ""),
            "reviewed_by": record.get("reviewed_by", ""),
            "process_status": record.get("process_status", "Nový"),
            "decision": record.get("decision", ""),
            "decision_date": record.get("decision_date", ""),
            "method_revision": record.get("method_revision", "Ne"),
            "revision_number": record.get("revision_number", ""),
            "process_owner": record.get("process_owner", ""),
            "signature": record.get("signature", ""),
        }

    def add_entry(self, parent, row, label, variable, column, columnspan=1, readonly=False):
        self._label(parent, label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(0, 4))
        state = "readonly" if readonly else tk.NORMAL
        ttk.Entry(parent, textvariable=variable, font=(self.FONT, 10), state=state).grid(
            row=row,
            column=column + 1,
            columnspan=columnspan,
            sticky="ew",
            padx=(0, 12),
            pady=(0, 10),
            ipady=3,
        )
        return row + 1 if column >= 2 or columnspan > 1 else row

    def add_combo(self, parent, row, label, variable, values, column):
        self._label(parent, label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(0, 4))
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", font=(self.FONT, 10)).grid(
            row=row,
            column=column + 1,
            sticky="ew",
            padx=(0, 12),
            pady=(0, 10),
            ipady=3,
        )

    def add_text(self, parent, row, label, value, height):
        self.section_label(parent, label, row)
        widget = tk.Text(parent, height=height, wrap="word", font=(self.FONT, 10), relief=tk.SOLID, borderwidth=1)
        widget.insert("1.0", value or "")
        widget.grid(row=row + 1, column=0, columnspan=4, sticky="ew", pady=(0, 12))
        return widget

    def section_label(self, parent, text, row):
        tk.Label(
            parent,
            text=text,
            font=(self.FONT, 11, "bold"),
            bg="white",
            fg=self.color("text", "#17202a"),
        ).grid(row=row, column=0, columnspan=4, sticky="w", pady=(10, 6))

    def center_child(self, dialog, width, height):
        self.update_idletasks()
        x = self.winfo_rootx() + max((self.winfo_width() - width) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - height) // 2, 0)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def next_request_number(self):
        year = datetime.now().year
        prefix = f"ZM-{year}-"
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT request_number FROM change_requests WHERE request_number LIKE ?",
            (prefix + "%",),
        )
        numbers = []
        for (number,) in cursor.fetchall():
            try:
                numbers.append(int(str(number).replace(prefix, "")))
            except ValueError:
                continue
        return f"{prefix}{(max(numbers) + 1 if numbers else 1):03d}"

    def save_record(self, record_id, payload, now, closed_at):
        cursor = self.conn.cursor()
        fields = (
            "request_number", "submitted_date", "proposer", "department", "contact",
            "area", "area_other", "current_state", "proposed_change", "justification",
            "impacts", "impact_comment", "owner_review_date", "reviewed_by",
            "process_status", "owner_reasoning", "decision", "decision_date",
            "method_revision", "revision_number", "process_owner", "signature",
        )
        values = [payload.get(field, "") for field in fields]
        if record_id:
            cursor.execute(
                f"""UPDATE change_requests
                    SET {', '.join(field + '=?' for field in fields)},
                        updated_at=?, closed_at=?
                    WHERE id=?""",
                values + [now, closed_at, record_id],
            )
        else:
            cursor.execute(
                f"""INSERT INTO change_requests
                    ({', '.join(fields)}, created_at, updated_at, closed_at)
                    VALUES ({', '.join('?' for _ in fields)}, ?, ?, ?)""",
                values + [now, now, closed_at],
            )
        self.commit_database()

    def delete_selected(self):
        if not self.can_edit():
            self.require_admin()
            return
        record_id = self.selected_id()
        if not record_id:
            return
        if not messagebox.askyesno(APP_NAME, "Opravdu chcete vybraný podnět smazat?", parent=self):
            return
        self.conn.execute("DELETE FROM change_requests WHERE id=?", (record_id,))
        self.commit_database()
        self.refresh()

    def export_csv(self):
        rows = self.fetch_rows()
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export změnových podnětů",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Všechny soubory", "*.*")],
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(("Číslo", "Datum", "Stav", "Oblast", "Navrhovatel", "Útvar", "Návrh", "Rozhodnutí"))
            for row in rows:
                writer.writerow((
                    row["request_number"],
                    row["submitted_date"],
                    row["process_status"],
                    row["area_display"],
                    row["proposer"],
                    row["department"],
                    row["proposed_change"],
                    row["decision"],
                ))
        messagebox.showinfo(APP_NAME, f"Export byl uložen:\n{path}", parent=self)

    def export_html(self):
        rows = self.fetch_rows()
        body = "\n".join(
            "<tr>"
            f"<td>{html.escape(row['request_number'] or '')}</td>"
            f"<td>{html.escape(row['submitted_date'] or '')}</td>"
            f"<td>{html.escape(row['process_status'] or '')}</td>"
            f"<td>{html.escape(row['area_display'] or '')}</td>"
            f"<td>{html.escape(row['proposer'] or '')}</td>"
            f"<td>{html.escape(row['department'] or '')}</td>"
            f"<td>{html.escape(row['proposed_change'] or '')}</td>"
            f"<td>{html.escape(row['decision'] or '')}</td>"
            "</tr>"
            for row in rows
        )
        document = f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><title>{APP_NAME}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:28px;color:#17202a}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #cbd5e1;padding:8px;vertical-align:top}}
th{{background:#e2e8f0;text-align:left}}tr:nth-child(even){{background:#f8fafc}}
</style></head><body><h1>{APP_NAME}</h1><p>Počet záznamů: {len(rows)}</p>
<table><thead><tr><th>Číslo</th><th>Datum</th><th>Stav</th><th>Oblast</th><th>Navrhovatel</th><th>Útvar</th><th>Návrh</th><th>Rozhodnutí</th></tr></thead>
<tbody>{body}</tbody></table></body></html>"""
        path = Path(tempfile.gettempdir()) / "zmenove_rizeni_export.html"
        path.write_text(document, encoding="utf-8")
        if messagebox.askyesno(APP_NAME, f"Export byl vytvořen:\n{path}\n\nOtevřít soubor?", parent=self):
            os.startfile(path)
