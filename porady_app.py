# -*- coding: utf-8 -*-

import configparser
import html
import os
import shutil
import sqlite3
import sys
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from porady_data import DataMixin
from porady_dialogs import DialogMixin
from porady_enhancements import EnhancementMixin
from porady_export import ExportMixin
from porady_orders import OrderMixin
from porady_progress import ProgressMixin
from porady_requirements import RequirementMixin
from porady_tasks import TaskOverviewMixin
from porady_agenda import AgendaMixin
from porady_layout import LayoutMixin
from porady_meetings import MeetingMixin
from porady_schema import SchemaMixin


class MeetingApp(DataMixin, SchemaMixin, DialogMixin, EnhancementMixin, OrderMixin, RequirementMixin, TaskOverviewMixin, ProgressMixin, ExportMixin, LayoutMixin, MeetingMixin, AgendaMixin):
    APP_VERSION = "4.47"
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
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.configure_database_connection()
        self.create_tables()
        self.is_admin = self.show_login_dialog()

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

        self.create_layout()
        self.refresh_item_description_choices()
        self.refresh_owner_choices()
        self.refresh_due_date_choices()
        self.load_meetings()
        self.root.after(700, self.show_startup_reminders)
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

        admin_button = tk.Label(
            actions,
            text="Přihlásit",
            bg=self.COLORS["primary"],
            fg="white",
            font=(self.FONT, 10, "bold"),
            width=14,
            padx=18,
            pady=14,
            cursor="hand2",
        )
        admin_button.pack(side=tk.LEFT)
        admin_button.bind("<Button-1>", lambda event: login_admin())
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


    def can_edit(self):
        return bool(self.is_admin)


    def require_admin(self):
        if self.can_edit():
            return True
        messagebox.showwarning("Jen pro čtení", "Úpravy může provádět pouze přihlášený admin.")
        return False


    def set_admin_mode(self, enabled):
        if not enabled and self.can_edit() and getattr(self, "current_id", None) and getattr(self, "notes_dirty", False):
            self.save_notes(show_message=False)
        self.is_admin = enabled
        if hasattr(self, "lbl_user_role"):
            self.lbl_user_role.config(text=self.get_role_text())
        if hasattr(self, "btn_login"):
            self.btn_login.config(text="Odhlásit admina" if self.can_edit() else "Přihlásit admina")
        self.apply_permission_state()


    def get_role_text(self):
        return "Admin - úpravy povoleny" if self.can_edit() else "Uživatel - jen čtení"


    def toggle_admin_login(self):
        if self.can_edit():
            self.set_admin_mode(False)
            return

        password = simpledialog.askstring("Přihlášení admina", "Zadejte heslo admina:", show="*")
        if password is None:
            return
        admin_password = self.get_admin_password()
        if not admin_password:
            messagebox.showwarning(
                "Přihlášení",
                "Admin heslo není nastavené. Doplňte ho v porady_config.ini nebo v proměnné PORADY_ADMIN_PASSWORD.",
            )
            return
        if password == admin_password:
            self.set_admin_mode(True)
        else:
            messagebox.showwarning("Přihlášení", "Nesprávné heslo admina.")


def run():
    root = tk.Tk()
    MeetingApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()

