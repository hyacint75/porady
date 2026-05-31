# -*- coding: utf-8 -*-

import os
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from porady_widgets import RoundedFrame


class DialogMixin:

    def open_folder(self, path):
        try:
            os.startfile(path)
        except OSError as error:
            messagebox.showwarning("Otevřít složku", f"Složku se nepodařilo otevřít:\n{error}")


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


    def create_dialog_header(self, parent, title, subtitle=None, right_widget=None):
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

        separator = tk.Frame(parent, height=1, bg=self.COLORS["border"])
        separator.pack(fill=tk.X, pady=(0, 18))
        return header


    def show_data_settings(self):
        dialog, content = self.create_dialog("Data a zálohy", 720, 350, 580, 300)
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
            text="Zavřít",
            command=dialog.destroy,
            variant="secondary",
        ).pack(side=tk.RIGHT)


    def show_about(self):
        dialog, content = self.create_dialog("O aplikaci", 600, 330, 520, 280)
        self.create_dialog_header(
            content,
            f"Správce porad {self.APP_VERSION}",
            "Aplikace pro evidenci porad, bodů programu, úkolů, odpovědností, termínů a zápisů.",
        )

        self.create_path_row(content, "Databáze", self.db_path, lambda: self.open_folder(self.db_path.parent))
        self.create_path_row(content, "Zálohy", self.backup_dir, lambda: self.open_folder(self.backup_dir))

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

