# -*- coding: utf-8 -*-

import configparser
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from tkinter import messagebox


class DataMixin:

    def get_app_data_dir(self, create=False):
        if os.name == "nt":
            base_dir = os.environ.get("APPDATA")
            app_dir = Path(base_dir) / self.APP_DIR_NAME if base_dir else Path.home() / self.APP_DIR_NAME
        else:
            base_dir = os.environ.get("XDG_DATA_HOME")
            app_dir = Path(base_dir) / self.APP_DIR_NAME if base_dir else Path.home() / ".local" / "share" / self.APP_DIR_NAME

        if create:
            app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir


    def get_runtime_dir(self):
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent


    def find_config_path(self):
        runtime_config = self.get_runtime_dir() / self.CONFIG_FILENAME
        app_config = self.app_data_dir / self.CONFIG_FILENAME
        if runtime_config.exists():
            return runtime_config
        if app_config.exists():
            return app_config
        return runtime_config


    def read_data_config(self):
        config = configparser.ConfigParser()
        if not self.config_path.exists():
            return config

        config.read(self.config_path, encoding="utf-8")
        return config


    def expand_config_path(self, raw_path):
        if not raw_path:
            return None

        expanded = os.path.expandvars(raw_path)
        return Path(expanded).expanduser()


    def get_configured_path(self, option_name):
        raw_path = self.data_config.get("data", option_name, fallback="").strip()
        if self.is_example_config_path(raw_path):
            return None
        return self.expand_config_path(raw_path)


    def is_example_config_path(self, raw_path):
        normalized_path = (raw_path or "").strip().replace("/", "\\").lower()
        return normalized_path.startswith("\\\\server\\sdilene\\porady")


    def get_admin_password(self):
        configured_password = self.data_config.get("security", "admin_password", fallback="").strip()
        if configured_password:
            return configured_password
        return os.environ.get("PORADY_ADMIN_PASSWORD", "").strip()


    def get_central_data_dir(self):
        configured_data_dir = self.get_configured_path("data_dir")
        if configured_data_dir:
            return configured_data_dir

        configured_database_path = self.get_configured_path("database_path")
        if configured_database_path:
            return configured_database_path.parent

        return self.get_runtime_dir()


    def paths_match(self, first_path, second_path):
        try:
            return first_path.resolve() == second_path.resolve()
        except OSError:
            return first_path.absolute() == second_path.absolute()


    def migrate_legacy_database(self, target_path):
        legacy_paths = [
            self.app_data_dir / self.DB_FILENAME,
            Path.cwd() / self.DB_FILENAME,
        ]

        for legacy_path in legacy_paths:
            if target_path.exists() or not legacy_path.exists() or self.paths_match(legacy_path, target_path):
                continue
            shutil.copy2(legacy_path, target_path)
            return legacy_path

        return None


    def prepare_database_path(self):
        configured_path = self.get_configured_path("database_path")
        target_path = configured_path if configured_path else self.data_dir / self.DB_FILENAME
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate_legacy_database(target_path)

        return target_path


    def prepare_backup_dir(self):
        configured_path = self.get_configured_path("backup_dir_path")
        backup_dir = configured_path if configured_path else self.data_dir / self.BACKUP_DIR_NAME
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir


    def prepare_data_paths(self):
        self.data_config = self.read_data_config()
        try:
            self.data_dir = self.get_central_data_dir()
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = self.prepare_database_path()
            self.backup_dir = self.prepare_backup_dir()
        except OSError as error:
            messagebox.showerror(
                "Datová složka",
                "Datovou složku nebo databázi se nepodařilo připravit.\n\n"
                f"Cesta: {getattr(self, 'data_dir', '')}\n"
                f"Chyba: {error}\n\n"
                "Zkontrolujte prosím porady_config.ini vedle aplikace.",
            )
            raise SystemExit(1) from error


    def configure_database_connection(self):
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.conn.execute("PRAGMA journal_mode = DELETE")
        self.conn.execute("PRAGMA synchronous = FULL")


    def commit_database(self):
        try:
            self.conn.commit()
            return True
        except sqlite3.OperationalError as error:
            if "locked" in str(error).lower() or "busy" in str(error).lower():
                self.conn.rollback()
                messagebox.showwarning(
                    "Databáze je používána",
                    "Databázi právě používá jiný uživatel. Zkuste akci za chvíli zopakovat.",
                )
                return False
            raise


    def create_database_backup(self, reason):
        if not self.db_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_reason = "".join(char for char in reason if char.isalnum() or char in ("-", "_")).strip("_")
        backup_path = self.backup_dir / f"porady_{timestamp}_{safe_reason or 'backup'}.db"
        shutil.copy2(self.db_path, backup_path)
        return backup_path


    def backup_before_delete(self, reason):
        try:
            if self.current_id and self.notes_dirty:
                self.save_notes(show_message=False)
            self.create_database_backup(reason)
            return True
        except OSError as error:
            messagebox.showerror("Záloha", f"Zálohu databáze se nepodařilo vytvořit:\n{error}")
            return False


    def write_database_config(self, database_path):
        config = self.read_data_config()
        config["data"] = {
            "database_path": str(database_path),
            "backup_dir_path": str(database_path.parent / self.BACKUP_DIR_NAME),
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as handle:
            config.write(handle)

