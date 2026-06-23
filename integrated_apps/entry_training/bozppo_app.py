# -*- coding: utf-8 -*-

import datetime as dt
import os
import tkinter as tk
import webbrowser
from tkinter import messagebox

from .bozppo_config import APP_TITLE, CERTIFICATES_DIR, HANDOVER_FILE, RESULTS_FILE, TRAINING_CONTENT_FILE
from .bozppo_content import QUESTIONS, TRAINING_SECTIONS, build_test_questions, ensure_training_content_file
from .bozppo_handover import HandoverMixin
from .bozppo_html import HtmlExportMixin
from .bozppo_results import TrainingResultsMixin
from .bozppo_risks import RiskBuilderMixin
from .bozppo_settings import load_app_settings, save_app_settings
from .bozppo_storage import prepare_data_storage
from .bozppo_ui import TrainingAppUiMixin


class TrainingApp(
    TrainingAppUiMixin,
    TrainingResultsMixin,
    HandoverMixin,
    RiskBuilderMixin,
    HtmlExportMixin,
    tk.Toplevel,
):
    def __init__(self, master=None, on_home=None, on_data_changed=None):
        super().__init__(master)
        self.on_home = on_home
        self.on_data_changed = on_data_changed
        prepare_data_storage()
        self.app_settings = load_app_settings()
        self.title(APP_TITLE)
        self.geometry("980x700")
        self.minsize(860, 620)
        if master is not None:
            self.transient(master.winfo_toplevel())

        self.test_questions = build_test_questions()
        self.training_sections = list(TRAINING_SECTIONS)
        self.answers = [tk.IntVar(value=-1) for _ in self.test_questions]
        self.worker_name = tk.StringVar()
        self.company_name = tk.StringVar()
        self.trainer_name = tk.StringVar(value=self.app_settings.get("trainer_name", ""))
        self.last_certificate_path = None
        self.overview_search = tk.StringVar()
        self.overview_result_filter = tk.StringVar(value="Vše")
        self.overview_validity_filter = tk.StringVar(value="Vše")
        self.overview_summary = tk.StringVar(value="Zatím nejsou načtené žádné záznamy.")
        self.logo_image = None
        self.handover_workplace = tk.StringVar()
        self.handover_location = tk.StringVar(value=self.app_settings.get("handover_location", ""))
        self.handover_customer = tk.StringVar(value=self.app_settings.get("handover_customer", "SVOS"))
        self.handover_company = tk.StringVar()
        self.handover_work_from = tk.StringVar(value=dt.date.today().strftime("%d.%m.%Y"))
        self.handover_work_to = tk.StringVar()
        self.handover_handed_by = tk.StringVar()
        self.handover_taken_by = tk.StringVar()
        self.handover_template = tk.StringVar(value="Obecné práce")
        self.last_handover_path = None
        self.handover_overview_summary = tk.StringVar(value="Zatím nejsou načtená žádná předání pracoviště.")
        self.topic_title = tk.StringVar()
        self.risk_document_title = tk.StringVar(value="Samostatná rizika pracoviště")
        self.risk_workplace = tk.StringVar()
        self.risk_company = tk.StringVar()
        self.risk_handover_date = tk.StringVar(value=dt.date.today().strftime("%d.%m.%Y"))
        self.risk_handed_by = tk.StringVar()
        self.risk_taken_by = tk.StringVar()
        self.last_risks_path = None

        self._configure_style()
        self._build_suite_toolbar()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - self.winfo_width()) // 2)
        y = max(0, (screen_height - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")
        self.lift()
        self.focus_force()

    def _build_suite_toolbar(self):
        toolbar = tk.Frame(self, bg="#182433", padx=14, pady=9)
        toolbar.pack(fill=tk.X)
        tk.Button(
            toolbar,
            text="← Rozcestník",
            command=self._return_home,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief=tk.FLAT,
            padx=16,
            pady=7,
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            toolbar,
            text=APP_TITLE,
            bg="#182433",
            fg="white",
            font=("Segoe UI", 11, "bold"),
        ).pack(side=tk.LEFT, padx=16)

    def _return_home(self):
        self.destroy()
        if self.on_home:
            self.on_home()

    def notify_data_changed(self):
        if self.on_data_changed:
            self.on_data_changed()

    def save_current_defaults(self):
        self.app_settings.update(
            {
                "trainer_name": self.trainer_name.get().strip(),
                "handover_customer": self.handover_customer.get().strip() or "SVOS",
                "handover_location": self.handover_location.get().strip(),
            }
        )
        save_app_settings(self.app_settings)
        messagebox.showinfo("Nastavení uloženo", "Výchozí údaje byly uloženy pro další spuštění aplikace.")

    def open_training_content_file(self):
        content_file = ensure_training_content_file()
        try:
            os.startfile(content_file)
        except OSError as error:
            try:
                webbrowser.open(content_file.as_uri())
            except OSError:
                messagebox.showerror(
                    "Soubor nelze otevřít",
                    f"Nepodařilo se otevřít soubor:\n{content_file}\n\n{error}",
                )



if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = TrainingApp(root)
    app.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
