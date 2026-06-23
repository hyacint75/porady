# -*- coding: utf-8 -*-

import configparser
import hashlib
import hmac
import html
import os
import secrets
import shutil
import sqlite3
import sys
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from porady_data import DataMixin
from porady_dialogs import DialogMixin
from porady_enhancements import EnhancementMixin
from porady_export import ExportMixin
from porady_orders import OrderMixin
from porady_progress import ProgressMixin
from porady_problems import ProblemMixin
from porady_requirements import RequirementMixin
from porady_tasks import TaskOverviewMixin
from porady_agenda import AgendaMixin
from porady_layout import LayoutMixin
from porady_meetings import MeetingMixin
from porady_schema import SchemaMixin
from porady_suite import SuiteMixin


class MeetingApp(DataMixin, SchemaMixin, DialogMixin, EnhancementMixin, OrderMixin, RequirementMixin, ProblemMixin, TaskOverviewMixin, ProgressMixin, ExportMixin, LayoutMixin, MeetingMixin, AgendaMixin, SuiteMixin):
    APP_VERSION = "4.85"
    APP_DIR_NAME = "Porady"
    DB_FILENAME = "porady.db"
    CONFIG_FILENAME = "porady_config.ini"
    BACKUP_DIR_NAME = "backups"
    LOGO_FILENAME = "svos_logo.png"

    COLORS = {
        "app_bg": "#eef2f6",
        "sidebar": "#182433",
        "sidebar_muted": "#9fb0c3",
        "panel": "#ffffff",
        "panel_soft": "#f8fafc",
        "border": "#d7dee8",
        "text": "#17202a",
        "muted": "#667085",
        "primary": "#2563eb",
        "primary_dark": "#1d4ed8",
        "danger": "#dc2626",
        "danger_dark": "#b91c1c",
        "success": "#15803d",
        "warning": "#f59e0b",
        "selection": "#dbeafe",
        "page_info": "#f0f9ff",
        "page_info_accent": "#0284c7",
        "page_meeting": "#f8fafc",
        "page_meeting_accent": "#2563eb",
        "page_progress": "#f0fdf4",
        "page_progress_accent": "#15803d",
        "page_tasks_accent": "#7c3aed",
        "page_orders_accent": "#dc2626",
        "page_requirements_accent": "#d97706",
        "page_problems_accent": "#0f766e",
    }

    FONT = "Segoe UI"
    CZECH_MONTHS = (
        "",
        "leden",
        "únor",
        "březen",
        "duben",
        "květen",
        "červen",
        "červenec",
        "srpen",
        "září",
        "říjen",
        "listopad",
        "prosinec",
    )

    def __init__(self, root):
        self.root = root
        self.root.title(f"Správce porad {self.APP_VERSION}")
        self.root.geometry("1080x760")
        self.root.minsize(920, 640)
        self.root.state("zoomed")
        self.root.configure(bg=self.COLORS["app_bg"])

        self.configure_styles()

        # Připojení k databázi
        self.app_data_dir = self.get_app_data_dir()
        self.config_path = self.find_config_path()
        self.prepare_data_paths()
        self.conn = self.connect_initial_database()
        self.create_tables()
        self.is_admin = False
        self.current_user = None
        self.current_user_role = "reader"
        self.current_user_display = "Uživatel"

        self.current_id = None
        self.current_agenda_data = []  # Ukládá řádky zobrazené v agendě
        self.all_agenda_data = []
        self.progress_data = []
        self.owner_progress_data = []
        self.progress_total = {"done": 0, "total": 0}
        self.show_open_only = tk.BooleanVar(value=False)
        self.active_point_id = None
        self.suppress_agenda_select_event = False
        self.editing_point_id = None
        self.editing_item_id = None
        self.notes_dirty = False
        self.meeting_search_var = tk.StringVar()
        self.show_archived_meetings = tk.BooleanVar(value=False)
        self.logo_image = self.load_logo_image()
        self.porady_workspace_loaded = False

        self.create_layout()
        self.initialize_suite()
        self.show_launcher_home()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)


    def show_login_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Přihlášení")
        dialog.geometry("420x250")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLORS["app_bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        result = {"admin": False}
        password_var = tk.StringVar()

        panel = tk.Frame(dialog, bg=self.COLORS["panel"], padx=24, pady=22)
        panel.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        tk.Label(
            panel,
            text="Přihlášení",
            font=(self.FONT, 16, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
        ).pack(fill=tk.X)

        tk.Label(
            panel,
            text="Zadejte heslo admina, nebo pokračujte jen pro čtení.",
            font=(self.FONT, 10),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
            wraplength=350,
        ).pack(fill=tk.X, pady=(6, 14))

        password_entry = ttk.Entry(panel, textvariable=password_var, show="*", font=(self.FONT, 10))
        password_entry.pack(fill=tk.X, ipady=3)

        actions = tk.Frame(panel, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, pady=(20, 0))

        def login_admin():
            admin_password = self.get_admin_password()
            if not admin_password:
                messagebox.showwarning(
                    "Přihlášení",
                    "Admin heslo není nastavené. Doplňte ho v porady_config.ini nebo v proměnné PORADY_ADMIN_PASSWORD.",
                )
                return
            if password_var.get() == admin_password:
                result["admin"] = True
                dialog.destroy()
                return
            messagebox.showwarning("Přihlášení", "Nesprávné heslo admina.")
            password_entry.focus_set()
            password_entry.select_range(0, tk.END)

        def login_user():
            result["admin"] = False
            dialog.destroy()

        admin_button = tk.Button(
            actions,
            text="Potvrdit heslo",
            command=login_admin,
            bg=self.COLORS["primary"],
            fg="white",
            activebackground=self.COLORS["primary_dark"],
            activeforeground="white",
            font=(self.FONT, 10, "bold"),
            width=16,
            padx=18,
            pady=12,
            cursor="hand2",
            relief=tk.FLAT,
            borderwidth=0,
        )
        admin_button.pack(side=tk.LEFT)
        admin_button.bind("<Enter>", lambda event: admin_button.config(bg=self.COLORS["primary_dark"]))
        admin_button.bind("<Leave>", lambda event: admin_button.config(bg=self.COLORS["primary"]))

        user_button = tk.Label(
            actions,
            text="Jen čtení",
            bg="#e6edf7",
            fg=self.COLORS["text"],
            font=(self.FONT, 10),
            width=14,
            padx=18,
            pady=14,
            cursor="hand2",
        )
        user_button.pack(side=tk.RIGHT)
        user_button.bind("<Button-1>", lambda event: login_user())
        user_button.bind("<Enter>", lambda event: user_button.config(bg="#d7e3f3"))
        user_button.bind("<Leave>", lambda event: user_button.config(bg="#e6edf7"))

        password_entry.bind("<Return>", lambda event: login_admin())
        dialog.protocol("WM_DELETE_WINDOW", login_user)
        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + max((self.root.winfo_width() - 420) // 2, 0)
        y = self.root.winfo_rooty() + max((self.root.winfo_height() - 250) // 2, 0)
        dialog.geometry(f"420x250+{x}+{y}")
        password_entry.focus_set()
        self.root.wait_window(dialog)
        return result["admin"]


    def normalize_role(self, role):
        normalized = str(role or "reader").strip().lower()
        if normalized in {"admin", "administrator", "administrátor"}:
            return "admin"
        if normalized in {"editor", "edit", "úpravy", "upravy"}:
            return "editor"
        return "reader"


    def role_display_name(self, role):
        return {
            "admin": "Administrátor",
            "editor": "Editor",
            "reader": "Čtenář",
        }.get(self.normalize_role(role), "Čtenář")


    def hash_password(self, password, salt=None):
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 200000)
        return salt, digest.hex()


    def verify_password_hash(self, password, salt, stored_hash):
        if not salt or not stored_hash:
            return False
        _salt, calculated_hash = self.hash_password(password, salt)
        return hmac.compare_digest(calculated_hash, stored_hash)


    def authenticate_app_user(self, username, password):
        username = str(username or "").strip()
        if not username or not password:
            return None
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, username, display_name, role, password_salt, password_hash, is_active
               FROM app_users
               WHERE lower(username)=lower(?)""",
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        user_id, stored_username, display_name, role, salt, password_hash, is_active = row
        if not is_active or not self.verify_password_hash(password, salt, password_hash):
            return None
        self.conn.execute("UPDATE app_users SET last_login=datetime('now') WHERE id=?", (user_id,))
        self.commit_database()
        return {
            "id": user_id,
            "username": stored_username,
            "display_name": display_name or stored_username,
            "role": self.normalize_role(role),
        }


    def set_current_user(self, username=None, display_name=None, role="reader"):
        self.current_user = username
        self.current_user_role = self.normalize_role(role)
        self.current_user_display = display_name or username or "Uživatel"
        self.is_admin = self.current_user_role in {"admin", "editor"}


    def refresh_permission_state(self):
        if hasattr(self, "lbl_user_role"):
            self.lbl_user_role.config(text=self.get_role_text())
        if hasattr(self, "btn_login"):
            self.btn_login.config(text="Odhlásit" if self.can_edit() else "Přihlásit")
        if hasattr(self, "btn_admin_top"):
            self.btn_admin_top.config(text="Odhlásit" if self.can_edit() else "Admin")
        change_window = getattr(self, "change_management_window", None)
        if change_window is not None and change_window.winfo_exists():
            change_window.update_permission_state()
        job_window = getattr(self, "job_evaluation_window", None)
        if job_window is not None and job_window.winfo_exists():
            job_window.update_permission_state()
        self.apply_permission_state()


    def can_edit(self):
        return self.current_user_role in {"admin", "editor"} or bool(self.is_admin)


    def can_manage_users(self):
        return self.current_user_role == "admin" or bool(self.is_admin and self.current_user is None)


    def require_admin(self):
        if self.can_edit():
            return True
        messagebox.showwarning("Jen pro čtení", "Úpravy může provádět pouze přihlášený administrátor nebo editor.")
        return False


    def require_user_admin(self):
        if self.can_manage_users():
            return True
        messagebox.showwarning("Administrace", "Správu uživatelů může provádět pouze administrátor.")
        return False


    def set_admin_mode(self, enabled):
        if not enabled and self.can_edit() and getattr(self, "current_id", None) and getattr(self, "notes_dirty", False):
            self.save_notes(show_message=False)
        self.set_current_user(None, "Administrátor" if enabled else "Uživatel", "admin" if enabled else "reader")
        self.refresh_permission_state()


    def get_role_text(self):
        if self.current_user:
            return f"{self.current_user_display} - {self.role_display_name(self.current_user_role)}"
        return "Admin - úpravy povoleny" if self.can_edit() else "Uživatel - jen čtení"


    def ask_admin_password(self, error_message=""):
        dialog = tk.Toplevel(self.root)
        dialog.title("Přihlášení admina")
        dialog.geometry("480x360")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLORS["app_bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        result = {"password": None}
        password_var = tk.StringVar()

        panel = tk.Frame(
            dialog,
            bg=self.COLORS["panel"],
            padx=26,
            pady=24,
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
        )
        panel.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(panel, bg=self.COLORS["panel"])
        header.pack(fill=tk.X)

        badge = tk.Label(
            header,
            text="ADMIN",
            font=(self.FONT, 9, "bold"),
            bg=self.COLORS["selection"],
            fg=self.COLORS["primary"],
            padx=10,
            pady=4,
        )
        badge.pack(anchor="w", pady=(0, 10))

        tk.Label(
            header,
            text="Přihlášení admina",
            font=(self.FONT, 18, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
        ).pack(fill=tk.X)

        tk.Label(
            header,
            text="Zadejte heslo pro povolení úprav v aplikacích.",
            font=(self.FONT, 10),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
            wraplength=380,
        ).pack(fill=tk.X, pady=(5, 18))

        password_entry = ttk.Entry(panel, textvariable=password_var, show="*", font=(self.FONT, 11))
        password_entry.pack(fill=tk.X, ipady=5)

        error_label = tk.Label(
            panel,
            text=error_message,
            font=(self.FONT, 9),
            bg=self.COLORS["panel"],
            fg=self.COLORS["danger"],
            anchor="w",
        )
        error_label.pack(fill=tk.X, pady=(8, 0))

        actions = tk.Frame(panel, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(22, 0))

        def confirm():
            password = password_var.get()
            if not password:
                error_label.config(text="Zadejte heslo admina.")
                password_entry.focus_set()
                return
            result["password"] = password
            dialog.destroy()

        def cancel():
            result["password"] = None
            dialog.destroy()

        self.create_button(
            actions,
            text="Potvrdit heslo",
            command=confirm,
            variant="primary",
        ).pack(side=tk.RIGHT)
        self.create_button(actions, text="Zrušit", command=cancel, variant="secondary").pack(side=tk.RIGHT, padx=(0, 10))

        password_entry.bind("<Return>", lambda event: confirm())
        password_entry.bind("<Escape>", lambda event: cancel())
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        self.center_dialog(dialog, 480, 360)
        password_entry.focus_set()
        self.root.wait_window(dialog)
        return result["password"]


    def toggle_admin_login(self):
        if self.can_edit():
            self.set_admin_mode(False)
            return

        has_users = self.conn.execute("SELECT COUNT(*) FROM app_users WHERE COALESCE(is_active, 1)=1").fetchone()[0] > 0
        if has_users:
            self.show_user_login_dialog()
            return

        admin_password = self.get_admin_password()
        if not admin_password:
            messagebox.showwarning(
                "Přihlášení",
                "Admin heslo není nastavené. Doplňte ho v porady_config.ini nebo v proměnné PORADY_ADMIN_PASSWORD.",
            )
            return

        error_message = ""
        while True:
            password = self.ask_admin_password(error_message)
            if password is None:
                return
            if password == admin_password:
                self.set_admin_mode(True)
                return
            error_message = "Nesprávné heslo admina."


    def show_user_login_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Přihlášení uživatele")
        dialog.geometry("500x390")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLORS["app_bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        username_var = tk.StringVar()
        password_var = tk.StringVar()
        result = {"user": None}

        panel = tk.Frame(
            dialog,
            bg=self.COLORS["panel"],
            padx=26,
            pady=24,
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
        )
        panel.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        tk.Label(
            panel,
            text="Přihlášení uživatele",
            font=(self.FONT, 18, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            panel,
            text="Zadejte uživatelské jméno a heslo. Role určuje dostupná oprávnění.",
            font=(self.FONT, 10),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
            wraplength=400,
        ).pack(fill=tk.X, pady=(5, 18))

        tk.Label(panel, text="Uživatel", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).pack(anchor="w")
        username_entry = ttk.Entry(panel, textvariable=username_var, font=(self.FONT, 11))
        username_entry.pack(fill=tk.X, pady=(4, 12), ipady=4)
        tk.Label(panel, text="Heslo", font=(self.FONT, 10, "bold"), bg=self.COLORS["panel"], fg=self.COLORS["text"]).pack(anchor="w")
        password_entry = ttk.Entry(panel, textvariable=password_var, show="*", font=(self.FONT, 11))
        password_entry.pack(fill=tk.X, pady=(4, 8), ipady=4)
        error_label = tk.Label(panel, text="", font=(self.FONT, 9), bg=self.COLORS["panel"], fg=self.COLORS["danger"], anchor="w")
        error_label.pack(fill=tk.X)

        actions = tk.Frame(panel, bg=self.COLORS["panel"])
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(20, 0))

        def confirm():
            user = self.authenticate_app_user(username_var.get(), password_var.get())
            if not user:
                error_label.config(text="Neplatné uživatelské jméno nebo heslo.")
                password_entry.focus_set()
                password_entry.select_range(0, tk.END)
                return
            result["user"] = user
            self.set_current_user(user["username"], user["display_name"], user["role"])
            self.refresh_permission_state()
            dialog.destroy()

        def cancel():
            dialog.destroy()

        self.create_button(actions, text="Přihlásit", command=confirm, variant="primary").pack(side=tk.RIGHT)
        self.create_button(actions, text="Zrušit", command=cancel, variant="secondary").pack(side=tk.RIGHT, padx=(0, 10))
        username_entry.bind("<Return>", lambda _event: password_entry.focus_set())
        password_entry.bind("<Return>", lambda _event: confirm())
        dialog.bind("<Escape>", lambda _event: cancel())
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        self.center_dialog(dialog, 500, 390)
        username_entry.focus_set()
        self.root.wait_window(dialog)
        return result["user"]


def run():
    root = tk.Tk()
    MeetingApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()

