# -*- coding: utf-8 -*-

import datetime as dt
import webbrowser
from html import escape
from tkinter import messagebox

from .bozppo_config import RISKS_DIR
from .bozppo_pictograms import pictogram_data_uri
from .bozppo_templates import HANDOVER_TEMPLATES


class RiskBuilderMixin:
    def build_standalone_risks(self):
        selected = self._selected_risk_templates()
        if not selected:
            messagebox.showwarning("Nejsou vybraná rizika", "Vyberte alespoň jeden typ práce.")
            return

        lines = [
            self.risk_document_title.get().strip() or "Samostatná rizika pracoviště",
            "",
            f"Pracoviště / zakázka: {self.risk_workplace.get().strip()}",
            f"Externí firma: {self.risk_company.get().strip()}",
            f"Datum předání / převzetí: {self.risk_handover_date.get().strip()}",
            f"Předal: {self.risk_handed_by.get().strip()}",
            f"Převzal: {self.risk_taken_by.get().strip()}",
            f"Zpracováno: {dt.datetime.now():%d.%m.%Y %H:%M}",
            "",
        ]
        for name in selected:
            template = HANDOVER_TEMPLATES[name]
            lines.extend(
                [
                    name,
                    f"Piktogramy: {', '.join(template.get('pictograms', []))}",
                    f"Rozsah: {template.get('scope', '')}",
                    f"Rizika: {template.get('risks', '')}",
                    f"Opatření a OOPP: {template.get('measures', '')}",
                    f"Požární ochrana: {template.get('fire', '')}",
                    f"Dokumentace: {template.get('docs', '')}",
                    "",
                ]
            )

        self.risk_output_text.delete("1.0", "end")
        self.risk_output_text.insert("1.0", "\n".join(lines).strip())


    def print_standalone_risks(self):
        content = self.risk_output_text.get("1.0", "end").strip()
        if not content:
            self.build_standalone_risks()
            content = self.risk_output_text.get("1.0", "end").strip()
        if not content:
            return

        RISKS_DIR.mkdir(exist_ok=True)
        title = self.risk_document_title.get().strip() or "Samostatná rizika pracoviště"
        file_stem = self._safe_filename(
            f"{dt.datetime.now():%Y-%m-%d_%H-%M}_{title}_{self.risk_workplace.get().strip()}"
        )
        output_path = RISKS_DIR / f"{file_stem}.html"
        output_path.write_text(self._build_standalone_risks_html(content), encoding="utf-8")
        self.last_risks_path = output_path
        webbrowser.open(output_path.as_uri())


    def clear_standalone_risks(self):
        for variable in self.risk_template_vars.values():
            variable.set(False)
        self.risk_output_text.delete("1.0", "end")
        self.last_risks_path = None


    def _selected_risk_templates(self):
        return [name for name, variable in self.risk_template_vars.items() if variable.get()]


    def _build_standalone_risks_html(self, content):
        logo_html = self._certificate_logo_html(RISKS_DIR)
        title = self.risk_document_title.get().strip() or "Samostatná rizika pracoviště"
        workplace = self.risk_workplace.get().strip()
        company = self.risk_company.get().strip()
        handover_date = self.risk_handover_date.get().strip()
        handed_by = self.risk_handed_by.get().strip()
        taken_by = self.risk_taken_by.get().strip()
        sections = self._risk_sections_from_text(content)
        section_html = "\n".join(
            (
                f'<div class="section"><h2>{escape(section_title)}</h2>'
                f'<div class="box">{self._format_risk_section_html(section_text)}</div></div>'
            )
            for section_title, section_text in sections
        )
        return f"""<!doctype html>
<html lang="cs">
<head>
    <meta charset="utf-8">
    <title>{escape(title)}</title>
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
            margin: 0 0 18px;
            padding-bottom: 10px;
        }}
        .meta {{
            margin: 0 0 18px;
        }}
        .section {{
            break-inside: avoid;
            margin-top: 14px;
            page-break-inside: avoid;
        }}
        .section h2 {{
            font-size: 15px;
            margin: 0;
        }}
        .box {{
            border: 1px solid #c9d1d9;
            margin-top: 6px;
            padding: 9px 10px;
        }}
        .pictograms {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 0 0 10px;
        }}
        .pictogram {{
            border: 2px solid #263238;
            border-radius: 4px;
            display: inline-flex;
            flex-direction: column;
            gap: 4px;
            padding: 5px;
            text-align: center;
            width: 86px;
        }}
        .pictogram img {{
            display: block;
            height: 86px;
            width: 76px;
        }}
        .pictogram span {{
            font-size: 9px;
            font-weight: bold;
        }}
        .print {{
            margin-top: 24px;
        }}
        .signatures {{
            break-inside: avoid;
            display: grid;
            gap: 56px;
            grid-template-columns: 1fr 1fr;
            margin-top: 64px;
            page-break-inside: avoid;
        }}
        .signature {{
            border-top: 1px solid #263238;
            padding-top: 8px;
            text-align: center;
        }}
        @page {{
            size: A4;
            margin: 14mm;
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
    <h1>{escape(title)}</h1>
    <div class="meta">
        Pracoviště / zakázka: {escape(workplace)}<br>
        Externí firma: {escape(company)}<br>
        Datum předání / převzetí: {escape(handover_date)}<br>
        Předal: {escape(handed_by)}<br>
        Převzal: {escape(taken_by)}<br>
        Zpracováno: {dt.datetime.now():%d.%m.%Y %H:%M}
    </div>
    {section_html}
    <div class="signatures">
        <div class="signature">Předal: {escape(handed_by)}</div>
        <div class="signature">Převzal: {escape(taken_by)}</div>
    </div>
    <p class="print">
        <button onclick="window.print()">Tisk / uložit jako PDF</button>
    </p>
</body>
</html>
"""


    @staticmethod
    def _format_risk_section_html(section_text):
        html_lines = []
        for line in section_text.splitlines():
            if line.startswith("Piktogramy:"):
                values = [value.strip() for value in line.split(":", 1)[1].split(",") if value.strip()]
                if values:
                    badges = "".join(
                        (
                            f'<span class="pictogram">'
                            f'<img src="{pictogram_data_uri(value)}" alt="{escape(value)}">'
                            f'<span>{escape(value)}</span></span>'
                        )
                        for value in values
                    )
                    html_lines.append(f'<div class="pictograms">{badges}</div>')
                continue
            html_lines.append(escape(line))
        return "<br>".join(html_lines)


    @staticmethod
    def _risk_sections_from_text(content):
        lines = [line.rstrip() for line in content.splitlines()]
        sections = []
        current_title = None
        current_lines = []
        for line in lines:
            if not line:
                continue
            if ":" not in line:
                if current_title is not None:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                current_title = line
                current_lines = []
            else:
                current_lines.append(line)
        if current_title is not None:
            sections.append((current_title, "\n".join(current_lines).strip()))
        return sections or [("Rizika", content)]
