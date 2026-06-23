# -*- coding: utf-8 -*-

import csv
import datetime as dt
import webbrowser
from html import escape
from tkinter import messagebox

from .bozppo_config import BASE_DIR, HANDOVER_DIR, HANDOVER_EXCEL_FILE, HANDOVER_FILE
from .bozppo_excel import write_xlsx
from .bozppo_storage import backup_file, parse_czech_date
from .bozppo_templates import HANDOVER_TEMPLATES


class HandoverMixin:
    def save_handover(self):
        required = [
            ("pracoviště / zakázka", self.handover_workplace.get().strip()),
            ("externí firma", self.handover_company.get().strip()),
            ("předal", self.handover_handed_by.get().strip()),
            ("převzal", self.handover_taken_by.get().strip()),
            ("rozsah předávaných prací", self._text_value(self.handover_scope_text)),
        ]
        missing = [label for label, value in required if not value]
        if missing:
            messagebox.showwarning("Chybí údaje", "Doplňte prosím: " + ", ".join(missing) + ".")
            return

        work_from = parse_czech_date(self.handover_work_from.get())
        work_to = parse_czech_date(self.handover_work_to.get())
        if self.handover_work_from.get().strip() and not work_from:
            messagebox.showwarning("Neplatné datum", "Datum Práce od zadejte ve formátu DD.MM.RRRR.")
            return
        if self.handover_work_to.get().strip() and not work_to:
            messagebox.showwarning("Neplatné datum", "Datum Práce do zadejte ve formátu DD.MM.RRRR.")
            return
        if work_from and work_to and work_to < work_from:
            messagebox.showwarning("Neplatný termín", "Datum Práce do nesmí být dříve než Práce od.")
            return

        row = self._handover_row()
        self._save_handover_csv(row)

        HANDOVER_DIR.mkdir(exist_ok=True)
        file_stem = self._safe_filename(
            f"{dt.datetime.now():%Y-%m-%d_%H-%M}_{row['pracoviste']}_{row['externi_firma']}"
        )
        handover_path = HANDOVER_DIR / f"{file_stem}.html"
        handover_path.write_text(self._build_handover_html(row), encoding="utf-8")
        self.last_handover_path = handover_path
        self.open_handover_button.configure(state="normal")
        self.load_handover_overview()
        webbrowser.open(handover_path.as_uri())
        messagebox.showinfo("Předání pracoviště", "Protokol byl uložen a otevřen pro tisk.")


    def _handover_row(self):
        return {
            "datum_vytvoreni": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pracoviste": self.handover_workplace.get().strip(),
            "misto": self.handover_location.get().strip(),
            "objednatel": self.handover_customer.get().strip(),
            "externi_firma": self.handover_company.get().strip(),
            "prace_od": self.handover_work_from.get().strip(),
            "prace_do": self.handover_work_to.get().strip(),
            "predal": self.handover_handed_by.get().strip(),
            "prevzal": self.handover_taken_by.get().strip(),
            "rozsah": self._text_value(self.handover_scope_text),
            "rizika": self._text_value(self.handover_risks_text),
            "opatreni": self._text_value(self.handover_measures_text),
            "pozarni_ochrana": self._text_value(self.handover_fire_text),
            "dokumentace": self._text_value(self.handover_docs_text),
            "poznamky": self._text_value(self.handover_notes_text),
        }


    def _save_handover_csv(self, row):
        HANDOVER_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_exists = HANDOVER_FILE.exists()
        backup_file(HANDOVER_FILE)
        with HANDOVER_FILE.open("a", newline="", encoding="utf-8-sig") as csv_file:
            fieldnames = list(row.keys())
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=";")
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        self.notify_data_changed()


    def load_handover_overview(self):
        if not hasattr(self, "handover_tree"):
            return

        for item in self.handover_tree.get_children():
            self.handover_tree.delete(item)

        rows = self._read_handover_rows()
        for row in reversed(rows):
            self.handover_tree.insert(
                "",
                "end",
                values=(
                    row["datum_vytvoreni"],
                    row["pracoviste"],
                    row["externi_firma"],
                    f"{row['prace_od']} - {row['prace_do']}",
                    row["predal"],
                    row["prevzal"],
                ),
            )

        if rows:
            self.handover_overview_summary.set(f"Celkem vydaných předání pracoviště: {len(rows)}")
        else:
            self.handover_overview_summary.set("Zatím nejsou uložená žádná předání pracoviště.")


    def _read_handover_rows(self):
        if not HANDOVER_FILE.exists():
            return []
        with HANDOVER_FILE.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";")
            return [row for row in reader]


    def open_handover_csv(self):
        if not HANDOVER_FILE.exists():
            messagebox.showwarning("Soubor nenalezen", "Zatím nebylo vytvořeno žádné předání pracoviště.")
            return
        webbrowser.open(HANDOVER_FILE.as_uri())


    def export_handover_excel(self):
        rows = self._read_handover_rows()
        if not rows:
            messagebox.showwarning("Přehled je prázdný", "Není co exportovat do Excelu.")
            return

        headers = [
            "Datum vytvoření",
            "Pracoviště",
            "Místo",
            "Objednatel",
            "Externí firma",
            "Práce od",
            "Práce do",
            "Předal",
            "Převzal",
            "Rozsah",
            "Rizika",
            "Opatření",
            "Požární ochrana",
            "Dokumentace",
            "Poznámky",
        ]
        keys = [
            "datum_vytvoreni",
            "pracoviste",
            "misto",
            "objednatel",
            "externi_firma",
            "prace_od",
            "prace_do",
            "predal",
            "prevzal",
            "rozsah",
            "rizika",
            "opatreni",
            "pozarni_ochrana",
            "dokumentace",
            "poznamky",
        ]
        data = [[row.get(key, "") for key in keys] for row in reversed(rows)]
        write_xlsx(HANDOVER_EXCEL_FILE, "Predani", headers, data)
        webbrowser.open(HANDOVER_EXCEL_FILE.as_uri())


    def print_handover_overview(self):
            rows = self._read_handover_rows()
            if not rows:
                messagebox.showwarning("Přehled je prázdný", "Zatím nejsou uložená žádná předání pracoviště.")
                return

            generated_at = dt.datetime.now()
            logo_html = self._certificate_logo_html(BASE_DIR)
            table_rows = "\n".join(
                "<tr>"
                f"<td>{escape(row.get('datum_vytvoreni', ''))}</td>"
                f"<td>{escape(row.get('pracoviste', ''))}</td>"
                f"<td>{escape(row.get('misto', ''))}</td>"
                f"<td>{escape(row.get('externi_firma', ''))}</td>"
                f"<td>{escape(row.get('prace_od', ''))} - {escape(row.get('prace_do', ''))}</td>"
                f"<td>{escape(row.get('predal', ''))}</td>"
                f"<td>{escape(row.get('prevzal', ''))}</td>"
                "</tr>"
                for row in reversed(rows)
            )
            output_file = BASE_DIR / "prehled_predani_pracovist.html"
            html = f"""<!doctype html>
    <html lang="cs">
    <head>
        <meta charset="utf-8">
        <title>Přehled vydaných předání pracovišť</title>
        <style>
            body {{
                color: #1f2933;
                font-family: Arial, sans-serif;
                font-size: 13px;
                margin: 32px;
            }}
            .logo-box {{
                align-items: center;
                border: 1px solid #c9d1d9;
                border-radius: 8px;
                display: flex;
                justify-content: flex-start;
                margin: 0 0 16px;
                min-height: 54px;
                padding: 8px 10px;
                width: 220px;
            }}
            .logo {{
                border-radius: 6px;
                display: block;
                height: auto;
                max-width: 200px;
                width: 200px;
            }}
            h1 {{
                border-bottom: 2px solid #263238;
                font-size: 24px;
                margin-bottom: 10px;
                padding-bottom: 10px;
            }}
            .summary {{
                margin: 12px 0 22px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #c9d1d9;
                padding: 7px 8px;
                text-align: left;
                vertical-align: top;
            }}
            th {{
                background: #eef2f5;
            }}
            .print {{
                margin-top: 24px;
            }}
            @page {{
                size: A4;
                margin: 14mm;
            }}
            thead {{
                display: table-header-group;
            }}
            tr {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}
            .logo-box, h1, .summary {{
                break-after: avoid;
                page-break-after: avoid;
            }}
            @media print {{
                body {{
                    margin: 0;
                }}
                .print {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        {logo_html}
        <h1>Přehled vydaných předání pracovišť</h1>
        <div class="summary">
            Vygenerováno: {generated_at:%d.%m.%Y %H:%M}<br>
            Celkem záznamů: {len(rows)}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Datum</th>
                    <th>Pracoviště / zakázka</th>
                    <th>Místo</th>
                    <th>Externí firma</th>
                    <th>Termín</th>
                    <th>Předal</th>
                    <th>Převzal</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        <p class="print">
            <button onclick="window.print()">Tisk / uložit jako PDF</button>
        </p>
    </body>
    </html>
    """
            output_file.write_text(html, encoding="utf-8")
            webbrowser.open(output_file.as_uri())


    def print_selected_handover(self):
        selection = self.handover_tree.selection()
        if not selection:
            messagebox.showwarning("Není vybráno předání", "V přehledu nejprve označte konkrétní předání pracoviště.")
            return

        values = self.handover_tree.item(selection[0], "values")
        if len(values) < 6:
            messagebox.showwarning("Neplatný záznam", "Vybraný řádek nemá všechny údaje pro tisk předání.")
            return

        row = self._find_handover_row(values)
        if not row:
            messagebox.showwarning("Záznam nenalezen", "Vybrané předání se nepodařilo dohledat v CSV souboru.")
            return

        HANDOVER_DIR.mkdir(exist_ok=True)
        file_stem = self._safe_filename(
            f"prehled_{row.get('datum_vytvoreni', '')}_{row.get('pracoviste', '')}_{row.get('externi_firma', '')}"
        )
        handover_path = HANDOVER_DIR / f"{file_stem}.html"
        handover_path.write_text(self._build_handover_html(row), encoding="utf-8")
        webbrowser.open(handover_path.as_uri())


    def _find_handover_row(self, values):
        datum, pracoviste, firma, termin, predal, prevzal = values[:6]
        for row in reversed(self._read_handover_rows()):
            row_termin = f"{row.get('prace_od', '')} - {row.get('prace_do', '')}"
            if (
                row.get("datum_vytvoreni", "") == datum
                and row.get("pracoviste", "") == pracoviste
                and row.get("externi_firma", "") == firma
                and row_termin == termin
                and row.get("predal", "") == predal
                and row.get("prevzal", "") == prevzal
            ):
                return row
        return None


    def _build_handover_html(self, row):
            logo_html = self._certificate_logo_html(HANDOVER_DIR)
            def cell(value):
                return escape(str(value)).replace("\n", "<br>")

            return f"""<!doctype html>
    <html lang="cs">
    <head>
        <meta charset="utf-8">
        <title>Protokol o předání pracoviště</title>
        <style>
            body {{
                color: #1f2933;
                font-family: Arial, sans-serif;
                font-size: 13px;
                line-height: 1.5;
                margin: 34px;
            }}
            .logo-box {{
                align-items: center;
                border: 1px solid #c9d1d9;
                border-radius: 8px;
                display: flex;
                justify-content: flex-start;
                margin: 0 0 16px;
                min-height: 54px;
                padding: 8px 10px;
                width: 220px;
            }}
            .logo {{
                border-radius: 6px;
                display: block;
                height: auto;
                max-width: 200px;
                width: 200px;
            }}
            h1 {{
                border-bottom: 2px solid #263238;
                font-size: 24px;
                margin: 0 0 20px;
                padding-bottom: 10px;
            }}
            table {{
                border-collapse: collapse;
                margin: 14px 0 20px;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #c9d1d9;
                padding: 8px 10px;
                text-align: left;
                vertical-align: top;
            }}
            th {{
                background: #eef2f5;
                width: 28%;
            }}
            .section {{
                break-inside: avoid;
                margin-top: 16px;
                page-break-inside: avoid;
            }}
            .section h2 {{
                font-size: 15px;
                margin: 0;
            }}
            .box {{
                border: 1px solid #c9d1d9;
                margin-top: 6px;
                min-height: 48px;
                padding: 9px 10px;
            }}
            .signatures {{
                break-inside: avoid;
                display: grid;
                gap: 56px;
                grid-template-columns: 1fr 1fr;
                margin-top: 72px;
                page-break-inside: avoid;
            }}
            .signature {{
                border-top: 1px solid #263238;
                padding-top: 8px;
                text-align: center;
            }}
            .print {{
                margin-top: 24px;
            }}
            @page {{
                size: A4;
                margin: 14mm;
            }}
            table, .logo-box, h1 {{
                break-after: avoid;
                page-break-after: avoid;
            }}
            tr {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}
            @media print {{
                body {{
                    margin: 0;
                }}
                .print {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        {logo_html}
        <h1>Protokol o předání pracoviště</h1>
        <table>
            <tr><th>Pracoviště / zakázka</th><td>{cell(row['pracoviste'])}</td></tr>
            <tr><th>Místo výkonu práce</th><td>{cell(row['misto'])}</td></tr>
            <tr><th>Objednatel / provoz</th><td>{cell(row['objednatel'])}</td></tr>
            <tr><th>Externí firma</th><td>{cell(row['externi_firma'])}</td></tr>
            <tr><th>Termín prací</th><td>{cell(row['prace_od'])} - {cell(row['prace_do'])}</td></tr>
            <tr><th>Předal</th><td>{cell(row['predal'])}</td></tr>
            <tr><th>Převzal</th><td>{cell(row['prevzal'])}</td></tr>
            <tr><th>Datum vytvoření</th><td>{cell(row['datum_vytvoreni'])}</td></tr>
        </table>
        <div class="section"><h2>Rozsah předávaných prací</h2><div class="box">{cell(row['rozsah'])}</div></div>
        <div class="section"><h2>Rizika pracoviště</h2><div class="box">{cell(row['rizika'])}</div></div>
        <div class="section"><h2>Bezpečnostní opatření a OOPP</h2><div class="box">{cell(row['opatreni'])}</div></div>
        <div class="section"><h2>Požární ochrana / horké práce</h2><div class="box">{cell(row['pozarni_ochrana'])}</div></div>
        <div class="section"><h2>Předaná dokumentace a povolení</h2><div class="box">{cell(row['dokumentace'])}</div></div>
        <div class="section"><h2>Poznámky</h2><div class="box">{cell(row['poznamky'])}</div></div>
        <div class="signatures">
            <div class="signature">Podpis předávající osoby</div>
            <div class="signature">Podpis přebírající osoby</div>
        </div>
        <p class="print">
            <button onclick="window.print()">Tisk / uložit jako PDF</button>
        </p>
    </body>
    </html>
    """


    def open_handover(self):
        if not self.last_handover_path or not self.last_handover_path.exists():
            messagebox.showwarning("Protokol nenalezen", "Nejprve uložte protokol o předání pracoviště.")
            return
        webbrowser.open(self.last_handover_path.as_uri())


    def reset_handover(self):
        self.handover_workplace.set("")
        self.handover_location.set(self.app_settings.get("handover_location", ""))
        self.handover_customer.set(self.app_settings.get("handover_customer", "SVOS"))
        self.handover_company.set("")
        self.handover_work_from.set(dt.date.today().strftime("%d.%m.%Y"))
        self.handover_work_to.set("")
        self.handover_handed_by.set("")
        self.handover_taken_by.set("")
        self.handover_template.set("Obecné práce")
        for text in (
            self.handover_scope_text,
            self.handover_risks_text,
            self.handover_measures_text,
            self.handover_fire_text,
            self.handover_docs_text,
            self.handover_notes_text,
        ):
            text.delete("1.0", "end")
        self.handover_risks_text.insert(
            "1.0",
            "Pohyb osob a vozidel, manipulace s materiálem, práce ve výškách, elektrická zařízení, hluk, prach.",
        )
        self.handover_measures_text.insert(
            "1.0",
            "Dodržovat pokyny odpovědné osoby, používat předepsané OOPP, udržovat pořádek, nezastavovat únikové cesty.",
        )
        self.handover_fire_text.insert(
            "1.0",
            "Dodržovat zákaz kouření a manipulace s otevřeným ohněm mimo povolená místa. Horké práce pouze na povolení.",
        )
        self.apply_handover_template()
        self.last_handover_path = None
        self.open_handover_button.configure(state="disabled")


    def apply_handover_template(self):
        template = HANDOVER_TEMPLATES.get(self.handover_template.get())
        if not template:
            return

        fields = (
            (self.handover_scope_text, "scope"),
            (self.handover_risks_text, "risks"),
            (self.handover_measures_text, "measures"),
            (self.handover_fire_text, "fire"),
            (self.handover_docs_text, "docs"),
        )
        for text_widget, key in fields:
            text_widget.delete("1.0", "end")
            text_widget.insert("1.0", template.get(key, ""))


    @staticmethod
    def _text_value(text_widget):
        return text_widget.get("1.0", "end").strip()
