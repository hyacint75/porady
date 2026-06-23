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
        if app_config.exists():
            return app_config
        if runtime_config.exists():
            return runtime_config
        return app_config


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

        return self.get_app_data_dir(create=True)


    def get_local_database_path(self):
        return self.get_app_data_dir(create=True) / self.DB_FILENAME


    def is_local_database(self, database_path=None):
        path = Path(database_path or self.db_path)
        return self.paths_match(path, self.get_local_database_path())


    def paths_match(self, first_path, second_path):
        try:
            return first_path.resolve() == second_path.resolve()
        except OSError:
            return first_path.absolute() == second_path.absolute()


    def migrate_legacy_database(self, target_path):
        if target_path.exists():
            return None

        runtime_dir = self.get_runtime_dir()
        candidates = (
            runtime_dir / self.DB_FILENAME,
            runtime_dir / "dist" / self.DB_FILENAME,
            runtime_dir.parent / self.DB_FILENAME,
            runtime_dir.parent / "dist" / self.DB_FILENAME,
            Path.cwd() / self.DB_FILENAME,
            Path.cwd() / "dist" / self.DB_FILENAME,
        )
        legacy_paths = []
        for path in candidates:
            if (
                path.exists()
                and not self.paths_match(path, target_path)
                and not any(self.paths_match(path, known) for known in legacy_paths)
            ):
                legacy_paths.append(path)

        if legacy_paths:
            newest_path = max(legacy_paths, key=lambda path: path.stat().st_mtime)
            shutil.copy2(newest_path, target_path)
            return newest_path

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
        self.database_fallback_active = False
        self.unavailable_database_path = None
        try:
            self.data_dir = self.get_central_data_dir()
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = self.prepare_database_path()
            self.backup_dir = self.prepare_backup_dir()
        except OSError as error:
            failed_path = self.get_configured_path("database_path") or getattr(self, "data_dir", "")
            if not self.activate_local_database_fallback(failed_path, error):
                raise SystemExit(1) from error


    def activate_local_database_fallback(self, failed_path, error):
        self.unavailable_database_path = Path(failed_path) if failed_path else None
        self.database_fallback_active = True
        self.data_dir = self.get_app_data_dir(create=True)
        self.db_path = self.get_local_database_path()
        self.backup_dir = self.data_dir / self.BACKUP_DIR_NAME
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        return True


    def connect_initial_database(self):
        try:
            connection = sqlite3.connect(self.db_path, timeout=30)
            self.configure_database_connection(connection)
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
            return connection
        except (OSError, sqlite3.Error) as error:
            try:
                connection.close()
            except (UnboundLocalError, sqlite3.Error):
                pass

            if self.is_local_database() or not self.activate_local_database_fallback(self.db_path, error):
                raise SystemExit(1) from error

            try:
                connection = sqlite3.connect(self.db_path, timeout=30)
                self.configure_database_connection(connection)
                return connection
            except (OSError, sqlite3.Error) as local_error:
                messagebox.showerror(
                    "Místní databáze",
                    f"Nepodařilo se otevřít ani místní databázi:\n{local_error}",
                )
                raise SystemExit(1) from local_error


    def configure_database_connection(self, connection=None):
        connection = connection or self.conn
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")


    def test_database_path(self, database_path):
        database_path = Path(database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path, timeout=5)
        try:
            connection.execute("PRAGMA busy_timeout = 5000")
            result = connection.execute("PRAGMA quick_check").fetchone()
            if not result or str(result[0]).lower() != "ok":
                raise sqlite3.DatabaseError(f"Kontrola databáze: {result[0] if result else 'bez výsledku'}")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS __porady_connection_test "
                "(id INTEGER PRIMARY KEY, checked_at TEXT)"
            )
            connection.execute(
                "INSERT INTO __porady_connection_test (checked_at) VALUES (datetime('now'))"
            )
            connection.rollback()
        finally:
            connection.close()


    def switch_database(self, database_path):
        selected_path = Path(database_path).resolve()
        self.test_database_path(selected_path)

        if self.paths_match(selected_path, self.db_path):
            self.database_fallback_active = False
            self.unavailable_database_path = None
            self.write_database_config(selected_path)
            self.update_database_status()
            return

        if self.current_id and self.notes_dirty:
            self.save_notes(show_message=False)

        old_connection = self.conn
        old_path = self.db_path
        old_data_dir = self.data_dir
        old_backup_dir = self.backup_dir
        launcher_visible = (
            getattr(self, "launcher_home_frame", None) is not None
            and self.launcher_home_frame.winfo_exists()
            and self.launcher_home_frame.winfo_ismapped()
        )
        new_connection = sqlite3.connect(selected_path, timeout=30)

        try:
            self.configure_database_connection(new_connection)
            self.conn = new_connection
            self.db_path = selected_path
            self.data_dir = selected_path.parent
            self.backup_dir = selected_path.parent / self.BACKUP_DIR_NAME
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.create_tables()
            self.write_database_config(selected_path)
        except (OSError, sqlite3.Error, configparser.Error):
            new_connection.close()
            self.conn = old_connection
            self.db_path = old_path
            self.data_dir = old_data_dir
            self.backup_dir = old_backup_dir
            raise

        quality_window = getattr(self, "quality_window", None)
        if quality_window is not None and quality_window.winfo_exists():
            quality_window.destroy()
            self.quality_window = None

        old_connection.close()
        self.database_fallback_active = False
        self.unavailable_database_path = None
        self.current_id = None
        self.notes_dirty = False

        self.sync_integrated_records()
        self.refresh_item_description_choices()
        self.refresh_owner_choices()
        self.refresh_due_date_choices()
        if getattr(self, "porady_workspace_loaded", False):
            self.load_meetings()
            self.refresh_dashboard_summary()
        self.update_database_status()
        if launcher_visible:
            self.show_launcher_home()


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
        if not config.has_section("data"):
            config.add_section("data")
        config["data"]["database_path"] = str(database_path)
        config["data"]["backup_dir_path"] = str(database_path.parent / self.BACKUP_DIR_NAME)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as handle:
            config.write(handle)
        self.data_config = config

