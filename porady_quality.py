from __future__ import annotations

import calendar
import copy
import json
import os
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk

from porady_quality_export import export_html


APP_NAME = "Měsíční vyhodnocení kvality"
VERSION = "1.0"
MONTHS = [
    "leden", "únor", "březen", "duben", "květen", "červen",
    "červenec", "srpen", "září", "říjen", "listopad", "prosinec",
]


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
        self.widgets[columns[0][0]].focus_set()

    def _save(self):
        self.result = {key: widget.get("1.0", "end-1c").strip() for key, widget in self.widgets.items()}
        self.destroy()


class TableEditor(ttk.Frame):
    def __init__(self, parent, columns: list[tuple[str, str]]):
        super().__init__(parent, padding=12)
        self.columns = columns
        keys = [key for key, _label in columns]
        self.tree = ttk.Treeview(self, columns=keys, show="headings", selectmode="browse")
        for key, label in columns:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=max(120, min(280, len(label) * 14)), minwidth=80)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        buttons = ttk.Frame(self)
        buttons.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Přidat", command=self.add).pack(side="left")
        ttk.Button(buttons, text="Upravit", command=self.edit).pack(side="left", padx=6)
        ttk.Button(buttons, text="Odstranit", command=self.delete).pack(side="left")
        ttk.Button(buttons, text="Nahoru", command=lambda: self.move(-1)).pack(side="left", padx=(18, 6))
        ttk.Button(buttons, text="Dolů", command=lambda: self.move(1)).pack(side="left")
        self.tree.bind("<Double-1>", lambda _event: self.edit())
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def set_rows(self, rows: list[dict]):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=[row.get(key, "") for key, _label in self.columns])

    def get_rows(self) -> list[dict]:
        keys = [key for key, _label in self.columns]
        return [dict(zip(keys, self.tree.item(item, "values"))) for item in self.tree.get_children()]

    def add(self):
        dialog = RowDialog(self, "Přidat záznam", self.columns)
        self.wait_window(dialog)
        if dialog.result is not None:
            self.tree.insert("", "end", values=[dialog.result[key] for key, _label in self.columns])

    def edit(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(APP_NAME, "Nejprve vyberte řádek, který chcete upravit.", parent=self)
            return
        item = selected[0]
        values = dict(zip([key for key, _label in self.columns], self.tree.item(item, "values")))
        dialog = RowDialog(self, "Upravit záznam", self.columns, values)
        self.wait_window(dialog)
        if dialog.result is not None:
            self.tree.item(item, values=[dialog.result[key] for key, _label in self.columns])

    def delete(self):
        selected = self.tree.selection()
        if selected and messagebox.askyesno(APP_NAME, "Odstranit vybraný řádek?", parent=self):
            self.tree.delete(selected[0])

    def move(self, direction: int):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        index = self.tree.index(item)
        target = index + direction
        if 0 <= target < len(self.tree.get_children()):
            self.tree.move(item, "", target)
            self.tree.selection_set(item)


class QualityApp(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1280x780")
        self.minsize(980, 640)
        self.transient(parent)
        self.data = default_data()
        self.current_file = None
        self.scalar_widgets = {}
        self.table_editors = {}
        self._configure_style()
        self._build_ui()
        self._load_into_ui(self.data)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _configure_style(self):
        style = ttk.Style(self)
        style.configure("Quality.TNotebook.Tab", padding=(15, 8), font=("Segoe UI", 10))
        style.configure("QualityAccent.TButton", font=("Segoe UI Semibold", 10))
        style.configure("QualityTitle.TLabel", font=("Segoe UI Semibold", 18), foreground="#1F4E78")
        style.configure("QualityHint.TLabel", foreground="#606060")

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(12, 10))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=APP_NAME, style="QualityTitle.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Nový měsíc", command=self.new_month).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Exportovat HTML", style="QualityAccent.TButton", command=self.export).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Uložit", command=self.save).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Načíst", command=self.load).pack(side="right", padx=(6, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._build_metadata_tab()
        self._build_text_tab()
        for key in TABLE_DEFINITIONS:
            self._build_table_tab(key)
        self._build_conclusion_tab()

        self.status = tk.StringVar(value="Připraveno")
        ttk.Label(self, textvariable=self.status, style="QualityHint.TLabel", padding=(12, 4)).pack(fill="x")

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

    def _build_table_tab(self, key: str):
        title, columns = TABLE_DEFINITIONS[key]
        editor = TableEditor(self.notebook, columns)
        self.notebook.add(editor, text=title)
        self.table_editors[key] = editor

    def _build_conclusion_tab(self):
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text="Závěr")
        frame.columnconfigure(0, weight=1)
        self._text_editor(frame, "conclusion", "Závěrečné vyhodnocení", 0, height=12)
        self._text_editor(frame, "next_goal", "Hlavní cíl pro další měsíc", 2, height=6)

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
        for path, widget in self.scalar_widgets.items():
            if "." in path:
                group, key = path.split(".", 1)
                value = data.get(group, {}).get(key, "")
            else:
                value = data.get(path, "")
            self._set_widget(widget, value)
        for key, editor in self.table_editors.items():
            editor.set_rows(data.get(key, []))

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

    def new_month(self):
        raw = simpledialog.askstring(APP_NAME, "Zadejte měsíc a rok ve formátu MM/RRRR:", parent=self)
        if not raw:
            return
        try:
            month, year = [int(part) for part in raw.replace(".", "/").split("/")]
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_NAME, "Zadejte platný měsíc ve formátu MM/RRRR, například 06/2026.", parent=self)
            return

        data = self._collect()
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
        self._load_into_ui(data)
        self.current_file = None
        self.status.set(f"Založeno nové období: {period}")

    def save(self):
        path = self.current_file
        if not path:
            suggested = self._safe_name(self._collect()["metadata"]["title"]) + ".json"
            path = filedialog.asksaveasfilename(
                parent=self, title="Uložit rozpracované vyhodnocení", defaultextension=".json",
                filetypes=[("Data vyhodnocení", "*.json")], initialfile=suggested,
            )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self._collect(), handle, ensure_ascii=False, indent=2)
            self.current_file = path
            self.status.set(f"Uloženo: {path}")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Soubor se nepodařilo uložit:\n{exc}", parent=self)

    def load(self):
        path = filedialog.askopenfilename(
            parent=self, title="Načíst vyhodnocení", filetypes=[("Data vyhodnocení", "*.json"), ("Všechny soubory", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict) or "metadata" not in loaded:
                raise ValueError("Soubor nemá očekávanou strukturu.")
            self.data = loaded
            self._load_into_ui(loaded)
            self.current_file = path
            self.status.set(f"Načteno: {path}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, f"Soubor se nepodařilo načíst:\n{exc}", parent=self)

    def export(self):
        data = self._collect()
        suggested = self._safe_name(data["metadata"]["title"]) + ".html"
        path = filedialog.asksaveasfilename(
            parent=self, title="Exportovat HTML zprávu", defaultextension=".html",
            filetypes=[("Webová stránka", "*.html"), ("Všechny soubory", "*.*")], initialfile=suggested,
        )
        if not path:
            return
        try:
            export_html(data, path)
            self.status.set(f"Exportováno: {path}")
            if messagebox.askyesno(APP_NAME, "HTML zpráva byla vytvořena.\n\nChcete ji nyní otevřít?", parent=self):
                os.startfile(path)
        except (OSError, KeyError, ValueError) as exc:
            messagebox.showerror(APP_NAME, f"HTML zprávu se nepodařilo vytvořit:\n{exc}", parent=self)

    @staticmethod
    def _safe_name(value: str) -> str:
        invalid = '<>:"/\\|?*'
        result = "".join("_" if char in invalid else char for char in value).strip().replace(" ", "_")
        return result or "Vyhodnoceni_kvality"

    def _close(self):
        if messagebox.askyesno(APP_NAME, "Ukončit aplikaci? Neuložené změny budou ztraceny.", parent=self):
            self.destroy()


def main():
    root = tk.Tk()
    root.withdraw()
    app = QualityApp(root)
    app.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
