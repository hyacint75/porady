# -*- coding: utf-8 -*-

import getpass
import sys
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from porady_widgets import RoundedFrame, bind_mousewheel_to_canvas


class LayoutMixin:

    def configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(
            "TEntry",
            fieldbackground="white",
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["border"],
            darkcolor=self.COLORS["border"],
            padding=8,
        )
        self.style.configure("TNotebook", background=self.COLORS["panel"], borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(14, 8), font=(self.FONT, 10))
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.COLORS["selection"])],
            foreground=[("selected", self.COLORS["primary"])],
        )
        self.general_info_font = tkfont.Font(family=self.FONT, size=10)
        self.general_info_invalid_font = tkfont.Font(family=self.FONT, size=10, overstrike=1)


    def on_close(self):
        workspace_open = (
            hasattr(self, "left_frame")
            and self.left_frame.winfo_exists()
            and self.left_frame.winfo_ismapped()
        )
        if workspace_open:
            if self.can_edit() and self.current_id and self.notes_dirty:
                self.save_notes(show_message=False)
            self.show_launcher_home()
            return
        self.conn.close()
        self.root.destroy()


    def resource_path(self, filename):
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base_path / filename


    def load_logo_image(self):
        logo_path = self.resource_path(self.LOGO_FILENAME)
        if not logo_path.exists():
            return None

        try:
            image = tk.PhotoImage(file=str(logo_path))
            max_width = 210
            if image.width() > max_width:
                factor = max(1, (image.width() + max_width - 1) // max_width)
                image = image.subsample(factor, factor)
            return image
        except tk.TclError:
            return None


    def create_layout(self):
        self.create_database_status_bar()

        self.left_frame = tk.Frame(self.root, width=310, bg=self.COLORS["sidebar"])
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)

        self.right_frame = tk.Frame(self.root, bg=self.COLORS["app_bg"], padx=24, pady=24)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.create_sidebar()
        self.create_detail_panel()


    def create_database_status_bar(self):
        self.database_status_bar = tk.Frame(
            self.root,
            bg="#e2e8f0",
            height=30,
            padx=12,
            pady=5,
            cursor="hand2",
        )
        self.database_status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.database_status_bar.pack_propagate(False)
        self.lbl_database_status = tk.Label(
            self.database_status_bar,
            text="",
            font=(self.FONT, 9, "bold"),
            bg="#e2e8f0",
            fg=self.COLORS["text"],
            anchor="w",
            cursor="hand2",
        )
        self.lbl_database_status.pack(fill=tk.X)
        self.database_status_bar.bind("<Button-1>", lambda _event: self.show_data_settings())
        self.lbl_database_status.bind("<Button-1>", lambda _event: self.show_data_settings())
        self.update_database_status()


    def update_database_status(self):
        if not hasattr(self, "lbl_database_status"):
            return

        if getattr(self, "database_fallback_active", False):
            label = "MÍSTNÍ NÁHRADNÍ DB"
            background = "#fef3c7"
            foreground = "#92400e"
        elif self.is_local_database():
            label = "MÍSTNÍ DB"
            background = "#dcfce7"
            foreground = "#166534"
        else:
            label = "SDÍLENÁ DB"
            background = "#dbeafe"
            foreground = "#1d4ed8"

        text = f"{label}  |  {self.db_path}"
        self.database_status_bar.config(bg=background)
        self.lbl_database_status.config(text=text, bg=background, fg=foreground)


    def show_launcher_home(self):
        if hasattr(self, "left_frame"):
            self.left_frame.pack_forget()
        if hasattr(self, "right_frame"):
            self.right_frame.pack_forget()
        if (
            hasattr(self, "launcher_home_shell")
            and self.launcher_home_shell is not None
            and self.launcher_home_shell.winfo_exists()
        ):
            self.launcher_home_shell.destroy()
        elif (
            hasattr(self, "launcher_home_frame")
            and self.launcher_home_frame is not None
            and self.launcher_home_frame.winfo_exists()
        ):
            self.launcher_home_frame.destroy()
        self.launcher_home_shell = None
        self.launcher_canvas = None
        self.launcher_scrollbar = None
        self.launcher_home_frame = None
        self.root.configure(bg=self.COLORS["app_bg"])
        self.root.title(f"Rozcestník aplikací {self.APP_VERSION}")
        portal_bg = "#f8fafc"
        self.root.configure(bg=portal_bg)
        self.launcher_home_shell = tk.Frame(self.root, bg=portal_bg)
        self.launcher_home_shell.pack(fill=tk.BOTH, expand=True)
        self.launcher_canvas = tk.Canvas(
            self.launcher_home_shell,
            bg=portal_bg,
            highlightthickness=0,
            borderwidth=0,
        )
        self.launcher_scrollbar = ttk.Scrollbar(
            self.launcher_home_shell,
            orient=tk.VERTICAL,
            command=self.launcher_canvas.yview,
        )
        self.launcher_canvas.configure(yscrollcommand=self.launcher_scrollbar.set)
        self.launcher_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.launcher_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.launcher_home_frame = tk.Frame(self.launcher_canvas, bg=portal_bg, padx=52, pady=28)
        self.launcher_window_id = self.launcher_canvas.create_window(
            (0, 0),
            window=self.launcher_home_frame,
            anchor="nw",
        )
        self.launcher_home_frame.bind(
            "<Configure>",
            lambda _event: self.launcher_canvas.configure(scrollregion=self.launcher_canvas.bbox("all")),
        )
        self.launcher_canvas.bind(
            "<Configure>",
            lambda event: self.launcher_canvas.itemconfigure(self.launcher_window_id, width=event.width),
        )

        header = tk.Frame(self.launcher_home_frame, bg=portal_bg)
        header.pack(fill=tk.X)
        brand = tk.Frame(header, bg=portal_bg)
        brand.grid(row=0, column=0, sticky="nw")
        header.columnconfigure(0, weight=1, uniform="launcher_header")
        header.columnconfigure(1, weight=1, uniform="launcher_header")
        header.columnconfigure(2, weight=1, uniform="launcher_header")
        if getattr(self, "logo_image", None):
            tk.Label(brand, image=self.logo_image, bg=portal_bg).pack(anchor="w")
        else:
            tk.Label(brand, text="SVOS", font=(self.FONT, 26, "bold"), bg=portal_bg, fg="#111827").pack(anchor="w")
        tk.Label(
            brand,
            text="Organizace: SVOS, spol. s r.o.",
            font=(self.FONT, 11),
            bg=portal_bg,
            fg="#334155",
        ).pack(anchor="w", pady=(18, 0))

        clock_panel = tk.Frame(header, bg=portal_bg)
        clock_panel.grid(row=0, column=1, sticky="n")
        self.launcher_clock_time_var = tk.StringVar(value="")
        self.launcher_clock_date_var = tk.StringVar(value="")
        tk.Label(
            clock_panel,
            textvariable=self.launcher_clock_time_var,
            font=("Consolas", 40, "bold"),
            bg=portal_bg,
            fg="#020617",
        ).pack(anchor="center")
        tk.Label(
            clock_panel,
            textvariable=self.launcher_clock_date_var,
            font=(self.FONT, 10, "bold"),
            bg=portal_bg,
            fg="#475569",
        ).pack(anchor="center", pady=(2, 0))
        self.update_launcher_clock()

        header_actions = tk.Frame(header, bg=portal_bg)
        header_actions.grid(row=0, column=2, sticky="ne")
        for text, command, color in (
            ("...", self.show_virtual_assistant, "#3557ff"),
            ("!", self.show_global_deadlines, "#3557ff"),
            ("●", self.toggle_admin_login, "#3557ff"),
            ("⚙", self.show_app_launcher_dialog, "#3557ff"),
            ("↪", self.show_porady_workspace, "#e11d48"),
        ):
            action = tk.Label(
                header_actions,
                text=text,
                width=2,
                font=(self.FONT, 19 if text == "⚙" else 18, "bold"),
                bg=portal_bg,
                fg=color,
                cursor="hand2",
            )
            action.pack(side=tk.LEFT, padx=(16, 0))
            action.bind("<Button-1>", lambda _event, callback=command: callback())

        summary = self.get_launcher_dashboard_summary()
        suite_summary = self.get_suite_dashboard_summary()

        tk.Label(
            self.launcher_home_frame,
            text="Přehled modulů",
            font=(self.FONT, 15, "bold"),
            bg=portal_bg,
            fg="#020617",
        ).pack(anchor="w", pady=(20, 20))

        modules = (
            {
                "title": "Porady a zápisy",
                "description": "Hlavní agenda porad, zápisů, bodů jednání a navazujících úkolů.",
                "icon": "▣",
                "accent": "#ea580c",
                "soft": "#fff8ed",
                "badges": (("Otevřené úkoly", str(summary["open_tasks"]), "#dff5f5"),),
                "command": self.show_porady_workspace,
            },
            {
                "title": "Virtuální asistent",
                "description": "Chat nad firemními daty, poradami a integrovanými aplikacemi.",
                "icon": "✦",
                "accent": "#8a00ff",
                "soft": "#f5e8ff",
                "badges": (("Aktivní chaty", "0", "#ead7ff"),),
                "command": self.show_virtual_assistant,
            },
            {
                "title": "Globální hledání",
                "description": "Vyhledávání napříč poradami, úkoly, požadavky, opatřeními a aplikacemi.",
                "icon": "⌕",
                "accent": "#3557ff",
                "soft": "#eef4ff",
                "badges": (),
                "command": self.show_global_search,
            },
            {
                "title": "Požadavky",
                "description": "Evidence požadavků z porad, jejich stav, odpovědnost a plnění.",
                "icon": "✓",
                "accent": "#d97706",
                "soft": "#fff7ed",
                "badges": (("Otevřené požadavky", str(summary["open_requirements"]), "#fff0d8"),),
                "command": self.show_requirements_application,
            },
            {
                "title": "Problémy a opatření",
                "description": "Řešení problémů, nápravná opatření, termíny a vazby na kvalitu.",
                "icon": "!",
                "accent": "#0f766e",
                "soft": "#eefffd",
                "badges": (("Otevřené problémy", str(summary["open_problems"]), "#dff5f5"), ("Po termínu", str(suite_summary["corrective_overdue"]), "#fde8df")),
                "command": self.show_problems_application,
            },
            {
                "title": "Měsíční vyhodnocení kvality",
                "description": "Měsíční souhrny kvality, reklamace, neshody, rizika a opatření.",
                "icon": "Q",
                "accent": "#1f4e78",
                "soft": "#f1f6ff",
                "badges": (("Vyhodnocení", str(suite_summary["quality"]), "#e6ebff"),),
                "command": self.show_quality_application,
            },
            {
                "title": "Vyhodnocení zakázky",
                "description": "Hodnocení zakázek podle financí, hodin, termínu, kvality a dodání.",
                "icon": "▭",
                "accent": "#0e7490",
                "soft": "#ecfeff",
                "badges": (("Záznamy", str(suite_summary["job_evaluations"]), "#dff5f5"),),
                "command": self.show_job_evaluation_application,
            },
            {
                "title": "Změnové řízení",
                "description": "Změnové podněty, posouzení, rozhodnutí a sledování realizace.",
                "icon": "Z",
                "accent": "#4f46e5",
                "soft": "#eef2ff",
                "badges": (("Podněty", str(suite_summary["change_requests"]), "#e6ebff"), ("K posouzení", str(suite_summary["change_pending"]), "#fff0d8")),
                "command": self.show_change_management_application,
            },
            {
                "title": "Společné termíny",
                "description": "Souhrn otevřených termínů z úkolů, nařízení, požadavků a opatření.",
                "icon": "▦",
                "accent": "#8a00ff",
                "soft": "#f8f0ff",
                "badges": (("Aktivních záznamů", str(summary["open_tasks"] + summary["open_orders"] + summary["open_requirements"]), "#ead7ff"),),
                "command": self.show_global_deadlines,
            },
            {
                "title": "Souhrnné exporty",
                "description": "Exporty a přehledy dat z porad i připojených agend.",
                "icon": "⌁",
                "accent": "#16803d",
                "soft": "#ecfff5",
                "badges": (),
                "command": self.show_suite_exports,
            },
            {
                "title": "Administrace",
                "description": "Správa admin režimu, rozcestníku, databáze, záloh a provozních kontrol.",
                "icon": "A",
                "accent": "#dc2626",
                "soft": "#fff1f2",
                "badges": (("Režim", "Admin" if self.can_edit() else "Jen čtení", "#fee2e2" if self.can_edit() else "#e6ebff"),),
                "command": self.show_admin_launcher,
            },
            {
                "title": "Školení externích firem",
                "description": "Integrovaná evidence školení a testů pro externí společnosti.",
                "icon": "E",
                "accent": "#b45309",
                "soft": "#fff7ed",
                "badges": (("Záznamy školení", str(suite_summary["trainings"]), "#fff0d8"),),
                "command": self.show_external_companies_application,
            },
            {
                "title": "Školení zaměstnanců",
                "description": "Integrovaná agenda vstupního školení zaměstnanců a výsledků testů.",
                "icon": "V",
                "accent": "#047857",
                "soft": "#ecfff5",
                "badges": (("Předání pracovišť", str(suite_summary["handovers"]), "#e4f4e9"),),
                "command": self.show_entry_training_application,
            },
        )

        module_grid = tk.Frame(self.launcher_home_frame, bg=portal_bg)
        module_grid.pack(fill=tk.BOTH, expand=True)
        for column in range(3):
            module_grid.columnconfigure(column, weight=1, uniform="portal_modules")
        for index, module in enumerate(modules):
            row, column = divmod(index, 3)
            self.create_portal_module_card(module_grid, module, row, column)

        bind_mousewheel_to_canvas(self.launcher_canvas, self.launcher_home_frame)


    def create_portal_module_card(self, parent, module, row, column):
        card = RoundedFrame(
            parent,
            radius=12,
            background="#ffffff",
            border="#d9dee7",
            border_width=1,
            padding=0,
            height=162,
            bg=parent.cget("bg"),
            cursor="hand2",
        )
        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=(0, 16 if column < 2 else 0),
            pady=(0, 16),
        )
        inner = card.inner
        inner.configure(bg="#ffffff", padx=18, pady=18, cursor="hand2")

        icon_box = tk.Frame(inner, bg=module["soft"], width=56, height=56, cursor="hand2")
        icon_box.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 18))
        icon_box.grid_propagate(False)
        tk.Label(
            icon_box,
            text=module["icon"],
            font=(self.FONT, 25, "bold"),
            bg=module["soft"],
            fg=module["accent"],
            cursor="hand2",
        ).place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(
            inner,
            text=module["title"],
            font=(self.FONT, 11, "bold"),
            bg="#ffffff",
            fg="#020617",
            anchor="w",
            cursor="hand2",
        )
        title.grid(row=0, column=1, sticky="ew", padx=(0, 16))

        dots = tk.Label(
            inner,
            text="⋮",
            font=(self.FONT, 17, "bold"),
            bg="#ffffff",
            fg="#0f3f69",
            cursor="hand2",
        )
        dots.grid(row=0, column=2, sticky="ne")

        description = tk.Label(
            inner,
            text=module["description"],
            font=(self.FONT, 10),
            bg="#ffffff",
            fg="#334155",
            anchor="nw",
            justify=tk.LEFT,
            wraplength=260,
            cursor="hand2",
        )
        description.grid(row=1, column=1, columnspan=2, sticky="new", pady=(10, 0))

        badges_frame = tk.Frame(inner, bg="#ffffff", cursor="hand2")
        badges_frame.grid(row=2, column=1, columnspan=2, sticky="sw", pady=(14, 0))
        for label, value, color in module["badges"]:
            badge = tk.Label(
                badges_frame,
                text=f"{label}: {value}",
                font=(self.FONT, 10, "bold"),
                bg=color,
                fg="#334155",
                padx=12,
                pady=4,
                cursor="hand2",
            )
            badge.pack(side=tk.LEFT, padx=(0, 8))

        inner.columnconfigure(1, weight=1)
        inner.rowconfigure(1, weight=1)

        def bind_click(widget):
            widget.bind("<Button-1>", lambda _event, callback=module["command"]: callback())
            widget.bind("<Enter>", lambda _event: card.configure(cursor="hand2"))
            for child in widget.winfo_children():
                bind_click(child)

        bind_click(card)


    def scroll_launcher_home(self, event):
        canvas = getattr(self, "launcher_canvas", None)
        if canvas is not None and canvas.winfo_exists():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


    def show_admin_launcher(self):
        self.show_admin_dashboard()


    def update_launcher_clock(self):
        clock_var = getattr(self, "launcher_clock_time_var", None)
        date_var = getattr(self, "launcher_clock_date_var", None)
        shell = getattr(self, "launcher_home_shell", None)
        if clock_var is None or date_var is None or shell is None or not shell.winfo_exists():
            return

        now = datetime.now()
        clock_var.set(now.strftime("%H:%M:%S"))
        date_var.set(now.strftime("%d.%m.%Y"))
        shell.after(1000, self.update_launcher_clock)


    def show_porady_workspace(self):
        self.root.unbind_all("<MouseWheel>")
        if (
            hasattr(self, "launcher_home_shell")
            and self.launcher_home_shell is not None
            and self.launcher_home_shell.winfo_exists()
        ):
            self.launcher_home_shell.destroy()
        self.launcher_home_frame = None
        self.launcher_home_shell = None
        if hasattr(self, "left_frame") and not self.left_frame.winfo_ismapped():
            self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        if hasattr(self, "right_frame") and not self.right_frame.winfo_ismapped():
            self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.root.title(f"Správce porad {self.APP_VERSION}")
        if not getattr(self, "porady_workspace_loaded", False):
            self.refresh_item_description_choices()
            self.refresh_owner_choices()
            self.refresh_due_date_choices()
            self.load_meetings()
            self.porady_workspace_loaded = True


    def show_requirements_application(self):
        self.show_launcher_home()
        self.show_requirement_overview(
            standalone=True,
            close_callback=self.show_launcher_home,
        )


    def show_requirements_tab(self):
        if hasattr(self, "detail_tabs") and hasattr(self, "requirements_tab"):
            self.detail_tabs.select(self.requirements_tab)
            if hasattr(self, "requirement_tab_refresh"):
                self.requirement_tab_refresh()


    def show_tasks_tab(self):
        if hasattr(self, "detail_tabs") and hasattr(self, "tasks_tab"):
            self.detail_tabs.select(self.tasks_tab)
            if hasattr(self, "task_tab_refresh"):
                self.task_tab_refresh()


    def show_orders_tab(self):
        if hasattr(self, "detail_tabs") and hasattr(self, "orders_tab"):
            self.detail_tabs.select(self.orders_tab)
            if hasattr(self, "order_tab_refresh"):
                self.order_tab_refresh()


    def show_problems_tab(self):
        if hasattr(self, "detail_tabs") and hasattr(self, "problems_tab"):
            self.detail_tabs.select(self.problems_tab)
            if hasattr(self, "problem_tab_refresh"):
                self.problem_tab_refresh()


    def show_problems_application(self):
        self.show_launcher_home()
        self.show_problem_overview(
            standalone=True,
            close_callback=self.show_launcher_home,
        )

    def show_quality_application(self):
        from porady_quality import QualityApp

        current_window = getattr(self, "quality_window", None)
        if current_window is not None and current_window.winfo_exists():
            current_window.deiconify()
            current_window.lift()
            current_window.focus_force()
            return

        self.quality_window = QualityApp(
            self.root,
            connection=self.conn,
            commit_callback=self.commit_database,
            on_home=self.show_launcher_home,
        )

        def close_quality():
            self.quality_window.destroy()
            self.quality_window = None
            self.show_launcher_home()

        self.quality_window.protocol("WM_DELETE_WINDOW", close_quality)
        self.quality_window.focus_set()

    def show_change_management_application(self):
        from porady_changes import ChangeManagementApp

        current_window = getattr(self, "change_management_window", None)
        if current_window is not None and current_window.winfo_exists():
            current_window.deiconify()
            current_window.lift()
            current_window.focus_force()
            return

        self.change_management_window = ChangeManagementApp(
            self.root,
            connection=self.conn,
            commit_callback=self.commit_database,
            can_edit_callback=self.can_edit,
            require_admin_callback=self.require_admin,
            toggle_admin_callback=self.toggle_admin_login,
            on_home=self.show_launcher_home,
            colors=self.COLORS,
            font=self.FONT,
        )

        def close_change_management():
            self.change_management_window.destroy()
            self.change_management_window = None
            self.show_launcher_home()

        self.change_management_window.protocol("WM_DELETE_WINDOW", close_change_management)
        self.change_management_window.focus_set()

    def show_job_evaluation_application(self):
        from porady_job_evaluation import JobEvaluationApp

        current_window = getattr(self, "job_evaluation_window", None)
        if current_window is not None and current_window.winfo_exists():
            current_window.deiconify()
            current_window.lift()
            current_window.focus_force()
            return

        self.job_evaluation_window = JobEvaluationApp(
            self.root,
            connection=self.conn,
            commit_callback=self.commit_database,
            can_edit_callback=self.can_edit,
            require_admin_callback=self.require_admin,
            toggle_admin_callback=self.toggle_admin_login,
            on_home=self.show_launcher_home,
            colors=self.COLORS,
            font=self.FONT,
        )

        def close_job_evaluation():
            self.job_evaluation_window.destroy()
            self.job_evaluation_window = None
            self.show_launcher_home()

        self.job_evaluation_window.protocol("WM_DELETE_WINDOW", close_job_evaluation)
        self.job_evaluation_window.focus_set()

    def show_virtual_assistant(self):
        from porady_assistant import VirtualAssistant

        current_window = getattr(self, "virtual_assistant_window", None)
        if current_window is not None and current_window.winfo_exists():
            current_window.deiconify()
            current_window.lift()
            current_window.focus_force()
            return

        self.virtual_assistant_window = VirtualAssistant(
            self.root,
            collect_search_rows=self._collect_search_rows,
            open_search_result=self._open_global_search_result,
            collect_deadlines=self._collect_deadlines,
            app_actions={
                "meetings": self.show_porady_workspace,
                "requirements": self.show_requirements_application,
                "problems": self.show_problems_application,
                "quality": self.show_quality_application,
                "change_management": self.show_change_management_application,
                "job_evaluation": self.show_job_evaluation_application,
                "external_companies": self.show_external_companies_application,
                "entry_training": self.show_entry_training_application,
            },
            on_home=self.show_launcher_home,
            colors=self.COLORS,
            font=self.FONT,
        )

        def close_assistant():
            self.virtual_assistant_window.destroy()
            self.virtual_assistant_window = None
            self.show_launcher_home()

        self.virtual_assistant_window.protocol("WM_DELETE_WINDOW", close_assistant)
        self.virtual_assistant_window.focus_set()


    def get_my_owner_value(self):
        username = getpass.getuser().strip().lower()
        for person in self.get_people_values():
            if person.strip().lower() == username:
                return person
        return ""


    def create_sidebar(self):
        header_frame = tk.Frame(self.left_frame, bg=self.COLORS["sidebar"], padx=20, pady=22)
        header_frame.pack(fill=tk.X)

        tk.Label(
            header_frame,
            text="Porady",
            font=(self.FONT, 22, "bold"),
            bg=self.COLORS["sidebar"],
            fg="white",
        ).pack(anchor="w")
        tk.Label(
            header_frame,
            text="Přehled schůzek a úkolů",
            font=(self.FONT, 10),
            bg=self.COLORS["sidebar"],
            fg=self.COLORS["sidebar_muted"],
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            header_frame,
            text=f"Verze {self.APP_VERSION}",
            font=(self.FONT, 9),
            bg=self.COLORS["sidebar"],
            fg=self.COLORS["sidebar_muted"],
        ).pack(anchor="w", pady=(8, 0))
        self.lbl_user_role = tk.Label(
            header_frame,
            text=self.get_role_text(),
            font=(self.FONT, 9, "bold"),
            bg=self.COLORS["sidebar"],
            fg="#dbeafe" if self.can_edit() else self.COLORS["sidebar_muted"],
        )
        self.lbl_user_role.pack(anchor="w", pady=(4, 0))

        search_frame = tk.Frame(self.left_frame, bg=self.COLORS["sidebar"], padx=16)
        search_frame.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            search_frame,
            text="Hledat poradu",
            font=(self.FONT, 9, "bold"),
            bg=self.COLORS["sidebar"],
            fg=self.COLORS["sidebar_muted"],
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 5))

        self.entry_meeting_search = tk.Entry(
            search_frame,
            textvariable=self.meeting_search_var,
            font=(self.FONT, 10),
            bg="#223247",
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.entry_meeting_search.pack(fill=tk.X, ipady=7)
        self.entry_meeting_search.bind("<KeyRelease>", lambda event: self.load_meetings())

        self.archive_check = tk.Checkbutton(
            search_frame,
            text="Zobrazit archiv",
            variable=self.show_archived_meetings,
            command=self.load_meetings,
            bg=self.COLORS["sidebar"],
            fg=self.COLORS["sidebar_muted"],
            activebackground=self.COLORS["sidebar"],
            activeforeground="white",
            selectcolor=self.COLORS["sidebar"],
            font=(self.FONT, 9),
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.archive_check.pack(anchor="w", pady=(8, 0))

        list_frame = tk.Frame(self.left_frame, bg=self.COLORS["sidebar"], padx=16)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.meeting_listbox = tk.Listbox(
            list_frame,
            font=(self.FONT, 10),
            bg="#223247",
            fg="#edf2f7",
            selectbackground=self.COLORS["primary"],
            selectforeground="white",
            activestyle="none",
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            exportselection=False,
        )
        self.meeting_listbox.pack(fill=tk.BOTH, expand=True)
        self.meeting_listbox.bind("<<ListboxSelect>>", self.on_select_meeting)

        self.lbl_meeting_count = tk.Label(
            list_frame,
            text="",
            font=(self.FONT, 9),
            bg=self.COLORS["sidebar"],
            fg=self.COLORS["sidebar_muted"],
            anchor="w",
        )
        self.lbl_meeting_count.pack(fill=tk.X, pady=(8, 0))

        actions_outer = tk.Frame(self.left_frame, bg=self.COLORS["sidebar"], padx=16)
        actions_outer.pack(fill=tk.X, pady=(0, 18))

        actions_canvas = tk.Canvas(
            actions_outer,
            height=320,
            bg=self.COLORS["sidebar"],
            highlightthickness=0,
            bd=0,
        )
        actions_scrollbar = ttk.Scrollbar(actions_outer, orient=tk.VERTICAL, command=actions_canvas.yview)
        actions_canvas.configure(yscrollcommand=actions_scrollbar.set)
        actions_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        actions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        sidebar_actions = tk.Frame(actions_canvas, bg=self.COLORS["sidebar"])
        actions_window = actions_canvas.create_window((0, 0), window=sidebar_actions, anchor="nw")

        def resize_actions(event):
            actions_canvas.itemconfigure(actions_window, width=event.width)

        def update_actions_scrollregion(event=None):
            actions_canvas.configure(scrollregion=actions_canvas.bbox("all"))

        def scroll_actions(event):
            actions_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def bind_actions_scroll(event=None):
            self.root.bind_all("<MouseWheel>", scroll_actions)

        def unbind_actions_scroll(event=None):
            self.root.unbind_all("<MouseWheel>")

        actions_canvas.bind("<Configure>", resize_actions)
        sidebar_actions.bind("<Configure>", update_actions_scrollregion)
        actions_outer.bind("<Enter>", bind_actions_scroll)
        actions_outer.bind("<Leave>", unbind_actions_scroll)

        self.btn_add_meeting = self.create_button(
            sidebar_actions,
            text="+ Nová porada",
            command=self.add_meeting,
            variant="primary",
        )
        self.btn_add_meeting.pack(fill=tk.X, pady=(0, 8))

        self.btn_copy = self.create_button(
            sidebar_actions,
            text="Kopírovat nevyřešené",
            command=self.copy_unresolved,
            variant="secondary",
        )
        self.btn_copy.pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Globální hledání",
            command=self.show_global_search,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Týdenní souhrn",
            command=self.show_weekly_summary,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Změny termínů",
            command=self.show_due_date_changes_overview,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Přehled podle osoby",
            command=self.show_person_overview,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Úkoly",
            command=self.show_tasks_tab,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Nařízení",
            command=self.show_orders_tab,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Tisk otevřených položek",
            command=self.export_open_items_overview,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="← Rozcestník",
            command=self.show_launcher_home,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.btn_people_manager = self.create_button(
            sidebar_actions,
            text="Odpovědnosti",
            command=self.show_people_manager,
            variant="secondary",
        )
        if self.can_edit():
            self.btn_people_manager.pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Požadavky",
            command=self.show_requirements_tab,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Opatření",
            command=self.show_problems_tab,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.btn_data_settings = self.create_button(
            sidebar_actions,
            text="Data a zálohy",
            command=self.show_data_settings,
            variant="secondary",
        )
        self.btn_data_settings.pack(fill=tk.X, pady=(0, 8))

        self.btn_login = self.create_button(
            sidebar_actions,
            text="Odhlásit admina" if self.can_edit() else "Přihlásit admina",
            command=self.toggle_admin_login,
            variant="secondary",
        )
        self.btn_login.pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="O aplikaci",
            command=self.show_about,
            variant="secondary",
        ).pack(fill=tk.X)


    def create_detail_panel(self):
        self.content_panel = RoundedFrame(
            self.right_frame,
            radius=16,
            background=self.COLORS["panel"],
            border=self.COLORS["border"],
            padding=24,
            bg=self.COLORS["app_bg"],
        )
        self.content_panel.pack(fill=tk.BOTH, expand=True)
        self.content = self.content_panel.inner

        title_row = tk.Frame(self.content, bg=self.COLORS["panel"])
        title_row.pack(fill=tk.X, pady=(0, 18))

        title_texts = tk.Frame(title_row, bg=self.COLORS["panel"])
        title_texts.pack(side=tk.LEFT, fill=tk.X, expand=True)

        if self.logo_image:
            logo_label = tk.Label(
                title_row,
                image=self.logo_image,
                bg=self.COLORS["panel"],
                borderwidth=0,
            )
            logo_label.pack(side=tk.RIGHT, padx=(18, 0))

        self.lbl_title = tk.Label(
            title_texts,
            text="Vyberte poradu ze seznamu",
            font=(self.FONT, 22, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
        )
        self.lbl_title.pack(fill=tk.X, anchor="w")

        self.lbl_subtitle = tk.Label(
            title_texts,
            text="Zápis a agenda se zobrazí po výběru porady.",
            font=(self.FONT, 10),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
        )
        self.lbl_subtitle.pack(fill=tk.X, anchor="w", pady=(3, 0))

        self.btn_edit_date = self.create_button(
            title_row,
            text="Změnit datum",
            command=self.edit_meeting_date,
            variant="secondary",
            state=tk.DISABLED,
        )
        self.btn_edit_date.pack(side=tk.RIGHT, padx=(16, 0))

        self.btn_admin_top = self.create_button(
            title_row,
            text="Odhlásit admina" if self.can_edit() else "Admin",
            command=self.toggle_admin_login,
            variant="secondary",
        )
        self.btn_admin_top.pack(side=tk.RIGHT, padx=(10, 0))

        self.dashboard_frame = tk.Frame(self.content, bg=self.COLORS["panel"])
        self.dashboard_frame.pack(fill=tk.X, pady=(0, 18))
        self.dashboard_labels = {}
        dashboard_items = (
            ("open_tasks", "Úkoly", self.COLORS["page_tasks_accent"], "tasks"),
            ("open_orders", "Nařízení", self.COLORS["page_orders_accent"], "orders"),
            ("open_requirements", "Požadavky", self.COLORS["page_requirements_accent"], "requirements"),
            ("open_problems", "Problémy", self.COLORS["page_problems_accent"], "problems"),
        )
        for column, (key, title, color, filter_type) in enumerate(dashboard_items):
            self.dashboard_frame.columnconfigure(column, weight=1, uniform="dashboard")
            tile = tk.Frame(
                self.dashboard_frame,
                bg=self.COLORS["panel_soft"],
                highlightthickness=1,
                highlightbackground=self.COLORS["border"],
                padx=12,
                pady=8,
                cursor="hand2",
            )
            tile.grid(row=0, column=column, sticky="ew", padx=(0, 8 if column < len(dashboard_items) - 1 else 0))
            accent = tk.Frame(tile, width=4, bg=color, cursor="hand2")
            accent.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
            text_frame = tk.Frame(tile, bg=self.COLORS["panel_soft"])
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            value_label = tk.Label(
                text_frame,
                text="0",
                font=(self.FONT, 16, "bold"),
                bg=self.COLORS["panel_soft"],
                fg=color,
                anchor="w",
                cursor="hand2",
            )
            value_label.pack(fill=tk.X)
            title_label = tk.Label(
                text_frame,
                text=title,
                font=(self.FONT, 9),
                bg=self.COLORS["panel_soft"],
                fg=self.COLORS["muted"],
                anchor="w",
                cursor="hand2",
            )
            title_label.pack(fill=tk.X)
            self.dashboard_labels[key] = value_label
            widgets = (tile, accent, text_frame, value_label, title_label)
            for widget in widgets:
                widget.bind("<Button-1>", lambda event, selected_filter=filter_type: self.show_dashboard_filter(selected_filter))
                widget.bind("<Enter>", lambda event, current_tile=tile: current_tile.config(bg="#eef4ff"))
                widget.bind("<Leave>", lambda event, current_tile=tile: current_tile.config(bg=self.COLORS["panel_soft"]))

        quick_filters = tk.Frame(self.content, bg=self.COLORS["panel"])
        quick_filters.pack(fill=tk.X, pady=(0, 14))
        for label, filter_type in (
            ("Dnes", "today"),
            ("Tento týden", "week"),
            ("Po termínu", "overdue"),
            ("Bez odpovědnosti", "no_owner"),
        ):
            self.create_button(
                quick_filters,
                text=label,
                command=lambda selected_filter=filter_type: self.show_open_items_overview(selected_filter),
                variant="secondary",
            ).pack(side=tk.LEFT, padx=(0, 8))

        self.detail_tabs = ttk.Notebook(self.content)
        self.detail_tabs.pack(fill=tk.BOTH, expand=True)
        self.detail_tabs.bind("<<NotebookTabChanged>>", self.on_detail_tab_changed)

        self.general_info_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["page_info"], padx=10, pady=14)
        self.meeting_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["page_meeting"], padx=10, pady=14)
        self.progress_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["page_progress"], padx=10, pady=14)
        self.tasks_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["panel"], padx=10, pady=14)
        self.orders_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["panel"], padx=10, pady=14)
        self.requirements_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["panel"], padx=10, pady=14)
        self.problems_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["panel"], padx=10, pady=14)
        self.calendar_tab = tk.Frame(self.detail_tabs, bg="#eef6ff", padx=10, pady=14)
        self.detail_tabs.add(self.general_info_tab, text="Všeobecné informace")
        self.detail_tabs.add(self.meeting_tab, text="Body programu")
        self.detail_tabs.add(self.progress_tab, text="Přehled plnění")
        self.detail_tabs.add(self.tasks_tab, text="Úkoly")
        self.detail_tabs.add(self.orders_tab, text="Nařízení")
        self.detail_tabs.add(self.requirements_tab, text="Požadavky")
        self.detail_tabs.add(self.problems_tab, text="Opatření")
        self.detail_tabs.add(self.calendar_tab, text="Kalendář")
        self.show_task_overview(parent=self.tasks_tab)
        self.show_order_overview(parent=self.orders_tab)
        self.show_requirement_overview(parent=self.requirements_tab)
        self.show_problem_overview(parent=self.problems_tab)

        self.create_page_accent(self.general_info_tab, self.COLORS["page_info_accent"])
        self.create_section_header(self.general_info_tab, "Všeobecné informace", self.COLORS["page_info_accent"])

        self.general_info_frame = tk.Frame(self.general_info_tab, bg=self.COLORS["page_info"])
        self.general_info_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 14))

        self.general_info_tree = ttk.Treeview(
            self.general_info_frame,
            columns=("created_at", "info"),
            show="headings",
            selectmode="browse",
        )
        self.general_info_tree.heading("created_at", text="Zadáno")
        self.general_info_tree.heading("info", text="Informace")
        self.general_info_tree.column("created_at", width=145, anchor="w", stretch=False)
        self.general_info_tree.column("info", width=680, anchor="w")
        self.general_info_tree.tag_configure("valid", foreground=self.COLORS["text"], font=self.general_info_font)
        self.general_info_tree.tag_configure("invalid", foreground=self.COLORS["muted"], font=self.general_info_invalid_font)
        self.general_info_scrollbar = ttk.Scrollbar(
            self.general_info_frame,
            orient=tk.VERTICAL,
            command=self.general_info_tree.yview,
        )
        self.general_info_tree.configure(yscrollcommand=self.general_info_scrollbar.set)
        self.general_info_tree.bind("<Double-1>", lambda event: self.edit_selected_general_info())
        self.general_info_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.general_info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.general_info_actions = tk.Frame(self.general_info_tab, bg=self.COLORS["page_info"])
        self.general_info_actions.pack(fill=tk.X)

        self.btn_add_general_info = self.create_button(
            self.general_info_actions,
            text="Nová informace",
            command=lambda: self.show_general_info_dialog(),
            variant="primary",
            state=tk.DISABLED,
        )
        self.btn_add_general_info.pack(side=tk.LEFT)

        self.btn_edit_general_info = self.create_button(
            self.general_info_actions,
            text="Upravit vybranou",
            command=self.edit_selected_general_info,
            variant="secondary",
            state=tk.DISABLED,
        )
        self.btn_edit_general_info.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_invalidate_general_info = self.create_button(
            self.general_info_actions,
            text="Zneplatnit vybranou",
            command=self.invalidate_selected_general_info,
            variant="secondary",
            state=tk.DISABLED,
        )
        self.btn_invalidate_general_info.pack(side=tk.LEFT, padx=(10, 0))

        self.text_notes = None

        self.create_page_accent(self.progress_tab, self.COLORS["page_progress_accent"])
        self.progress_scroll_canvas = tk.Canvas(
            self.progress_tab,
            bg=self.COLORS["page_progress"],
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        self.progress_scrollbar = ttk.Scrollbar(
            self.progress_tab,
            orient=tk.VERTICAL,
            command=self.progress_scroll_canvas.yview,
        )
        self.progress_scroll_canvas.configure(yscrollcommand=self.progress_scrollbar.set)
        self.progress_scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.progress_content = tk.Frame(
            self.progress_scroll_canvas,
            bg=self.COLORS["page_progress"],
        )
        self.progress_content_window = self.progress_scroll_canvas.create_window(
            (0, 0),
            window=self.progress_content,
            anchor="nw",
        )
        self.progress_content.bind(
            "<Configure>",
            lambda event: self.progress_scroll_canvas.configure(
                scrollregion=self.progress_scroll_canvas.bbox("all")
            ),
        )
        self.progress_scroll_canvas.bind(
            "<Configure>",
            lambda event: self.progress_scroll_canvas.itemconfigure(
                self.progress_content_window,
                width=event.width,
            ),
        )
        self.progress_scroll_canvas.bind(
            "<Enter>",
            lambda event: self.root.bind_all("<MouseWheel>", self.scroll_progress_overview),
        )
        self.progress_scroll_canvas.bind(
            "<Leave>",
            lambda event: self.root.unbind_all("<MouseWheel>"),
        )

        progress_header = tk.Frame(self.progress_content, bg=self.COLORS["page_progress"])
        progress_header.pack(fill=tk.X)
        tk.Label(
            progress_header,
            text="Přehled plnění",
            font=(self.FONT, 12, "bold"),
            bg=self.COLORS["page_progress"],
            fg=self.COLORS["page_progress_accent"],
        ).pack(side=tk.LEFT)
        self.lbl_progress_summary = tk.Label(
            progress_header,
            text="Bez bodů programu.",
            font=(self.FONT, 10),
            bg=self.COLORS["page_progress"],
            fg=self.COLORS["muted"],
        )
        self.lbl_progress_summary.pack(side=tk.RIGHT)

        point_progress_header = tk.Frame(self.progress_content, bg=self.COLORS["page_progress"])
        point_progress_header.pack(fill=tk.X)
        tk.Label(
            point_progress_header,
            text="Plnění podle bodů programu",
            font=(self.FONT, 12, "bold"),
            bg=self.COLORS["page_progress"],
            fg=self.COLORS["page_progress_accent"],
        ).pack(side=tk.LEFT)

        self.progress_canvas = tk.Canvas(
            self.progress_content,
            height=118,
            bg=self.COLORS["panel_soft"],
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            bd=0,
        )
        self.progress_canvas.pack(fill=tk.X, pady=(6, 16))
        self.progress_canvas.bind("<Configure>", lambda event: self.draw_progress_overview())

        owner_progress_header = tk.Frame(self.progress_content, bg=self.COLORS["page_progress"])
        owner_progress_header.pack(fill=tk.X)
        tk.Label(
            owner_progress_header,
            text="Plnění podle odpovědnosti",
            font=(self.FONT, 12, "bold"),
            bg=self.COLORS["page_progress"],
            fg=self.COLORS["page_progress_accent"],
        ).pack(side=tk.LEFT)

        self.owner_progress_canvas = tk.Canvas(
            self.progress_content,
            height=118,
            bg=self.COLORS["panel_soft"],
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            bd=0,
        )
        self.owner_progress_canvas.pack(fill=tk.X, pady=(6, 16))
        self.owner_progress_canvas.bind("<Configure>", lambda event: self.draw_owner_progress_overview())

        self.create_page_accent(self.calendar_tab, "#f59e0b")
        calendar_header = tk.Frame(self.calendar_tab, bg="#eef6ff")
        calendar_header.pack(fill=tk.X)
        tk.Label(
            calendar_header,
            text="Kalendář položek",
            font=(self.FONT, 12, "bold"),
            bg="#eef6ff",
            fg="#92400e",
        ).pack(side=tk.LEFT)
        self.lbl_lotus_calendar_month = tk.Label(
            calendar_header,
            text="",
            font=(self.FONT, 11, "bold"),
            bg="#eef6ff",
            fg=self.COLORS["text"],
        )
        self.lbl_lotus_calendar_month.pack(side=tk.LEFT, padx=(18, 0))
        self.create_button(
            calendar_header,
            text=">",
            command=lambda: self.shift_lotus_calendar_month(1),
            variant="secondary",
        ).pack(side=tk.RIGHT, padx=(8, 0))
        self.create_button(
            calendar_header,
            text="Dnes",
            command=self.show_lotus_calendar_today,
            variant="secondary",
        ).pack(side=tk.RIGHT, padx=(8, 0))
        self.create_button(
            calendar_header,
            text="<",
            command=lambda: self.shift_lotus_calendar_month(-1),
            variant="secondary",
        ).pack(side=tk.RIGHT)

        self.lotus_calendar_frame = tk.Frame(self.calendar_tab, bg="#eef6ff")
        self.lotus_calendar_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.lotus_calendar_canvas = tk.Canvas(
            self.lotus_calendar_frame,
            height=420,
            bg="#eef6ff",
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            bd=0,
        )
        self.lotus_calendar_scrollbar = ttk.Scrollbar(
            self.lotus_calendar_frame,
            orient=tk.VERTICAL,
            command=self.lotus_calendar_canvas.yview,
        )
        self.lotus_calendar_canvas.configure(yscrollcommand=self.lotus_calendar_scrollbar.set)
        self.lotus_calendar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.lotus_calendar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lotus_calendar_canvas.bind("<Configure>", lambda event: self.draw_lotus_calendar())
        self.lotus_calendar_canvas.bind("<Enter>", lambda event: self.root.bind_all("<MouseWheel>", self.scroll_lotus_calendar))
        self.lotus_calendar_canvas.bind("<Leave>", lambda event: self.root.unbind_all("<MouseWheel>"))

        agenda_header = tk.Frame(self.meeting_tab, bg=self.COLORS["page_meeting"])
        agenda_header.pack(fill=tk.X)
        tk.Label(
            agenda_header,
            text="Body programu",
            font=(self.FONT, 12, "bold"),
            bg=self.COLORS["page_meeting"],
            fg=self.COLORS["page_meeting_accent"],
        ).pack(side=tk.LEFT)

        self.open_only_check = tk.Checkbutton(
            agenda_header,
            text="Jen otevřené",
            variable=self.show_open_only,
            command=self.load_meeting_details,
            bg=self.COLORS["page_meeting"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["page_meeting"],
            activeforeground=self.COLORS["text"],
            selectcolor=self.COLORS["page_meeting"],
            font=(self.FONT, 10),
            relief=tk.FLAT,
            borderwidth=0,
            padx=10,
        )
        self.open_only_check.pack(side=tk.LEFT, padx=(14, 0))

        self.lbl_agenda_count = tk.Label(
            agenda_header,
            text="Dvojklikem označíte bod jako vyřešený.",
            font=(self.FONT, 10),
            bg=self.COLORS["page_meeting"],
            fg=self.COLORS["muted"],
        )
        self.lbl_agenda_count.pack(side=tk.RIGHT)

        self.agenda_area = tk.Frame(self.meeting_tab, bg=self.COLORS["panel"])
        self.agenda_area.pack(fill=tk.BOTH, expand=True)

        self.agenda_list_frame = tk.Frame(self.agenda_area, bg=self.COLORS["panel"])

        self.agenda_listbox = tk.Listbox(
            self.agenda_list_frame,
            height=8,
            font=("Consolas", 11),
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["text"],
            selectbackground=self.COLORS["selection"],
            selectforeground=self.COLORS["text"],
            activestyle="none",
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["primary"],
            exportselection=False,
        )
        self.agenda_listbox.bind("<Double-1>", self.toggle_agenda_item)
        self.agenda_listbox.bind("<<ListboxSelect>>", self.on_select_agenda_row)
        self.agenda_scrollbar = ttk.Scrollbar(
            self.agenda_list_frame,
            orient=tk.VERTICAL,
            command=self.agenda_listbox.yview,
        )
        self.agenda_listbox.configure(yscrollcommand=self.agenda_scrollbar.set)

        self.btn_frame = tk.Frame(self.agenda_area, bg=self.COLORS["panel"])
        self.btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))

        self.item_entry_frame = tk.Frame(self.agenda_area, bg=self.COLORS["panel"])
        self.item_entry_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 12))

        self.agenda_entry_frame = tk.Frame(self.agenda_area, bg=self.COLORS["panel"])
        self.agenda_entry_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 10))

        self.agenda_list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(6, 10))
        self.agenda_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.agenda_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.entry_new_point = ttk.Entry(self.agenda_entry_frame, font=(self.FONT, 11))
        self.entry_new_point.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=3)
        self.entry_new_point.bind("<Return>", lambda event: self.add_agenda_point())

        self.btn_add_point = self.create_button(
            self.agenda_entry_frame,
            text="Přidat bod programu",
            command=self.add_agenda_point,
            variant="secondary",
        )
        self.btn_add_point.pack(side=tk.RIGHT)

        self.btn_cancel_point_edit = self.create_button(
            self.agenda_entry_frame,
            text="Zrušit",
            command=self.reset_point_form,
            variant="secondary",
        )

        self.entry_new_item = ttk.Combobox(self.item_entry_frame, font=(self.FONT, 11))
        self.entry_new_item.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=3)
        self.entry_new_item.bind("<FocusIn>", lambda event: self.refresh_item_description_choices())
        self.entry_new_item.bind("<Return>", lambda event: self.add_agenda_item())

        self.entry_new_owner = ttk.Combobox(self.item_entry_frame, font=(self.FONT, 10), width=16)
        self.entry_new_owner.pack(side=tk.LEFT, padx=(0, 8), ipady=3)
        self.entry_new_owner.insert(0, "Odpovědnost")
        self.entry_new_owner.bind("<FocusIn>", lambda event: self.clear_entry_placeholder(self.entry_new_owner, "Odpovědnost"))
        self.entry_new_owner.bind("<Return>", lambda event: self.add_agenda_item())

        self.entry_new_due_date = ttk.Entry(self.item_entry_frame, font=(self.FONT, 10), width=12)
        self.entry_new_due_date.pack(side=tk.LEFT, padx=(0, 8), ipady=3)
        self.entry_new_due_date.insert(0, self.get_today_due_date())
        self.entry_new_due_date.bind("<FocusIn>", lambda event: self.clear_entry_placeholder(self.entry_new_due_date, "Termín"))
        self.entry_new_due_date.bind("<Button-1>", self.open_due_date_picker)
        self.entry_new_due_date.bind("<Up>", self.open_due_date_picker)
        self.entry_new_due_date.bind("<Return>", lambda event: self.add_agenda_item())

        self.btn_add_item = self.create_button(
            self.item_entry_frame,
            text="Přidat položku",
            command=self.add_agenda_item,
            variant="primary",
        )
        self.btn_add_item.pack(side=tk.RIGHT)

        self.btn_cancel_edit = self.create_button(
            self.item_entry_frame,
            text="Zrušit",
            command=self.reset_item_form,
            variant="secondary",
        )

        self.btn_delete = self.create_button(
            self.btn_frame,
            text="Smazat poradu",
            command=self.delete_meeting,
            variant="danger",
            state=tk.DISABLED,
        )
        self.btn_delete.pack(side=tk.LEFT)

        self.btn_archive = self.create_button(
            self.btn_frame,
            text="Archiv",
            command=self.archive_current_meeting,
            variant="secondary",
            state=tk.DISABLED,
        )
        self.btn_archive.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_history = self.create_button(
            self.btn_frame,
            text="Historie",
            command=lambda: self.show_history_dialog(meeting_id=self.current_id),
            variant="secondary",
            state=tk.DISABLED,
        )
        self.btn_history.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_delete_agenda = self.create_button(
            self.btn_frame,
            text="Smazat vybrané",
            command=self.delete_agenda_item,
            variant="secondary",
            state=tk.DISABLED,
        )
        self.btn_delete_agenda.pack(side=tk.LEFT, padx=10)

        self.btn_export = self.create_button(
            self.btn_frame,
            text="Export / tisk",
            command=self.export_meeting,
            variant="secondary",
            state=tk.DISABLED,
        )
        self.btn_export.pack(side=tk.RIGHT, padx=(10, 0))

        self.apply_permission_state()


    def create_page_accent(self, parent, color):
        tk.Frame(parent, height=4, bg=color).pack(fill=tk.X, pady=(0, 10))


    def on_detail_tab_changed(self, event=None):
        if hasattr(self, "progress_canvas"):
            self.draw_progress_overview()
        selected_tab = self.detail_tabs.select()
        tab_refreshes = (
            ("tasks_tab", "task_tab_refresh"),
            ("orders_tab", "order_tab_refresh"),
            ("requirements_tab", "requirement_tab_refresh"),
            ("problems_tab", "problem_tab_refresh"),
        )
        for tab_name, refresh_name in tab_refreshes:
            if (
                hasattr(self, tab_name)
                and selected_tab == str(getattr(self, tab_name))
                and hasattr(self, refresh_name)
            ):
                getattr(self, refresh_name)()
                break


    def scroll_progress_overview(self, event):
        self.progress_scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


    def create_section_header(self, parent, title, color=None):
        background = parent.cget("bg")
        tk.Label(
            parent,
            text=title,
            font=(self.FONT, 12, "bold"),
            bg=background,
            fg=color or self.COLORS["text"],
        ).pack(anchor="w")

    def get_launcher_dashboard_summary(self):
        summary = {
            "open_items": 0,
            "open_tasks": 0,
            "open_orders": 0,
            "open_requirements": 0,
            "open_problems": 0,
            "due_today": 0,
            "overdue": 0,
        }
        today = self.parse_due_date(self.get_today_due_date())
        c = self.conn.cursor()

        dated_sources = (
            ("agenda_items", "due_date", "is_resolved", "agenda"),
            ("meeting_orders", "due_date", "is_resolved", "orders"),
            ("meeting_requirements", "due_date", "is_resolved", "requirements"),
        )
        for table_name, due_column, resolved_column, source in dated_sources:
            if source == "agenda":
                c.execute(
                    f"""SELECT {due_column}, {resolved_column}
                        FROM {table_name}
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM agenda_items AS copied_item
                            WHERE copied_item.copied_from_item_id = agenda_items.id
                        )"""
                )
            else:
                copied_column = (
                    "copied_from_order_id"
                    if table_name == "meeting_orders"
                    else "copied_from_requirement_id"
                )
                c.execute(
                    f"""SELECT {due_column}, {resolved_column}
                        FROM {table_name}
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM {table_name} AS copied_item
                            WHERE copied_item.{copied_column} = {table_name}.id
                        )"""
                )
            for due_date, is_resolved in c.fetchall():
                if is_resolved == 1:
                    continue
                summary["open_items"] += 1
                source_key = {
                    "agenda": "open_tasks",
                    "orders": "open_orders",
                    "requirements": "open_requirements",
                }[source]
                summary[source_key] += 1
                parsed_due = self.parse_due_date(due_date)
                if parsed_due == today:
                    summary["due_today"] += 1
                elif parsed_due and parsed_due < today:
                    summary["overdue"] += 1

        c.execute("SELECT due_date, COALESCE(status, 'Nový') FROM corrective_actions")
        for due_date, status in c.fetchall():
            if status == "Uzavřeno":
                continue
            summary["open_items"] += 1
            summary["open_problems"] += 1
            parsed_due = self.parse_due_date(due_date)
            if parsed_due == today:
                summary["due_today"] += 1
            elif parsed_due and parsed_due < today:
                summary["overdue"] += 1

        return summary

    def refresh_dashboard_summary(self):
        if not hasattr(self, "dashboard_labels"):
            return

        summary = {
            "open_tasks": 0,
            "open_orders": 0,
            "open_requirements": 0,
            "open_problems": 0,
            "due_today": 0,
            "overdue": 0,
        }
        today = self.parse_due_date(self.get_today_due_date())
        c = self.conn.cursor()

        c.execute(
            """SELECT due_date, is_resolved
               FROM agenda_items
               WHERE NOT EXISTS (
                   SELECT 1
                   FROM agenda_items AS copied_item
                   WHERE copied_item.copied_from_item_id = agenda_items.id
               )"""
        )
        for due_date, is_resolved in c.fetchall():
            if is_resolved == 1:
                continue
            summary["open_tasks"] += 1
            parsed_due = self.parse_due_date(due_date)
            if parsed_due == today:
                summary["due_today"] += 1
            elif parsed_due and parsed_due < today:
                summary["overdue"] += 1

        for table_name, key in (("meeting_orders", "open_orders"), ("meeting_requirements", "open_requirements")):
            copied_column = (
                "copied_from_order_id"
                if table_name == "meeting_orders"
                else "copied_from_requirement_id"
            )
            c.execute(
                f"""SELECT due_date, is_resolved
                    FROM {table_name}
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM {table_name} AS copied_item
                        WHERE copied_item.{copied_column} = {table_name}.id
                    )"""
            )
            for due_date, is_resolved in c.fetchall():
                if is_resolved == 1:
                    continue
                summary[key] += 1
                parsed_due = self.parse_due_date(due_date)
                if parsed_due == today:
                    summary["due_today"] += 1
                elif parsed_due and parsed_due < today:
                    summary["overdue"] += 1

        c.execute("SELECT status FROM corrective_actions")
        for status, in c.fetchall():
            if (status or "Nový") != "Uzavřeno":
                summary["open_problems"] += 1

        for key, value in summary.items():
            if key in self.dashboard_labels:
                self.dashboard_labels[key].config(text=str(value))


    def show_dashboard_filter(self, filter_type):
        tab_actions = {
            "tasks": self.show_tasks_tab,
            "orders": self.show_orders_tab,
            "requirements": self.show_requirements_tab,
            "problems": self.show_problems_tab,
        }
        if filter_type in tab_actions:
            tab_actions[filter_type]()
            return
        self.show_open_items_overview(filter_type)


    def apply_permission_state(self):
        if not hasattr(self, "agenda_listbox"):
            return

        edit_state = tk.NORMAL if self.can_edit() else tk.DISABLED
        selected_edit_state = tk.NORMAL if self.can_edit() and getattr(self, "current_id", None) else tk.DISABLED
        readonly_widget_state = "normal" if self.can_edit() else "disabled"

        if hasattr(self, "lbl_user_role"):
            self.lbl_user_role.config(
                text=self.get_role_text(),
                fg="#dbeafe" if self.can_edit() else self.COLORS["sidebar_muted"],
            )

        if hasattr(self, "btn_data_settings"):
            if not self.btn_data_settings.winfo_ismapped():
                pack_options = {"fill": tk.X, "pady": (0, 8)}
                if hasattr(self, "btn_login"):
                    pack_options["before"] = self.btn_login
                self.btn_data_settings.pack(**pack_options)

        if hasattr(self, "btn_people_manager"):
            if self.can_edit():
                if not self.btn_people_manager.winfo_ismapped():
                    pack_options = {"fill": tk.X, "pady": (0, 8)}
                    if hasattr(self, "btn_data_settings"):
                        pack_options["before"] = self.btn_data_settings
                    self.btn_people_manager.pack(**pack_options)
            else:
                self.btn_people_manager.pack_forget()

        if hasattr(self, "btn_admin_top"):
            self.btn_admin_top.config(text="Odhlásit admina" if self.can_edit() else "Admin")

        for button_name in (
            "btn_add_meeting",
            "btn_copy",
            "btn_add_point",
            "btn_add_item",
        ):
            button = getattr(self, button_name, None)
            if button:
                button.config(state=edit_state)

        for button in getattr(self, "requirement_tab_edit_buttons", []):
            button.config(state=tk.NORMAL)
        for button in getattr(self, "order_tab_edit_buttons", []):
            button.config(state=edit_state)
        for button in getattr(self, "problem_tab_edit_buttons", []):
            button.config(state=tk.NORMAL)

        for button_name in (
            "btn_edit_date",
            "btn_delete",
            "btn_delete_agenda",
            "btn_archive",
            "btn_history",
            "btn_add_general_info",
            "btn_edit_general_info",
            "btn_invalidate_general_info",
        ):
            button = getattr(self, button_name, None)
            if button:
                button.config(state=selected_edit_state)

        for widget_name in (
            "entry_new_point",
            "entry_new_item",
            "entry_new_owner",
            "entry_new_due_date",
        ):
            widget = getattr(self, widget_name, None)
            if widget:
                widget.config(state=readonly_widget_state)

        if self.text_notes is not None:
            self.text_notes.config(state=edit_state)

