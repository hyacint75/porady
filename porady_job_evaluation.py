# -*- coding: utf-8 -*-

import base64
import csv
import html
import json
import os
import sys
import tempfile
import threading
import tkinter as tk
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from porady_widgets import bind_mousewheel_to_canvas, configure_treeview_sorting, reapply_treeview_sorting


APP_NAME = "Vyhodnocení zakázky"
STATUSES = ("Rozpracováno", "K vyhodnocení", "Vyhodnoceno", "Uzavřeno")
RESULTS = ("Vyhovuje", "Vyhovuje s výhradou", "Nevyhovuje")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_AI_MODEL = "gpt-4.1-mini"


def parse_number(value):
    text = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def format_number(value):
    return f"{float(value or 0):,.2f}".replace(",", " ").replace(".", ",")


def pdf_escape(text):
    return str(text or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_text(text, width=92):
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def write_simple_pdf(path, title, lines):
    pages = []
    current = []
    for line in lines:
        wrapped = wrap_text(line, 96)
        for item in wrapped:
            current.append(item)
            if len(current) >= 42:
                pages.append(current)
                current = []
    if current:
        pages.append(current)
    if not pages:
        pages = [[""]]

    objects = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
    font_object_number = 3 + len(pages) * 2
    for index, page_lines in enumerate(pages):
        page_object = 3 + index * 2
        content_object = page_object + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_object_number} 0 R >> >> "
            f"/Contents {content_object} 0 R >>"
        )
        stream_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
        stream_lines.append(f"({pdf_escape(title)}) Tj")
        stream_lines.append("T*")
        stream_lines.append("T*")
        for line in page_lines:
            stream_lines.append(f"({pdf_escape(line)}) Tj")
            stream_lines.append("T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        objects.append(f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    output = bytearray()
    output.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        encoded = body.encode("latin-1", errors="replace")
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(encoded)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
    )
    Path(path).write_bytes(output)


