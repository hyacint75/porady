from __future__ import annotations

import calendar
import base64
import copy
import getpass
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from porady_quality_export import export_html


APP_NAME = "Měsíční vyhodnocení kvality"
VERSION = "1.1"
MONTHS = [
    "leden", "únor", "březen", "duben", "květen", "červen",
    "červenec", "srpen", "září", "říjen", "listopad", "prosinec",
]


def center_window(window, parent, width: int, height: int):
    parent = parent.winfo_toplevel()
    parent.update_idletasks()
    window.update_idletasks()
    parent_width = max(parent.winfo_width(), parent.winfo_screenwidth())
    parent_height = max(parent.winfo_height(), parent.winfo_screenheight())
    parent_x = parent.winfo_rootx() if parent.winfo_ismapped() else 0
    parent_y = parent.winfo_rooty() if parent.winfo_ismapped() else 0
    if parent.winfo_ismapped() and parent.winfo_width() > 1:
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
    x = parent_x + max((parent_width - width) // 2, 0)
    y = parent_y + max((parent_height - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")


def default_data() -> dict:
    return {
        "metadata": {
            "title": "Vyhodnocení kvality za květen 2026",
            "company": "SVOS, spol. s r.o.",
            "prepared_by": "Oddělení řízení kvality",
            "period": "květen 2026",
            "next_period": "červen 2026",
            "prepared_date": "10.6.2026",
            "approved_by": "-",
            "signature_name": "Kaas Petr",
        },
        "purpose": (
            "Toto vyhodnocení slouží ke zhodnocení stavu kvality za měsíc květen 2026, "
            "k posouzení plnění požadavků zákazníků, interních požadavků a požadavků systému "
            "managementu kvality. Součástí vyhodnocení je přehled zjištěných neshod, reklamací, "
            "interních kontrol, nápravných opatření a návrh opatření ke zlepšení."
        ),
        "summary": (
            "Za měsíc květen 2026 byl systém řízení kvality zaměřen zejména na průběžnou kontrolu "
            "výrobních zakázek, mezioperační a výstupní kontroly výrobků, řešení interních neshod, "
            "sledování zákaznických požadavků a podporu výroby při odstraňování opakovaných vad."
        ),
        "overview": [
            {"area": "Stav systému kvality", "comment": "-", "status": "stabilní"},
            {"area": "Hlavní problém měsíce", "comment": "Stanovení jasných pravidel pro systémy lakování", "status": "neuspokojivý"},
            {"area": "Další problém měsíce", "comment": "Větší míra poškození na karoseriích a dveřích po zámečnických úpravách", "status": "zhoršující se"},
            {"area": "Priorita pro další měsíc", "comment": "Snížení počtu poškození na karoseriích a dveřích", "status": "zhoršující se"},
            {"area": "Priorita pro další měsíc", "comment": "Zlepšení kvality tmelení na vozidlech a ostatní výrobě", "status": "zhoršující se"},
        ],
        "complaints": [
            {"indicator": "Počet nových zákaznických reklamací", "value": "0", "note": "0"},
            {"indicator": "Počet uzavřených zákaznických reklamací", "value": "0", "note": "0"},
            {"indicator": "Počet otevřených reklamací ke konci měsíce", "value": "1", "note": "Sklo Jelcz"},
            {"indicator": "Počet opakovaných reklamací", "value": "0", "note": "0"},
        ],
        "nonconformity_stats": [
            {"indicator": "Počet interních neshod", "value": "9", "note": "-"},
            {"indicator": "Počet odstraněných neshod", "value": "9", "note": "-"},
            {"indicator": "Počet otevřených neshod", "value": "0", "note": "-"},
            {"indicator": "Počet opakovaných neshod", "value": "9", "note": "Dveře, karoserie – deformace plechu, poškození; odlupující se lak na rámečku oken"},
            {"indicator": "Počet neshod z mezioperační kontroly", "value": "0", "note": "-"},
            {"indicator": "Počet neshod z výstupní kontroly", "value": "> 180", "note": "Viz protokoly z výstupních kontrol"},
        ],
        "nonconformities": [
            {"area": "Výrobní provedení", "finding": "Karoserie, dveře – deformace plechu", "cause": "Deformace plechu vlivem svařovacích a upínacích prací", "measure": "Dodržování technologické kázně při svařování a upínání dílů, průběžná kontrola kvality prováděných prací", "owner": "Mistr, pracovník"},
            {"area": "Povrchová úprava", "finding": "Odlupující se lak rámečků dveří", "cause": "Neprovedené odmaštění povrchu", "measure": "Fix na zkoušky odmaštění povrchu", "owner": "ŘK"},
            {"area": "Montáž", "finding": "Povolený šroub horního uchycení LZ tlumiče", "cause": "Selhání samokontroly pracovníka", "measure": "Rozšíření kontrolní karty vozidla o kontrolu dotažení šroubů podvozku", "owner": "Mistr, ŘK"},
        ],
        "inspection_intro": "V průběhu měsíce byly prováděny vstupní, mezioperační a výstupní kontroly. Zvláštní pozornost byla věnována kritickým znakům jakosti, správnosti výrobní dokumentace a odstranění dříve zjištěných neshod.",
        "inspections": [
            {"type": "Vstupní kontrola", "count": "1", "issues": "0", "note": "OK / diskrétní mřížky chladiče (komaxit)"},
            {"type": "Mezioperační kontrola", "count": "8", "issues": "0", "note": "OK"},
            {"type": "Výstupní kontrola", "count": "6", "issues": "0", "note": "OK"},
        ],
        "supplier_stats": [
            {"indicator": "Počet dodavatelských neshod", "value": "0", "note": "-"},
            {"indicator": "Počet reklamací na dodavatele", "value": "0", "note": "-"},
            {"indicator": "Počet opakovaných problémů u dodavatelů", "value": "0", "note": "-"},
            {"indicator": "Počet požadovaných vyjádření / 8D od dodavatelů", "value": "0", "note": "-"},
        ],
        "supplier_issues": [],
        "corrective_actions": [
            {"number": "1", "source": "Dveře, karoserie – deformace plechu, poškození", "description": "Zavést povinné používání ochranných podložek, krytek hran a určených přepravních vozíků / stojanů.", "owner": "mistr", "deadline": "30.6.2026", "status": "otevřeno", "effectiveness": "-"},
            {"number": "2", "source": "Odlupující se lak na rámečku oken", "description": "Doplnit kontrolní bod před lakováním: čistota povrchu, odmaštění, zdrsnění, stav hran a rohů rámečku.", "owner": "Mistr, ŘK", "deadline": "30.6.2026", "status": "otevřeno", "effectiveness": "-"},
            {"number": "3", "source": "Vyklepaný šroub uchycení zadního tlumiče vozidla T6", "description": "Rozšíření kontrolní karty vozidla o kontrolu dotažení šroubů podvozku.", "owner": "Pracovník, mistr, ŘK", "deadline": "30.6.2026", "status": "otevřeno", "effectiveness": "-"},
        ],
        "risks": [
            {"risk": "Opakování stejných výrobních vad", "impact": "zvýšené náklady, zdržení zakázky", "probability": "vysoká", "severity": "vysoká", "measure": "důsledná analýza příčin"},
            {"risk": "Neúplná kontrolní dokumentace", "impact": "obtížné prokazování shody", "probability": "vysoká", "severity": "vysoká", "measure": "kontrola úplnosti záznamů"},
            {"risk": "Nedostatečné předání informací mezi úseky", "impact": "vznik chyb při výrobě", "probability": "vysoká", "severity": "vysoká", "measure": "zlepšit komunikaci výroba-kvalita-technologie"},
            {"risk": "Nedodržení rozměrů a sestavení", "impact": "opravy, přepracování", "probability": "vysoká", "severity": "vysoká", "measure": "mezioperační kontrola kritických rozměrů"},
        ],
        "next_actions": [
            {"number": "1", "description": "Zaměřit se na opakované interní neshody a stanovit jejich skutečnou příčinu.", "owner": "Kaas Petr", "deadline": "30.6.2026", "note": "Spolupráce s výrobou a TÚ"},
            {"number": "2", "description": "Zlepšit kvalitu zápisů v systému PALSTAT.", "owner": "Mrázek Aleš", "deadline": "30.6.2026", "note": "-"},
            {"number": "3", "description": "Důsledně vyžadovat fotodokumentaci u významných neshod.", "owner": "Mrázek Aleš", "deadline": "30.6.2026", "note": "PALSTAT"},
            {"number": "4", "description": "Provádět mezioperační kontroly u kritických výrobních kroků.", "owner": "Mrázek Aleš", "deadline": "30.6.2026", "note": "Kontrola dotažení komponent podvozku"},
            {"number": "5", "description": "Pravidelně vyhodnocovat otevřená nápravná opatření.", "owner": "Autoři nápravných opatření", "deadline": "průběžně", "note": "-"},
        ],
        "conclusion": "Na základě provedeného vyhodnocení lze konstatovat, že systém řízení kvality byl v hodnoceném měsíci funkční. Byly prováděny kontroly, neshody byly evidovány a řešeny. Pro další období je nutné posílit prevenci opakovaných neshod, zlepšit úplnost záznamů a důsledněji vyhodnocovat účinnost přijatých opatření.",
        "next_goal": "Hlavním cílem pro další měsíc je snížení počtu opakovaných vad, lepší sledování příčin neshod a zvýšení důslednosti při mezioperační kontrole.",
    }


TABLE_DEFINITIONS = {
    "overview": ("Celkové hodnocení", [("area", "Hodnocená oblast"), ("comment", "Vyhodnocení / komentář"), ("status", "Stav")]),
    "complaints": ("Zákaznické reklamace", [("indicator", "Ukazatel"), ("value", "Hodnota"), ("note", "Poznámka")]),
    "nonconformity_stats": ("Statistika neshod", [("indicator", "Ukazatel"), ("value", "Hodnota"), ("note", "Poznámka")]),
    "nonconformities": ("Přehled interních neshod", [("area", "Oblast"), ("finding", "Popis zjištění"), ("cause", "Pravděpodobná příčina"), ("measure", "Návrh opatření"), ("owner", "Odpovědnost")]),
    "inspections": ("Kontrolní činnost", [("type", "Druh kontroly"), ("count", "Počet kontrol"), ("issues", "Zjištěné neshody"), ("note", "Vyhodnocení / poznámka")]),
    "supplier_stats": ("Statistika dodavatelské kvality", [("indicator", "Ukazatel"), ("value", "Hodnota"), ("note", "Poznámka")]),
    "supplier_issues": ("Problémy dodavatelů", [("supplier", "Dodavatel"), ("problem", "Popis problému"), ("impact", "Dopad"), ("measure", "Požadované opatření"), ("status", "Stav")]),
    "corrective_actions": ("Nápravná a preventivní opatření", [("number", "Č."), ("source", "Zdroj"), ("description", "Popis opatření"), ("owner", "Odpovědná osoba"), ("deadline", "Termín"), ("status", "Stav"), ("effectiveness", "Vyhodnocení účinnosti")]),
    "risks": ("Rizika z pohledu kvality", [("risk", "Riziko"), ("impact", "Dopad"), ("probability", "Pravděpodobnost"), ("severity", "Závažnost"), ("measure", "Navržené opatření")]),
    "next_actions": ("Opatření pro další měsíc", [("number", "Č."), ("description", "Navržené opatření"), ("owner", "Odpovědná osoba"), ("deadline", "Termín"), ("note", "Poznámka")]),
}


class RowDialog(tk.Toplevel):
    def __init__(self, parent, title: str, columns: list[tuple[str, str]], values: dict | None = None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(True, True)
        self.result = None
        self.columns = columns
        self.widgets = {}
        values = values or {}
        self.columnconfigure(1, weight=1)

        for row, (key, label) in enumerate(columns):
            ttk.Label(self, text=label + ":").grid(row=row, column=0, sticky="nw", padx=(16, 8), pady=7)
            widget = tk.Text(self, height=2 if len(columns) < 6 else 1, width=62, wrap="word")
            widget.insert("1.0", values.get(key, ""))
            widget.grid(row=row, column=1, sticky="ew", padx=(0, 16), pady=7)
            self.widgets[key] = widget

        buttons = ttk.Frame(self)
        buttons.grid(row=len(columns), column=0, columnspan=2, sticky="e", padx=16, pady=16)
        ttk.Button(buttons, text="Zrušit", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Uložit", style="QualityAccent.TButton", command=self._save).pack(side="right")
        self.bind("<Escape>", lambda _event: self.destroy())
        self.grab_set()
        self.after_idle(lambda: center_window(self, parent, 760, max(300, 105 + len(columns) * 58)))
        self.widgets[columns[0][0]].focus_set()

    def _save(self):
        self.result = {key: widget.get("1.0", "end-1c").strip() for key, widget in self.widgets.items()}
        self.destroy()


class TableEditor(ttk.Frame):
    def __init__(
        self,
        parent,
        columns: list[tuple[str, str]],
        *,
        editable: bool = True,
        show_controls: bool = True,
    ):
        super().__init__(parent, padding=16)
        self.columns = columns
        self.editable = editable
        self.rows = []
        self.row_ids = []
        self.selected_row = None
        self.selected_column = 0
        self.on_open = None
        self.on_change = None
        self.row_color_fn = None
        self._cell_editor = None
        self._editing_row = None
        self._editing_column = None
        self.column_widths = [max(140, min(300, len(label) * 14)) for _key, label in columns]

        hint = ttk.Label(
            self,
            text=(
                "Dvojklikem upravíte buňku přímo v tabulce. Enter uloží, Tab přejde na další sloupec."
                if editable else
                "Dvojklikem otevřete vybrané vyhodnocení."
            ),
            style="QualityHint.TLabel",
        )
        hint.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.canvas = tk.Canvas(
            self,
            background="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#CBD5E1",
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.grid_frame = tk.Frame(self.canvas, background="#CBD5E1")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        scroll_x.grid(row=2, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.grid_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._fit_grid_width)

        if show_controls:
            buttons = ttk.Frame(self)
            buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            ttk.Button(
                buttons,
                text="+ Přidat řádek",
                style="QualityAccent.TButton",
                command=self.add,
            ).pack(side="left")
            ttk.Button(buttons, text="Upravit detail", command=self.edit).pack(side="left", padx=6)
            ttk.Button(buttons, text="Odstranit řádek", command=self.delete).pack(side="left")
            ttk.Button(buttons, text="Nahoru", command=lambda: self.move(-1)).pack(side="left", padx=(18, 6))
            ttk.Button(buttons, text="Dolů", command=lambda: self.move(1)).pack(side="left")
            ttk.Button(buttons, text="Vymazat buňku", command=self.clear_cell).pack(side="right")

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self._render()

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_grid_width(self, event):
        content_width = sum(self.column_widths)
        self.canvas.itemconfigure(self.canvas_window, width=max(content_width, event.width))

    def _render(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()

        for column, ((_key, label), width) in enumerate(zip(self.columns, self.column_widths)):
            header = tk.Label(
                self.grid_frame,
                text=label,
                width=1,
                background="#1F4E78",
                foreground="#FFFFFF",
                font=("Segoe UI Semibold", 10),
                anchor="center",
                justify="center",
                padx=8,
                pady=9,
                borderwidth=0,
            )
            header.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0, 1 if column < len(self.columns) - 1 else 0),
                pady=(0, 1),
            )
            self.grid_frame.grid_columnconfigure(column, minsize=width, weight=1)

        for row_index, row in enumerate(self.rows):
            selected = row_index == self.selected_row
            row_color = self.row_color_fn(row) if self.row_color_fn else None
            for column, ((key, _label), width) in enumerate(zip(self.columns, self.column_widths)):
                cell = tk.Label(
                    self.grid_frame,
                    text=row.get(key, ""),
                    background=(
                        "#D9EAF7"
                        if selected
                        else row_color or ("#F4F8FB" if row_index % 2 else "#FFFFFF")
                    ),
                    foreground="#17202A",
                    font=("Segoe UI", 10),
                    anchor="center",
                    justify="center",
                    wraplength=width - 18,
                    padx=8,
                    pady=8,
                    borderwidth=0,
                )
                cell.grid(
                    row=row_index + 1,
                    column=column,
                    sticky="nsew",
                    padx=(0, 1),
                    pady=(0, 1),
                )
                cell.bind("<Button-1>", lambda _event, r=row_index, c=column: self._select_cell(r, c))
                cell.bind("<Double-1>", lambda _event, r=row_index, c=column: self._activate_cell(r, c))
        self.after_idle(self._update_scroll_region)

    def set_rows(self, rows: list[dict], row_ids=None):
        self.rows = [dict(row) for row in rows]
        self.row_ids = list(row_ids or range(len(rows)))
        self.selected_row = None
        self._render()

    def get_rows(self) -> list[dict]:
        return [dict(row) for row in self.rows]

    def get_selected_id(self):
        if self.selected_row is None or self.selected_row >= len(self.row_ids):
            return None
        return self.row_ids[self.selected_row]

    def _select_cell(self, row: int, column: int):
        self.selected_row = row
        self.selected_column = column
        for row_index in range(len(self.rows)):
            background = "#D9EAF7" if row_index == row else ("#F4F8FB" if row_index % 2 else "#FFFFFF")
            for cell in self.grid_frame.grid_slaves(row=row_index + 1):
                if isinstance(cell, tk.Label):
                    cell.configure(background=background)

    def _activate_cell(self, row: int, column: int):
        self._select_cell(row, column)
        if self.editable:
            self._open_cell_editor(row, column)
        elif self.on_open:
            self.on_open()

    def add(self):
        self.rows.append({key: "" for key, _label in self.columns})
        self.row_ids.append(None)
        self.selected_row = len(self.rows) - 1
        self.selected_column = 0
        self._render()
        self._notify_change()
        self.after_idle(lambda: self._open_cell_editor(self.selected_row, 0))

    def edit(self):
        if self.selected_row is None:
            messagebox.showinfo(APP_NAME, "Nejprve vyberte řádek, který chcete upravit.", parent=self)
            return
        values = self.rows[self.selected_row]
        dialog = RowDialog(self, "Upravit záznam", self.columns, values)
        self.wait_window(dialog)
        if dialog.result is not None:
            self.rows[self.selected_row] = dialog.result
            self._render()
            self._notify_change()

    def delete(self):
        if self.selected_row is not None and messagebox.askyesno(
            APP_NAME,
            "Odstranit vybraný řádek?",
            parent=self,
            default=messagebox.YES,
        ):
            del self.rows[self.selected_row]
            del self.row_ids[self.selected_row]
            self.selected_row = None
            self._render()
            self._notify_change()

    def move(self, direction: int):
        if self.selected_row is None:
            return
        target = self.selected_row + direction
        if 0 <= target < len(self.rows):
            self.rows[self.selected_row], self.rows[target] = self.rows[target], self.rows[self.selected_row]
            self.row_ids[self.selected_row], self.row_ids[target] = self.row_ids[target], self.row_ids[self.selected_row]
            self.selected_row = target
            self._render()
            self._notify_change()

    def clear_cell(self):
        if self.selected_row is None:
            return
        key = self.columns[self.selected_column][0]
        self.rows[self.selected_row][key] = ""
        self._render()
        self._notify_change()

    def _open_cell_editor(self, row: int, column: int):
        self._finish_cell_edit()
        if row is None or not (0 <= row < len(self.rows)):
            return
        cells = self.grid_frame.grid_slaves(row=row + 1, column=column)
        if not cells:
            return
        cell = cells[0]
        key = self.columns[column][0]
        editor = ttk.Entry(cell, font=("Segoe UI", 10), justify="center")
        editor.insert(0, self.rows[row].get(key, ""))
        editor.select_range(0, "end")
        editor.place(x=1, y=1, relwidth=1, relheight=1, width=-2, height=-2)
        editor.focus_set()
        editor.bind("<Return>", lambda _event: self._finish_cell_edit())
        editor.bind("<Escape>", lambda _event: self._cancel_cell_edit())
        editor.bind("<Tab>", lambda _event: self._move_cell(1))
        editor.bind("<Shift-Tab>", lambda _event: self._move_cell(-1))
        editor.bind("<FocusOut>", lambda _event: self._finish_cell_edit())
        self._cell_editor = editor
        self._editing_row = row
        self._editing_column = column

    def _finish_cell_edit(self):
        if self._cell_editor is None:
            return
        editor = self._cell_editor
        row = self._editing_row
        column = self._editing_column
        value = editor.get().strip()
        self._cell_editor = None
        self._editing_row = None
        editor.destroy()
        if row is not None and column is not None and row < len(self.rows):
            self.rows[row][self.columns[column][0]] = value
            self.selected_row = row
            self.selected_column = column
            self._render()
            self._notify_change()

    def _cancel_cell_edit(self):
        if self._cell_editor is not None:
            self._cell_editor.destroy()
        self._cell_editor = None
        self._editing_row = None

    def _move_cell(self, direction: int):
        row = self._editing_row
        column = self._editing_column or 0
        self._finish_cell_edit()
        if row is None:
            return "break"

        next_column = column + direction
        next_row = row
        if next_column >= len(self.columns):
            next_column = 0
            if row == len(self.rows) - 1:
                self.rows.append({key: "" for key, _label in self.columns})
                self.row_ids.append(None)
                next_row = len(self.rows) - 1
            else:
                next_row = row + 1
        elif next_column < 0:
            if row == 0:
                next_column = 0
            else:
                next_column = len(self.columns) - 1
                next_row = row - 1
        self.selected_row = next_row
        self.selected_column = next_column
        self._render()
        self.after_idle(lambda: self._open_cell_editor(next_row, next_column))
        return "break"

    def _notify_change(self):
        if self.on_change:
            self.on_change()


class QualityApp(tk.Toplevel):
    def __init__(self, parent, connection=None, commit_callback=None, on_home=None):
        super().__init__(parent)
        self.parent = parent
        self.conn = connection or sqlite3.connect(":memory:")
        self.commit_callback = commit_callback
        self.on_home = on_home
        self.title(f"{APP_NAME} {VERSION}")
        self.minsize(980, 640)
        self.data = default_data()
        self.current_record_id = None
        self.scalar_widgets = {}
        self.table_editors = {}
        self.autosave_job = None
        self.dirty = False
        self.loading_ui = False
        self._ensure_database_table()
        self._configure_style()
        self._build_ui()
        self._load_into_ui(self.data)
        self._bind_autosave()
        self.refresh_overview()
        self.after_idle(lambda: center_window(self, parent, 1280, 780))
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _ensure_database_table(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS quality_evaluations
               (id INTEGER PRIMARY KEY, period TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
                prepared_date TEXT, data_json TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS quality_attachments
               (id INTEGER PRIMARY KEY, evaluation_id INTEGER NOT NULL,
                file_name TEXT NOT NULL, mime_type TEXT, file_data BLOB NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(evaluation_id) REFERENCES quality_evaluations(id) ON DELETE CASCADE)"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS quality_history
               (id INTEGER PRIMARY KEY, evaluation_id INTEGER,
                period TEXT, action TEXT NOT NULL, changed_at TEXT NOT NULL,
                changed_by TEXT, details TEXT)"""
        )
        self.conn.commit()

    def _commit(self):
        if self.commit_callback:
            return self.commit_callback()
        self.conn.commit()
        return True

    def _configure_style(self):
        style = ttk.Style(self)
        style.configure("Quality.TNotebook.Tab", padding=(15, 8), font=("Segoe UI", 10))
        style.configure(
            "QualityAccent.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(12, 7),
        )
        style.configure("QualityTitle.TLabel", font=("Segoe UI Semibold", 18), foreground="#1F4E78")
        style.configure("QualityHint.TLabel", foreground="#606060")
        style.configure(
            "Quality.Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#17202A",
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Quality.Treeview.Heading",
            background="#1F4E78",
            foreground="#FFFFFF",
            relief="flat",
            padding=(10, 9),
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Quality.Treeview",
            background=[("selected", "#D9EAF7")],
            foreground=[("selected", "#17202A")],
        )
        style.map(
            "Quality.Treeview.Heading",
            background=[("active", "#2D6594")],
        )

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(12, 10))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="← Rozcestník", command=self.return_home).pack(side="left", padx=(0, 10))
        ttk.Label(toolbar, text=APP_NAME, style="QualityTitle.TLabel").pack(side="left")
        self.fullscreen_button = ttk.Button(
            toolbar,
            text="Celá obrazovka",
            command=self.toggle_maximized,
        )
        self.fullscreen_button.pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Nový měsíc", command=self.new_month).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Kopírovat měsíc", command=self.copy_previous_month).pack(side="right", padx=(6, 0))
        ttk.Button(
            toolbar,
            text="Export a tisk",
            style="QualityAccent.TButton",
            command=self.export_and_print,
        ).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Exportovat HTML", command=self.export).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Export PDF", command=self.export_pdf).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Uložit", command=self.save).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Přehled", command=self.show_overview).pack(side="right", padx=(6, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.configure(style="Quality.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._build_overview_tab()
        self._build_metadata_tab()
        self._build_text_tab()
        self._build_tables_tab()
        self._build_conclusion_tab()
        self._build_attachments_tab()
        self._build_history_tab()

        self.status = tk.StringVar(value="Připraveno")
        ttk.Label(self, textvariable=self.status, style="QualityHint.TLabel", padding=(12, 4)).pack(fill="x")

    def return_home(self):
        if self.dirty:
            self.save(silent=True)
        self.destroy()
        if self.on_home:
            self.on_home()

    def toggle_maximized(self):
        maximized = self.state() == "zoomed"
        self.state("normal" if maximized else "zoomed")
        self.fullscreen_button.configure(text="Celá obrazovka" if maximized else "Obnovit")

    def _build_overview_tab(self):
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text="Měsíční přehled")
        self.overview_tab = frame
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(
            header,
            text="Uložená měsíční vyhodnocení",
            font=("Segoe UI Semibold", 15),
            foreground="#1F4E78",
        ).pack(side="left")
        ttk.Button(header, text="Obnovit", command=self.refresh_overview).pack(side="right")

        filters = ttk.Frame(frame)
        filters.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(filters, text="Hledat:").pack(side="left")
        self.overview_search_var = tk.StringVar()
        search_entry = ttk.Entry(filters, textvariable=self.overview_search_var, width=38)
        search_entry.pack(side="left", padx=(8, 14))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_overview())
        ttk.Label(
            filters,
            text="Trend porovnává počet reklamací a interních neshod s předchozím měsícem.",
            style="QualityHint.TLabel",
        ).pack(side="left")

        self.overview_table = TableEditor(
            frame,
            [
                ("period", "Období"),
                ("title", "Název dokumentu"),
                ("prepared_date", "Datum zpracování"),
                ("trend", "Trend"),
                ("updated_at", "Naposledy upraveno"),
            ],
            editable=False,
            show_controls=False,
        )
        self.overview_table.column_widths = [150, 430, 160, 130, 180]
        self.overview_table.row_color_fn = self._overview_row_color
        self.overview_table.on_open = self.load_selected
        self.overview_table.grid(row=2, column=0, columnspan=2, sticky="nsew")

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(
            buttons,
            text="Otevřít vyhodnocení",
            style="QualityAccent.TButton",
            command=self.load_selected,
        ).pack(side="left")
        ttk.Button(buttons, text="Odstranit", command=self.delete_selected).pack(side="left", padx=6)
        ttk.Button(buttons, text="Historie", command=self.show_history).pack(side="left")
        ttk.Button(buttons, text="Přílohy", command=self.show_attachments).pack(side="left", padx=6)

        self.trend_canvas = tk.Canvas(
            frame,
            height=210,
            background="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#CBD5E1",
        )
        self.trend_canvas.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    def show_overview(self):
        self.refresh_overview()
        self.notebook.select(self.overview_tab)

    def _build_metadata_tab(self):
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="Základní údaje")
        fields = [
            ("title", "Název dokumentu"),
            ("company", "Společnost"),
            ("prepared_by", "Zpracoval / oddělení"),
            ("period", "Hodnocené období"),
            ("next_period", "Následující období"),
            ("prepared_date", "Datum zpracování"),
            ("approved_by", "Schválil"),
            ("signature_name", "Jméno pro podpis"),
        ]
        frame.columnconfigure(1, weight=1)
        for row, (key, label) in enumerate(fields):
            ttk.Label(frame, text=label + ":").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=8)
            entry = ttk.Entry(frame)
            entry.grid(row=row, column=1, sticky="ew", pady=8)
            self.scalar_widgets[f"metadata.{key}"] = entry
        ttk.Label(
            frame,
            text="Tlačítko „Nový měsíc“ automaticky přepočítá období, termíny a číslování.",
            style="QualityHint.TLabel",
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(18, 0))

    def _text_editor(self, parent, key: str, title: str, row: int, height: int = 7):
        ttk.Label(parent, text=title, font=("Segoe UI Semibold", 11)).grid(row=row, column=0, sticky="w", pady=(0, 6))
        text = tk.Text(parent, height=height, wrap="word", undo=True, font=("Segoe UI", 10))
        text.grid(row=row + 1, column=0, sticky="nsew", pady=(0, 16))
        self.scalar_widgets[key] = text
        parent.rowconfigure(row + 1, weight=1)

    def _build_text_tab(self):
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text="Účel a shrnutí")
        frame.columnconfigure(0, weight=1)
        self._text_editor(frame, "purpose", "Účel vyhodnocení", 0)
        self._text_editor(frame, "summary", "Celkové shrnutí", 2)
        self._text_editor(frame, "inspection_intro", "Úvod ke kontrolní činnosti", 4, height=5)

    def _build_tables_tab(self):
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="Tabulky")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        selector = ttk.Frame(frame)
        selector.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 8))
        ttk.Label(
            selector,
            text="Vyberte tabulku:",
            font=("Segoe UI Semibold", 10),
        ).pack(side="left", padx=(0, 10))

        self.table_selector = ttk.Combobox(
            selector,
            state="readonly",
            width=48,
            font=("Segoe UI", 10),
        )
        self.table_selector.pack(side="left", fill="x", expand=True)
        self.table_selector.bind("<<ComboboxSelected>>", self._show_selected_table)

        self.table_container = ttk.Frame(frame)
        self.table_container.grid(row=1, column=0, sticky="nsew")
        self.table_container.columnconfigure(0, weight=1)
        self.table_container.rowconfigure(0, weight=1)

        self.table_keys = list(TABLE_DEFINITIONS)
        titles = []
        for key in self.table_keys:
            title, columns = TABLE_DEFINITIONS[key]
            titles.append(title)
            editor = TableEditor(self.table_container, columns)
            editor.on_change = self._mark_dirty
            if key in ("corrective_actions", "next_actions"):
                editor.row_color_fn = self._deadline_row_color
            editor.grid(row=0, column=0, sticky="nsew")
            editor.grid_remove()
            self.table_editors[key] = editor

        self.table_selector["values"] = titles
        self.table_selector.current(0)
        self._show_selected_table()

    def _show_selected_table(self, _event=None):
        index = self.table_selector.current()
        if index < 0:
            return
        for editor in self.table_editors.values():
            editor.grid_remove()
        editor = self.table_editors[self.table_keys[index]]
        editor.grid()
        editor.tkraise()

    def _build_conclusion_tab(self):
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text="Závěr")
        frame.columnconfigure(0, weight=1)
        self._text_editor(frame, "conclusion", "Závěrečné vyhodnocení", 0, height=12)
        self._text_editor(frame, "next_goal", "Hlavní cíl pro další měsíc", 2, height=6)

    def _build_attachments_tab(self):
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text="Přílohy")
        self.attachments_tab = frame
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Přílohy a fotografie uložené přímo v databázi",
            font=("Segoe UI Semibold", 14),
            foreground="#1F4E78",
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.attachments_tree = ttk.Treeview(
            frame,
            columns=("name", "type", "size", "created"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in (
            ("name", "Soubor", 430),
            ("type", "Typ", 180),
            ("size", "Velikost", 110),
            ("created", "Přidáno", 170),
        ):
            self.attachments_tree.heading(key, text=label)
            self.attachments_tree.column(key, width=width, anchor="center")
        self.attachments_tree.grid(row=1, column=0, sticky="nsew")
        self.attachments_tree.bind("<Double-1>", lambda _event: self.open_attachment())
        controls = ttk.Frame(frame)
        controls.grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Button(controls, text="Přidat přílohu / fotografii", command=self.add_attachment).pack(side="left")
        ttk.Button(controls, text="Otevřít", command=self.open_attachment).pack(side="left", padx=6)
        ttk.Button(controls, text="Odstranit", command=self.delete_attachment).pack(side="left")

    def _build_history_tab(self):
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text="Historie")
        self.history_tab = frame
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Historie změn měsíčního vyhodnocení",
            font=("Segoe UI Semibold", 14),
            foreground="#1F4E78",
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.history_tree = ttk.Treeview(
            frame,
            columns=("time", "user", "action", "details"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in (
            ("time", "Čas", 170),
            ("user", "Uživatel", 150),
            ("action", "Akce", 170),
            ("details", "Podrobnosti", 650),
        ):
            self.history_tree.heading(key, text=label)
            self.history_tree.column(key, width=width, anchor="center")
        self.history_tree.grid(row=1, column=0, sticky="nsew")
        ttk.Button(frame, text="Obnovit", command=self.refresh_history).grid(row=2, column=0, sticky="w", pady=(12, 0))

    def show_attachments(self):
        self.refresh_attachments()
        self.notebook.select(self.attachments_tab)

    def show_history(self):
        self.refresh_history()
        self.notebook.select(self.history_tab)

    def refresh_attachments(self):
        if not hasattr(self, "attachments_tree"):
            return
        self.attachments_tree.delete(*self.attachments_tree.get_children())
        if self.current_record_id is None:
            return
        rows = self.conn.execute(
            """SELECT id, file_name, mime_type, length(file_data), created_at
               FROM quality_attachments WHERE evaluation_id=? ORDER BY id DESC""",
            (self.current_record_id,),
        ).fetchall()
        for attachment_id, name, mime_type, size, created_at in rows:
            self.attachments_tree.insert(
                "",
                "end",
                iid=str(attachment_id),
                values=(name, mime_type or "-", self._format_size(size), created_at.replace("T", " ")),
            )

    @staticmethod
    def _format_size(size):
        size = int(size or 0)
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} kB"
        return f"{size} B"

    def add_attachment(self):
        if self.current_record_id is None:
            if not self.save():
                return
        paths = filedialog.askopenfilenames(
            parent=self,
            title="Vybrat přílohy nebo fotografie",
            filetypes=[
                ("Obrázky a dokumenty", "*.png *.jpg *.jpeg *.gif *.bmp *.pdf *.doc *.docx *.xls *.xlsx *.txt"),
                ("Všechny soubory", "*.*"),
            ],
        )
        if not paths:
            return
        now = datetime.now().isoformat(timespec="seconds")
        try:
            for path in paths:
                file_path = Path(path)
                self.conn.execute(
                    """INSERT INTO quality_attachments
                       (evaluation_id, file_name, mime_type, file_data, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        self.current_record_id,
                        file_path.name,
                        mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
                        file_path.read_bytes(),
                        now,
                    ),
                )
            self._log_history(
                self.current_record_id,
                self.data.get("metadata", {}).get("period", ""),
                "přidány přílohy",
                ", ".join(Path(path).name for path in paths),
            )
            self._commit()
            self.refresh_attachments()
        except (OSError, sqlite3.Error) as exc:
            messagebox.showerror(APP_NAME, f"Přílohu se nepodařilo uložit:\n{exc}", parent=self)

    def _selected_attachment_id(self):
        selected = self.attachments_tree.selection()
        return int(selected[0]) if selected else None

    def open_attachment(self):
        attachment_id = self._selected_attachment_id()
        if attachment_id is None:
            messagebox.showinfo(APP_NAME, "Nejprve vyberte přílohu.", parent=self)
            return
        row = self.conn.execute(
            "SELECT file_name, file_data FROM quality_attachments WHERE id=?",
            (attachment_id,),
        ).fetchone()
        if not row:
            return
        temp_dir = Path(tempfile.gettempdir()) / "PoradyQualityAttachments"
        temp_dir.mkdir(parents=True, exist_ok=True)
        target = temp_dir / f"{attachment_id}_{row[0]}"
        target.write_bytes(row[1])
        os.startfile(target)

    def delete_attachment(self):
        attachment_id = self._selected_attachment_id()
        if attachment_id is None:
            return
        if not messagebox.askyesno(
            APP_NAME,
            "Odstranit vybranou přílohu z databáze?",
            parent=self,
            default=messagebox.YES,
        ):
            return
        row = self.conn.execute(
            "SELECT file_name FROM quality_attachments WHERE id=?",
            (attachment_id,),
        ).fetchone()
        self.conn.execute("DELETE FROM quality_attachments WHERE id=?", (attachment_id,))
        self._log_history(
            self.current_record_id,
            self.data.get("metadata", {}).get("period", ""),
            "odstraněna příloha",
            row[0] if row else "",
        )
        self._commit()
        self.refresh_attachments()

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        self.history_tree.delete(*self.history_tree.get_children())
        if self.current_record_id is None:
            return
        rows = self.conn.execute(
            """SELECT changed_at, changed_by, action, details
               FROM quality_history WHERE evaluation_id=?
               ORDER BY id DESC LIMIT 250""",
            (self.current_record_id,),
        ).fetchall()
        for changed_at, user, action, details in rows:
            self.history_tree.insert(
                "",
                "end",
                values=(changed_at.replace("T", " "), user or "-", action, details or ""),
            )

    @staticmethod
    def _set_widget(widget, value):
        if isinstance(widget, tk.Text):
            widget.delete("1.0", "end")
            widget.insert("1.0", value)
        else:
            widget.delete(0, "end")
            widget.insert(0, value)

    @staticmethod
    def _get_widget(widget):
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c").strip()
        return widget.get().strip()

    def _load_into_ui(self, data: dict):
        self.loading_ui = True
        for path, widget in self.scalar_widgets.items():
            if "." in path:
                group, key = path.split(".", 1)
                value = data.get(group, {}).get(key, "")
            else:
                value = data.get(path, "")
            self._set_widget(widget, value)
        for key, editor in self.table_editors.items():
            editor.set_rows(data.get(key, []))
        self.loading_ui = False
        self.dirty = False

    def _bind_autosave(self):
        for widget in self.scalar_widgets.values():
            if isinstance(widget, tk.Text):
                widget.edit_modified(False)
                widget.bind("<<Modified>>", self._text_modified, add="+")
            else:
                widget.bind("<KeyRelease>", self._mark_dirty, add="+")
                widget.bind("<<ComboboxSelected>>", self._mark_dirty, add="+")

    def _text_modified(self, event):
        widget = event.widget
        if widget.edit_modified():
            widget.edit_modified(False)
            self._mark_dirty()

    def _mark_dirty(self, _event=None):
        if self.loading_ui:
            return
        self.dirty = True
        self.status.set("Neuložené změny")
        if self.autosave_job:
            self.after_cancel(self.autosave_job)
        self.autosave_job = self.after(1800, self._autosave)

    def _autosave(self):
        self.autosave_job = None
        if not self.dirty or self.current_record_id is None:
            return
        if self.save(silent=True):
            self.status.set(f"Automaticky uloženo v {datetime.now().strftime('%H:%M:%S')}")

    @staticmethod
    def _parse_date(value):
        value = (value or "").strip()
        for fmt in ("%d.%m.%Y", "%d.%m.%y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    def _deadline_row_color(self, row):
        deadline = self._parse_date(row.get("deadline", ""))
        status = (row.get("status", "") or "").strip().lower()
        if deadline and deadline < date.today() and status not in ("uzavřeno", "splněno", "hotovo"):
            return "#FEE2E2"
        return None

    def _validate(self, data, *, show_message=True):
        meta = data.get("metadata", {})
        missing = [
            label
            for key, label in (
                ("title", "Název dokumentu"),
                ("prepared_by", "Zpracoval / oddělení"),
                ("period", "Hodnocené období"),
                ("prepared_date", "Datum zpracování"),
            )
            if not str(meta.get(key, "")).strip()
        ]
        invalid_dates = []
        if meta.get("prepared_date") and not self._parse_date(meta.get("prepared_date")):
            invalid_dates.append("Datum zpracování")
        for table_key in ("corrective_actions", "next_actions"):
            for index, row in enumerate(data.get(table_key, []), 1):
                deadline = (row.get("deadline", "") or "").strip()
                if deadline and deadline.lower() != "průběžně" and not self._parse_date(deadline):
                    invalid_dates.append(f"{TABLE_DEFINITIONS[table_key][0]} – řádek {index}")
        if missing or invalid_dates:
            if show_message:
                parts = []
                if missing:
                    parts.append("Doplňte povinná pole:\n• " + "\n• ".join(missing))
                if invalid_dates:
                    parts.append("Opravte datum ve formátu DD.MM.RRRR:\n• " + "\n• ".join(invalid_dates))
                messagebox.showwarning(APP_NAME, "\n\n".join(parts), parent=self)
            return False
        return True

    def _collect(self) -> dict:
        result = copy.deepcopy(self.data)
        for path, widget in self.scalar_widgets.items():
            value = self._get_widget(widget)
            if "." in path:
                group, key = path.split(".", 1)
                result.setdefault(group, {})[key] = value
            else:
                result[path] = value
        for key, editor in self.table_editors.items():
            result[key] = editor.get_rows()
        self.data = result
        return result

    def refresh_overview(self):
        if not hasattr(self, "overview_table"):
            return
        rows = self.conn.execute(
            """SELECT id, period, title, prepared_date, updated_at, data_json
               FROM quality_evaluations
               ORDER BY updated_at DESC, id DESC"""
        ).fetchall()
        display_rows = []
        row_ids = []
        parsed = []
        for record_id, period, title, prepared_date, updated_at, payload in rows:
            try:
                data = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                data = {}
            parsed.append((record_id, period, title, prepared_date, updated_at, data))
        parsed.sort(key=lambda item: self._period_sort_key(item[1]), reverse=True)
        previous_score = None
        search = self.overview_search_var.get().strip().lower() if hasattr(self, "overview_search_var") else ""
        chart_rows = []
        for record_id, period, title, prepared_date, updated_at, data in reversed(parsed):
            metrics = self._quality_metrics(data)
            score = metrics["complaints"] + metrics["nonconformities"]
            if previous_score is None:
                trend = "bez srovnání"
            elif score < previous_score:
                trend = "zlepšení"
            elif score > previous_score:
                trend = "zhoršení"
            else:
                trend = "stabilní"
            previous_score = score
            chart_rows.append((period, metrics))
            if search and search not in f"{period} {title} {prepared_date} {trend}".lower():
                continue
            display_updated = updated_at
            try:
                display_updated = datetime.fromisoformat(updated_at).strftime("%d.%m.%Y %H:%M")
            except (TypeError, ValueError):
                pass
            row_ids.append(record_id)
            display_rows.append({
                "period": period,
                "title": title,
                "prepared_date": prepared_date,
                "trend": trend,
                "updated_at": display_updated,
            })
        self.overview_table.set_rows(list(reversed(display_rows)), list(reversed(row_ids)))
        self._draw_trend_chart(chart_rows[-12:])

    @staticmethod
    def _period_sort_key(period):
        text = (period or "").strip().lower()
        for index, month in enumerate(MONTHS, 1):
            if text.startswith(month):
                match = re.search(r"(\d{4})", text)
                return (int(match.group(1)) if match else 0, index)
        return (0, 0)

    @staticmethod
    def _numeric_value(value):
        match = re.search(r"-?\d+", str(value or "").replace(" ", ""))
        return int(match.group()) if match else 0

    def _quality_metrics(self, data):
        def total(rows, phrases):
            return sum(
                self._numeric_value(row.get("value", ""))
                for row in rows
                if any(phrase in (row.get("indicator", "") or "").lower() for phrase in phrases)
            )
        complaints = total(data.get("complaints", []), ("nových", "otevřených"))
        nonconformities = total(data.get("nonconformity_stats", []), ("interních neshod",))
        open_actions = sum(
            1 for row in data.get("corrective_actions", [])
            if (row.get("status", "") or "").lower() not in ("uzavřeno", "splněno", "hotovo")
        )
        return {
            "complaints": complaints,
            "nonconformities": nonconformities,
            "open_actions": open_actions,
        }

    @staticmethod
    def _overview_row_color(row):
        return {
            "zlepšení": "#DCFCE7",
            "zhoršení": "#FEE2E2",
            "stabilní": "#FEF3C7",
        }.get(row.get("trend"))

    def _draw_trend_chart(self, rows):
        canvas = self.trend_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 900)
        height = 210
        margin = 42
        if not rows:
            canvas.create_text(width / 2, height / 2, text="Pro graf zatím nejsou data.", fill="#667085")
            return
        maximum = max(
            1,
            max(max(metrics.values()) for _period, metrics in rows),
        )
        plot_width = width - margin * 2
        plot_height = height - 65
        canvas.create_line(margin, 15, margin, 15 + plot_height, fill="#94A3B8")
        canvas.create_line(margin, 15 + plot_height, width - margin, 15 + plot_height, fill="#94A3B8")
        series = (
            ("complaints", "Reklamace", "#D97706"),
            ("nonconformities", "Neshody", "#DC2626"),
            ("open_actions", "Otevřená opatření", "#2563EB"),
        )
        for series_index, (key, label, color) in enumerate(series):
            points = []
            for index, (_period, metrics) in enumerate(rows):
                x = margin + (plot_width * index / max(len(rows) - 1, 1))
                y = 15 + plot_height - (metrics[key] / maximum * plot_height)
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=color, width=2, smooth=True)
            else:
                canvas.create_oval(points[0] - 3, points[1] - 3, points[0] + 3, points[1] + 3, fill=color)
            canvas.create_text(margin + series_index * 170, height - 14, text=f"■ {label}", fill=color, anchor="w")
        for index, (period, _metrics) in enumerate(rows):
            x = margin + (plot_width * index / max(len(rows) - 1, 1))
            canvas.create_text(x, 15 + plot_height + 14, text=period[:3], fill="#475569", font=("Segoe UI", 8))

    def load_selected(self):
        record_id = self.overview_table.get_selected_id()
        if record_id is None:
            messagebox.showinfo(APP_NAME, "Nejprve vyberte měsíční vyhodnocení.", parent=self)
            return
        row = self.conn.execute(
            "SELECT data_json FROM quality_evaluations WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            self.refresh_overview()
            messagebox.showwarning(APP_NAME, "Vybrané vyhodnocení už neexistuje.", parent=self)
            return
        try:
            loaded = json.loads(row[0])
        except (TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, f"Vyhodnocení se nepodařilo načíst:\n{exc}", parent=self)
            return
        self.data = loaded
        self.current_record_id = record_id
        self._load_into_ui(loaded)
        self.refresh_attachments()
        self.refresh_history()
        self.notebook.select(1)
        self.status.set(f"Načteno z databáze: {loaded.get('metadata', {}).get('period', '')}")

    def delete_selected(self):
        record_id = self.overview_table.get_selected_id()
        if record_id is None:
            messagebox.showinfo(APP_NAME, "Nejprve vyberte měsíční vyhodnocení.", parent=self)
            return
        if not messagebox.askyesno(
            APP_NAME,
            "Odstranit vybrané měsíční vyhodnocení z databáze?",
            parent=self,
            default=messagebox.YES,
        ):
            return
        period = self.data.get("metadata", {}).get("period", "")
        self._log_history(record_id, period, "odstraněno", "Vyhodnocení bylo odstraněno.")
        self.conn.execute("DELETE FROM quality_attachments WHERE evaluation_id = ?", (record_id,))
        self.conn.execute("DELETE FROM quality_evaluations WHERE id = ?", (record_id,))
        if self._commit() is False:
            return
        if self.current_record_id == record_id:
            self.current_record_id = None
        self.refresh_overview()
        self.status.set("Vyhodnocení bylo odstraněno.")

    def new_month(self):
        raw = simpledialog.askstring(APP_NAME, "Zadejte měsíc a rok ve formátu MM/RRRR:", parent=self)
        if not raw:
            return
        self._set_new_period(self._collect(), raw)

    def _set_new_period(self, data, raw):
        try:
            month, year = [int(part) for part in raw.replace(".", "/").split("/")]
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_NAME, "Zadejte platný měsíc ve formátu MM/RRRR, například 06/2026.", parent=self)
            return False
        next_month = month % 12 + 1
        next_year = year + (1 if month == 12 else 0)
        period = f"{MONTHS[month - 1]} {year}"
        next_period = f"{MONTHS[next_month - 1]} {next_year}"
        last_day = calendar.monthrange(next_year, next_month)[1]
        data["metadata"].update(
            title=f"Vyhodnocení kvality za {period}",
            period=period,
            next_period=next_period,
            prepared_date=date.today().strftime("%d.%m.%Y").lstrip("0").replace(".0", "."),
        )
        for index, action in enumerate(data["next_actions"], 1):
            action["number"] = str(index)
            if action.get("deadline", "").lower() != "průběžně":
                action["deadline"] = f"{last_day}.{next_month}.{next_year}"
        for index, action in enumerate(data["corrective_actions"], 1):
            action["number"] = str(index)
        self.data = data
        self._load_into_ui(data)
        self.current_record_id = None
        self.notebook.select(1)
        self.dirty = True
        self.status.set(f"Založeno nové období: {period}")
        return True

    def copy_previous_month(self):
        record_id = self.overview_table.get_selected_id()
        if record_id is None:
            row = self.conn.execute(
                "SELECT id FROM quality_evaluations ORDER BY updated_at DESC, id DESC LIMIT 1"
            ).fetchone()
            record_id = row[0] if row else None
        if record_id is None:
            messagebox.showinfo(APP_NAME, "Zatím není uložené vyhodnocení, které lze kopírovat.", parent=self)
            return
        row = self.conn.execute(
            "SELECT data_json FROM quality_evaluations WHERE id=?",
            (record_id,),
        ).fetchone()
        if not row:
            return
        raw = simpledialog.askstring(
            APP_NAME,
            "Zadejte nový měsíc a rok ve formátu MM/RRRR:",
            parent=self,
        )
        if not raw:
            return
        copied = copy.deepcopy(json.loads(row[0]))
        if self._set_new_period(copied, raw):
            self.status.set("Minulý měsíc byl zkopírován jako nový návrh.")

    def save(self, silent=False):
        data = self._collect()
        if not self._validate(data, show_message=not silent):
            return False
        metadata = data.get("metadata", {})
        period = metadata.get("period", "").strip()
        title = metadata.get("title", "").strip() or f"Vyhodnocení kvality za {period}"
        if not period:
            return False

        existing = self.conn.execute(
            "SELECT id FROM quality_evaluations WHERE period = ?",
            (period,),
        ).fetchone()
        record_id = self.current_record_id
        if existing and existing[0] != record_id:
            if silent or not messagebox.askyesno(
                APP_NAME,
                f"Vyhodnocení za období „{period}“ už existuje.\n\nChcete ho nahradit?",
                parent=self,
                default=messagebox.YES,
            ):
                return False
            if record_id is not None:
                self.conn.execute("DELETE FROM quality_evaluations WHERE id = ?", (record_id,))
            record_id = existing[0]

        now = datetime.now().isoformat(timespec="seconds")
        payload = json.dumps(data, ensure_ascii=False)
        try:
            old_payload = None
            if record_id is not None:
                old_row = self.conn.execute(
                    "SELECT data_json FROM quality_evaluations WHERE id=?",
                    (record_id,),
                ).fetchone()
                old_payload = old_row[0] if old_row else None
            if record_id is None:
                cursor = self.conn.execute(
                    """INSERT INTO quality_evaluations
                       (period, title, prepared_date, data_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (period, title, metadata.get("prepared_date", ""), payload, now, now),
                )
                record_id = cursor.lastrowid
            else:
                self.conn.execute(
                    """UPDATE quality_evaluations
                       SET period = ?, title = ?, prepared_date = ?, data_json = ?, updated_at = ?
                       WHERE id = ?""",
                    (period, title, metadata.get("prepared_date", ""), payload, now, record_id),
                )
            if self._commit() is False:
                return False
            self.current_record_id = record_id
            self._log_history(
                record_id,
                period,
                "vytvořeno" if old_payload is None else ("automaticky uloženo" if silent else "upraveno"),
                self._change_summary(old_payload, payload),
            )
            self._commit()
            self.dirty = False
            self.refresh_overview()
            if not silent:
                self.status.set(f"Uloženo do databáze: {period}")
            self.refresh_attachments()
            self.refresh_history()
            return True
        except sqlite3.Error as exc:
            if not silent:
                messagebox.showerror(APP_NAME, f"Vyhodnocení se nepodařilo uložit:\n{exc}", parent=self)
            return False

    def _change_summary(self, old_payload, new_payload):
        if not old_payload:
            return "První uložení vyhodnocení."
        try:
            old = json.loads(old_payload)
            new = json.loads(new_payload)
        except (TypeError, json.JSONDecodeError):
            return "Obsah vyhodnocení byl změněn."
        changed = []
        for key in ("metadata", "purpose", "summary", "inspection_intro", "conclusion", "next_goal"):
            if old.get(key) != new.get(key):
                changed.append(key)
        for key in TABLE_DEFINITIONS:
            if old.get(key) != new.get(key):
                changed.append(TABLE_DEFINITIONS[key][0])
        return "Změněno: " + ", ".join(changed) if changed else "Uloženo bez změny obsahu."

    def _log_history(self, record_id, period, action, details=""):
        self.conn.execute(
            """INSERT INTO quality_history
               (evaluation_id, period, action, changed_at, changed_by, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                period,
                action,
                datetime.now().isoformat(timespec="seconds"),
                getpass.getuser(),
                details,
            ),
        )

    def export(self, *, print_after=False):
        data = self._data_for_export()
        if not self._validate(data):
            return
        suggested = self._safe_name(data["metadata"]["title"]) + ".html"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportovat a tisknout" if print_after else "Exportovat HTML zprávu",
            defaultextension=".html",
            filetypes=[("Webová stránka", "*.html"), ("Všechny soubory", "*.*")], initialfile=suggested,
        )
        if not path:
            return
        try:
            export_html(data, path, auto_print=print_after)
            self.status.set(f"Exportováno: {path}")
            if print_after:
                os.startfile(path)
                self.status.set(f"Otevřen tiskový dialog: {path}")
                return
            if messagebox.askyesno(
                APP_NAME,
                "HTML zpráva byla vytvořena.\n\nChcete ji nyní otevřít?",
                parent=self,
                default=messagebox.YES,
            ):
                os.startfile(path)
        except (OSError, KeyError, ValueError) as exc:
            messagebox.showerror(APP_NAME, f"HTML zprávu se nepodařilo vytvořit:\n{exc}", parent=self)

    def export_and_print(self):
        self.export(print_after=True)

    @staticmethod
    def _find_edge():
        candidates = [
            shutil.which("msedge"),
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return str(candidate)
        return None

    def export_pdf(self):
        data = self._data_for_export()
        if not self._validate(data):
            return
        suggested = self._safe_name(data["metadata"]["title"]) + ".pdf"
        output_path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportovat PDF",
            defaultextension=".pdf",
            filetypes=[("PDF dokument", "*.pdf")],
            initialfile=suggested,
        )
        if not output_path:
            return
        edge = self._find_edge()
        if not edge:
            messagebox.showerror(
                APP_NAME,
                "Pro přímý PDF export nebyl nalezen Microsoft Edge.",
                parent=self,
            )
            return
        try:
            with tempfile.TemporaryDirectory(prefix="porady_quality_pdf_") as temp_dir:
                html_path = Path(temp_dir) / "quality.html"
                export_html(data, str(html_path))
                result = subprocess.run(
                    [
                        edge,
                        "--headless",
                        "--disable-gpu",
                        "--no-pdf-header-footer",
                        f"--print-to-pdf={Path(output_path).resolve()}",
                        html_path.resolve().as_uri(),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                if result.returncode != 0 or not Path(output_path).exists():
                    raise OSError(result.stderr.strip() or "PDF soubor nebyl vytvořen.")
            self.status.set(f"PDF exportováno: {output_path}")
            if messagebox.askyesno(
                APP_NAME,
                "PDF bylo vytvořeno.\n\nChcete ho otevřít?",
                parent=self,
                default=messagebox.YES,
            ):
                os.startfile(output_path)
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror(APP_NAME, f"PDF se nepodařilo vytvořit:\n{exc}", parent=self)

    def _data_for_export(self):
        data = self._collect()
        attachments = []
        if self.current_record_id is not None:
            rows = self.conn.execute(
                """SELECT file_name, mime_type, file_data
                   FROM quality_attachments WHERE evaluation_id=? ORDER BY id""",
                (self.current_record_id,),
            ).fetchall()
            for file_name, mime_type, file_data in rows:
                item = {"name": file_name, "mime_type": mime_type or "application/octet-stream"}
                if (mime_type or "").startswith("image/"):
                    item["data_uri"] = (
                        f"data:{mime_type};base64,"
                        + base64.b64encode(file_data).decode("ascii")
                    )
                attachments.append(item)
        data["attachments"] = attachments
        return data

    @staticmethod
    def _safe_name(value: str) -> str:
        invalid = '<>:"/\\|?*'
        result = "".join("_" if char in invalid else char for char in value).strip().replace(" ", "_")
        return result or "Vyhodnoceni_kvality"

    def _close(self):
        if messagebox.askyesno(
            APP_NAME,
            "Ukončit aplikaci? Neuložené změny budou ztraceny.",
            parent=self,
            default=messagebox.YES,
        ):
            self.destroy()


def main():
    root = tk.Tk()
    root.withdraw()
    app = QualityApp(root)
    app.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
