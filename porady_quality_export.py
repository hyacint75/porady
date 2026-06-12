from __future__ import annotations

import html
import os
from datetime import datetime


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value)).replace("\n", "<br>")


def _paragraph(value: object, css_class: str = "") -> str:
    class_attr = f' class="{css_class}"' if css_class else ""
    return f"<p{class_attr}>{_escape(value)}</p>"


def _table(headers: list[str], rows: list[dict], keys: list[str]) -> str:
    head = "".join(f"<th>{_escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_escape(row.get(key, ''))}</td>" for key in keys)
        body_rows.append(f"<tr>{cells}</tr>")
    if not body_rows:
        body_rows.append(f'<tr><td colspan="{len(headers)}" class="empty">Bez záznamů</td></tr>')
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )


def _section(title: str, content: str, *, page_break: bool = False) -> str:
    css_class = ' class="page-break"' if page_break else ""
    return f"<section{css_class}><h2>{_escape(title)}</h2>{content}</section>"


def _build_html(data: dict) -> str:
    meta = data["metadata"]
    generated = datetime.now().strftime("%d.%m.%Y %H:%M")
    parts = [
        _section("1. Účel vyhodnocení", _paragraph(data.get("purpose", ""))),
        _section(
            "2. Celkové shrnutí",
            _paragraph(data.get("summary", ""))
            + _table(
                ["Hodnocená oblast", "Vyhodnocení / komentář", "Stav"],
                data.get("overview", []),
                ["area", "comment", "status"],
            ),
        ),
        _section(
            "3. Přehled reklamací",
            "<h3>3.1 Zákaznické reklamace</h3>"
            + _table(
                ["Ukazatel", "Hodnota", "Poznámka"],
                data.get("complaints", []),
                ["indicator", "value", "note"],
            ),
            page_break=True,
        ),
        _section(
            "4. Interní neshody",
            _table(
                ["Ukazatel", "Hodnota", "Poznámka"],
                data.get("nonconformity_stats", []),
                ["indicator", "value", "note"],
            )
            + _table(
                ["Oblast neshody", "Popis zjištění", "Pravděpodobná příčina", "Návrh opatření", "Odpovědnost"],
                data.get("nonconformities", []),
                ["area", "finding", "cause", "measure", "owner"],
            ),
        ),
        _section(
            "5. Výsledky kontrolní činnosti",
            _paragraph(data.get("inspection_intro", ""))
            + _table(
                ["Druh kontroly", "Počet kontrol", "Zjištěné neshody", "Vyhodnocení / poznámka"],
                data.get("inspections", []),
                ["type", "count", "issues", "note"],
            ),
            page_break=True,
        ),
        _section(
            "6. Vyhodnocení dodavatelské kvality",
            _table(
                ["Ukazatel", "Hodnota", "Poznámka"],
                data.get("supplier_stats", []),
                ["indicator", "value", "note"],
            )
            + _table(
                ["Dodavatel", "Popis problému", "Dopad", "Požadované opatření", "Stav"],
                data.get("supplier_issues", []),
                ["supplier", "problem", "impact", "measure", "status"],
            ),
        ),
        _section(
            "7. Nápravná a preventivní opatření",
            _table(
                ["Č.", "Zdroj", "Popis opatření", "Odpovědná osoba", "Termín", "Stav", "Vyhodnocení účinnosti"],
                data.get("corrective_actions", []),
                ["number", "source", "description", "owner", "deadline", "status", "effectiveness"],
            ),
            page_break=True,
        ),
        _section(
            "8. Rizika z pohledu kvality",
            _table(
                ["Riziko", "Dopad", "Pravděpodobnost", "Závažnost", "Navržené opatření"],
                data.get("risks", []),
                ["risk", "impact", "probability", "severity", "measure"],
            ),
        ),
        _section(
            f"9. Návrh opatření pro {meta.get('next_period', '')}",
            _table(
                ["Č.", "Navržené opatření", "Odpovědná osoba", "Termín", "Poznámka"],
                data.get("next_actions", []),
                ["number", "description", "owner", "deadline", "note"],
            ),
            page_break=True,
        ),
        _section(
            "10. Závěr",
            _paragraph(data.get("conclusion", ""))
            + _paragraph(data.get("next_goal", ""), "goal")
            + _table(
                ["Podpis zpracovatele", "Datum", "Podpis schvalující osoby", "Datum"],
                [{
                    "prepared": meta.get("signature_name", ""),
                    "prepared_date": meta.get("prepared_date", ""),
                    "approved": "",
                    "approved_date": "",
                }],
                ["prepared", "prepared_date", "approved", "approved_date"],
            ),
        ),
    ]
    return f"""<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(meta.get("title", "Vyhodnocení kvality"))}</title>
  <style>
    :root {{ color-scheme: light; --blue: #1f4e78; --line: #aab7c4; --soft: #eaf2f8; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #eef2f6; color: #17202a; font: 15px/1.45 "Segoe UI", Arial, sans-serif; }}
    main {{ width: min(1180px, calc(100% - 32px)); margin: 24px auto; padding: 42px; background: white; box-shadow: 0 4px 20px #0002; }}
    header {{ text-align: center; margin-bottom: 34px; }}
    h1 {{ margin: 0; color: var(--blue); font-size: 30px; text-transform: uppercase; }}
    header .company {{ margin: 8px 0 24px; font-size: 19px; font-weight: 700; }}
    h2 {{ color: var(--blue); margin: 30px 0 12px; font-size: 22px; }}
    h3 {{ color: var(--blue); margin: 20px 0 10px; font-size: 17px; }}
    p {{ margin: 0 0 14px; }}
    .goal {{ font-weight: 700; }}
    .meta {{ max-width: 760px; margin: 0 auto; }}
    .table-wrap {{ overflow-x: auto; margin: 12px 0 22px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid var(--line); padding: 8px 9px; text-align: left; vertical-align: top; }}
    th {{ background: var(--blue); color: white; }}
    tbody tr:nth-child(even) td {{ background: var(--soft); }}
    .empty {{ text-align: center; color: #667085; font-style: italic; }}
    footer {{ margin-top: 30px; color: #667085; font-size: 12px; text-align: right; }}
    @media print {{
      @page {{ size: A4 landscape; margin: 12mm; }}
      body {{ background: white; font-size: 10pt; }}
      main {{ width: auto; margin: 0; padding: 0; box-shadow: none; }}
      .page-break {{ break-before: page; }}
      .table-wrap {{ overflow: visible; }}
      table {{ font-size: 8pt; break-inside: auto; }}
      tr {{ break-inside: avoid; }}
      thead {{ display: table-header-group; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{_escape(meta.get("title", ""))}</h1>
    <div class="company">{_escape(meta.get("company", ""))}</div>
    <div class="meta">{_table(
        ["Položka", "Údaj"],
        [
            {"item": "Zpracoval", "value": meta.get("prepared_by", "")},
            {"item": "Období", "value": meta.get("period", "")},
            {"item": "Datum zpracování", "value": meta.get("prepared_date", "")},
            {"item": "Schválil", "value": meta.get("approved_by", "")},
        ],
        ["item", "value"],
    )}</div>
  </header>
  {''.join(parts)}
  <footer>HTML export vytvořen {generated}</footer>
</main>
</body>
</html>
"""


def export_html(data: dict, output_path: str) -> str:
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(_build_html(data))
    return output_path
