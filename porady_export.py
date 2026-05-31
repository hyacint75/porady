# -*- coding: utf-8 -*-

import html
import os
import tkinter as tk
from tkinter import filedialog, messagebox


class ExportMixin:

    def export_meeting(self):
        if not self.current_id:
            return

        c = self.conn.cursor()
        c.execute("SELECT title, date, notes FROM meetings WHERE id=?", (self.current_id,))
        meeting = c.fetchone()
        if not meeting:
            messagebox.showwarning("Export", "Vybraná porada už neexistuje. Seznam bude obnoven.")
            self.current_id = None
            self.clear_right_panel()
            self.load_meetings()
            return
        safe_title = "".join(char for char in meeting[0] if char.isalnum() or char in (" ", "-", "_")).strip()

        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            initialfile=f"Zapis_{meeting[1]}_{safe_title}.html",
            filetypes=[("Tiskový HTML zápis", "*.html"), ("Textové soubory", "*.txt")],
        )

        if filepath:
            if filepath.lower().endswith(".txt"):
                self.write_txt_export(filepath, meeting)
            else:
                self.write_html_export(filepath, meeting)
                if messagebox.askyesno("Export", "Zápis byl exportován. Chcete ho otevřít pro tisk?"):
                    try:
                        os.startfile(filepath)
                    except OSError:
                        messagebox.showwarning("Export", "Soubor se nepodařilo automaticky otevřít.")

            messagebox.showinfo("Export", "Zápis z porady byl úspěšně exportován.")


    def write_txt_export(self, filepath, meeting):
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(f"PORADA: {meeting[0]}\n")
            file.write(f"DATUM: {self.format_czech_date(meeting[1])}\n")
            file.write("=" * 40 + "\n\n")

            file.write("BODY PROGRAMU / ÚKOLY:\n")
            file.write("-" * 40 + "\n")
            for row in self.all_agenda_data:
                if row["type"] == "point":
                    file.write(f"\n{row['title']}\n")
                else:
                    status = "[X]" if row["is_resolved"] == 1 else "[ ]"
                    meta = self.format_item_meta(
                        row.get("owner"),
                        row.get("due_date"),
                        row.get("due_date_reason"),
                    )
                    file.write(f"  {status} {row['description']}{meta}\n")

            file.write("\n\nZÁPIS:\n")
            file.write("-" * 40 + "\n")
            file.write(self.text_notes.get(1.0, tk.END).strip())


    def write_html_export(self, filepath, meeting):
        title = html.escape(meeting[0])
        date = html.escape(self.format_czech_date(meeting[1]))
        notes = self.format_notes_for_html(self.text_notes.get(1.0, tk.END).strip())
        agenda_html = self.build_agenda_html()
        progress_html = self.build_progress_html()

        document = f"""<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>Zápis z porady - {title}</title>
  <style>
    :root {{
      --text: #17202a;
      --muted: #667085;
      --border: #d7dee8;
      --soft: #f8fafc;
      --primary: #2563eb;
      --success: #15803d;
      --warning: #f59e0b;
      --danger: #dc2626;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #eef2f6;
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }}
    main {{
      max-width: 920px;
      margin: 32px auto;
      background: white;
      padding: 40px 46px;
      border: 1px solid var(--border);
    }}
    header {{
      border-bottom: 2px solid var(--text);
      padding-bottom: 18px;
      margin-bottom: 26px;
    }}
    h1 {{
      margin: 0;
      font-size: 30px;
      line-height: 1.2;
    }}
    .meta {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 15px;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 18px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 6px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin: 18px 0 6px;
    }}
    .stat {{
      background: var(--soft);
      border: 1px solid var(--border);
      padding: 12px;
    }}
    .stat strong {{
      display: block;
      font-size: 22px;
    }}
    .stat span {{ color: var(--muted); }}
    .progress-row {{
      display: grid;
      grid-template-columns: minmax(120px, 190px) 1fr 92px;
      align-items: center;
      gap: 18px;
      margin: 10px 0;
    }}
    .progress-row.total {{
      font-weight: 700;
      margin-bottom: 16px;
    }}
    .bar {{
      height: 12px;
      background: #e5eaf1;
      overflow: hidden;
    }}
    .bar span {{
      display: block;
      height: 100%;
      background: var(--warning);
    }}
    .bar span.done {{ background: var(--success); }}
    .bar span.empty {{ background: var(--muted); }}
    .percent {{
      color: var(--muted);
      text-align: right;
      white-space: nowrap;
    }}
    .point {{
      break-inside: avoid;
      margin: 18px 0;
      border: 1px solid var(--border);
    }}
    .point-title {{
      background: var(--soft);
      border-bottom: 1px solid var(--border);
      padding: 10px 12px;
      font-weight: 700;
      color: var(--primary);
    }}
    .tasks {{
      list-style: none;
      margin: 0;
      padding: 8px 12px 10px;
    }}
    .tasks li {{
      padding: 6px 0;
      border-bottom: 1px solid #edf1f5;
    }}
    .tasks li:last-child {{ border-bottom: 0; }}
    .status {{
      display: inline-block;
      width: 24px;
      font-weight: 700;
    }}
    .task-meta {{
      display: block;
      margin-left: 28px;
      color: var(--muted);
      font-size: 12px;
    }}
    .resolved {{ color: var(--success); }}
    .open {{ color: var(--muted); }}
    .overdue {{ color: var(--danger); font-weight: 700; }}
    .notes {{
      background: var(--soft);
      border: 1px solid var(--border);
      padding: 14px 16px;
      min-height: 100px;
      white-space: normal;
    }}
    .print-button {{
      position: fixed;
      right: 24px;
      top: 18px;
      border: 0;
      background: var(--primary);
      color: white;
      font: 700 14px "Segoe UI", Arial, sans-serif;
      padding: 10px 14px;
      cursor: pointer;
    }}
    @media print {{
      body {{ background: white; }}
      main {{
        max-width: none;
        margin: 0;
        padding: 0;
        border: 0;
      }}
      .print-button {{ display: none; }}
    }}
  </style>
</head>
<body>
  <button class="print-button" onclick="window.print()">Tisk</button>
  <main>
    <header>
      <h1>{title}</h1>
      <div class="meta">Datum porady: {date}</div>
    </header>

    <section>
      <h2>Přehled plnění</h2>
      {progress_html}
    </section>

    <section>
      <h2>Plnění podle odpovědnosti</h2>
      {self.build_owner_progress_html()}
    </section>

    <section>
      <h2>Body programu</h2>
      {agenda_html}
    </section>

    <section>
      <h2>Zápis z porady</h2>
      <div class="notes">{notes}</div>
    </section>
  </main>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(document)


    def build_progress_html(self):
        total_done = self.progress_total["done"]
        total_count = self.progress_total["total"]
        total_percent = round((total_done / total_count) * 100) if total_count else 0
        open_count = total_count - total_done

        rows = [
            '<div class="summary">',
            f'<div class="stat"><strong>{total_count}</strong><span>položek celkem</span></div>',
            f'<div class="stat"><strong>{total_done}</strong><span>splněno</span></div>',
            f'<div class="stat"><strong>{open_count}</strong><span>otevřeno</span></div>',
            "</div>",
            self.build_progress_row_html("Celkem", total_done, total_count, total_percent, "total"),
        ]

        for point in self.progress_data:
            done = point["done"]
            total = point["total"]
            percent = round((done / total) * 100) if total else 0
            rows.append(self.build_progress_row_html(point["title"], done, total, percent))

        return "\n".join(rows)


    def build_owner_progress_html(self):
        if not self.owner_progress_data:
            return "<p>Nejsou zadané žádné odpovědnosti.</p>"

        rows = []
        for owner_row in self.owner_progress_data:
            done = owner_row["done"]
            total = owner_row["total"]
            percent = round((done / total) * 100) if total else 0
            rows.append(self.build_progress_row_html(owner_row["owner"], done, total, percent))
        return "\n".join(rows)


    def build_progress_row_html(self, label, done, total, percent, extra_class=""):
        bar_class = "done" if percent == 100 and total else ""
        if percent == 0:
            bar_class = "empty"

        return (
            f'<div class="progress-row {extra_class}">'
            f"<div>{html.escape(label)}</div>"
            f'<div class="bar"><span class="{bar_class}" style="width: {percent}%"></span></div>'
            f'<div class="percent">{done}/{total} ({percent}%)</div>'
            "</div>"
        )


    def build_agenda_html(self):
        sections = []
        current_point = None
        current_items = []

        for row in self.all_agenda_data:
            if row["type"] == "point":
                if current_point is not None:
                    sections.append(self.build_point_html(current_point, current_items))
                current_point = row["title"]
                current_items = []
            else:
                current_items.append(row)

        if current_point is not None:
            sections.append(self.build_point_html(current_point, current_items))

        if not sections:
            return "<p>Nejsou zadané žádné body programu.</p>"
        return "\n".join(sections)


    def build_point_html(self, title, items):
        if not items:
            items_html = '<li><span class="status open">○</span>Bez položek</li>'
        else:
            rendered_items = []
            for item in items:
                is_resolved = item["is_resolved"] == 1
                status = "✓" if is_resolved else "○"
                status_class = "resolved" if is_resolved else "open"
                item_class = " overdue" if self.is_item_overdue(item.get("due_date"), item["is_resolved"]) else ""
                description = html.escape(item["description"])
                meta_parts = []
                if item.get("owner"):
                    meta_parts.append(f"Odpovědnost: {html.escape(item['owner'])}")
                if item.get("due_date"):
                    meta_parts.append(f"Termín: {html.escape(item['due_date'])}")
                if item.get("due_date_reason"):
                    meta_parts.append(f"Důvod prodloužení: {html.escape(item['due_date_reason'])}")
                meta_html = f'<span class="task-meta">{" | ".join(meta_parts)}</span>' if meta_parts else ""
                rendered_items.append(
                    f'<li class="{item_class.strip()}"><span class="status {status_class}">{status}</span>{description}{meta_html}</li>'
                )
            items_html = "\n".join(rendered_items)

        return (
            '<article class="point">'
            f'<div class="point-title">{html.escape(title)}</div>'
            f'<ul class="tasks">{items_html}</ul>'
            "</article>"
        )


    def format_notes_for_html(self, notes):
        if not notes:
            return "<p>Bez zápisu.</p>"

        paragraphs = []
        for block in notes.split("\n\n"):
            text = html.escape(block.strip()).replace("\n", "<br>")
            if text:
                paragraphs.append(f"<p>{text}</p>")
        return "\n".join(paragraphs) if paragraphs else "<p>Bez zápisu.</p>"

