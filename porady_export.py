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
        c.execute("SELECT title, date FROM meetings WHERE id=?", (self.current_id,))
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
            initialfile=f"Prehled_porady_{meeting[1]}_{safe_title}.html",
            filetypes=[("Tiskový HTML přehled", "*.html"), ("Textové soubory", "*.txt")],
        )

        if filepath:
            if filepath.lower().endswith(".txt"):
                self.write_txt_export(filepath, meeting)
            else:
                self.write_html_export(filepath, meeting)
                if messagebox.askyesno("Export", "Přehled byl exportován. Chcete ho otevřít pro tisk?"):
                    try:
                        os.startfile(filepath)
                    except OSError:
                        messagebox.showwarning("Export", "Soubor se nepodařilo automaticky otevřít.")

            messagebox.showinfo("Export", "Přehled porady byl úspěšně exportován.")


    def write_txt_export(self, filepath, meeting):
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(f"PORADA: {meeting[0]}\n")
            file.write(f"DATUM: {self.format_czech_date(meeting[1])}\n")
            file.write("=" * 40 + "\n\n")

            general_info = self.fetch_export_general_info()
            file.write("VŠEOBECNÉ INFORMACE:\n")
            file.write("-" * 40 + "\n")
            if general_info:
                for row in general_info:
                    file.write(f"- {row['info_text']}\n")
            else:
                file.write("Bez všeobecných informací.\n")
            file.write("\n")

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

            self.write_record_txt_section(file, "NAŘÍZENÍ", self.fetch_export_orders())
            self.write_record_txt_section(file, "POŽADAVKY", self.fetch_export_requirements())


    def write_html_export(self, filepath, meeting):
        title = html.escape(meeting[0])
        date = html.escape(self.format_czech_date(meeting[1]))
        agenda_html = self.build_agenda_html()
        progress_html = self.build_progress_html()
        general_info_html = self.build_general_info_html()
        orders_html = self.build_record_list_html("Nařízení", self.fetch_export_orders())
        requirements_html = self.build_record_list_html("Požadavky", self.fetch_export_requirements())

        document = f"""<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>Přehled porady - {title}</title>
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
    .record-list {{
      list-style: none;
      padding: 0;
      margin: 0;
      border: 1px solid var(--border);
    }}
    .record-list li {{
      padding: 10px 12px;
      border-bottom: 1px solid #edf1f5;
    }}
    .record-list li:last-child {{ border-bottom: 0; }}
    .record-title {{ font-weight: 700; }}
    .record-meta {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
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
      <h2>Všeobecné informace</h2>
      {general_info_html}
    </section>

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
      <h2>Nařízení</h2>
      {orders_html}
    </section>

    <section>
      <h2>Požadavky</h2>
      {requirements_html}
    </section>

    <section>
  </main>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(document)

    def fetch_export_general_info(self):
        c = self.conn.cursor()
        c.execute(
            """SELECT info_text, created_at
               FROM meeting_general_info
               WHERE meeting_id=? AND COALESCE(is_invalid, 0)=0
               ORDER BY datetime(created_at), id""",
            (self.current_id,),
        )
        return [{"info_text": row[0] or "", "created_at": row[1] or ""} for row in c.fetchall()]


    def fetch_export_records(self, table_name):
        c = self.conn.cursor()
        c.execute(
            f"""SELECT description, owner, due_date, is_resolved
                FROM {table_name}
                WHERE meeting_id=?
                ORDER BY COALESCE(is_resolved, 0), id""",
            (self.current_id,),
        )
        records = []
        for description, owner, due_date, is_resolved in c.fetchall():
            status_text, status_tag = self.get_record_status(due_date, is_resolved)
            records.append(
                {
                    "description": description or "",
                    "owner": owner or "",
                    "due_date": due_date or "",
                    "status_text": status_text,
                    "status_tag": status_tag,
                }
            )
        return records


    def fetch_export_orders(self):
        return self.fetch_export_records("meeting_orders")


    def fetch_export_requirements(self):
        return self.fetch_export_records("meeting_requirements")


    def write_record_txt_section(self, file, title, records):
        file.write(f"\n\n{title}:\n")
        file.write("-" * 40 + "\n")
        if not records:
            file.write(f"Bez položek v sekci {title.lower()}.\n")
            return

        for record in records:
            meta = []
            if record["owner"]:
                meta.append(f"odp.: {record['owner']}")
            if record["due_date"]:
                meta.append(f"termín: {record['due_date']}")
            meta.append(f"stav: {record['status_text']}")
            file.write(f"- {record['description']} [{', '.join(meta)}]\n")


    def build_general_info_html(self):
        rows = self.fetch_export_general_info()
        if not rows:
            return "<p>Bez všeobecných informací.</p>"

        items = []
        for row in rows:
            created_at = self.format_general_info_timestamp(row["created_at"])
            meta = f'<span class="record-meta">Zadáno: {html.escape(created_at)}</span>' if created_at else ""
            items.append(f'<li><span class="record-title">{html.escape(row["info_text"])}</span>{meta}</li>')
        return f'<ul class="record-list">{"".join(items)}</ul>'


    def build_record_list_html(self, title, records):
        if not records:
            return f"<p>Bez položek v sekci {html.escape(title.lower())}.</p>"

        items = []
        for record in records:
            meta_parts = [f"Stav: {html.escape(record['status_text'])}"]
            if record["owner"]:
                meta_parts.append(f"Odpovědnost: {html.escape(record['owner'])}")
            if record["due_date"]:
                meta_parts.append(f"Termín: {html.escape(record['due_date'])}")
            items.append(
                '<li>'
                f'<span class="status {record["status_tag"]}">{"✓" if record["status_tag"] == "resolved" else "○"}</span>'
                f'<span class="record-title">{html.escape(record["description"])}</span>'
                f'<span class="record-meta">{" | ".join(meta_parts)}</span>'
                '</li>'
            )
        return f'<ul class="record-list">{"".join(items)}</ul>'


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

