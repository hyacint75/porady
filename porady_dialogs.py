# -*- coding: utf-8 -*-

import configparser
import os
import shlex
import shutil
import sqlite3
import subprocess
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from porady_widgets import RoundedFrame


class DialogMixin:
    INTERNAL_LAUNCHERS = {
        "__PORADY__",
        "__REQUIREMENTS__",
        "__PROBLEMS__",
        "__QUALITY__",
        "__CHANGE_MANAGEMENT__",
        "__JOB_EVALUATION__",
        "__EXTERNAL_COMPANIES__",
        "__ENTRY_TRAINING__",
    }

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

            if target == "__QUALITY__":
                self.show_quality_application()
                return "quality"

            if target == "__CHANGE_MANAGEMENT__":
                self.show_change_management_application()
                return "change_management"

            if target == "__JOB_EVALUATION__":
                self.show_job_evaluation_application()
                return "job_evaluation"

            if target == "__EXTERNAL_COMPANIES__":
                self.show_external_companies_application()
                return "external_companies"

            if target == "__ENTRY_TRAINING__":
                self.show_entry_training_application()
                return "entry_training"

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
        except (ImportError, OSError, ValueError, tk.TclError) as error:
            messagebox.showerror("Rozcestník aplikací", f"Aplikaci „{name}“ se nepodařilo spustit:\n{error}")
            return None


    def _show_integrated_training_application(self, window_attribute, application_class):
        window = getattr(self, window_attribute, None)
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = application_class(
            self.root,
            on_home=self.show_launcher_home,
            on_data_changed=self.sync_integrated_records,
        )
        setattr(self, window_attribute, window)


    def show_external_companies_application(self):
        from integrated_apps.external_companies import TrainingApp

        self._show_integrated_training_application("external_companies_window", TrainingApp)


    def show_entry_training_application(self):
        from integrated_apps.entry_training import TrainingApp

        self._show_integrated_training_application("entry_training_window", TrainingApp)


    def show_app_launcher_dialog(self):
        dialog, content = self.create_dialog("Správa aplikací", 900, 560, 760, 450)

        def close_launcher():
            dialog.destroy()
            self.show_launcher_home()

        dialog.protocol("WM_DELETE_WINDOW", close_launcher)
        self.create_dialog_header(
            content,
            "Správa aplikací",
            "Nastavení aplikací zobrazených jako ikony na hlavní stránce.",
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
                target_display = "Vnitřní aplikace" if target_path in self.INTERNAL_LAUNCHERS else target_path
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
                if result in (
                    "workspace",
                    "requirements",
                    "problems",
                    "quality",
                    "change_management",
                    "job_evaluation",
                    "external_companies",
                    "entry_training",
                ):
                    dialog.destroy()

        def add_launcher():
            self.show_app_launcher_form(parent_dialog=dialog, refresh_callback=refresh)

        def edit_launcher():
            launcher_id = get_selected_id()
            if launcher_id:
                c = self.conn.cursor()
                c.execute("SELECT target_path FROM app_launchers WHERE id=?", (launcher_id,))
                row = c.fetchone()
                if row and row[0] in self.INTERNAL_LAUNCHERS:
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
            if row and row[0] in self.INTERNAL_LAUNCHERS:
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
        choose_existing = messagebox.askyesnocancel(
            "Nastavit databázi",
            "Chcete vybrat existující databázi?\n\n"
            "Ano = vybrat existující soubor\n"
            "Ne = vytvořit novou databázi",
        )
        if choose_existing is None:
            return

        initial_dir = self.db_path.parent if self.db_path.parent.exists() else self.get_runtime_dir()
        if choose_existing:
            path = filedialog.askopenfilename(
                title="Vybrat existující databázi",
                initialdir=str(initial_dir),
                filetypes=[("SQLite databáze", "*.db"), ("Všechny soubory", "*.*")],
            )
        else:
            path = filedialog.asksaveasfilename(
                title="Vytvořit novou databázi",
                initialdir=str(initial_dir),
                initialfile=self.DB_FILENAME,
                defaultextension=".db",
                filetypes=[("SQLite databáze", "*.db"), ("Všechny soubory", "*.*")],
            )
        if not path:
            return

        selected_path = Path(path)
        try:
            selected_path.parent.mkdir(parents=True, exist_ok=True)
            if not selected_path.exists() and self.db_path.exists() and messagebox.askyesno(
                "Nová databáze",
                "Chcete do nové databáze zkopírovat aktuální data?\n\n"
                "Volbou Ne vznikne prázdná databáze.",
            ):
                self.commit_database()
                shutil.copy2(self.db_path, selected_path)

            self.switch_database(selected_path)
        except (OSError, sqlite3.Error, configparser.Error) as error:
            messagebox.showerror(
                "Nastavení databáze",
                "Databázi se nepodařilo otestovat nebo připojit.\n\n"
                f"Cesta: {selected_path}\n"
                f"Chyba: {error}\n\n"
                "Původní databáze zůstala aktivní.",
            )
            return

        messagebox.showinfo(
            "Nastavení databáze",
            f"Databáze byla úspěšně otestována a připojena:\n{selected_path.resolve()}",
        )
        settings_dialog = getattr(self, "data_settings_dialog", None)
        if settings_dialog is not None and settings_dialog.winfo_exists():
            settings_dialog.destroy()
            self.data_settings_dialog = None


    def test_current_database_connection(self):
        try:
            self.test_database_path(self.db_path)
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror(
                "Test databáze",
                f"Test čtení a zápisu selhal:\n{error}",
            )
            return

        messagebox.showinfo(
            "Test databáze",
            f"Čtení i zápis fungují správně:\n{self.db_path}",
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
        if modal:
            dialog.transient(self.root)
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


    def show_admin_dashboard(self):
        dialog, content = self.create_dialog("Administrace", 980, 700, 840, 600)

        def close_admin():
            dialog.destroy()
            self.show_launcher_home()

        dialog.protocol("WM_DELETE_WINDOW", close_admin)

        def render_status(header):
            status = "Admin aktivní" if self.can_edit() else "Jen pro čtení"
            color = "#166534" if self.can_edit() else "#92400e"
            background = "#dcfce7" if self.can_edit() else "#fef3c7"
            tk.Label(
                header,
                text=status,
                font=(self.FONT, 10, "bold"),
                bg=background,
                fg=color,
                padx=12,
                pady=7,
            ).pack(side=tk.RIGHT)

        self.create_dialog_header(
            content,
            "Administrace",
            "Centrální místo pro správu režimu admina, rozcestníku, databáze, záloh a provozních kontrol.",
            right_widget=render_status,
            accent=self.COLORS["primary"],
        )

        info = tk.Frame(content, bg="#f8fafc", padx=14, pady=12, highlightthickness=1, highlightbackground=self.COLORS["border"])
        info.pack(fill=tk.X, pady=(0, 16))
        rows = (
            ("Aktuální režim", "Admin - úpravy povoleny" if self.can_edit() else "Uživatel - jen čtení"),
            ("Databáze", str(self.db_path)),
            ("Zálohy", str(self.backup_dir)),
            ("Konfigurace", str(self.config_path)),
        )
        for label, value in rows:
            line = tk.Frame(info, bg="#f8fafc")
            line.pack(fill=tk.X, pady=2)
            tk.Label(line, text=label, width=16, anchor="w", font=(self.FONT, 10, "bold"), bg="#f8fafc", fg="#334155").pack(side=tk.LEFT)
            tk.Label(line, text=value, anchor="w", font=(self.FONT, 10), bg="#f8fafc", fg=self.COLORS["text"], wraplength=720, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True)

        grid = tk.Frame(content, bg=self.COLORS["panel"])
        grid.pack(fill=tk.BOTH, expand=True)
        for column in range(2):
            grid.columnconfigure(column, weight=1, uniform="admin_cards")

        cards = (
            (
                "Admin režim",
                "Přihlášení nebo odhlášení administrátora pro úpravy dat.",
                "Odhlásit admina" if self.can_edit() else "Přihlásit admina",
                lambda: (self.toggle_admin_login(), dialog.destroy(), self.show_admin_dashboard()),
                True,
            ),
            (
                "Správa rozcestníku",
                "Přidání, úprava, skrytí nebo řazení aplikací v rozcestníku.",
                "Otevřít správu",
                self.show_app_launcher_dialog,
                self.can_edit(),
            ),
            (
                "Uživatelé a role",
                "Zakládání uživatelů, reset hesel, aktivace účtů a přiřazení rolí.",
                "Spravovat uživatele",
                self.show_user_management_dialog,
                self.can_manage_users(),
            ),
            (
                "Data a zálohy",
                "Cesty k databázi, ruční záloha, obnova, import a export databáze.",
                "Otevřít data",
                self.show_data_settings,
                True,
            ),
            (
                "Kontrola databáze",
                "Rychlé ověření čtení a zápisu aktuálně připojené databáze.",
                "Otestovat",
                self.test_current_database_connection,
                True,
            ),
            (
                "Kompletní ZIP záloha",
                "Uložení databáze, konfigurace a důležitých provozních souborů do archivu.",
                "Vytvořit ZIP",
                self.create_complete_backup,
                self.can_edit(),
            ),
            (
                "Synchronizace školení",
                "Načtení integrovaných záznamů ze školení do společných přehledů.",
                "Synchronizovat",
                self.sync_integrated_records,
                True,
            ),
        )
        for index, (title, description, button_text, command, enabled) in enumerate(cards):
            self.create_admin_card(grid, title, description, button_text, command, enabled, index // 2, index % 2)

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(16, 0))
        self.create_button(actions, text="Zavřít", command=close_admin, variant="secondary").pack(side=tk.RIGHT)


    def create_admin_card(self, parent, title, description, button_text, command, enabled, row, column):
        card = tk.Frame(
            parent,
            bg="white",
            padx=16,
            pady=14,
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
        )
        card.grid(row=row, column=column, sticky="nsew", padx=(0, 12 if column == 0 else 0), pady=(0, 12))
        tk.Label(
            card,
            text=title,
            font=(self.FONT, 12, "bold"),
            bg="white",
            fg=self.COLORS["text"],
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            card,
            text=description,
            font=(self.FONT, 10),
            bg="white",
            fg=self.COLORS["muted"],
            anchor="w",
            justify=tk.LEFT,
            wraplength=390,
        ).pack(fill=tk.X, pady=(6, 12))
        self.create_button(
            card,
            text=button_text,
            command=command,
            variant="primary" if enabled else "secondary",
            state=tk.NORMAL if enabled else tk.DISABLED,
        ).pack(anchor="w")


    def fetch_app_users(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, username, display_name, role, is_active, created_at, updated_at, last_login
               FROM app_users
               ORDER BY lower(username)"""
        )
        return cursor.fetchall()


    def active_admin_count(self, exclude_user_id=None):
        cursor = self.conn.cursor()
        if exclude_user_id is None:
            cursor.execute("SELECT COUNT(*) FROM app_users WHERE role='admin' AND COALESCE(is_active, 1)=1")
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM app_users WHERE role='admin' AND COALESCE(is_active, 1)=1 AND id<>?",
                (exclude_user_id,),
            )
        return cursor.fetchone()[0]


    def show_user_management_dialog(self):
        if not self.require_user_admin():
            return

        dialog, content = self.create_dialog("Uživatelé a role", 960, 590, 820, 480)
        self.create_dialog_header(
            content,
            "Uživatelé a role",
            "Správa přístupů do aplikace. Administrátor spravuje nastavení, editor upravuje data, čtenář pouze prohlíží.",
            accent="#dc2626",
        )

        tree_frame = tk.Frame(content, bg=self.COLORS["panel"])
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("username", "display_name", "role", "active", "last_login")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for key, label, width in (
            ("username", "Uživatel", 150),
            ("display_name", "Jméno", 210),
            ("role", "Role", 130),
            ("active", "Stav", 90),
            ("last_login", "Poslední přihlášení", 160),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        def refresh():
            tree.delete(*tree.get_children())
            for user_id, username, display_name, role, is_active, _created, _updated, last_login in self.fetch_app_users():
                tree.insert(
                    "",
                    tk.END,
                    iid=str(user_id),
                    values=(
                        username,
                        display_name or "",
                        self.role_display_name(role),
                        "Aktivní" if is_active else "Neaktivní",
                        last_login or "",
                    ),
                )

        def selected_user_id():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Uživatelé a role", "Vyberte uživatele ze seznamu.", parent=dialog)
                return None
            return int(selection[0])

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(16, 0))
        self.create_button(actions, "Nový uživatel", lambda: self.show_user_form(parent_dialog=dialog, refresh_callback=refresh), "primary").pack(side=tk.LEFT)
        self.create_button(actions, "Upravit", lambda: self.show_user_form(selected_user_id(), dialog, refresh), "secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(actions, "Reset hesla", lambda: self.show_user_password_reset(selected_user_id(), dialog, refresh), "secondary").pack(side=tk.LEFT, padx=(8, 0))

        def toggle_active():
            user_id = selected_user_id()
            if not user_id:
                return
            cursor = self.conn.cursor()
            cursor.execute("SELECT username, role, is_active FROM app_users WHERE id=?", (user_id,))
            row = cursor.fetchone()
            if not row:
                refresh()
                return
            username, role, is_active = row
            if is_active and self.normalize_role(role) == "admin" and self.active_admin_count(exclude_user_id=user_id) <= 0:
                messagebox.showwarning("Uživatelé a role", "Nelze deaktivovat posledního aktivního administrátora.", parent=dialog)
                return
            new_state = 0 if is_active else 1
            self.conn.execute("UPDATE app_users SET is_active=?, updated_at=? WHERE id=?", (new_state, datetime.now().isoformat(timespec="seconds"), user_id))
            self.commit_database()
            refresh()
            messagebox.showinfo("Uživatelé a role", f"Uživatel {username} byl {'aktivován' if new_state else 'deaktivován'}.", parent=dialog)

        self.create_button(actions, "Aktivovat / deaktivovat", toggle_active, "secondary").pack(side=tk.LEFT, padx=(8, 0))
        self.create_button(actions, "Zavřít", dialog.destroy, "secondary").pack(side=tk.RIGHT)
        tree.bind("<Double-1>", lambda _event: self.show_user_form(selected_user_id(), dialog, refresh))
        refresh()


    def show_user_form(self, user_id=None, parent_dialog=None, refresh_callback=None):
        if not self.require_user_admin():
            return

        record = None
        if user_id:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, username, display_name, role, is_active FROM app_users WHERE id=?", (user_id,))
            record = cursor.fetchone()
            if not record:
                messagebox.showwarning("Uživatelé a role", "Vybraný uživatel už neexistuje.", parent=parent_dialog)
                if refresh_callback:
                    refresh_callback()
                return

        dialog, content = self.create_dialog("Uživatel", 560, 460, 500, 400, modal=True)
        if parent_dialog is not None:
            dialog.transient(parent_dialog)
        self.create_dialog_header(
            content,
            "Upravit uživatele" if user_id else "Nový uživatel",
            "Role Administrátor spravuje aplikaci, Editor upravuje data, Čtenář data pouze prohlíží.",
        )

        username_var = tk.StringVar(value=record[1] if record else "")
        display_var = tk.StringVar(value=record[2] if record else "")
        role_values = ("Administrátor", "Editor", "Čtenář")
        role_to_code = {"Administrátor": "admin", "Editor": "editor", "Čtenář": "reader"}
        code_to_role = {value: key for key, value in role_to_code.items()}
        role_var = tk.StringVar(value=code_to_role.get(self.normalize_role(record[3] if record else "reader"), "Čtenář"))
        active_var = tk.BooleanVar(value=bool(record[4]) if record else True)
        password_var = tk.StringVar()
        confirm_var = tk.StringVar()

        form = tk.Frame(content, bg=self.COLORS["panel"])
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        def row(label, widget, index):
            tk.Label(form, text=label, bg=self.COLORS["panel"], fg=self.COLORS["text"], font=(self.FONT, 10, "bold")).grid(row=index, column=0, sticky="w", padx=(0, 12), pady=(0, 10))
            widget.grid(row=index, column=1, sticky="ew", pady=(0, 10), ipady=3)

        row("Uživatel", ttk.Entry(form, textvariable=username_var, font=(self.FONT, 10)), 0)
        row("Jméno", ttk.Entry(form, textvariable=display_var, font=(self.FONT, 10)), 1)
        row("Role", ttk.Combobox(form, textvariable=role_var, values=role_values, state="readonly", font=(self.FONT, 10)), 2)
        row("Heslo" + ("" if not user_id else " (volitelně)"), ttk.Entry(form, textvariable=password_var, show="*", font=(self.FONT, 10)), 3)
        row("Potvrzení hesla", ttk.Entry(form, textvariable=confirm_var, show="*", font=(self.FONT, 10)), 4)
        ttk.Checkbutton(form, text="Aktivní účet", variable=active_var).grid(row=5, column=1, sticky="w", pady=(0, 10))

        actions = tk.Frame(content, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(12, 0))

        def save():
            username = username_var.get().strip()
            display_name = display_var.get().strip()
            role_code = role_to_code.get(role_var.get(), "reader")
            password = password_var.get()
            confirm = confirm_var.get()
            if not username:
                messagebox.showwarning("Uživatelé a role", "Vyplňte uživatelské jméno.", parent=dialog)
                return
            if not user_id and not password:
                messagebox.showwarning("Uživatelé a role", "Vyplňte heslo nového uživatele.", parent=dialog)
                return
            if password or confirm:
                if password != confirm:
                    messagebox.showwarning("Uživatelé a role", "Heslo a potvrzení se neshodují.", parent=dialog)
                    return
                if len(password) < 6:
                    messagebox.showwarning("Uživatelé a role", "Heslo musí mít alespoň 6 znaků.", parent=dialog)
                    return
            if user_id and self.normalize_role(record[3]) == "admin" and (role_code != "admin" or not active_var.get()) and self.active_admin_count(exclude_user_id=user_id) <= 0:
                messagebox.showwarning("Uživatelé a role", "Nelze odebrat nebo deaktivovat posledního aktivního administrátora.", parent=dialog)
                return

            now = datetime.now().isoformat(timespec="seconds")
            try:
                if user_id:
                    if password:
                        salt, password_hash = self.hash_password(password)
                        self.conn.execute(
                            """UPDATE app_users
                               SET username=?, display_name=?, role=?, password_salt=?, password_hash=?,
                                   is_active=?, updated_at=?
                               WHERE id=?""",
                            (username, display_name, role_code, salt, password_hash, 1 if active_var.get() else 0, now, user_id),
                        )
                    else:
                        self.conn.execute(
                            """UPDATE app_users
                               SET username=?, display_name=?, role=?, is_active=?, updated_at=?
                               WHERE id=?""",
                            (username, display_name, role_code, 1 if active_var.get() else 0, now, user_id),
                        )
                else:
                    salt, password_hash = self.hash_password(password)
                    self.conn.execute(
                        """INSERT INTO app_users
                           (username, display_name, role, password_salt, password_hash, is_active, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (username, display_name, role_code, salt, password_hash, 1 if active_var.get() else 0, now, now),
                    )
                self.commit_database()
            except sqlite3.IntegrityError:
                messagebox.showwarning("Uživatelé a role", "Uživatel se stejným jménem už existuje.", parent=dialog)
                return

            if refresh_callback:
                refresh_callback()
            dialog.destroy()

        self.create_button(actions, "Uložit", save, "primary").pack(side=tk.RIGHT)
        self.create_button(actions, "Zrušit", dialog.destroy, "secondary").pack(side=tk.RIGHT, padx=(0, 8))


    def show_user_password_reset(self, user_id, parent_dialog=None, refresh_callback=None):
        if not user_id or not self.require_user_admin():
            return
        cursor = self.conn.cursor()
        cursor.execute("SELECT username FROM app_users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        if not row:
            messagebox.showwarning("Uživatelé a role", "Vybraný uživatel už neexistuje.", parent=parent_dialog)
            return
        self.show_user_form(user_id=user_id, parent_dialog=parent_dialog, refresh_callback=refresh_callback)


    def show_data_settings(self):
        dialog, content = self.create_dialog("Data a zálohy", 980, 500, 820, 420)
        self.data_settings_dialog = dialog
        dialog.protocol(
            "WM_DELETE_WINDOW",
            lambda: (setattr(self, "data_settings_dialog", None), dialog.destroy()),
        )
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
            state=tk.NORMAL,
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

        second_actions = tk.Frame(content, bg=self.COLORS["panel"])
        second_actions.pack(fill=tk.X, pady=(12, 0))
        self.create_button(
            second_actions,
            text="Otestovat připojení",
            command=self.test_current_database_connection,
            variant="secondary",
            state=tk.NORMAL,
        ).pack(side=tk.LEFT)
        self.create_button(
            second_actions,
            text="Kompletní ZIP záloha",
            command=self.create_complete_backup,
            variant="primary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            second_actions,
            text="Import starých aplikací",
            command=self.import_legacy_applications,
            variant="secondary",
            state=tk.NORMAL if self.can_edit() else tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.create_button(
            second_actions,
            text="Synchronizovat školení",
            command=self.sync_integrated_records,
            variant="secondary",
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
                "Aplikace používá společnou SQLite databázi, centrální registr školení a kompletní ZIP zálohy.",
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
        self.create_button(
            actions,
            text="Historie verzí",
            command=self.show_release_history,
            variant="secondary",
        ).pack(side=tk.LEFT)
        self.create_button(
            actions,
            text="Aktualizace",
            command=self.check_for_updates,
            variant="primary",
        ).pack(side=tk.LEFT, padx=(10, 0))


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

