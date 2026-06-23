# -*- coding: utf-8 -*-

import csv
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
import urllib.request
import webbrowser
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from integrated_apps.entry_training.bozppo_config import (
    DATA_DIR as ENTRY_DATA_DIR,
    HANDOVER_FILE as ENTRY_HANDOVER_FILE,
    RESULTS_FILE as ENTRY_RESULTS_FILE,
)
from integrated_apps.external_companies.bozppo_config import (
    DATA_DIR as EXTERNAL_DATA_DIR,
    HANDOVER_FILE as EXTERNAL_HANDOVER_FILE,
    RESULTS_FILE as EXTERNAL_RESULTS_FILE,
)
from integrated_apps.external_companies.bozppo_excel import write_xlsx


class SuiteMixin:
    RELEASE_HISTORY = (
        ("4.85", "Opraveno rolování rozcestníku aplikací na menších obrazovkách a při větším počtu dlaždic."),
        ("4.84", "Doplněna aplikace Vyhodnocení zakázky s přehledem, formulářem a exportem do HTML, PDF a CSV."),
        ("4.83", "Doplněn virtuální asistent pro nápovědu, vyhledávání, termíny a rychlé otevření modulů."),
        ("4.82", "Nový podnět ve Změnovém řízení dostává automatické číslo ihned při založení formuláře."),
        ("4.81", "Do aplikace Změnové řízení bylo doplněno přihlášení a odhlášení admina přímo z okna aplikace."),
        ("4.80", "Doplněna aplikace Změnové řízení pro evidenci podnětů ke změně, stanoviska vlastníka procesu a exporty."),
        ("4.79", "Test připojení, okamžité přepnutí databáze, stavová lišta a místní náhradní databáze."),
        ("4.78", "Interaktivní hledání, dashboard a upozornění opatření, vazby, přílohy, historie, grafy a jednotná databáze."),
        ("4.77", "Opravena kolize se starým hledáním; tlačítko nyní používá hledání ve všech aplikacích."),
        ("4.76", "Globální hledání doplněno o přepínače aplikací a opravu staršího kódování textů."),
        ("4.75", "Globální hledání rozšířeno na všechny aplikace, témata, přílohy a dokumenty."),
        ("4.74", "Nápravná opatření doplněna o samostatnou přehledovou záložku."),
        ("4.73", "Dashboard doplněn o celkový počet nápravných opatření."),
        ("4.72", "Společný dashboard, hledání, termíny, zálohy, exporty, import a aktualizace."),
        ("4.71", "Integrace aplikací Externí firmy a Vstupní školení."),
        ("4.70", "Rozšíření měsíčního vyhodnocení kvality."),
        ("4.69", "Rozcestník aplikací a samostatné moduly."),
    )

    def initialize_suite(self):
        self.sync_integrated_records()
        self.root.after(1800, self.check_for_updates_silently)
        self.root.after(2600, self.create_automatic_suite_backup)

    @staticmethod
    def _read_csv(path):
        if not path.exists():
            return []
        with path.open("r", newline="", encoding="utf-8-sig") as stream:
            return list(csv.DictReader(stream, delimiter=";"))

    @staticmethod
    def _record_key(source, record_type, payload):
        raw = json.dumps([source, record_type, payload], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def sync_integrated_records(self):
        sources = (
            ("Externí firmy", "školení", EXTERNAL_RESULTS_FILE),
            ("Externí firmy", "předání pracoviště", EXTERNAL_HANDOVER_FILE),
            ("Vstupní školení", "školení", ENTRY_RESULTS_FILE),
            ("Vstupní školení", "předání pracoviště", ENTRY_HANDOVER_FILE),
        )
        cursor = self.conn.cursor()
        for source, record_type, path in sources:
            cursor.execute(
                "DELETE FROM suite_records WHERE source=? AND record_type=?",
                (source, record_type),
            )
            for row in self._read_csv(path):
                normalized = {str(key): str(value or "") for key, value in row.items()}
                title = (
                    normalized.get("pracovník")
                    or normalized.get("pracovnik")
                    or normalized.get("pracoviste")
                    or normalized.get("externi_firma")
                    or record_type
                )
                event_date = (
                    normalized.get("datum")
                    or normalized.get("datum_vytvoreni")
                    or normalized.get("prace_do")
                    or ""
                )
                cursor.execute(
                    """INSERT OR REPLACE INTO suite_records
                       (source, record_type, external_key, title, event_date, data_json, imported_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        source,
                        record_type,
                        self._record_key(source, record_type, normalized),
                        title,
                        event_date,
                        json.dumps(normalized, ensure_ascii=False),
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
        self.commit_database()

    def get_suite_dashboard_summary(self):
        self.sync_integrated_records()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM suite_records WHERE record_type='školení'")
        trainings = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM suite_records WHERE record_type='předání pracoviště'")
        handovers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM quality_evaluations")
        quality = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM corrective_actions")
        corrective_actions = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM change_requests")
        change_requests = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM job_evaluations")
        job_evaluations = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM change_requests WHERE COALESCE(process_status, 'Nový') IN ('Nový', 'K posouzení', 'Vráceno k doplnění')"
        )
        change_pending = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM change_requests WHERE COALESCE(process_status, '') IN ('Schváleno', 'Schváleno s úpravou')"
        )
        change_approved = cursor.fetchone()[0]
        cursor.execute("SELECT due_date, COALESCE(status, 'Nový') FROM corrective_actions")
        today = date.today()
        corrective_open = 0
        corrective_overdue = 0
        for due_date, status in cursor.fetchall():
            if status == "Uzavřeno":
                continue
            corrective_open += 1
            parsed_due = self.parse_due_date(due_date)
            if parsed_due and parsed_due < today:
                corrective_overdue += 1
        return {
            "trainings": trainings,
            "handovers": handovers,
            "quality": quality,
            "corrective_actions": corrective_actions,
            "corrective_open": corrective_open,
            "corrective_overdue": corrective_overdue,
            "change_requests": change_requests,
            "change_pending": change_pending,
            "change_approved": change_approved,
            "job_evaluations": job_evaluations,
        }

    def show_corrective_action_reminders(self):
        today = date.today()
        records = []
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, problem_title, owner, due_date, status
               FROM corrective_actions
               WHERE COALESCE(status, 'Nový') != 'Uzavřeno'"""
        )
        for record_id, title, owner, due_date, status in cursor.fetchall():
            parsed_due = self.parse_due_date(due_date)
            if not parsed_due:
                continue
            days = (parsed_due - today).days
            if days <= 7:
                records.append((days, record_id, title or "", owner or "", due_date or "", status or "Nový"))
        if not records:
            return
        records.sort(key=lambda row: row[0])
        dialog, content = self.create_dialog("Upozornění na nápravná opatření", 860, 500, 700, 390)
        self.create_dialog_header(
            content,
            "Blížící se termíny opatření",
            "Otevřená opatření po termínu nebo s termínem během následujících 7 dnů.",
            accent=self.COLORS["warning"],
        )
        columns = ("state", "due", "owner", "title")
        tree = ttk.Treeview(content, columns=columns, show="headings", selectmode="browse")
        for key, title, width in (
            ("state", "Stav termínu", 120),
            ("due", "Termín", 100),
            ("owner", "Odpovědnost", 160),
            ("title", "Problém / opatření", 420),
        ):
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="center" if key in ("state", "due") else "w")
        tree.tag_configure("overdue", background="#fee2e2")
        tree.tag_configure("soon", background="#fef3c7")
        tree.pack(fill=tk.BOTH, expand=True)
        for days, record_id, title, owner, due_date, _status in records:
            state = f"{abs(days)} dnů po termínu" if days < 0 else ("Dnes" if days == 0 else f"Za {days} dnů")
            tree.insert("", tk.END, iid=str(record_id), values=(state, due_date, owner or "-", title), tags=("overdue" if days < 0 else "soon",))

        def open_selected():
            selection = tree.selection()
            if selection:
                self.show_problem_dialog(problem_id=int(selection[0]))

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(12, 0))
        self.create_button(actions, text="Otevřít opatření", command=open_selected, variant="primary").pack(side=tk.LEFT)
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)
        tree.bind("<Double-1>", lambda _event: open_selected())

    def _collect_search_rows(self, query="", include_metadata=False):
        query_folded = self._repair_search_text(query).strip().casefold()
        rows = []
        cursor = self.conn.cursor()

        def add_row(source, record_type, title, event_date="", *details, record_id=None, meeting_id=None, target_path=None):
            source = self._repair_search_text(source)
            record_type = self._repair_search_text(record_type)
            title = self._repair_search_text(title)
            event_date = self._repair_search_text(event_date)
            detail = " | ".join(
                self._repair_search_text(value)
                for value in details
                if value not in (None, "")
            )
            display = (source, record_type, title, event_date, detail)
            if not query_folded or query_folded in " ".join(display).casefold():
                rows.append(
                    {
                        "display": display,
                        "source": source,
                        "record_type": record_type,
                        "record_id": record_id,
                        "meeting_id": meeting_id,
                        "target_path": target_path,
                    }
                )

        cursor.execute("SELECT id, title, date, notes FROM meetings")
        for meeting_id, title, meeting_date, notes in cursor.fetchall():
            add_row("Porady", "porada", title, meeting_date, notes, record_id=meeting_id, meeting_id=meeting_id)

        cursor.execute(
            """SELECT agenda_points.id, agenda_points.meeting_id, agenda_points.title, meetings.title, meetings.date
               FROM agenda_points
               LEFT JOIN meetings ON meetings.id=agenda_points.meeting_id"""
        )
        for point_id, meeting_id, point_title, meeting_title, meeting_date in cursor.fetchall():
            add_row("Porady", "bod programu", point_title, meeting_date, meeting_title, record_id=point_id, meeting_id=meeting_id)

        cursor.execute(
            """SELECT agenda_items.id, agenda_points.meeting_id, agenda_items.description, agenda_items.due_date, agenda_items.owner,
                      agenda_items.priority, agenda_items.due_date_reason,
                      agenda_points.title, meetings.title
               FROM agenda_items
               LEFT JOIN agenda_points ON agenda_points.id=agenda_items.point_id
               LEFT JOIN meetings ON meetings.id=agenda_points.meeting_id"""
        )
        for record_id, meeting_id, description, due_date, owner, priority, reason, point_title, meeting_title in cursor.fetchall():
            add_row("Porady", "úkol", description, due_date, owner, priority, reason, point_title, meeting_title, record_id=record_id, meeting_id=meeting_id)

        cursor.execute(
            """SELECT meeting_general_info.id, meeting_general_info.meeting_id, info_text, created_at, meetings.title
               FROM meeting_general_info
               LEFT JOIN meetings ON meetings.id=meeting_general_info.meeting_id"""
        )
        for record_id, meeting_id, info_text, created_at, meeting_title in cursor.fetchall():
            add_row("Porady", "všeobecná informace", info_text, created_at, meeting_title, record_id=record_id, meeting_id=meeting_id)

        cursor.execute(
            """SELECT meeting_orders.id, meeting_orders.meeting_id, description, due_date, owner, priority, created_at, meetings.title
               FROM meeting_orders
               LEFT JOIN meetings ON meetings.id=meeting_orders.meeting_id"""
        )
        for record_id, meeting_id, description, due_date, owner, priority, created_at, meeting_title in cursor.fetchall():
            add_row("Porady", "nařízení", description, due_date, owner, priority, created_at, meeting_title, record_id=record_id, meeting_id=meeting_id)

        cursor.execute(
            """SELECT meeting_requirements.id, meeting_requirements.meeting_id, description, due_date, owner, priority, requirement_status, created_at, meetings.title
               FROM meeting_requirements
               LEFT JOIN meetings ON meetings.id=meeting_requirements.meeting_id"""
        )
        for record_id, meeting_id, description, due_date, owner, priority, status, created_at, meeting_title in cursor.fetchall():
            add_row("Požadavky", "požadavek", description, due_date, owner, priority, status, created_at, meeting_title, record_id=record_id, meeting_id=meeting_id)

        cursor.execute(
            """SELECT id, meeting_id, problem_title, due_date, problem_description, root_cause, corrective_action,
                      owner, status, priority, created_at
               FROM corrective_actions"""
        )
        for record_id, meeting_id, title, due_date, description, cause, action, owner, status, priority, created_at in cursor.fetchall():
            add_row(
                "Problémy a opatření",
                "nápravné opatření",
                title,
                due_date,
                description,
                cause,
                action,
                owner,
                status,
                priority,
                created_at,
                record_id=record_id,
                meeting_id=meeting_id,
            )

        cursor.execute(
            """SELECT id, request_number, submitted_date, proposer, department, contact,
                      area, area_other, current_state, proposed_change, justification,
                      impacts, impact_comment, process_status, decision, decision_date,
                      owner_reasoning, revision_number
               FROM change_requests"""
        )
        for (
            record_id,
            request_number,
            submitted_date,
            proposer,
            department,
            contact,
            area,
            area_other,
            current_state,
            proposed_change,
            justification,
            impacts,
            impact_comment,
            status,
            decision,
            decision_date,
            owner_reasoning,
            revision_number,
        ) in cursor.fetchall():
            add_row(
                "Změnové řízení",
                "podnět ke změně",
                proposed_change or request_number,
                submitted_date,
                request_number,
                proposer,
                department,
                contact,
                area_other if area == "Jiné" and area_other else area,
                current_state,
                justification,
                impacts,
                impact_comment,
                status,
                decision,
                decision_date,
                owner_reasoning,
                revision_number,
                record_id=record_id,
            )

        cursor.execute(
            """SELECT id, job_number, job_name, customer, project_manager, evaluation_date,
                      status, result, planned_revenue, actual_revenue, planned_cost,
                      actual_cost, planned_hours, actual_hours, planned_finish,
                      actual_finish, schedule_variance_days, quality_result,
                      delivery_result, positives, negatives, corrective_actions,
                      conclusion
               FROM job_evaluations"""
        )
        for (
            record_id,
            job_number,
            job_name,
            customer,
            project_manager,
            evaluation_date,
            status,
            result,
            planned_revenue,
            actual_revenue,
            planned_cost,
            actual_cost,
            planned_hours,
            actual_hours,
            planned_finish,
            actual_finish,
            schedule_variance_days,
            quality_result,
            delivery_result,
            positives,
            negatives,
            corrective_actions,
            conclusion,
        ) in cursor.fetchall():
            add_row(
                "Vyhodnocení zakázky",
                "vyhodnocení zakázky",
                job_name or job_number,
                evaluation_date,
                job_number,
                customer,
                project_manager,
                status,
                result,
                planned_revenue,
                actual_revenue,
                planned_cost,
                actual_cost,
                planned_hours,
                actual_hours,
                planned_finish,
                actual_finish,
                schedule_variance_days,
                quality_result,
                delivery_result,
                positives,
                negatives,
                corrective_actions,
                conclusion,
                record_id=record_id,
            )

        cursor.execute("SELECT id, title, period, prepared_date, data_json FROM quality_evaluations")
        quality_records = {}
        for record_id, title, period, prepared_date, payload in cursor.fetchall():
            quality_records[record_id] = (title, period)
            add_row("Vyhodnocení kvality", "vyhodnocení", title, period, prepared_date, self._flatten_json(payload), record_id=record_id)

        cursor.execute("SELECT evaluation_id, file_name, mime_type, created_at FROM quality_attachments")
        for evaluation_id, file_name, mime_type, created_at in cursor.fetchall():
            evaluation_title, period = quality_records.get(evaluation_id, ("Vyhodnocení kvality", ""))
            add_row("Vyhodnocení kvality", "příloha", file_name, period or created_at, evaluation_title, mime_type, record_id=evaluation_id)

        cursor.execute("SELECT period, action, changed_at, changed_by, details FROM quality_history")
        for period, action, changed_at, changed_by, details in cursor.fetchall():
            add_row("Vyhodnocení kvality", "historie", action, period or changed_at, changed_by, details)

        cursor.execute(
            """SELECT comment_text, created_at, created_by, record_type, meetings.title
               FROM item_comments
               LEFT JOIN meetings ON meetings.id=item_comments.meeting_id"""
        )
        for comment, created_at, author, record_type, meeting_title in cursor.fetchall():
            add_row("Porady", "komentář", comment, created_at, author, record_type, meeting_title)

        cursor.execute("SELECT record_type, field_name, old_value, new_value, changed_at, changed_by FROM change_history")
        for record_type, field_name, old_value, new_value, changed_at, changed_by in cursor.fetchall():
            add_row("Porady", "historie změn", field_name or record_type, changed_at, old_value, new_value, changed_by)

        cursor.execute("SELECT name, target_path, arguments FROM app_launchers")
        for name, target_path, arguments in cursor.fetchall():
            add_row("Rozcestník", "aplikace", name, "", target_path, arguments)

        cursor.execute("SELECT source, record_type, title, event_date, data_json FROM suite_records")
        for source, record_type, title, event_date, payload in cursor.fetchall():
            add_row(source, record_type, title, event_date, self._flatten_json(payload))

        self._add_training_content_search_rows(add_row, "Externí firmy", EXTERNAL_DATA_DIR)
        self._add_training_content_search_rows(add_row, "Vstupní školení", ENTRY_DATA_DIR)
        if include_metadata:
            return rows
        return [row["display"] for row in rows]

    @staticmethod
    def _repair_search_text(value):
        text = str(value or "")
        for _attempt in range(3):
            try:
                repaired = text.encode("cp1252").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
            if repaired == text:
                break
            text = repaired
        return text

    @staticmethod
    def _flatten_json(payload):
        try:
            value = json.loads(payload) if isinstance(payload, str) else payload
        except (TypeError, json.JSONDecodeError):
            return str(payload or "")

        parts = []

        def walk(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    parts.append(str(key))
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)
            elif item not in (None, ""):
                parts.append(str(item))

        walk(value)
        return " | ".join(parts)

    def _add_training_content_search_rows(self, add_row, source, data_dir):
        content_path = data_dir / "skoleni_obsah.json"
        if content_path.exists():
            try:
                payload = json.loads(content_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            for section in payload.get("training_sections", []):
                add_row(source, "téma školení", section.get("title", ""), "", section.get("text", ""))
            for question in payload.get("questions", []):
                add_row(source, "testová otázka", question.get("text", ""), "", *question.get("options", []))

        settings_path = data_dir / "nastaveni.json"
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                settings = {}
            for key, value in settings.items():
                add_row(source, "nastavení", key, "", value)

        ignored_names = {
            "prehled_proskolenych.html",
            "skoleni_obsah.json",
            "zaznamy_skoleni.csv",
            "predani_pracoviste.csv",
            "nastaveni.json",
        }
        for path in data_dir.rglob("*"):
            if not path.is_file() or path.name in ignored_names:
                continue
            if "zalohy" in {part.casefold() for part in path.parts}:
                continue
            if path.suffix.casefold() not in {".html", ".htm", ".txt"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d.%m.%Y")
            except OSError:
                text = ""
                modified = ""
            plain_text = re.sub(r"<[^>]+>", " ", text)
            plain_text = self._repair_search_text(
                html.unescape(re.sub(r"\s+", " ", plain_text)).strip()
            )
            add_row(source, "dokument", path.stem, modified, plain_text, target_path=str(path))

    def show_suite_global_search(self):
        dialog, content = self.create_dialog("Centrální vyhledávání", 1050, 650, 820, 500)
        self.create_dialog_header(content, "Centrální vyhledávání", "Vyhledávání ve všech aplikacích, záznamech, tématech a dokumentech.")
        filters = tk.Frame(content, bg=self.COLORS["panel"])
        filters.pack(fill=tk.X, pady=(0, 12))
        query_var = tk.StringVar()
        dialog.global_search_query_var = query_var
        entry = ttk.Entry(filters, textvariable=query_var, font=(self.FONT, 11))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        source_var = tk.StringVar(value="Všechny aplikace")
        dialog.global_search_source_var = source_var
        source_filter = ttk.Combobox(
            filters,
            textvariable=source_var,
            state="readonly",
            width=24,
            values=(
                "Všechny aplikace",
                "Porady",
                "Požadavky",
                "Problémy a opatření",
                "Vyhodnocení kvality",
                "Externí firmy",
                "Vstupní školení",
                "Rozcestník",
            ),
        )
        source_filter.pack(side=tk.LEFT, padx=(10, 0), ipady=4)
        count_var = tk.StringVar()
        dialog.global_search_count_var = count_var
        tk.Label(
            content,
            textvariable=count_var,
            font=(self.FONT, 9),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 6))
        source_counts = tk.Frame(content, bg=self.COLORS["panel"])
        source_counts.pack(fill=tk.X, pady=(0, 8))
        columns = ("source", "type", "title", "date", "detail")
        tree_frame = tk.Frame(content, bg=self.COLORS["panel"])
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for key, label, width in (
            ("source", "Aplikace", 140),
            ("type", "Typ", 130),
            ("title", "Název", 240),
            ("date", "Datum / termín", 130),
            ("detail", "Podrobnosti", 380),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="center" if key == "date" else "w")
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        preview = tk.Text(content, height=6, wrap=tk.WORD, font=(self.FONT, 10), relief=tk.SOLID, borderwidth=1)
        preview.tag_configure("match", background="#fde68a", foreground="#7c2d12")
        preview.pack(fill=tk.X, pady=(10, 0))
        current_results = {}

        def show_preview(*_args):
            preview.config(state=tk.NORMAL)
            preview.delete("1.0", tk.END)
            selection = tree.selection()
            result = current_results.get(selection[0]) if selection else None
            if result:
                preview.insert("1.0", "\n".join(part for part in result["display"] if part))
                term = query_var.get().strip()
                if term:
                    start = "1.0"
                    while True:
                        position = preview.search(term, start, stopindex=tk.END, nocase=True)
                        if not position:
                            break
                        end = f"{position}+{len(term)}c"
                        preview.tag_add("match", position, end)
                        start = end
            preview.config(state=tk.DISABLED)

        def refresh(*_args):
            tree.delete(*tree.get_children())
            current_results.clear()
            query = entry.get()
            selected_source = source_filter.get()
            rows = self._collect_search_rows(query, include_metadata=True)
            if selected_source != "Všechny aplikace":
                rows = [row for row in rows if row["source"] == selected_source]
            for index, row in enumerate(rows):
                item_id = f"result_{index}"
                current_results[item_id] = row
                tree.insert("", tk.END, iid=item_id, values=row["display"])
            count_var.set(f"Nalezeno: {len(rows)}")
            for child in source_counts.winfo_children():
                child.destroy()
            counts = {}
            for row in self._collect_search_rows(query, include_metadata=True):
                counts[row["source"]] = counts.get(row["source"], 0) + 1
            for source, count in sorted(counts.items()):
                button = tk.Button(
                    source_counts,
                    text=f"{source}: {count}",
                    command=lambda selected=source: (source_filter.set(selected), refresh()),
                    bg="#e6edf7",
                    fg=self.COLORS["text"],
                    activebackground="#d7e3f3",
                    relief=tk.FLAT,
                    padx=8,
                    pady=4,
                    cursor="hand2",
                    font=(self.FONT, 9),
                )
                button.pack(side=tk.LEFT, padx=(0, 6))
            show_preview()

        def open_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Centrální vyhledávání", "Nejprve vyberte výsledek.", parent=dialog)
                return
            self._open_global_search_result(current_results.get(selection[0]), dialog)

        def export_results():
            rows = [current_results[item_id]["display"] for item_id in tree.get_children()]
            if not rows:
                messagebox.showwarning("Export hledání", "Není co exportovat.", parent=dialog)
                return
            filepath = filedialog.asksaveasfilename(
                parent=dialog,
                defaultextension=".html",
                initialfile=f"Vysledky_hledani_{datetime.now():%Y-%m-%d}.html",
                filetypes=[("HTML", "*.html")],
            )
            if not filepath:
                return
            body = "".join(
                "<tr>" + "".join(f"<td>{html.escape(str(value or ''))}</td>" for value in row) + "</tr>"
                for row in rows
            )
            document = f"""<!doctype html><html lang="cs"><head><meta charset="utf-8">
<title>Výsledky hledání</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:28px;color:#17202a}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #d7dee8;padding:8px;text-align:left;vertical-align:top}}
th{{background:#f1f5f9}}tr:nth-child(even){{background:#f8fafc}}
</style></head><body><h1>Výsledky hledání</h1>
<p>Dotaz: {html.escape(query_var.get())} | počet: {len(rows)}</p>
<table><thead><tr><th>Aplikace</th><th>Typ</th><th>Název</th><th>Datum</th><th>Podrobnosti</th></tr></thead>
<tbody>{body}</tbody></table></body></html>"""
            Path(filepath).write_text(document, encoding="utf-8")
            if messagebox.askyesno("Export hledání", "Výsledky byly exportovány. Otevřít soubor?", parent=dialog):
                os.startfile(filepath)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(10, 0))
        self.create_button(actions, text="Otevřít vybrané", command=open_selected, variant="primary").pack(side=tk.LEFT)
        self.create_button(actions, text="Export výsledků", command=export_results, variant="secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(actions, text="Zavřít", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT)

        search_state = {"query": None, "source": None}

        def watch_search():
            if not dialog.winfo_exists():
                return
            current = (entry.get(), source_filter.get())
            if current != (search_state["query"], search_state["source"]):
                search_state["query"], search_state["source"] = current
                refresh()
            dialog.after(180, watch_search)

        entry.bind("<KeyRelease>", refresh)
        entry.bind("<<Paste>>", lambda _event: dialog.after_idle(refresh))
        entry.bind("<<Cut>>", lambda _event: dialog.after_idle(refresh))
        query_var.trace_add("write", refresh)
        source_filter.bind("<<ComboboxSelected>>", refresh)
        tree.bind("<<TreeviewSelect>>", show_preview)
        tree.bind("<Double-1>", lambda _event: open_selected())
        tree.bind("<Return>", lambda _event: open_selected())
        refresh()
        search_state["query"] = entry.get()
        search_state["source"] = source_filter.get()
        dialog.after(180, watch_search)
        entry.focus_set()

    def _open_global_search_result(self, result, search_dialog=None):
        if not result:
            return
        record_type = result.get("record_type", "")
        record_id = result.get("record_id")
        meeting_id = result.get("meeting_id")
        target_path = result.get("target_path")

        if target_path and Path(target_path).exists():
            os.startfile(target_path)
            return
        if record_type == "požadavek" and record_id:
            self.show_requirement_dialog(requirement_id=record_id)
            return
        if record_type == "nápravné opatření" and record_id:
            self.show_problem_dialog(problem_id=record_id)
            return
        if record_type == "podnět ke změně" and record_id:
            self.show_change_management_application()

            def open_change_record():
                window = getattr(self, "change_management_window", None)
                if not window or not window.winfo_exists():
                    return
                if self.can_edit():
                    window.open_form(record_id)
                else:
                    window.tree.selection_set(str(record_id))
                    window.tree.focus(str(record_id))
                    window.show_detail()
                window.lift()

            self.root.after(120, open_change_record)
            return
        if record_type == "vyhodnocení zakázky" and record_id:
            self.show_job_evaluation_application()

            def open_job_record():
                window = getattr(self, "job_evaluation_window", None)
                if not window or not window.winfo_exists():
                    return
                if self.can_edit():
                    window.open_form(record_id)
                else:
                    window.tree.selection_set(str(record_id))
                    window.tree.focus(str(record_id))
                    window.show_detail()
                window.lift()

            self.root.after(120, open_job_record)
            return
        if result.get("source") == "Vyhodnocení kvality" and record_id:
            self.show_quality_application()

            def load_quality():
                window = getattr(self, "quality_window", None)
                if not window or not window.winfo_exists():
                    return
                row = self.conn.execute("SELECT data_json FROM quality_evaluations WHERE id=?", (record_id,)).fetchone()
                if not row:
                    return
                try:
                    window.data = json.loads(row[0])
                except (TypeError, json.JSONDecodeError):
                    return
                window.current_record_id = record_id
                window._load_into_ui(window.data)
                window.refresh_attachments()
                window.refresh_history()
                window.notebook.select(1)
                window.lift()

            self.root.after(120, load_quality)
            return
        if meeting_id:
            if self.current_id and self.notes_dirty:
                self.save_notes(show_message=False)
            self.current_id = meeting_id
            self.show_open_only.set(False)
            self.show_porady_workspace()
            self.load_meetings()
            self.load_meeting_details()
            self.root.lift()
            return
        if result.get("source") == "Externí firmy":
            self.show_external_companies_application()
        elif result.get("source") == "Vstupní školení":
            self.show_entry_training_application()

    def _collect_deadlines(self):
        deadlines = []
        today = date.today()
        cursor = self.conn.cursor()
        sources = (
            ("Úkol", "SELECT description, due_date, owner FROM agenda_items WHERE COALESCE(is_resolved, 0)=0"),
            ("Nařízení", "SELECT description, due_date, owner FROM meeting_orders WHERE COALESCE(is_resolved, 0)=0"),
            ("Požadavek", "SELECT description, due_date, owner FROM meeting_requirements WHERE COALESCE(is_resolved, 0)=0"),
            ("Problém", "SELECT problem_title, due_date, owner FROM corrective_actions WHERE COALESCE(status, 'Nový')!='Uzavřeno'"),
            ("Podnět ke změně", "SELECT proposed_change, decision_date, proposer FROM change_requests WHERE COALESCE(process_status, 'Nový') IN ('Schváleno', 'Schváleno s úpravou', 'Odloženo') AND COALESCE(decision_date, '')!=''"),
        )
        for record_type, sql in sources:
            cursor.execute(sql)
            for title, due_date, owner in cursor.fetchall():
                parsed = self.parse_due_date(due_date)
                if parsed:
                    deadlines.append((parsed, record_type, title or "", owner or ""))

        for source, result_file in (
            ("Externí školení", EXTERNAL_RESULTS_FILE),
            ("Vstupní školení", ENTRY_RESULTS_FILE),
        ):
            for row in self._read_csv(result_file):
                result = (row.get("výsledek") or row.get("vysledek") or "").upper()
                if "NESPL" in result:
                    continue
                value = row.get("datum", "").split(" ")[0]
                parsed = None
                for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                    try:
                        parsed = datetime.strptime(value, fmt).date()
                        break
                    except ValueError:
                        continue
                if parsed:
                    due = parsed + timedelta(days=365)
                    person = row.get("pracovník") or row.get("pracovnik") or ""
                    company = row.get("firma", "")
                    deadlines.append((due, source, person, company))
        return sorted(deadlines, key=lambda item: item[0])

    def show_global_deadlines(self):
        dialog, content = self.create_dialog("Společné termíny", 980, 620, 760, 480)
        self.create_dialog_header(content, "Společné termíny", "Otevřené položky a konce platnosti školení.")
        columns = ("status", "date", "type", "title", "owner")
        tree = ttk.Treeview(content, columns=columns, show="headings")
        for key, label, width in (
            ("status", "Stav", 110),
            ("date", "Termín", 120),
            ("type", "Typ", 150),
            ("title", "Název", 330),
            ("owner", "Osoba / firma", 200),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="center" if key in ("status", "date") else "w")
        tree.tag_configure("overdue", background="#fee2e2")
        tree.tag_configure("soon", background="#fef3c7")
        tree.pack(fill=tk.BOTH, expand=True)
        today = date.today()
        for due, record_type, title, owner in self._collect_deadlines():
            days = (due - today).days
            status = "Po termínu" if days < 0 else ("Do 30 dnů" if days <= 30 else "Aktivní")
            tag = "overdue" if days < 0 else ("soon" if days <= 30 else "")
            tree.insert("", tk.END, values=(status, due.strftime("%d.%m.%Y"), record_type, title, owner), tags=(tag,))

    def create_complete_backup(self):
        if not self.require_admin():
            return
        if self.current_id and self.notes_dirty:
            self.save_notes(show_message=False)
        self.sync_integrated_records()
        output = self._write_complete_backup("kompletni_zaloha")
        messagebox.showinfo("Kompletní záloha", f"Všechna data byla uložena do:\n{output}")

    def _write_complete_backup(self, prefix):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        output = self.backup_dir / f"{prefix}_{datetime.now():%Y-%m-%d_%H-%M-%S}.zip"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            if self.db_path.exists():
                archive.write(self.db_path, f"Porady/{self.db_path.name}")
            for label, directory in (("Externi_firmy", EXTERNAL_DATA_DIR), ("Vstupni_skoleni", ENTRY_DATA_DIR)):
                if directory.exists():
                    for path in directory.rglob("*"):
                        if path.is_file():
                            archive.write(path, Path(label) / path.relative_to(directory))
        return output

    def create_automatic_suite_backup(self):
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backups = sorted(self.backup_dir.glob("automaticka_kompletni_*.zip"), key=lambda path: path.stat().st_mtime)
            if backups and datetime.fromtimestamp(backups[-1].stat().st_mtime).date() == date.today():
                return
            self._write_complete_backup("automaticka_kompletni")
            for old_backup in backups[:-9]:
                old_backup.unlink(missing_ok=True)
        except OSError:
            return

    def _suite_report_rows(self):
        rows = self._collect_search_rows()
        return [["Aplikace", "Typ", "Název", "Datum / termín", "Podrobnosti"], *[list(row) for row in rows]]

    def export_suite_report(self, export_format):
        rows = self._suite_report_rows()
        output_dir = self.app_data_dir / "exporty"
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        if export_format == "xlsx":
            output = output_dir / f"celkovy_prehled_{stamp}.xlsx"
            write_xlsx(output, "Prehled", rows[0], rows[1:])
            os.startfile(output)
            return
        body = "\n".join(
            "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
            for row in rows[1:]
        )
        document = f"""<!doctype html><html lang="cs"><head><meta charset="utf-8">
<title>Celkový přehled aplikací</title><style>
body{{font-family:Segoe UI,Arial;margin:28px;color:#17202a}} h1{{color:#2563eb}}
table{{border-collapse:collapse;width:100%;font-size:11px}} th,td{{border:1px solid #d7dee8;padding:7px}}
th{{background:#eef2f6}} @media print{{body{{margin:10mm}}}}</style></head>
<body><h1>Celkový přehled aplikací</h1><p>Vytvořeno {datetime.now():%d.%m.%Y %H:%M}</p>
<table><thead><tr>{''.join(f'<th>{html.escape(value)}</th>' for value in rows[0])}</tr></thead>
<tbody>{body}</tbody></table></body></html>"""
        html_path = output_dir / f"celkovy_prehled_{stamp}.html"
        html_path.write_text(document, encoding="utf-8")
        if export_format == "html":
            webbrowser.open(html_path.as_uri())
            return
        pdf_path = output_dir / f"celkovy_prehled_{stamp}.pdf"
        edge = self._find_edge()
        if not edge:
            messagebox.showwarning("Export PDF", "Microsoft Edge nebyl nalezen. Otevírám HTML pro ruční tisk do PDF.")
            webbrowser.open(html_path.as_uri())
            return
        subprocess.run(
            [str(edge), "--headless", "--disable-gpu", f"--print-to-pdf={pdf_path.resolve()}", html_path.resolve().as_uri()],
            check=True,
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        os.startfile(pdf_path)

    @staticmethod
    def _find_edge():
        candidates = (
            shutil.which("msedge"),
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
        )
        return next((Path(item) for item in candidates if item and Path(item).exists()), None)

    def show_suite_exports(self):
        dialog, content = self.create_dialog("Společné exporty", 620, 300, 520, 260)
        self.create_dialog_header(content, "Společné exporty", "Souhrn dat ze všech částí aplikace.")
        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=24)
        for label, fmt in (("HTML", "html"), ("Excel", "xlsx"), ("PDF", "pdf")):
            self.create_button(actions, text=label, command=lambda value=fmt: self.export_suite_report(value), variant="primary").pack(
                side=tk.LEFT, padx=(0, 10)
            )

    def import_legacy_applications(self):
        if not self.require_admin():
            return
        source = filedialog.askdirectory(title="Vyberte původní složku aplikace")
        if not source:
            return
        source_path = Path(source)
        imported = 0
        mappings = (
            ("zaznamy_skoleni.csv", EXTERNAL_RESULTS_FILE if "extern" in source_path.name.casefold() else ENTRY_RESULTS_FILE),
            ("predani_pracoviste.csv", EXTERNAL_HANDOVER_FILE if "extern" in source_path.name.casefold() else ENTRY_HANDOVER_FILE),
        )
        for filename, target in mappings:
            candidate = source_path / filename
            if not candidate.exists():
                candidate = source_path / "dist" / filename
            if candidate.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    backup = target.with_name(f"{target.stem}_pred_importem_{datetime.now():%Y%m%d_%H%M%S}{target.suffix}")
                    shutil.copy2(target, backup)
                shutil.copy2(candidate, target)
                imported += 1
        self.sync_integrated_records()
        messagebox.showinfo("Import starých dat", f"Importováno souborů: {imported}")

    def _version_tuple(self, value):
        try:
            return tuple(int(part) for part in str(value).split("."))
        except ValueError:
            return (0,)

    def _load_update_manifest(self):
        local = Path(sys.executable).resolve().parent / "porady_latest_version.json"
        if local.exists():
            return json.loads(local.read_text(encoding="utf-8"))
        parser = getattr(self, "data_config", None)
        url = parser.get("updates", "manifest_url", fallback="") if parser else ""
        if not url:
            return None
        with urllib.request.urlopen(url, timeout=4) as response:
            return json.loads(response.read().decode("utf-8"))

    def check_for_updates(self, silent=False):
        try:
            manifest = self._load_update_manifest()
            if not manifest:
                if not silent:
                    messagebox.showinfo("Aktualizace", "Zdroj aktualizací není nastaven. Lze použít soubor porady_latest_version.json vedle EXE.")
                return
            latest = str(manifest.get("version", "0"))
            if self._version_tuple(latest) > self._version_tuple(self.APP_VERSION):
                messagebox.showinfo("Dostupná aktualizace", f"Je dostupná verze {latest}.\n\n{manifest.get('notes', '')}")
            elif not silent:
                messagebox.showinfo("Aktualizace", f"Používáte aktuální verzi {self.APP_VERSION}.")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            if not silent:
                messagebox.showwarning("Aktualizace", f"Kontrolu se nepodařilo dokončit:\n{error}")

    def check_for_updates_silently(self):
        self.check_for_updates(silent=True)

    def show_release_history(self):
        dialog, content = self.create_dialog("Historie verzí", 760, 500, 620, 400)
        self.create_dialog_header(content, "Historie verzí", "Přehled hlavních změn aplikace.")
        for version, description in self.RELEASE_HISTORY:
            row = tk.Frame(content, bg=self.COLORS["panel"], pady=8)
            row.pack(fill=tk.X)
            tk.Label(row, text=version, width=8, font=(self.FONT, 11, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["primary"]).pack(side=tk.LEFT)
            tk.Label(row, text=description, font=(self.FONT, 10), bg=self.COLORS["panel"], fg=self.COLORS["text"], anchor="w", wraplength=590).pack(side=tk.LEFT, fill=tk.X, expand=True)
