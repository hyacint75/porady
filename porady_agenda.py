# -*- coding: utf-8 -*-

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog


class AgendaMixin:

    def clear_entry_placeholder(self, entry, placeholder):
        if not self.can_edit():
            return

        if entry.get() == placeholder:
            entry.delete(0, tk.END)


    def format_item_meta(self, owner, due_date, due_date_reason=None):
        parts = []
        if owner:
            parts.append(f"odp.: {owner}")
        if due_date:
            parts.append(f"termín: {due_date}")
        if due_date_reason:
            parts.append(f"důvod prodloužení: {due_date_reason}")
        return f"  [{', '.join(parts)}]" if parts else ""


    def is_item_overdue(self, due_date, is_resolved):
        if is_resolved == 1 or not due_date:
            return False
        parsed_due_date = self.parse_due_date(due_date)
        return bool(parsed_due_date and parsed_due_date < datetime.now().date())

    def get_record_status(self, due_date, is_resolved):
        if is_resolved == 1:
            return "Splněno", "resolved"

        parsed_due_date = self.parse_due_date(due_date)
        if not parsed_due_date:
            return "Bez termínu", "no_due"

        today = datetime.now().date()
        if parsed_due_date < today:
            return "Po termínu", "overdue"
        if parsed_due_date == today:
            return "Dnes", "today"
        return "Otevřeno", "open"

    def configure_status_tags(self, tree):
        tree.tag_configure("resolved", foreground=self.COLORS["success"])
        tree.tag_configure("overdue", foreground=self.COLORS["danger"])
        tree.tag_configure("today", foreground=self.COLORS["warning"])
        tree.tag_configure("no_due", foreground=self.COLORS["muted"])
        tree.tag_configure("open", foreground=self.COLORS["primary"])


    def get_item_form_values(self):
        description = self.entry_new_item.get().strip()
        owner = self.entry_new_owner.get().strip()
        due_date = self.entry_new_due_date.get().strip()
        if owner == "Odpovědnost":
            owner = ""
        if due_date == "Termín":
            due_date = ""
        parsed_due_date = self.parse_due_date(due_date)
        if parsed_due_date:
            due_date = parsed_due_date.strftime("%d.%m.%Y")
        return description, owner, due_date


    def reset_item_form(self):
        self.editing_item_id = None
        self.entry_new_item.delete(0, tk.END)
        self.entry_new_owner.delete(0, tk.END)
        self.entry_new_owner.insert(0, "Odpovědnost")
        self.entry_new_due_date.delete(0, tk.END)
        self.entry_new_due_date.insert(0, self.get_today_due_date())
        self.btn_add_item.config(text="Přidat položku")
        self.btn_cancel_edit.pack_forget()


    def reset_point_form(self):
        self.editing_point_id = None
        self.entry_new_point.delete(0, tk.END)
        self.btn_add_point.config(text="Přidat bod programu")
        self.btn_cancel_point_edit.pack_forget()


    def start_edit_point(self, row):
        if not self.can_edit():
            return

        self.editing_point_id = row["id"]
        self.entry_new_point.delete(0, tk.END)
        self.entry_new_point.insert(0, row["title"])
        self.btn_add_point.config(text="Uložit bod")
        if not self.btn_cancel_point_edit.winfo_ismapped():
            self.btn_cancel_point_edit.pack(side=tk.RIGHT, padx=(0, 8))
        self.entry_new_point.focus_set()


    def start_edit_item(self, row):
        if not self.can_edit():
            return

        self.editing_item_id = row["id"]
        self.entry_new_item.delete(0, tk.END)
        self.entry_new_item.insert(0, row["description"])
        self.entry_new_owner.delete(0, tk.END)
        self.entry_new_owner.insert(0, row.get("owner") or "Odpovědnost")
        self.entry_new_due_date.delete(0, tk.END)
        self.entry_new_due_date.insert(0, row.get("due_date") or "Termín")
        self.btn_add_item.config(text="Uložit změny")
        if not self.btn_cancel_edit.winfo_ismapped():
            self.btn_cancel_edit.pack(side=tk.RIGHT, padx=(0, 8))
        self.entry_new_item.focus_set()


    def add_agenda_point(self):
        if not self.require_admin():
            return

        if not self.current_id:
            return

        if self.editing_point_id:
            self.update_agenda_point()
            return

        title = self.entry_new_point.get().strip()
        if not title:
            messagebox.showwarning("Bod programu", "Zadejte název bodu programu, například 250137.")
            return

        c = self.conn.cursor()
        c.execute("INSERT INTO agenda_points (meeting_id, title) VALUES (?, ?)", (self.current_id, title))
        self.commit_database()
        self.entry_new_point.delete(0, tk.END)
        self.load_meeting_details()
        self.select_agenda_point(c.lastrowid)


    def update_agenda_point(self):
        if not self.require_admin():
            return

        title = self.entry_new_point.get().strip()
        if not title:
            messagebox.showwarning("Bod programu", "Zadejte název bodu programu.")
            return

        point_id = self.editing_point_id
        c = self.conn.cursor()
        c.execute("UPDATE agenda_points SET title=? WHERE id=?", (title, point_id))
        self.commit_database()
        self.reset_point_form()
        self.load_meeting_details()
        self.select_agenda_point(point_id)


    def add_agenda_item(self):
        if not self.require_admin():
            return

        if not self.current_id:
            return

        if self.editing_item_id:
            self.update_agenda_item()
            return

        point_id = self.get_selected_point_id()
        if not point_id:
            messagebox.showwarning("Položka bodu", "Nejprve vyberte nebo vytvořte bod programu.")
            return

        new_desc, owner, due_date = self.get_item_form_values()
        if due_date and not self.parse_due_date(due_date):
            messagebox.showwarning("Termín", "Zadejte platný termín, například 13.05.2026, nebo pole vymažte.")
            self.entry_new_due_date.focus_set()
            return
        if new_desc:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO agenda_items (point_id, description, is_resolved, owner, due_date) VALUES (?, ?, 0, ?, ?)",
                (point_id, new_desc, owner, due_date),
            )
            new_item_id = c.lastrowid
            self.log_change("úkol", new_item_id, self.current_id, "vytvořeno", "", new_desc)
            self.commit_database()
            self.reset_item_form()
            self.refresh_item_description_choices()
            self.refresh_owner_choices()
            self.load_meeting_details()
            self.select_agenda_point(point_id)


    def update_agenda_item(self):
        if not self.require_admin():
            return

        description, owner, due_date = self.get_item_form_values()
        if not description:
            messagebox.showwarning("Položka bodu", "Zadejte text položky.")
            return
        if due_date and not self.parse_due_date(due_date):
            messagebox.showwarning("Termín", "Zadejte platný termín, například 13.05.2026, nebo pole vymažte.")
            self.entry_new_due_date.focus_set()
            return

        item_id = self.editing_item_id
        c = self.conn.cursor()
        c.execute("SELECT description, owner, due_date, due_date_reason, is_resolved FROM agenda_items WHERE id=?", (item_id,))
        previous_row = c.fetchone()
        due_date_reason = previous_row[3] if previous_row else ""
        old_due = self.parse_due_date(previous_row[2]) if previous_row else None
        new_due = self.parse_due_date(due_date)
        if old_due and new_due and new_due > old_due and not due_date_reason:
            due_date_reason = simpledialog.askstring(
                "Důvod prodloužení",
                "Termín byl prodloužen. Zadejte důvod prodloužení termínu:",
            )
            if not due_date_reason:
                return

        c.execute(
            "UPDATE agenda_items SET description=?, owner=?, due_date=?, due_date_reason=? WHERE id=?",
            (description, owner, due_date, due_date_reason, item_id),
        )
        if previous_row:
            self.log_field_changes(
                "úkol",
                item_id,
                self.current_id,
                {
                    "text": previous_row[0],
                    "odpovědnost": previous_row[1],
                    "termín": previous_row[2],
                    "důvod prodloužení": previous_row[3],
                },
                {
                    "text": description,
                    "odpovědnost": owner,
                    "termín": due_date,
                    "důvod prodloužení": due_date_reason,
                },
            )
        self.commit_database()
        self.reset_item_form()
        self.refresh_item_description_choices()
        self.refresh_owner_choices()
        self.load_meeting_details()


    def on_select_agenda_row(self, event):
        if self.suppress_agenda_select_event:
            return

        row = self.get_selected_agenda_row()
        if not self.can_edit():
            if row and row["type"] == "point":
                self.active_point_id = row["id"]
            elif row and row["type"] == "item":
                self.active_point_id = row["point_id"]
            return

        if row and row["type"] == "point":
            self.active_point_id = row["id"]
            self.reset_item_form()
            self.start_edit_point(row)
        elif row and row["type"] == "item":
            self.active_point_id = row["point_id"]
            self.start_edit_item(row)


    def get_selected_agenda_row(self):
        selection = self.agenda_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self.current_agenda_data):
            return None
        return self.current_agenda_data[index]


    def get_selected_point_id(self):
        row = self.get_selected_agenda_row()
        if row:
            if row["type"] == "point":
                self.active_point_id = row["id"]
                return row["id"]
            self.active_point_id = row["point_id"]
            return row["point_id"]

        if self.active_point_id and self.agenda_point_exists(self.active_point_id):
            return self.active_point_id

        point_rows = [row for row in self.current_agenda_data if row["type"] == "point"]
        if len(point_rows) == 1:
            self.active_point_id = point_rows[0]["id"]
            return point_rows[0]["id"]
        all_point_rows = [row for row in self.all_agenda_data if row["type"] == "point"]
        if len(all_point_rows) == 1:
            self.active_point_id = all_point_rows[0]["id"]
            return all_point_rows[0]["id"]
        return None


    def agenda_point_exists(self, point_id):
        return any(row["type"] == "point" and row["id"] == point_id for row in self.all_agenda_data)


    def ensure_active_agenda_point(self):
        if self.active_point_id and self.agenda_point_exists(self.active_point_id):
            self.select_agenda_point(self.active_point_id, keep_form=True)
            return

        point_rows = [row for row in self.current_agenda_data if row["type"] == "point"]
        if not point_rows:
            point_rows = [row for row in self.all_agenda_data if row["type"] == "point"]
        self.active_point_id = point_rows[0]["id"] if point_rows else None
        if self.active_point_id:
            self.select_agenda_point(self.active_point_id, keep_form=True)


    def select_agenda_point(self, point_id, keep_form=False):
        for index, row in enumerate(self.current_agenda_data):
            if row["type"] == "point" and row["id"] == point_id:
                self.active_point_id = point_id
                self.suppress_agenda_select_event = keep_form
                try:
                    self.agenda_listbox.selection_clear(0, tk.END)
                    self.agenda_listbox.selection_set(index)
                    self.agenda_listbox.activate(index)
                    self.agenda_listbox.see(index)
                finally:
                    self.suppress_agenda_select_event = False
                return


    def select_agenda_item(self, item_id):
        for index, row in enumerate(self.current_agenda_data):
            if row["type"] == "item" and row["id"] == item_id:
                self.agenda_listbox.selection_clear(0, tk.END)
                self.agenda_listbox.selection_set(index)
                self.agenda_listbox.activate(index)
                self.agenda_listbox.see(index)
                return


    def toggle_agenda_item(self, event):
        if not self.require_admin():
            return

        row = self.get_selected_agenda_row()
        if row and row["type"] == "item" and self.current_id:
            current_status = row["is_resolved"]
            new_status = 1 if current_status == 0 else 0

            c = self.conn.cursor()
            c.execute("UPDATE agenda_items SET is_resolved=? WHERE id=?", (new_status, row["id"]))
            self.log_change("úkol", row["id"], self.current_id, "stav", "splněno" if current_status == 1 else "otevřeno", "splněno" if new_status == 1 else "otevřeno")
            self.commit_database()
            self.load_meeting_details()


    def delete_agenda_item(self):
        if not self.require_admin():
            return

        row = self.get_selected_agenda_row()
        if row and self.current_id:
            c = self.conn.cursor()
            if row["type"] == "point":
                if not messagebox.askyesno("Smazat bod programu", "Smazat bod programu včetně všech položek?"):
                    return
                if not self.backup_before_delete("delete_point"):
                    return
                c.execute("DELETE FROM agenda_items WHERE point_id=?", (row["id"],))
                c.execute("DELETE FROM agenda_points WHERE id=?", (row["id"],))
                if self.editing_point_id == row["id"]:
                    self.reset_point_form()
            else:
                if not self.backup_before_delete("delete_item"):
                    return
                c.execute("DELETE FROM agenda_items WHERE id=?", (row["id"],))
                if self.editing_item_id == row["id"]:
                    self.reset_item_form()
            self.commit_database()
            self.load_meeting_details()


    def copy_unresolved(self):
        if not self.require_admin():
            return

        if not self.current_id:
            messagebox.showwarning("Upozornění", "Nejprve vyberte poradu ze seznamu.")
            return

        if self.notes_dirty:
            self.save_notes(show_message=False)

        c = self.conn.cursor()
        c.execute("SELECT title, notes FROM meetings WHERE id=?", (self.current_id,))
        meeting = c.fetchone()
        if not meeting:
            messagebox.showwarning("Kopírovat poradu", "Vybraná porada už neexistuje. Seznam bude obnoven.")
            self.current_id = None
            self.clear_right_panel()
            self.load_meetings()
            return
        old_title, old_notes = meeting

        new_title = simpledialog.askstring(
            "Kopírovat poradu",
            "Název nové porady:",
            initialvalue=f"{old_title} (Pokračování)",
        )
        if new_title:
            date_str = datetime.now().strftime("%Y-%m-%d")
            c.execute(
                "INSERT INTO meetings (title, date, notes, general_info) VALUES (?, ?, ?, ?)",
                (new_title, date_str, old_notes or "", ""),
            )
            new_meeting_id = c.lastrowid

            c.execute(
                """SELECT info_text, created_at, is_invalid, invalidated_at
                   FROM meeting_general_info
                   WHERE meeting_id=? AND COALESCE(is_invalid, 0)=0
                   ORDER BY datetime(created_at), id""",
                (self.current_id,),
            )
            for info_text, created_at, is_invalid, invalidated_at in c.fetchall():
                c.execute(
                    """INSERT INTO meeting_general_info
                       (meeting_id, info_text, created_at, is_invalid, invalidated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (new_meeting_id, info_text, created_at, is_invalid, invalidated_at),
                )

            # Zkopírovat pouze body programu, které mají nevyřešené položky
            transferred_count = 0
            c.execute("SELECT id, title FROM agenda_points WHERE meeting_id=? ORDER BY id", (self.current_id,))
            for old_point_id, point_title in c.fetchall():
                c.execute(
                    """SELECT description, owner, due_date, due_date_reason
                       FROM agenda_items WHERE point_id=? AND is_resolved=0 ORDER BY id""",
                    (old_point_id,),
                )
                unresolved_items = c.fetchall()
                if not unresolved_items:
                    continue

                c.execute("INSERT INTO agenda_points (meeting_id, title) VALUES (?, ?)", (new_meeting_id, point_title))
                new_point_id = c.lastrowid
                for item in unresolved_items:
                    c.execute(
                        """INSERT INTO agenda_items
                           (point_id, description, is_resolved, owner, due_date, due_date_reason)
                           VALUES (?, ?, 0, ?, ?, ?)""",
                        (new_point_id, item[0], item[1], item[2], item[3]),
                    )
                    transferred_count += 1

            c.execute(
                """SELECT description, owner, due_date, created_at
                   FROM meeting_orders
                   WHERE meeting_id=? AND COALESCE(is_resolved, 0)=0
                   ORDER BY id""",
                (self.current_id,),
            )
            order_count = 0
            for description, owner, due_date, created_at in c.fetchall():
                c.execute(
                    """INSERT INTO meeting_orders
                       (meeting_id, description, owner, due_date, is_resolved, created_at, completed_at)
                       VALUES (?, ?, ?, ?, 0, ?, '')""",
                    (new_meeting_id, description, owner, due_date, created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
                order_count += 1

            c.execute(
                """SELECT description, owner, due_date, created_at
                   FROM meeting_requirements
                   WHERE meeting_id=? AND COALESCE(is_resolved, 0)=0
                   ORDER BY id""",
                (self.current_id,),
            )
            requirement_count = 0
            for description, owner, due_date, created_at in c.fetchall():
                c.execute(
                    """INSERT INTO meeting_requirements
                       (meeting_id, description, owner, due_date, is_resolved, created_at, completed_at)
                       VALUES (?, ?, ?, ?, 0, ?, '')""",
                    (new_meeting_id, description, owner, due_date, created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
                requirement_count += 1

            self.commit_database()
            self.current_id = new_meeting_id
            self.load_meetings()
            self.load_meeting_details()
            messagebox.showinfo(
                "Hotovo",
                "Nová porada byla vytvořena.\n\n"
                f"Přeneseno: {transferred_count} úkolů, {order_count} nařízení, {requirement_count} požadavků.",
            )

