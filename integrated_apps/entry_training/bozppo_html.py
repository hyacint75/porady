# -*- coding: utf-8 -*-

import base64
import datetime as dt
import re
import webbrowser
from html import escape
from tkinter import messagebox

from .bozppo_config import BASE_DIR, CERTIFICATES_DIR, LOGO_FILES, OVERVIEW_PRINT_FILE, PASS_LIMIT
from .bozppo_content import QUESTIONS


class HtmlExportMixin:
    def print_overview(self):
            rows = self._read_result_rows()
            if not rows:
                messagebox.showwarning("Přehled je prázdný", "Zatím nejsou uložené žádné záznamy o proškolení.")
                return

            passed_count = sum(1 for row in rows if row["vysledek"] == "SPLNĚNO")
            failed_count = sum(1 for row in rows if row["vysledek"] == "NESPLNĚNO")
            generated_at = dt.datetime.now()
            table_rows = "\n".join(
                "<tr>"
                f"<td>{escape(row['datum'])}</td>"
                f"<td>{escape(row['pracovnik'])}</td>"
                f"<td>{escape(row['firma'])}</td>"
                f"<td>{escape(row['skolitel'])}</td>"
                f"<td>{escape(row['spravne'])}/{escape(row['celkem'])}</td>"
                f"<td>{escape(row['procenta'])} %</td>"
                f"<td>{escape(row['vysledek'])}</td>"
                "</tr>"
                for row in reversed(rows)
            )

            html = f"""<!doctype html>
    <html lang="cs">
    <head>
        <meta charset="utf-8">
        <title>Přehled proškolených zaměstnanců</title>
        <style>
            body {{
                color: #1f2933;
                font-family: Arial, sans-serif;
                font-size: 13px;
                margin: 32px;
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
        <h1>Přehled proškolených zaměstnanců</h1>
        <div class="summary">
            Vygenerováno: {generated_at:%d.%m.%Y %H:%M}<br>
            Celkem záznamů: {len(rows)} | Splněno: {passed_count} | Nesplněno: {failed_count}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Datum</th>
                    <th>Zaměstnanec</th>
                    <th>Oddělení</th>
                    <th>Školitel</th>
                    <th>Skóre</th>
                    <th>%</th>
                    <th>Výsledek</th>
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
            OVERVIEW_PRINT_FILE.write_text(html, encoding="utf-8")
            webbrowser.open(OVERVIEW_PRINT_FILE.as_uri())


    def print_selected_certificate(self):
        selection = self.overview_tree.selection()
        if not selection:
            messagebox.showwarning("Není vybrán zaměstnanec", "V přehledu nejprve označte zaměstnance.")
            return

        values = self.overview_tree.item(selection[0], "values")
        if len(values) < 8:
            messagebox.showwarning("Neplatný záznam", "Vybraný řádek nemá všechny údaje pro tisk potvrzení.")
            return

        score_parts = str(values[5]).split("/", 1)
        correct = score_parts[0] if score_parts else ""
        total = score_parts[1] if len(score_parts) > 1 else str(len(QUESTIONS))
        row = {
            "datum": values[0],
            "pracovnik": values[1],
            "firma": values[2],
            "skolitel": values[3],
            "spravne": correct,
            "celkem": total,
            "procenta": values[6],
            "vysledek": values[7],
        }

        CERTIFICATES_DIR.mkdir(exist_ok=True)
        file_stem = self._safe_filename(f"prehled_{row['datum']}_{row['pracovnik']}_{row['firma']}")
        certificate_path = CERTIFICATES_DIR / f"{file_stem}.html"
        html = self._build_certificate_html(row)
        certificate_path.write_text(html, encoding="utf-8")
        webbrowser.open(certificate_path.as_uri())


    def _logo_data_uri(self):
        for logo_file in LOGO_FILES:
            if logo_file.exists():
                logo_data = base64.b64encode(logo_file.read_bytes()).decode("ascii")
                return f"data:image/png;base64,{logo_data}"
        return ""


    def _certificate_logo_html(self, output_dir=None):
        output_dir = output_dir or CERTIFICATES_DIR
        logo_file = next((path for path in LOGO_FILES if path.exists()), None)
        if logo_file:
            output_dir.mkdir(exist_ok=True)
            (output_dir / "svos_logo.png").write_bytes(logo_file.read_bytes())

        logo_data_uri = self._logo_data_uri()
        fallback = f"this.onerror=null;this.src='{logo_data_uri}';" if logo_data_uri else ""
        return f'<div class="logo-box"><img class="logo" src="svos_logo.png" alt="SVOS" onerror="{fallback}"></div>'


    def _build_certificate_html(self, row):
            logo_html = self._certificate_logo_html()
            return f"""<!doctype html>
    <html lang="cs">
    <head>
        <meta charset="utf-8">
        <title>Potvrzení o absolvování vstupního školení</title>
        <style>
            body {{
                color: #1f2933;
                font-family: Arial, sans-serif;
                line-height: 1.5;
                margin: 42px;
            }}
            .top {{
                margin-bottom: 18px;
            }}
            .logo-box {{
                align-items: center;
                border: 1px solid #c9d1d9;
                border-radius: 8px;
                display: flex;
                justify-content: flex-start;
                margin: 0 0 18px;
                min-height: 54px;
                padding: 8px 10px;
                position: relative;
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
                font-size: 26px;
                margin: 0 0 28px;
                padding-bottom: 12px;
            }}
            table {{
                border-collapse: collapse;
                margin: 24px 0;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #c9d1d9;
                padding: 10px 12px;
                text-align: left;
            }}
            th {{
                background: #eef2f5;
                width: 34%;
            }}
            .result {{
                font-size: 18px;
                font-weight: bold;
            }}
            .signatures {{
                break-inside: avoid;
                display: grid;
                gap: 56px;
                grid-template-columns: 1fr 1fr;
                margin-top: 80px;
                page-break-inside: avoid;
            }}
            .signature {{
                border-top: 1px solid #263238;
                padding-top: 8px;
                text-align: center;
            }}
            .print {{
                margin-top: 32px;
            }}
            @page {{
                size: A4;
                margin: 18mm;
            }}
            table, .logo-box, h1, .signatures {{
                break-inside: avoid;
                page-break-inside: avoid;
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
        <div class="top">
            {logo_html}
            <h1>Potvrzení o absolvování vstupního školení</h1>
        </div>
        <p>
            Potvrzujeme, že níže uvedený zaměstnanec absolvoval vstupní školení
            pro nové zaměstnance včetně základních pravidel BOZP, požární ochrany,
            ochrany informací a interních postupů.
        </p>
        <table>
            <tr><th>Zaměstnanec</th><td>{escape(str(row['pracovnik']))}</td></tr>
            <tr><th>Oddělení / pracoviště</th><td>{escape(str(row['firma']))}</td></tr>
            <tr><th>Školitel / nadřízený</th><td>{escape(str(row['skolitel']))}</td></tr>
            <tr><th>Datum a čas školení</th><td>{escape(str(row['datum']))}</td></tr>
            <tr><th>Výsledek testu</th><td class="result">{escape(str(row['vysledek']))}</td></tr>
            <tr><th>Skóre</th><td>{escape(str(row['spravne']))}/{escape(str(row['celkem']))} ({escape(str(row['procenta']))} %)</td></tr>
            <tr><th>Limit pro splnění</th><td>{PASS_LIMIT} %</td></tr>
        </table>
        <p>
            Zaměstnanec byl seznámen se základními pravidly firmy, pracovním režimem,
            bezpečným pohybem po pracovišti, používáním OOPP, požární ochranou,
            hlášením mimořádných událostí, první pomocí a ochranou firemních informací.
        </p>
        <div class="signatures">
            <div class="signature">Podpis zaměstnance</div>
            <div class="signature">Podpis školitele</div>
        </div>
        <p class="print">
            <button onclick="window.print()">Tisk / uložit jako PDF</button>
        </p>
    </body>
    </html>
    """


    @staticmethod
    def _safe_filename(value):
        safe = re.sub(r"[^0-9A-Za-zÁ-ž._-]+", "_", value.strip())
        safe = re.sub(r"_+", "_", safe).strip("._")
        return safe or "potvrzeni"