class JobEvaluationApp(tk.Toplevel):
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
        self.style.configure("Job.Treeview", rowheight=28, font=(self.FONT, 10))
        self.style.configure("Job.Treeview.Heading", font=(self.FONT, 10, "bold"))

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
            parent, text=text, command=command, state=state, bg=bg, fg=fg,
            activebackground=active_bg, activeforeground=fg, disabledforeground="#667085",
            font=font, relief=tk.FLAT, borderwidth=0, padx=14, pady=8, cursor="hand2",
        )

    def create_layout(self):
        shell = tk.Frame(self, bg=self.color("app_bg", "#eef2f6"), padx=22, pady=22)
        shell.pack(fill=tk.BOTH, expand=True)
        header = tk.Frame(shell, bg=self.color("app_bg", "#eef2f6"))
        header.pack(fill=tk.X)
        tk.Label(header, text=APP_NAME, font=(self.FONT, 22, "bold"), bg=self.color("app_bg", "#eef2f6"), fg=self.color("text", "#17202a")).pack(side=tk.LEFT)
        self.create_button(header, "← Rozcestník", self.close).pack(side=tk.RIGHT)
        if self.toggle_admin_login:
            self.btn_admin = self.create_button(header, self.admin_button_text(), self.toggle_admin_from_window)
            self.btn_admin.pack(side=tk.RIGHT, padx=(0, 8))

        panel = tk.Frame(shell, bg="white", padx=18, pady=18, highlightthickness=1, highlightbackground=self.color("border", "#d7dee8"))
        panel.pack(fill=tk.BOTH, expand=True, pady=(18, 0))

        filters = tk.Frame(panel, bg="white")
        filters.pack(fill=tk.X, pady=(0, 12))
        self._label(filters, "Hledat").pack(side=tk.LEFT, padx=(0, 8))
        search = ttk.Entry(filters, textvariable=self.search_var, font=(self.FONT, 10))
        search.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        tk.Label(filters, textvariable=self.count_var, bg="white", fg=self.color("muted", "#667085"), font=(self.FONT, 10)).pack(side=tk.RIGHT, padx=(14, 0))

        columns = ("job_number", "price_diff", "cost_diff", "defects", "rework")
        table_frame = tk.Frame(panel, bg="white")
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", style="Job.Treeview")
        headings = {
            "job_number": ("Záznam", 180),
            "price_diff": ("Rozdíl cen", 150),
            "cost_diff": ("Rozdíl nákladů", 150),
            "defects": ("Součet neshod", 140),
            "rework": ("Repase celkem", 160),
        }
        for key, (label, width) in headings.items():
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w", stretch=key == "job_number")
        configure_treeview_sorting(self.tree, column_types={"price_diff": "number", "cost_diff": "number", "defects": "number", "rework": "number"})
        self.tree.tag_configure("good", background="#dcfce7")
        self.tree.tag_configure("warn", background="#fef3c7")
        self.tree.tag_configure("bad", background="#fee2e2")
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(panel, bg="white")
        actions.pack(fill=tk.X, pady=(14, 0))
        edit_state = tk.NORMAL if self.can_edit() else tk.DISABLED
        for attr, text, command, variant in (
            ("btn_new", "Nové vyhodnocení", lambda: self.open_form(), "primary"),
            ("btn_edit", "Upravit", self.open_selected, "secondary"),
            ("btn_delete", "Smazat", self.delete_selected, "danger"),
        ):
            button = self.create_button(actions, text, command, variant, edit_state)
            button.pack(side=tk.LEFT, padx=(0 if not self.edit_buttons else 8, 0))
            setattr(self, attr, button)
            self.edit_buttons.append(button)
        self.create_button(actions, "Detail", self.show_detail).pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(actions, "Export PDF", self.export_selected_pdf).pack(side=tk.RIGHT)
        self.create_button(actions, "Export HTML", self.export_selected_html).pack(side=tk.RIGHT, padx=(0, 8))
        self.create_button(actions, "Tisk", self.print_selected).pack(side=tk.RIGHT, padx=(0, 8))
        self.create_button(actions, "Export CSV", self.export_csv).pack(side=tk.RIGHT, padx=(0, 8))

        search.bind("<KeyRelease>", lambda _event: self.refresh())
        self.tree.bind("<Double-1>", lambda _event: self.open_selected() if self.can_edit() else self.show_detail())
        self.tree.bind("<Return>", lambda _event: self.open_selected() if self.can_edit() else self.show_detail())

    def _label(self, parent, text):
        return tk.Label(parent, text=text, bg="white", fg=self.color("text", "#17202a"), font=(self.FONT, 10, "bold"))

    def admin_button_text(self):
        return "Odhlásit admina" if self.can_edit() else "Admin"

    def toggle_admin_from_window(self):
        if self.toggle_admin_login:
            self.toggle_admin_login()
            self.update_permission_state()

    def update_permission_state(self):
        state = tk.NORMAL if self.can_edit() else tk.DISABLED
        for button in self.edit_buttons:
            button.configure(state=state)
        if hasattr(self, "btn_admin"):
            self.btn_admin.configure(text=self.admin_button_text())

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = self.fetch_rows()
        for row in rows:
            tag = "good"
            self.tree.insert(
                "", tk.END, iid=str(row["id"]),
                values=(
                    row["job_number"] or f"Vyhodnocení #{row['id']}",
                    format_number(row["price_difference"]),
                    format_number(row["cost_difference"]),
                    format_number(row["total_defects"]),
                    format_number(row["total_rework_cost"]),
                ),
                tags=(tag,),
            )
        self.count_var.set(f"Záznamů: {len(rows)}")
        reapply_treeview_sorting(self.tree)

    def fetch_rows(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, job_number, job_name, customer, project_manager, evaluation_date,
                      status, result, planned_revenue, actual_revenue, planned_cost,
                      actual_cost, planned_hours, actual_hours, planned_finish,
                      actual_finish, schedule_variance_days, quality_result,
                      paint_defects, mechanical_defects, mechanical_rework_cost, paint_rework_cost,
                      paint_defect_1, paint_action_1, paint_defect_2, paint_action_2, paint_defect_3, paint_action_3,
                      mechanical_defect_1, mechanical_action_1, mechanical_defect_2, mechanical_action_2, mechanical_defect_3, mechanical_action_3,
                      delivery_result, positives, negatives, corrective_actions,
                      conclusion, created_at, updated_at
               FROM job_evaluations
               ORDER BY id DESC"""
        )
        rows = [self.row_to_dict(row) for row in cursor.fetchall()]
        query = self.search_var.get().strip().casefold()
        filtered = []
        for row in rows:
            haystack = " ".join(str(value or "") for value in row.values()).casefold()
            if query and query not in haystack:
                continue
            filtered.append(row)
        return filtered

    def row_to_dict(self, row):
        keys = (
            "id", "job_number", "job_name", "customer", "project_manager", "evaluation_date",
            "status", "result", "planned_revenue", "actual_revenue", "planned_cost",
            "actual_cost", "planned_hours", "actual_hours", "planned_finish",
            "actual_finish", "schedule_variance_days", "quality_result",
            "paint_defects", "mechanical_defects", "mechanical_rework_cost", "paint_rework_cost",
            "paint_defect_1", "paint_action_1", "paint_defect_2", "paint_action_2", "paint_defect_3", "paint_action_3",
            "mechanical_defect_1", "mechanical_action_1", "mechanical_defect_2", "mechanical_action_2", "mechanical_defect_3", "mechanical_action_3",
            "delivery_result", "positives", "negatives", "corrective_actions",
            "conclusion", "created_at", "updated_at",
        )
        data = dict(zip(keys, row))
        for key in (
            "planned_revenue", "actual_revenue", "planned_cost", "actual_cost",
            "planned_hours", "actual_hours", "schedule_variance_days",
            "paint_defects", "mechanical_defects", "mechanical_rework_cost", "paint_rework_cost",
        ):
            data[key] = parse_number(data.get(key))
        data["price_difference"] = data["actual_revenue"] - data["planned_revenue"]
        data["cost_difference"] = data["actual_cost"] - data["planned_cost"]
        data["total_defects"] = data["paint_defects"] + data["mechanical_defects"]
        data["total_rework_cost"] = data["mechanical_rework_cost"] + data["paint_rework_cost"]
        data["planned_profit"] = data["planned_revenue"] - data["planned_cost"]
        data["actual_profit"] = data["actual_revenue"] - data["actual_cost"]
        data["profit_variance"] = data["actual_profit"] - data["planned_profit"]
        data["hours_variance"] = data["actual_hours"] - data["planned_hours"]
        return data

    def selected_id(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(APP_NAME, "Vyberte vyhodnocení ze seznamu.", parent=self)
            return None
        return int(selection[0])

    def get_record(self, record_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, job_number, job_name, customer, project_manager, evaluation_date,
                      status, result, planned_revenue, actual_revenue, planned_cost,
                      actual_cost, planned_hours, actual_hours, planned_finish,
                      actual_finish, schedule_variance_days, quality_result,
                      paint_defects, mechanical_defects, mechanical_rework_cost, paint_rework_cost,
                      paint_defect_1, paint_action_1, paint_defect_2, paint_action_2, paint_defect_3, paint_action_3,
                      mechanical_defect_1, mechanical_action_1, mechanical_defect_2, mechanical_action_2, mechanical_defect_3, mechanical_action_3,
                      delivery_result, positives, negatives, corrective_actions,
                      conclusion, created_at, updated_at
               FROM job_evaluations WHERE id=?""",
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

    def open_form(self, record_id=None):
        if not self.can_edit():
            self.require_admin()
            return
        record = self.get_record(record_id) if record_id else {}
        dialog = tk.Toplevel(self)
        dialog.title("Upravit vyhodnocení" if record_id else "Nové vyhodnocení zakázky")
        dialog.geometry("940x760")
        dialog.minsize(820, 620)
        dialog.configure(bg=self.color("app_bg", "#eef2f6"))
        dialog.transient(self)
        dialog.grab_set()

        panel = tk.Frame(
            dialog,
            bg="white",
            padx=18,
            pady=18,
            highlightthickness=1,
            highlightbackground=self.color("border", "#d7dee8"),
        )
        panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        canvas = tk.Canvas(panel, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=canvas.yview)
        form = tk.Frame(canvas, bg="white")
        form.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        values = self.default_values(record)
        variables = {key: tk.StringVar(value=value) for key, value in values.items()}
        text_sync_callbacks = []
        text_widgets = {}
        header = tk.Frame(form, bg="#f1f6ff", padx=14, pady=12, highlightthickness=1, highlightbackground="#dbeafe")
        header.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 16))
        tk.Label(header, text=APP_NAME, font=(self.FONT, 18, "bold"), bg="#f1f6ff", fg=self.color("text", "#17202a")).pack(anchor="w")
        tk.Label(header, text="Zobrazují se pouze požadované vstupy a automatické dopočty.", font=(self.FONT, 10), bg="#f1f6ff", fg=self.color("muted", "#667085")).pack(anchor="w", pady=(4, 0))
        row = 1

        calculated = {
            "price_difference": tk.StringVar(),
            "cost_difference": tk.StringVar(),
            "total_defects": tk.StringVar(),
            "total_rework_cost": tk.StringVar(),
        }

        def refresh_calculations(*_args):
            price_difference = parse_number(variables["actual_revenue"].get()) - parse_number(variables["planned_revenue"].get())
            cost_difference = parse_number(variables["actual_cost"].get()) - parse_number(variables["planned_cost"].get())
            total_defects = parse_number(variables["paint_defects"].get()) + parse_number(variables["mechanical_defects"].get())
            total_rework_cost = parse_number(variables["mechanical_rework_cost"].get()) + parse_number(variables["paint_rework_cost"].get())
            calculated["price_difference"].set(format_number(price_difference))
            calculated["cost_difference"].set(format_number(cost_difference))
            calculated["total_defects"].set(format_number(total_defects))
            calculated["total_rework_cost"].set(format_number(total_rework_cost))

        for watched in (
            "planned_revenue", "actual_revenue", "planned_cost", "actual_cost",
            "paint_defects", "mechanical_defects", "mechanical_rework_cost", "paint_rework_cost",
        ):
            variables[watched].trace_add("write", refresh_calculations)

        self.section_label(form, "Ceny", row)
        row += 1
        row = self.add_entry(form, row, "Kalkulovaná cena", variables["planned_revenue"], 0)
        row = self.add_entry(form, row, "Skutečná cena", variables["actual_revenue"], 2)
        row = self.add_calculation_row(form, row, "Počítaný rozdíl cen", calculated["price_difference"])

        self.section_label(form, "Náklady", row)
        row += 1
        row = self.add_entry(form, row, "Kalkulované náklady", variables["planned_cost"], 0)
        row = self.add_entry(form, row, "Skutečné náklady", variables["actual_cost"], 2)
        row = self.add_calculation_row(form, row, "Počítaný rozdíl nákladů", calculated["cost_difference"])

        self.section_label(form, "Neshody", row)
        row += 1
        row = self.add_entry(form, row, "Počet neshod lakových", variables["paint_defects"], 0)
        row = self.add_entry(form, row, "Počet neshod mechanických", variables["mechanical_defects"], 2)
        row = self.add_calculation_row(form, row, "Součet neshod", calculated["total_defects"])

        self.section_label(form, "Tři nejčastější lakové závady", row)
        row += 1
        for index in range(1, 4):
            row = self.add_text_pair(
                form,
                row,
                f"Laková závada {index}",
                variables[f"paint_defect_{index}"],
                "Navrhované nápravné odstranění",
                variables[f"paint_action_{index}"],
                text_sync_callbacks,
                f"paint_defect_{index}",
                f"paint_action_{index}",
                text_widgets,
            )

        self.section_label(form, "Tři nejčastější mechanické závady", row)
        row += 1
        for index in range(1, 4):
            row = self.add_text_pair(
                form,
                row,
                f"Mechanická závada {index}",
                variables[f"mechanical_defect_{index}"],
                "Navrhované nápravné opatření",
                variables[f"mechanical_action_{index}"],
                text_sync_callbacks,
                f"mechanical_defect_{index}",
                f"mechanical_action_{index}",
                text_widgets,
            )

        self.section_label(form, "Repase", row)
        row += 1
        row = self.add_entry(form, row, "Náklady na repase mechanické", variables["mechanical_rework_cost"], 0)
        row = self.add_entry(form, row, "Náklady na repase lakové", variables["paint_rework_cost"], 2)
        row = self.add_calculation_row(form, row, "Celkové náklady na repase", calculated["total_rework_cost"])

        self.section_label(form, "Závěrečné vyhodnocení", row)
        row += 1
        row = self.add_text_field(
            form,
            row,
            variables["conclusion"],
            height=4,
            sync_callbacks=text_sync_callbacks,
            widget_key="conclusion",
            widget_registry=text_widgets,
        )
        refresh_calculations()

        bind_mousewheel_to_canvas(canvas, panel, form)

        for column in range(4):
            form.columnconfigure(column, weight=1)
        actions = tk.Frame(dialog, bg=self.color("app_bg", "#eef2f6"))
        actions.pack(fill=tk.X, padx=12, pady=(0, 12))

        def save():
            for sync_callback in text_sync_callbacks:
                sync_callback()
            payload = {key: var.get().strip() for key, var in variables.items()}
            if not payload.get("job_number"):
                payload["job_number"] = record.get("job_number") or f"Vyhodnocení {datetime.now().strftime('%Y%m%d-%H%M%S')}"
            payload.setdefault("job_name", payload["job_number"])
            self.save_record(record_id, payload)
            self.refresh()
            dialog.destroy()

        ai_button = self.create_button(
            actions,
            "AI návrh opatření",
            lambda: self.generate_ai_corrective_actions(dialog, variables, calculated, text_widgets, text_sync_callbacks, ai_button),
            "primary",
        )
        ai_button.pack(side=tk.LEFT)
        self.create_button(actions, "Uložit", save, "primary").pack(side=tk.RIGHT)
        self.create_button(actions, "Zrušit", dialog.destroy).pack(side=tk.RIGHT, padx=(0, 8))
        dialog.bind("<Control-s>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.after(1, lambda: self.center_child(dialog, 940, 760))

    def default_values(self, record):
        return {
            "job_number": record.get("job_number", ""),
            "job_name": record.get("job_name", ""),
            "customer": record.get("customer", ""),
            "project_manager": record.get("project_manager", ""),
            "evaluation_date": record.get("evaluation_date", datetime.now().strftime("%d.%m.%Y")),
            "status": record.get("status", "Rozpracováno"),
            "result": record.get("result", "Vyhovuje"),
            "planned_revenue": str(record.get("planned_revenue", "")),
            "actual_revenue": str(record.get("actual_revenue", "")),
            "planned_cost": str(record.get("planned_cost", "")),
            "actual_cost": str(record.get("actual_cost", "")),
            "paint_defects": str(record.get("paint_defects", "")),
            "mechanical_defects": str(record.get("mechanical_defects", "")),
            "mechanical_rework_cost": str(record.get("mechanical_rework_cost", "")),
            "paint_rework_cost": str(record.get("paint_rework_cost", "")),
            "paint_defect_1": record.get("paint_defect_1", ""),
            "paint_action_1": record.get("paint_action_1", ""),
            "paint_defect_2": record.get("paint_defect_2", ""),
            "paint_action_2": record.get("paint_action_2", ""),
            "paint_defect_3": record.get("paint_defect_3", ""),
            "paint_action_3": record.get("paint_action_3", ""),
            "mechanical_defect_1": record.get("mechanical_defect_1", ""),
            "mechanical_action_1": record.get("mechanical_action_1", ""),
            "mechanical_defect_2": record.get("mechanical_defect_2", ""),
            "mechanical_action_2": record.get("mechanical_action_2", ""),
            "mechanical_defect_3": record.get("mechanical_defect_3", ""),
            "mechanical_action_3": record.get("mechanical_action_3", ""),
            "conclusion": record.get("conclusion", ""),
            "planned_hours": str(record.get("planned_hours", "")),
            "actual_hours": str(record.get("actual_hours", "")),
            "planned_finish": record.get("planned_finish", ""),
            "actual_finish": record.get("actual_finish", ""),
            "schedule_variance_days": str(record.get("schedule_variance_days", "")),
            "quality_result": record.get("quality_result", ""),
            "delivery_result": record.get("delivery_result", ""),
        }

    @staticmethod
    def field_label(key):
        return {
            "planned_revenue": "Plán tržby",
            "actual_revenue": "Skut. tržby",
            "planned_cost": "Plán náklady",
            "actual_cost": "Skut. náklady",
            "planned_hours": "Plán hodin",
            "actual_hours": "Skut. hodin",
        }[key]

    def add_entry(self, parent, row, label, variable, column):
        self._label(parent, label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(0, 4))
        ttk.Entry(parent, textvariable=variable, font=(self.FONT, 10)).grid(row=row, column=column + 1, sticky="ew", padx=(0, 12), pady=(0, 10), ipady=3)
        return row + 1 if column >= 2 else row

    def add_combo(self, parent, row, label, variable, values, column):
        self._label(parent, label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(0, 4))
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", font=(self.FONT, 10)).grid(row=row, column=column + 1, sticky="ew", padx=(0, 12), pady=(0, 10), ipady=3)

    def add_calculation_row(self, parent, row, label, variable):
        frame = tk.Frame(parent, bg="#f8fafc", padx=10, pady=9, highlightthickness=1, highlightbackground="#d7dee8")
        frame.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        tk.Label(frame, text=label, bg="#f8fafc", fg=self.color("muted", "#667085"), font=(self.FONT, 10, "bold")).pack(side=tk.LEFT)
        tk.Label(frame, textvariable=variable, bg="#f8fafc", fg="#1d4ed8", font=(self.FONT, 13, "bold")).pack(side=tk.RIGHT)
        return row + 1

    def add_text_field(self, parent, row, variable, height=2, sync_callbacks=None, widget_key=None, widget_registry=None):
        widget = tk.Text(
            parent,
            height=height,
            wrap="word",
            font=(self.FONT, 10),
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#d7dee8",
            highlightcolor="#2563eb",
            padx=10,
            pady=8,
        )
        widget.insert("1.0", variable.get())
        widget.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        def sync_variable(_event=None):
            variable.set(widget.get("1.0", "end-1c").strip())

        widget.bind("<KeyRelease>", sync_variable, add="+")
        widget.bind("<FocusOut>", sync_variable, add="+")
        if sync_callbacks is not None:
            sync_callbacks.append(sync_variable)
        if widget_key and widget_registry is not None:
            widget_registry[widget_key] = widget
        return row + 1

    def add_text_pair(
        self,
        parent,
        row,
        left_label,
        left_variable,
        right_label,
        right_variable,
        sync_callbacks=None,
        left_key=None,
        right_key=None,
        widget_registry=None,
    ):
        self._label(parent, left_label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=(0, 4))
        self._label(parent, right_label).grid(row=row, column=2, sticky="w", padx=(0, 8), pady=(0, 4))
        row += 1
        left_widget = tk.Text(parent, height=2, wrap="word", font=(self.FONT, 10), relief=tk.FLAT, borderwidth=0, highlightthickness=1, highlightbackground="#d7dee8", highlightcolor="#2563eb", padx=8, pady=6)
        right_widget = tk.Text(parent, height=2, wrap="word", font=(self.FONT, 10), relief=tk.FLAT, borderwidth=0, highlightthickness=1, highlightbackground="#d7dee8", highlightcolor="#2563eb", padx=8, pady=6)
        left_widget.insert("1.0", left_variable.get())
        right_widget.insert("1.0", right_variable.get())
        left_widget.grid(row=row, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(0, 10))
        right_widget.grid(row=row, column=2, columnspan=2, sticky="ew", padx=(0, 12), pady=(0, 10))

        def sync_left(_event=None):
            left_variable.set(left_widget.get("1.0", "end-1c").strip())

        def sync_right(_event=None):
            right_variable.set(right_widget.get("1.0", "end-1c").strip())

        left_widget.bind("<KeyRelease>", sync_left, add="+")
        left_widget.bind("<FocusOut>", sync_left, add="+")
        right_widget.bind("<KeyRelease>", sync_right, add="+")
        right_widget.bind("<FocusOut>", sync_right, add="+")
        if sync_callbacks is not None:
            sync_callbacks.extend((sync_left, sync_right))
        if widget_registry is not None:
            if left_key:
                widget_registry[left_key] = left_widget
            if right_key:
                widget_registry[right_key] = right_widget
        return row + 1

    def ai_settings_path(self):
        base_dir = Path(os.environ.get("APPDATA") or Path.home())
        return base_dir / "Porady" / "ai_settings.json"

    def load_ai_settings(self):
        settings = {
            "api_key": os.environ.get("OPENAI_API_KEY", "").strip(),
            "model": os.environ.get("PORADY_OPENAI_MODEL", DEFAULT_AI_MODEL).strip() or DEFAULT_AI_MODEL,
        }
        path = self.ai_settings_path()
        if path.exists():
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                stored = {}
            settings["api_key"] = settings["api_key"] or str(stored.get("api_key", "")).strip()
            settings["model"] = str(stored.get("model", settings["model"])).strip() or DEFAULT_AI_MODEL
        return settings

    def save_ai_settings(self, api_key, model):
        path = self.ai_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"api_key": api_key.strip(), "model": model.strip() or DEFAULT_AI_MODEL}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def request_ai_settings(self, parent):
        settings = self.load_ai_settings()
        if settings["api_key"]:
            return settings

        dialog = tk.Toplevel(parent)
        dialog.title("Nastavení online AI")
        dialog.geometry("520x260")
        dialog.resizable(False, False)
        dialog.configure(bg=self.color("app_bg", "#eef2f6"))
        dialog.transient(parent)
        dialog.grab_set()

        api_key_var = tk.StringVar()
        model_var = tk.StringVar(value=settings["model"])
        save_var = tk.BooleanVar(value=True)
        result = {"settings": None}

        panel = tk.Frame(dialog, bg="white", padx=18, pady=18, highlightthickness=1, highlightbackground="#d7dee8")
        panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        tk.Label(panel, text="Online AI pro návrh opatření", font=(self.FONT, 15, "bold"), bg="white", fg="#17202a").pack(anchor="w")
        tk.Label(
            panel,
            text="Zadejte OpenAI API klíč. Klíč se použije jen po kliknutí na AI návrh.",
            font=(self.FONT, 10),
            bg="white",
            fg="#475569",
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(6, 14))

        tk.Label(panel, text="API klíč", font=(self.FONT, 10, "bold"), bg="white", fg="#334155").pack(anchor="w")
        key_entry = ttk.Entry(panel, textvariable=api_key_var, show="*", font=(self.FONT, 10))
        key_entry.pack(fill=tk.X, pady=(3, 10), ipady=3)
        tk.Label(panel, text="Model", font=(self.FONT, 10, "bold"), bg="white", fg="#334155").pack(anchor="w")
        ttk.Entry(panel, textvariable=model_var, font=(self.FONT, 10)).pack(fill=tk.X, pady=(3, 8), ipady=3)
        ttk.Checkbutton(panel, text="Uložit klíč v profilu Windows", variable=save_var).pack(anchor="w")

        actions = tk.Frame(panel, bg="white")
        actions.pack(fill=tk.X, pady=(14, 0))

        def confirm():
            api_key = api_key_var.get().strip()
            model = model_var.get().strip() or DEFAULT_AI_MODEL
            if not api_key:
                messagebox.showwarning(APP_NAME, "Zadejte OpenAI API klíč.", parent=dialog)
                return
            if save_var.get():
                try:
                    self.save_ai_settings(api_key, model)
                except OSError as exc:
                    messagebox.showwarning(APP_NAME, f"Klíč se nepodařilo uložit:\n{exc}", parent=dialog)
            result["settings"] = {"api_key": api_key, "model": model}
            dialog.destroy()

        self.create_button(actions, "Použít", confirm, "primary").pack(side=tk.RIGHT)
        self.create_button(actions, "Zrušit", dialog.destroy).pack(side=tk.RIGHT, padx=(0, 8))
        key_entry.focus_set()
        dialog.bind("<Return>", lambda _event: confirm())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        parent.wait_window(dialog)
        return result["settings"]

    def build_ai_payload(self, variables, calculated):
        def value(key):
            return variables[key].get().strip()

        return {
            "financials": {
                "kalkulovana_cena": value("planned_revenue"),
                "skutecna_cena": value("actual_revenue"),
                "rozdil_cen": calculated["price_difference"].get(),
                "kalkulovane_naklady": value("planned_cost"),
                "skutecne_naklady": value("actual_cost"),
                "rozdil_nakladu": calculated["cost_difference"].get(),
            },
            "defects": {
                "pocet_lakovych_neshod": value("paint_defects"),
                "pocet_mechanickych_neshod": value("mechanical_defects"),
                "soucet_neshod": calculated["total_defects"].get(),
                "lakove_zavady": [value(f"paint_defect_{index}") for index in range(1, 4)],
                "mechanicke_zavady": [value(f"mechanical_defect_{index}") for index in range(1, 4)],
            },
            "rework": {
                "repase_mechanicke": value("mechanical_rework_cost"),
                "repase_lakove": value("paint_rework_cost"),
                "repase_celkem": calculated["total_rework_cost"].get(),
            },
        }

    def call_openai_for_corrective_actions(self, api_key, model, context):
        prompt = (
            "Jsi odborný asistent pro vyhodnocení zakázky ve výrobní firmě SVOS. "
            "Navrhni stručná, praktická a auditovatelná nápravná opatření pro zadané lakové a mechanické závady. "
            "Piš česky. Neuváděj právní ani bezpečnostní jistoty, pouze pracovní návrhy k posouzení. "
            "Vrať výhradně validní JSON bez markdownu ve tvaru: "
            '{"paint_actions":["...","...","..."],"mechanical_actions":["...","...","..."],"conclusion":"..."} '
            "Počet položek v obou seznamech musí být přesně 3. Pokud závada chybí, navrhni obecné preventivní opatření."
        )
        body = {
            "model": model or DEFAULT_AI_MODEL,
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            "text": {"format": {"type": "text"}},
            "max_output_tokens": 900,
        }
        request = urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API vrátilo chybu {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Nepodařilo se připojit k online AI: {exc}") from exc

        text = self.extract_openai_text(payload)
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"AI nevrátila čitelný JSON:\n{text[:700]}") from exc
        return self.normalize_ai_result(result)

    @staticmethod
    def extract_openai_text(payload):
        if payload.get("output_text"):
            return str(payload["output_text"]).strip()
        parts = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    parts.append(str(content["text"]))
        return "\n".join(parts).strip()

    @staticmethod
    def normalize_ai_result(result):
        paint_actions = list(result.get("paint_actions") or [])[:3]
        mechanical_actions = list(result.get("mechanical_actions") or [])[:3]
        while len(paint_actions) < 3:
            paint_actions.append("")
        while len(mechanical_actions) < 3:
            mechanical_actions.append("")
        return {
            "paint_actions": [str(value).strip() for value in paint_actions],
            "mechanical_actions": [str(value).strip() for value in mechanical_actions],
            "conclusion": str(result.get("conclusion", "")).strip(),
        }

    def generate_ai_corrective_actions(self, dialog, variables, calculated, text_widgets, text_sync_callbacks, ai_button):
        for sync_callback in text_sync_callbacks:
            sync_callback()
        settings = self.request_ai_settings(dialog)
        if not settings:
            return

        context = self.build_ai_payload(variables, calculated)
        ai_button.configure(state=tk.DISABLED, text="AI pracuje...")

        def worker():
            try:
                result = self.call_openai_for_corrective_actions(settings["api_key"], settings["model"], context)
            except Exception as exc:
                dialog.after(0, lambda error=exc: self.finish_ai_corrective_actions(dialog, variables, text_widgets, ai_button, error=error))
                return
            dialog.after(0, lambda ai_result=result: self.finish_ai_corrective_actions(dialog, variables, text_widgets, ai_button, result=ai_result))

        threading.Thread(target=worker, daemon=True).start()

    def finish_ai_corrective_actions(self, dialog, variables, text_widgets, ai_button, result=None, error=None):
        if ai_button.winfo_exists():
            ai_button.configure(state=tk.NORMAL, text="AI návrh opatření")
        if error:
            messagebox.showerror(APP_NAME, str(error), parent=dialog)
            return

        for index, value in enumerate(result["paint_actions"], start=1):
            self.set_text_value(variables, text_widgets, f"paint_action_{index}", value)
        for index, value in enumerate(result["mechanical_actions"], start=1):
            self.set_text_value(variables, text_widgets, f"mechanical_action_{index}", value)
        if result["conclusion"]:
            self.set_text_value(variables, text_widgets, "conclusion", result["conclusion"])
        messagebox.showinfo(APP_NAME, "AI návrh byl doplněn do formuláře. Před uložením jej prosím zkontrolujte.", parent=dialog)

    @staticmethod
    def set_text_value(variables, text_widgets, key, value):
        variables[key].set(value)
        widget = text_widgets.get(key)
        if widget is not None and widget.winfo_exists():
            widget.delete("1.0", tk.END)
            widget.insert("1.0", value)

    def section_label(self, parent, text, row):
        tk.Label(
            parent,
            text=text,
            bg="#eef4ff",
            fg="#1d4ed8",
            font=(self.FONT, 11, "bold"),
            padx=10,
            pady=6,
            anchor="w",
        ).grid(row=row, column=0, columnspan=4, sticky="ew", pady=(12, 8))

    def add_text(self, parent, row, label, value, height):
        self.section_label(parent, label, row)
        widget = tk.Text(
            parent,
            height=height,
            wrap="word",
            font=(self.FONT, 10),
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#d7dee8",
            highlightcolor="#2563eb",
            padx=10,
            pady=8,
        )
        widget.insert("1.0", value or "")
        widget.grid(row=row + 1, column=0, columnspan=4, sticky="ew", pady=(0, 12))
        return widget

    def center_child(self, dialog, width, height):
        self.update_idletasks()
        x = self.winfo_rootx() + max((self.winfo_width() - width) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - height) // 2, 0)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def save_record(self, record_id, payload):
        fields = (
            "job_number", "job_name", "customer", "project_manager", "evaluation_date",
            "status", "result", "planned_revenue", "actual_revenue", "planned_cost",
            "actual_cost", "paint_defects", "mechanical_defects", "mechanical_rework_cost", "paint_rework_cost",
            "paint_defect_1", "paint_action_1", "paint_defect_2", "paint_action_2", "paint_defect_3", "paint_action_3",
            "mechanical_defect_1", "mechanical_action_1", "mechanical_defect_2", "mechanical_action_2", "mechanical_defect_3", "mechanical_action_3",
            "planned_hours", "actual_hours", "planned_finish",
            "actual_finish", "schedule_variance_days", "quality_result",
            "delivery_result", "positives", "negatives", "corrective_actions", "conclusion",
        )
        values = [payload.get(field, "") for field in fields]
        now = datetime.now().isoformat(timespec="seconds")
        if record_id:
            self.conn.execute(
                f"UPDATE job_evaluations SET {', '.join(field + '=?' for field in fields)}, updated_at=? WHERE id=?",
                values + [now, record_id],
            )
        else:
            self.conn.execute(
                f"INSERT INTO job_evaluations ({', '.join(fields)}, created_at, updated_at) VALUES ({', '.join('?' for _ in fields)}, ?, ?)",
                values + [now, now],
            )
        self.commit_database()

    def delete_selected(self):
        if not self.can_edit():
            self.require_admin()
            return
        record_id = self.selected_id()
        if not record_id:
            return
        if messagebox.askyesno(APP_NAME, "Opravdu chcete vybrané vyhodnocení smazat?", parent=self):
            self.conn.execute("DELETE FROM job_evaluations WHERE id=?", (record_id,))
            self.commit_database()
            self.refresh()

    def show_detail(self):
        record_id = self.selected_id()
        if not record_id:
            return
        record = self.get_record(record_id)
        dialog = tk.Toplevel(self)
        dialog.title(record["job_number"] or APP_NAME)
        dialog.geometry("780x640")
        dialog.minsize(640, 480)
        text = tk.Text(dialog, wrap="word", font=(self.FONT, 10), padx=16, pady=16)
        text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        text.insert("1.0", "\n".join(self.report_lines(record)))
        text.configure(state="disabled")
        actions = tk.Frame(dialog)
        actions.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.create_button(actions, "Zavřít", dialog.destroy).pack(side=tk.RIGHT)
        dialog.transient(self)

    def report_lines(self, record):
        lines = [
            f"Vyhodnocení zakázky: {record['job_number'] or record['id']}",
            "",
            "Ceny:",
            f"Kalkulovaná cena: {format_number(record['planned_revenue'])}",
            f"Skutečná cena: {format_number(record['actual_revenue'])}",
            f"Počítaný rozdíl cen: {format_number(record['price_difference'])}",
            "",
            "Náklady:",
            f"Kalkulované náklady: {format_number(record['planned_cost'])}",
            f"Skutečné náklady: {format_number(record['actual_cost'])}",
            f"Počítaný rozdíl nákladů: {format_number(record['cost_difference'])}",
            "",
            "Neshody:",
            f"Počet neshod lakových: {format_number(record['paint_defects'])}",
            f"Počet neshod mechanických: {format_number(record['mechanical_defects'])}",
            f"Součet neshod: {format_number(record['total_defects'])}",
            "",
            "Repase:",
            f"Náklady na repase mechanické: {format_number(record['mechanical_rework_cost'])}",
            f"Náklady na repase lakové: {format_number(record['paint_rework_cost'])}",
            f"Celkové náklady na repase: {format_number(record['total_rework_cost'])}",
        ]
        lines.extend((
            "",
            "Tři nejčastější lakové závady:",
        ))
        for index in range(1, 4):
            lines.append(f"Laková závada {index}: {record.get(f'paint_defect_{index}') or '-'}")
            lines.append(f"Navrhované nápravné odstranění {index}: {record.get(f'paint_action_{index}') or '-'}")
        lines.extend((
            "",
            "Tři nejčastější mechanické závady:",
        ))
        for index in range(1, 4):
            lines.append(f"Mechanická závada {index}: {record.get(f'mechanical_defect_{index}') or '-'}")
            lines.append(f"Navrhované nápravné opatření {index}: {record.get(f'mechanical_action_{index}') or '-'}")
        lines.extend((
            "",
            "Závěrečné vyhodnocení:",
            record.get("conclusion") or "-",
        ))
        return lines

    def logo_data_uri(self):
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        logo_path = base_path / "svos_logo.png"
        if not logo_path.exists():
            return ""
        try:
            encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        except OSError:
            return ""
        return f"data:image/png;base64,{encoded}"

    def report_sections(self, record):
        return (
            (
                "Základní údaje",
                (
                    ("Záznam", record["job_number"] or f"Vyhodnocení #{record['id']}"),
                ),
            ),
            (
                "Ceny",
                (
                    ("Kalkulovaná cena", format_number(record["planned_revenue"])),
                    ("Skutečná cena", format_number(record["actual_revenue"])),
                    ("Počítaný rozdíl cen", format_number(record["price_difference"])),
                ),
            ),
            (
                "Náklady",
                (
                    ("Kalkulované náklady", format_number(record["planned_cost"])),
                    ("Skutečné náklady", format_number(record["actual_cost"])),
                    ("Počítaný rozdíl nákladů", format_number(record["cost_difference"])),
                ),
            ),
            (
                "Neshody",
                (
                    ("Počet neshod lakových", format_number(record["paint_defects"])),
                    ("Počet neshod mechanických", format_number(record["mechanical_defects"])),
                    ("Součet neshod", format_number(record["total_defects"])),
                ),
            ),
            (
                "Tři nejčastější lakové závady",
                tuple(
                    item
                    for index in range(1, 4)
                    for item in (
                        (f"Laková závada {index}", record.get(f"paint_defect_{index}") or "-"),
                        (f"Navrhované nápravné odstranění {index}", record.get(f"paint_action_{index}") or "-"),
                    )
                ),
            ),
            (
                "Tři nejčastější mechanické závady",
                tuple(
                    item
                    for index in range(1, 4)
                    for item in (
                        (f"Mechanická závada {index}", record.get(f"mechanical_defect_{index}") or "-"),
                        (f"Navrhované nápravné opatření {index}", record.get(f"mechanical_action_{index}") or "-"),
                    )
                ),
            ),
            (
                "Repase",
                (
                    ("Náklady na repase mechanické", format_number(record["mechanical_rework_cost"])),
                    ("Náklady na repase lakové", format_number(record["paint_rework_cost"])),
                    ("Celkové náklady na repase", format_number(record["total_rework_cost"])),
                ),
            ),
            (
                "Závěrečné vyhodnocení",
                (
                    ("Vyhodnocení", record.get("conclusion") or "-"),
                ),
            ),
        )

    def build_html_report(self, record):
        logo = self.logo_data_uri()
        logo_html = f'<img src="{logo}" alt="SVOS">' if logo else '<div class="logo-text">SVOS</div>'
        cards = (
            ("Rozdíl cen", format_number(record["price_difference"])),
            ("Součet neshod", format_number(record["total_defects"])),
            ("Repase celkem", format_number(record["total_rework_cost"])),
        )
        cards_html = "".join(
            f"<div class='metric'><span>{html.escape(label)}</span><strong>{html.escape(str(value or '-'))}</strong></div>"
            for label, value in cards
        )
        sections_html = []
        for title, rows in self.report_sections(record):
            body = "".join(
                f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(value or '-'))}</td></tr>"
                for label, value in rows
            )
            sections_html.append(f"<section><h2>{html.escape(title)}</h2><table>{body}</table></section>")
        return f"""<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>{html.escape(APP_NAME)} - {html.escape(record['job_number'] or str(record['id']))}</title>
  <style>
    @page {{ size: A4; margin: 14mm; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; color: #17202a; background: #f8fafc; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 28px; }}
    header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; margin-bottom: 22px; }}
    .brand img {{ max-width: 120px; max-height: 48px; object-fit: contain; }}
    .logo-text {{ font-size: 28px; font-weight: 800; letter-spacing: 2px; }}
    .meta {{ color: #475569; font-size: 14px; margin-top: 10px; }}
    h1 {{ margin: 0; color: #020617; font-size: 26px; }}
    .subtitle {{ margin-top: 8px; color: #334155; font-size: 15px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 18px 0 20px; }}
    .metric {{ background: white; border: 1px solid #d9dee7; border-radius: 10px; padding: 14px 16px; }}
    .metric span {{ display: block; color: #64748b; font-size: 13px; margin-bottom: 6px; }}
    .metric strong {{ color: #1d4ed8; font-size: 18px; }}
    section {{ background: white; border: 1px solid #d9dee7; border-radius: 10px; padding: 18px; margin: 14px 0; page-break-inside: avoid; }}
    h2 {{ margin: 0 0 12px; color: #1d4ed8; font-size: 17px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 9px 10px; border-top: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
    th {{ width: 240px; color: #475569; font-weight: 700; }}
    td {{ color: #17202a; white-space: pre-wrap; }}
    .print-actions {{ text-align: right; margin-bottom: 12px; }}
    button {{ border: 0; background: #2563eb; color: white; padding: 9px 14px; border-radius: 8px; font-weight: 700; cursor: pointer; }}
    @media print {{
      body {{ background: white; }}
      main {{ padding: 0; max-width: none; }}
      .print-actions {{ display: none; }}
      section, .metric {{ border-color: #cbd5e1; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="print-actions"><button onclick="window.print()">Tisk</button></div>
    <header>
      <div class="brand">{logo_html}<div class="meta">SVOS, spol. s r.o.</div></div>
      <div>
        <h1>{html.escape(APP_NAME)}</h1>
        <div class="subtitle">{html.escape(record['job_number'] or f"Vyhodnocení #{record['id']}")}</div>
      </div>
    </header>
    <div class="metrics">{cards_html}</div>
    {''.join(sections_html)}
  </main>
</body>
</html>"""

    def selected_record(self):
        record_id = self.selected_id()
        return self.get_record(record_id) if record_id else None

    def export_selected_html(self):
        record = self.selected_record()
        if record:
            self.export_html(record)

    def export_selected_pdf(self):
        record = self.selected_record()
        if record:
            self.export_pdf(record)

    def print_selected(self):
        record = self.selected_record()
        if not record:
            return
        output_dir = Path(tempfile.gettempdir()) / "porady_job_evaluation_print"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_number = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (record["job_number"] or str(record["id"])))
        path = output_dir / f"Vyhodnoceni_zakazky_{safe_number}.html"
        path.write_text(self.build_html_report(record), encoding="utf-8")
        try:
            os.startfile(str(path), "print")
        except OSError:
            os.startfile(str(path))
            messagebox.showinfo(APP_NAME, "Soubor byl otevřen v prohlížeči. Tisk spusťte z otevřené sestavy.", parent=self)

    def export_html(self, record):
        path = filedialog.asksaveasfilename(
            parent=self, title="Export vyhodnocení zakázky do HTML",
            initialfile=f"Vyhodnoceni_zakazky_{record['job_number'] or record['id']}.html",
            defaultextension=".html", filetypes=[("HTML", "*.html"), ("Všechny soubory", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(self.build_html_report(record), encoding="utf-8")
        if messagebox.askyesno(APP_NAME, "HTML export byl uložen. Otevřít soubor?", parent=self):
            os.startfile(path)

    def export_pdf(self, record):
        path = filedialog.asksaveasfilename(
            parent=self, title="Export vyhodnocení zakázky do PDF",
            initialfile=f"Vyhodnoceni_zakazky_{record['job_number'] or record['id']}.pdf",
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf"), ("Všechny soubory", "*.*")],
        )
        if not path:
            return
        write_simple_pdf(path, APP_NAME, ["SVOS, spol. s r.o.", ""] + self.report_lines(record))
        if messagebox.askyesno(APP_NAME, "PDF export byl uložen. Otevřít soubor?", parent=self):
            os.startfile(path)

    def export_csv(self):
        rows = self.fetch_rows()
        path = filedialog.asksaveasfilename(parent=self, title="Export vyhodnocení zakázek", defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("Všechny soubory", "*.*")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow((
                "Záznam",
                "Kalkulovaná cena",
                "Skutečná cena",
                "Počítaný rozdíl cen",
                "Kalkulované náklady",
                "Skutečné náklady",
                "Počítaný rozdíl nákladů",
                "Počet neshod lakových",
                "Počet neshod mechanických",
                "Součet neshod",
                "Náklady na repase mechanické",
                "Náklady na repase lakové",
                "Celkové náklady na repase",
                "Laková závada 1",
                "Navrhované nápravné odstranění 1",
                "Laková závada 2",
                "Navrhované nápravné odstranění 2",
                "Laková závada 3",
                "Navrhované nápravné odstranění 3",
                "Mechanická závada 1",
                "Navrhované nápravné opatření 1",
                "Mechanická závada 2",
                "Navrhované nápravné opatření 2",
                "Mechanická závada 3",
                "Navrhované nápravné opatření 3",
                "Závěrečné vyhodnocení",
            ))
            for row in rows:
                writer.writerow((
                    row["job_number"] or f"Vyhodnocení #{row['id']}",
                    format_number(row["planned_revenue"]),
                    format_number(row["actual_revenue"]),
                    format_number(row["price_difference"]),
                    format_number(row["planned_cost"]),
                    format_number(row["actual_cost"]),
                    format_number(row["cost_difference"]),
                    format_number(row["paint_defects"]),
                    format_number(row["mechanical_defects"]),
                    format_number(row["total_defects"]),
                    format_number(row["mechanical_rework_cost"]),
                    format_number(row["paint_rework_cost"]),
                    format_number(row["total_rework_cost"]),
                    row.get("paint_defect_1") or "",
                    row.get("paint_action_1") or "",
                    row.get("paint_defect_2") or "",
                    row.get("paint_action_2") or "",
                    row.get("paint_defect_3") or "",
                    row.get("paint_action_3") or "",
                    row.get("mechanical_defect_1") or "",
                    row.get("mechanical_action_1") or "",
                    row.get("mechanical_defect_2") or "",
                    row.get("mechanical_action_2") or "",
                    row.get("mechanical_defect_3") or "",
                    row.get("mechanical_action_3") or "",
                    row.get("conclusion") or "",
                ))
        messagebox.showinfo(APP_NAME, f"CSV export byl uložen:\n{path}", parent=self)
