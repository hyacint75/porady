# -*- coding: utf-8 -*-

import os
import shlex
import shutil
import sqlite3
import subprocess
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from porady_widgets import RoundedFrame


class DialogMixin:

    def open_folder(self, path):
        try:
            os.startfile(path)
        except OSError as error:
            messagebox.showwarning("Otevřít složku", f"Složku se nepodařilo otevřít:\n{error}")


    def fetch_app_launchers(self, include_inactive=False):
        c = self.conn.cursor()
        query = """SELECT id, name, target_path, arguments, sort_order, is_active
                   FROM app_launchers"""
        if not include_inactive:
            query += " WHERE COALESCE(is_active, 1)=1"
        query += " ORDER BY COALESCE(sort_order, 0), name"
        c.execute(query)
        return c.fetchall()


    def open_app_launcher(self, launcher_id):
        c = self.conn.cursor()
        c.execute(
            """SELECT name, target_path, arguments
               FROM app_launchers
               WHERE id=? AND COALESCE(is_active, 1)=1""",
            (launcher_id,),
        )
        row = c.fetchone()
        if not row:
            messagebox.showwarning("Rozcestník aplikací", "Vybraná aplikace už není dostupná.")
            return None

        name, target_path, arguments = row
        target = os.path.expanduser(os.path.expandvars(target_path.strip()))
        args = (arguments or "").strip()
        if not target:
            messagebox.showwarning("Rozcestník aplikací", "U aplikace není vyplněná cesta.")
            return None

        try:
            if target == "__PORADY__":
                self.show_porady_workspace()
                return "workspace"

            if target == "__REQUIREMENTS__":
                self.show_requirements_application()
                return "requirements"

            if target == "__PROBLEMS__":
                self.show_problems_application()
                return "problems"

            if target.lower().startswith(("http://", "https://")):
                webbrowser.open(target)
                return "external"

            resolved_target = Path(target)
            if not resolved_target.exists():
                messagebox.showwarning("Rozcestník aplikací", f"Cesta k aplikaci neexistuje:\n{target}")
                return None

            if args:
                command = [str(resolved_target)] + shlex.split(args, posix=False)
                subprocess.Popen(command, cwd=str(resolved_target.parent))
            else:
                os.startfile(str(resolved_target))
            return "external"
        except (OSError, ValueError) as error:
            messagebox.showerror("Rozcestník aplikací", f"Aplikaci „{name}“ se nepodařilo spustit:\n{error}")
            return None


    def show_app_launcher_dialog(self):
        dialog, content = self.create_dialog("Rozcestník aplikací", 900, 560, 760, 450)
        launcher_home_active = hasattr(self, "left_frame") and not self.left_frame.winfo_ismapped()

        def close_launcher():
            if launcher_home_active:
                self.root.destroy()
            else:
                dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close_launcher)
        self.create_dialog_header(
            content,
            "Rozcestník aplikací",
            "Jedno místo pro spuštění dalších nástrojů a aplikací.",
            accent=self.COLORS["primary"],
        )

        list_frame = tk.Frame(content, bg=self.COLORS["panel"])
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "target", "arguments", "order", "active")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("name", text="Název")
        tree.heading("target", text="Cesta / odkaz")
        tree.heading("arguments", text="Argumenty")
        tree.heading("order", text="Pořadí")
        tree.heading("active", text="Aktivní")
        tree.column("name", width=180, anchor="w", stretch=False)
        tree.column("target", width=360, anchor="w")
        tree.column("arguments", width=140, anchor="w", stretch=False)
        tree.column("order", width=70, anchor="center", stretch=False)
        tree.column("active", width=70, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh():
            tree.delete(*tree.get_children())
            for launcher_id, name, target_path, arguments, sort_order, is_active in self.fetch_app_launchers(include_inactive=self.can_edit()):
                target_display = "Vnitřní aplikace" if target_path in ("__PORADY__", "__REQUIREMENTS__", "__PROBLEMS__") else target_path
                tree.insert(
                    "",
                    tk.END,
                    iid=str(launcher_id),
                    values=(
                        name,
                        target_display,
                        arguments or "",
                        sort_order or 0,
                        "Ano" if is_active else "Ne",
                    ),
                )

        def get_selected_id():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Rozcestník aplikací", "Vyberte aplikaci ze seznamu.")
                return None
            return int(selection[0])

        def launch_selected():
            launcher_id = get_selected_id()
            if launcher_id:
                result = self.open_app_launcher(launcher_id)
                if result in ("workspace", "requirements", "problems"):
                    dialog.destroy()

        def add_launcher():
            self.show_app_launcher_form(parent_dialog=dialog, refresh_callback=refresh)

        def edit_launcher():
            launcher_id = get_selected_id()
            if launcher_id:
                c = self.conn.cursor()
                c.execute("SELECT target_path FROM app_launchers WHERE id=?", (launcher_id,))
                row = c.fetchone()
                if row and row[0] in ("__PORADY__", "__REQUIREMENTS__", "__PROBLEMS__"):
                    messagebox.showinfo("Rozcestník aplikací", "Tato položka je základní součást rozcestníku.")
                    return
                self.show_app_launcher_form(launcher_id=launcher_id, parent_dialog=dialog, refresh_callback=refresh)

        def delete_launcher():
            if not self.require_admin():
                return
            launcher_id = get_selected_id()
            if not launcher_id:
                return
            c = self.conn.cursor()
            c.execute("SELECT target_path FROM app_launchers WHERE id=?", (launcher_id,))
            row = c.fetchone()
            if row and row[0] in ("__PORADY__", "__REQUIREMENTS__", "__PROBLEMS__"):
                messagebox.showinfo("Rozcestník aplikací", "Tuto základní položku nelze z rozcestníku odstranit.")
                return
            if not messagebox.askyesno("Smazat aplikaci", "Opravdu chcete vybranou aplikaci odstranit z rozcestníku?"):
                return
            c.execute("DELETE FROM app_launchers WHERE id=?", (launcher_id,))
            self.commit_database()
            refresh()

        tree.bind("<Double-1>", lambda event: launch_selected())
        refresh()
        children = tree.get_children()
        if children:
            tree.selection_set(children[0])
            tree.focus(children[0])

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(18, 0))

        def toggle_admin_from_launcher():
            self.toggle_admin_login()
            btn_admin_launcher.config(text="Odhlásit admina" if self.can_edit() else "Admin")
            refresh()

        self.create_button(actions, text="Spustit", command=launch_selected, variant="primary").pack(side=tk.LEFT)
        self.create_button(
            actions,
            text="Přidat aplikaci",
            command=add_launcher,
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            actions,
            text="Upravit",
            command=edit_launcher,
            variant="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            actions,
            text="Smazat",
            command=delete_launcher,
            variant="danger",
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(actions, text="Zavřít", command=close_launcher, variant="secondary").pack(side=tk.RIGHT)
        btn_admin_launcher = self.create_button(
            actions,
            text="Odhlásit admina" if self.can_edit() else "Admin",
            command=toggle_admin_from_launcher,
            variant="secondary",
        )
        btn_admin_launcher.pack(side=tk.RIGHT, padx=(0, 10))


    def show_app_launcher_form(self, launcher_id=None, parent_dialog=None, refresh_callback=None):
        if not self.require_admin():
            return

        values = {
            "name": "",
            "target_path": "",
            "arguments": "",
            "sort_order": "0",
            "is_active": 1,
        }
        if launcher_id:
            c = self.conn.cursor()
            c.execute(
                """SELECT name, target_path, arguments, sort_order, is_active
                   FROM app_launchers
                   WHERE id=?""",
                (launcher_id,),
            )
            row = c.fetchone()
            if not row:
                messagebox.showwarning("Rozcestník aplikací", "Vybraná aplikace už neexistuje.")
                return
            values.update(
                {
                    "name": row[0],
                    "target_path": row[1],
                    "arguments": row[2] or "",
                    "sort_order": str(row[3] or 0),
                    "is_active": row[4],
                }
            )

        dialog, content = self.create_dialog(
            "Upravit aplikaci" if launcher_id else "Přidat aplikaci",
            780,
            520,
            620,
            430,
            modal=True,
        )
        if parent_dialog:
            dialog.transient(parent_dialog)

        self.create_dialog_header(
            content,
            "Upravit aplikaci" if launcher_id else "Přidat aplikaci",
            "Uložte cestu k programu, dokumentu, složce nebo webový odkaz.",
        )

        name_var = tk.StringVar(value=values["name"])
        target_var = tk.StringVar(value=values["target_path"])
        args_var = tk.StringVar(value=values["arguments"])
        order_var = tk.StringVar(value=values["sort_order"])
        active_var = tk.BooleanVar(value=bool(values["is_active"]))

        def create_labeled_entry(label, variable):
            row = tk.Frame(content, bg=self.COLORS["panel"])
            row.pack(fill=tk.X, pady=(0, 12))
            tk.Label(
                row,
                text=label,
                width=14,
                font=(self.FONT, 10, "bold"),
                bg=self.COLORS["panel"],
                fg=self.COLORS["text"],
                anchor="w",
            ).pack(side=tk.LEFT)
            entry = ttk.Entry(row, textvariable=variable, font=(self.FONT, 10))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
            return row, entry

        name_row, name_entry = create_labeled_entry("Název", name_var)
        target_row, target_entry = create_labeled_entry("Cesta / odkaz", target_var)

        def browse_target():
            path = filedialog.askopenfilename(title="Vybrat aplikaci nebo soubor")
            if path:
                target_var.set(path)
                if not name_var.get().strip():
                    name_var.set(Path(path).stem)

        self.create_button(target_row, text="Vybrat", command=browse_target, variant="secondary").pack(side=tk.RIGHT, padx=(10, 0))
        create_labeled_entry("Argumenty", args_var)
        create_labeled_entry("Pořadí", order_var)

        tk.Checkbutton(
            content,
            text="Zobrazovat v rozcestníku",
            variable=active_var,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["panel"],
            activeforeground=self.COLORS["text"],
            selectcolor=self.COLORS["panel"],
            font=(self.FONT, 10),
            relief=tk.FLAT,
            borderwidth=0,
        ).pack(anchor="w", pady=(0, 12))

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(12, 0))

        def save():
            name = name_var.get().strip()
            target_path = target_var.get().strip()
            arguments = args_var.get().strip()
            if not name:
                messagebox.showwarning("Rozcestník aplikací", "Zadejte název aplikace.", parent=dialog)
                return
            if not target_path:
                messagebox.showwarning("Rozcestník aplikací", "Zadejte cestu nebo odkaz.", parent=dialog)
                return
            try:
                sort_order = int(order_var.get().strip() or "0")
            except ValueError:
                messagebox.showwarning("Rozcestník aplikací", "Pořadí musí být celé číslo.", parent=dialog)
                return

            c = self.conn.cursor()
            if launcher_id:
                c.execute(
                    """UPDATE app_launchers
                       SET name=?, target_path=?, arguments=?, sort_order=?, is_active=?
                       WHERE id=?""",
                    (name, target_path, arguments, sort_order, 1 if active_var.get() else 0, launcher_id),
                )
            else:
                c.execute(
                    """INSERT INTO app_launchers (name, target_path, arguments, sort_order, is_active)
                       VALUES (?, ?, ?, ?, ?)""",
                    (name, target_path, arguments, sort_order, 1 if active_var.get() else 0),
                )
            self.commit_database()
            if refresh_callback:
                refresh_callback()
            dialog.destroy()

        self.create_button(actions, text="Uložit", command=save, variant="primary").pack(side=tk.RIGHT)
        self.create_button(actions, text="Zrušit", command=dialog.destroy, variant="secondary").pack(side=tk.RIGHT, padx=(0, 10))
        dialog.bind("<Control-s>", lambda event: save())
        dialog.bind("<Return>", lambda event: save())
        dialog.lift()
        dialog.focus_force()
        if launcher_id:
            target_entry.focus_set()
        else:
            name_entry.focus_set()


    def create_manual_backup(self):
        if not self.require_admin():
            return

        try:
            if self.current_id and self.notes_dirty:
                self.save_notes(show_message=False)
            backup_path = self.create_database_backup("manual")
            if backup_path:
                messagebox.showinfo("Záloha", f"Záloha byla vytvořena:\n{backup_path}")
            else:
                messagebox.showwarning("Záloha", "Databáze zatím neexistuje, zálohu není možné vytvořit.")
        except OSError as error:
            messagebox.showerror("Záloha", f"Zálohu databáze se nepodařilo vytvořit:\n{error}")


    def choose_shared_database(self):
        if not self.require_admin():
            return

        path = filedialog.asksaveasfilename(
            title="Vybrat sdílenou databázi",
            initialfile=self.DB_FILENAME,
            defaultextension=".db",
            filetypes=[("SQLite databáze", "*.db"), ("Všechny soubory", "*.*")],
        )
        if not path:
            return

        selected_path = Path(path)
        if not selected_path.exists() and self.db_path.exists():
            if messagebox.askyesno(
                "Sdílená databáze",
                "Zvolená databáze zatím neexistuje. Chcete do ní zkopírovat aktuální data?",
            ):
                selected_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.db_path, selected_path)

        self.write_database_config(selected_path)
        messagebox.showinfo(
            "Sdílená databáze",
            "Cesta ke sdílené databázi byla uložena. Restartujte aplikaci, aby se změna použila.",
        )


    def restore_database_backup(self):
        if not self.require_admin():
            return

        backup_path = filedialog.askopenfilename(
            title="Obnovit databázi ze zálohy",
            initialdir=str(self.backup_dir),
            filetypes=[("SQLite databáze", "*.db"), ("Všechny soubory", "*.*")],
        )
        if not backup_path:
            return

        selected_path = Path(backup_path)
        if not selected_path.exists():
            messagebox.showwarning("Obnova zálohy", "Vybraná záloha neexistuje.")
            return
        if self.paths_match(selected_path, self.db_path):
            messagebox.showwarning("Obnova zálohy", "Vybraný soubor je aktuální databáze, ne záloha.")
            return
        if not messagebox.askyesno(
            "Obnova zálohy",
            "Opravdu chcete nahradit aktuální databázi vybranou zálohou?\n\n"
            "Před obnovou se ještě vytvoří bezpečnostní záloha aktuální databáze.",
        ):
            return

        try:
            if self.current_id and self.notes_dirty:
                self.save_notes(show_message=False)
            self.create_database_backup("before_restore")
            self.conn.close()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(selected_path, self.db_path)
            self.conn = sqlite3.connect(self.db_path, timeout=30)
            self.configure_database_connection()
            self.create_tables()
            self.log_audit("obnova ze zálohy", str(selected_path))
            self.commit_database()
            self.current_id = None
            self.notes_dirty = False
            self.load_meetings()
            self.refresh_dashboard_summary()
            messagebox.showinfo("Obnova zálohy", "Databáze byla obnovena ze zálohy.")
        except (OSError, sqlite3.Error) as error:
            try:
                self.conn = sqlite3.connect(self.db_path, timeout=30)
                self.configure_database_connection()
            except sqlite3.Error:
                pass
            messagebox.showerror("Obnova zálohy", f"Databázi se nepodařilo obnovit:\n{error}")


    def create_dialog(self, title, width, height, min_width=None, min_height=None, modal=False):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.minsize(min_width or width, min_height or height)
        dialog.configure(bg=self.COLORS["app_bg"])
        dialog.transient(self.root)
        if modal:
            dialog.grab_set()

        content_panel = RoundedFrame(
            dialog,
            radius=16,
            background=self.COLORS["panel"],
            border=self.COLORS["border"],
            padding=24,
            bg=self.COLORS["app_bg"],
        )
        content_panel.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        dialog.after(1, lambda: self.center_dialog(dialog, width, height))
        return dialog, content_panel.inner


    def center_dialog(self, dialog, width, height):
        self.root.update_idletasks()
        dialog.update_idletasks()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = max(self.root.winfo_width(), 1)
        root_height = max(self.root.winfo_height(), 1)
        x = root_x + max((root_width - width) // 2, 0)
        y = root_y + max((root_height - height) // 2, 0)
        dialog.geometry(f"{width}x{height}+{x}+{y}")


    def create_dialog_header(self, parent, title, subtitle=None, right_widget=None, accent=None):
        header = tk.Frame(parent, bg=self.COLORS["panel"])
        header.pack(fill=tk.X, pady=(0, 18))

        texts = tk.Frame(header, bg=self.COLORS["panel"])
        texts.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            texts,
            text=title,
            font=(self.FONT, 18, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
        ).pack(fill=tk.X)

        if subtitle:
            tk.Label(
                texts,
                text=subtitle,
                font=(self.FONT, 10),
                bg=self.COLORS["panel"],
                fg=self.COLORS["muted"],
                anchor="w",
                justify=tk.LEFT,
                wraplength=720,
            ).pack(fill=tk.X, pady=(5, 0))

        if right_widget:
            right_widget(header)

        if accent:
            tk.Frame(parent, height=4, bg=accent).pack(fill=tk.X, pady=(0, 12))

        separator = tk.Frame(parent, height=1, bg=self.COLORS["border"])
        separator.pack(fill=tk.X, pady=(0, 18))
        return header


    def show_data_settings(self):
        dialog, content = self.create_dialog("Data a zálohy", 860, 430, 720, 350)
        self.create_dialog_header(
            content,
            "Data a zálohy",
            "Umístění databáze a automatických záloh používaných aplikací.",
        )

        self.create_path_row(content, "Databáze", self.db_path, lambda: self.open_folder(self.db_path.parent))
        self.create_path_row(content, "Zálohy", self.backup_dir, lambda: self.open_folder(self.backup_dir))
        self.create_path_row(content, "Konfigurace", self.config_path, lambda: self.open_folder(self.config_path.parent))

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(18, 0))

        self.create_button(
            actions,
            text="Vytvořit zálohu",
            command=self.create_manual_backup,
            variant="primary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT)

        self.create_button(
            actions,
            text="Nastavit sdílenou DB",
            command=self.choose_shared_database,
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Obnovit ze zálohy",
            command=self.restore_database_backup,
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Export DB",
            command=self.export_database_copy,
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Import DB",
            command=self.import_database_copy,
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.create_button(
            actions,
            text="Zavřít",
            command=dialog.destroy,
            variant="secondary",
        ).pack(side=tk.RIGHT)


    def show_about(self):
        dialog, content = self.create_dialog("O aplikaci", 720, 520, 620, 440)
        self.create_dialog_header(
            content,
            f"Správce porad {self.APP_VERSION}",
            "Aplikace pro evidenci porad, zápisů, bodů programu a navazujících rozhodnutí.",
            accent=self.COLORS["primary"],
        )

        sections = (
            (
                "Co aplikace eviduje",
                "Porady, zápisy, body programu, úkoly, všeobecné informace, samostatná nařízení a požadavky.",
            ),
            (
                "Názvosloví",
                "Úkol je položka v bodu programu. Nařízení je samostatné rozhodnutí z porady. Požadavek je samostatný podnět, ze kterého lze podle potřeby vytvořit úkol.",
            ),
            (
                "Režimy práce",
                "Admin může vytvářet a upravovat záznamy. Uživatel v režimu jen pro čtení může data procházet bez rizika nechtěných změn.",
            ),
            (
                "Přehledy",
                "Samostatné přehledy pomáhají sledovat otevřené úkoly, nařízení, požadavky, termíny a odpovědnosti napříč poradami.",
            ),
            (
                "Data a zálohy",
                "Aplikace používá lokální nebo sdílenou SQLite databázi a umí vytvářet zálohy před vybranými zásahy.",
            ),
        )

        info_frame = tk.Frame(content, bg=self.COLORS["panel"])
        info_frame.pack(fill=tk.BOTH, expand=True)

        for title, text in sections:
            tk.Label(
                info_frame,
                text=title,
                font=(self.FONT, 10, "bold"),
                bg=self.COLORS["panel"],
                fg=self.COLORS["primary"],
                anchor="w",
            ).pack(fill=tk.X, pady=(0, 3))
            tk.Label(
                info_frame,
                text=text,
                font=(self.FONT, 10),
                bg=self.COLORS["panel"],
                fg=self.COLORS["text"],
                anchor="w",
                justify=tk.LEFT,
                wraplength=620,
            ).pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            info_frame,
            text=f"Verze aplikace: {self.APP_VERSION}",
            font=(self.FONT, 9, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
        ).pack(fill=tk.X, pady=(4, 0))

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(18, 0))

        self.create_button(
            actions,
            text="Zavřít",
            command=dialog.destroy,
            variant="primary",
        ).pack(side=tk.RIGHT)


    def create_path_row(self, parent, label, path, open_command):
        row = tk.Frame(parent, bg=self.COLORS["panel"])
        row.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            row,
            text=label,
            width=12,
            font=(self.FONT, 10, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
        ).pack(side=tk.LEFT)

        value = ttk.Entry(row, font=(self.FONT, 10))
        value.insert(0, str(path))
        value.configure(state="readonly")
        value.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=3)

        self.create_button(
            row,
            text="Otevřít",
            command=open_command,
            variant="secondary",
        ).pack(side=tk.RIGHT)


    def create_button(self, parent, text, command, variant="secondary", state=tk.NORMAL):
        variants = {
            "primary": {
                "bg": self.COLORS["primary"],
                "fg": "white",
                "active_bg": self.COLORS["primary_dark"],
                "font": (self.FONT, 10, "bold"),
            },
            "secondary": {
                "bg": "#e6edf7",
                "fg": self.COLORS["text"],
                "active_bg": "#d7e3f3",
                "font": (self.FONT, 10),
            },
            "danger": {
                "bg": "#fee2e2",
                "fg": self.COLORS["danger"],
                "active_bg": "#fecaca",
                "font": (self.FONT, 10, "bold"),
            },
        }
        colors = variants[variant]
        return tk.Button(
            parent,
            text=text,
            command=command,
            state=state,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=colors["active_bg"],
            activeforeground=colors["fg"],
            disabledforeground="#667085",
            font=colors["font"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=14,
            pady=8,
            cursor="hand2",
        )

