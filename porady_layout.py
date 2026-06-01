# -*- coding: utf-8 -*-

import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk

from porady_widgets import RoundedFrame


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
        if self.can_edit() and self.current_id and self.notes_dirty:
            self.save_notes(show_message=False)
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
        self.left_frame = tk.Frame(self.root, width=310, bg=self.COLORS["sidebar"])
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)

        self.right_frame = tk.Frame(self.root, bg=self.COLORS["app_bg"], padx=24, pady=24)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.create_sidebar()
        self.create_detail_panel()


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

        sidebar_actions = tk.Frame(self.left_frame, bg=self.COLORS["sidebar"], padx=16, pady=18)
        sidebar_actions.pack(fill=tk.X)

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
            text="Přehled úkolů",
            command=self.show_task_overview,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Přehled nařízení",
            command=self.show_order_overview,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.create_button(
            sidebar_actions,
            text="Tisk otevřených položek",
            command=self.export_open_items_overview,
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
            text="Přehled požadavků",
            command=self.show_requirement_overview,
            variant="secondary",
        ).pack(fill=tk.X, pady=(0, 8))

        self.btn_data_settings = self.create_button(
            sidebar_actions,
            text="Data a zálohy",
            command=self.show_data_settings,
            variant="secondary",
        )
        if self.can_edit():
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

        self.dashboard_frame = tk.Frame(self.content, bg=self.COLORS["panel"])
        self.dashboard_frame.pack(fill=tk.X, pady=(0, 18))
        self.dashboard_labels = {}
        dashboard_items = (
            ("open_tasks", "Úkoly", self.COLORS["page_tasks_accent"], "tasks"),
            ("open_orders", "Nařízení", self.COLORS["page_orders_accent"], "orders"),
            ("open_requirements", "Požadavky", self.COLORS["page_requirements_accent"], "requirements"),
            ("due_today", "Dnes", self.COLORS["warning"], "today"),
            ("overdue", "Po termínu", self.COLORS["danger"], "overdue"),
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
                widget.bind("<Button-1>", lambda event, selected_filter=filter_type: self.show_open_items_overview(selected_filter))
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
        self.detail_tabs.bind("<<NotebookTabChanged>>", lambda event: self.draw_progress_overview())

        self.general_info_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["page_info"], padx=10, pady=14)
        self.meeting_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["page_meeting"], padx=10, pady=14)
        self.progress_tab = tk.Frame(self.detail_tabs, bg=self.COLORS["page_progress"], padx=10, pady=14)
        self.detail_tabs.add(self.general_info_tab, text="Všeobecné informace")
        self.detail_tabs.add(self.meeting_tab, text="Zápis a body programu")
        self.detail_tabs.add(self.progress_tab, text="Přehled plnění")

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

        self.create_page_accent(self.meeting_tab, self.COLORS["page_meeting_accent"])
        self.create_section_header(self.meeting_tab, "Zápis z porady", self.COLORS["page_meeting_accent"])

        self.notes_frame = tk.Frame(
            self.meeting_tab,
            bg=self.COLORS["panel_soft"],
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["primary"],
        )
        self.notes_frame.pack(fill=tk.X, pady=(6, 14))

        self.text_notes = tk.Text(
            self.notes_frame,
            height=2,
            font=(self.FONT, 11),
            wrap=tk.WORD,
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=10,
            highlightthickness=0,
        )
        self.notes_scrollbar = ttk.Scrollbar(
            self.notes_frame,
            orient=tk.VERTICAL,
            command=self.text_notes.yview,
        )
        self.text_notes.configure(yscrollcommand=self.notes_scrollbar.set)
        self.text_notes.bind("<<Modified>>", self.on_notes_modified)
        self.text_notes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.create_page_accent(self.progress_tab, self.COLORS["page_progress_accent"])
        progress_header = tk.Frame(self.progress_tab, bg=self.COLORS["page_progress"])
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

        self.progress_canvas = tk.Canvas(
            self.progress_tab,
            height=118,
            bg=self.COLORS["panel_soft"],
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            bd=0,
        )
        self.progress_canvas.pack(fill=tk.X, pady=(6, 16))
        self.progress_canvas.bind("<Configure>", lambda event: self.draw_progress_overview())

        owner_progress_header = tk.Frame(self.progress_tab, bg=self.COLORS["page_progress"])
        owner_progress_header.pack(fill=tk.X)
        tk.Label(
            owner_progress_header,
            text="Plnění podle odpovědnosti",
            font=(self.FONT, 12, "bold"),
            bg=self.COLORS["page_progress"],
            fg=self.COLORS["page_progress_accent"],
        ).pack(side=tk.LEFT)

        self.owner_progress_canvas = tk.Canvas(
            self.progress_tab,
            height=118,
            bg=self.COLORS["panel_soft"],
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            bd=0,
        )
        self.owner_progress_canvas.pack(fill=tk.X, pady=(6, 16))
        self.owner_progress_canvas.bind("<Configure>", lambda event: self.draw_owner_progress_overview())

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

        self.entry_new_due_date = ttk.Combobox(self.item_entry_frame, font=(self.FONT, 10), width=12)
        self.entry_new_due_date.pack(side=tk.LEFT, padx=(0, 8), ipady=3)
        self.entry_new_due_date.insert(0, self.get_today_due_date())
        self.entry_new_due_date.bind("<FocusIn>", lambda event: self.clear_entry_placeholder(self.entry_new_due_date, "Termín"))
        self.entry_new_due_date.bind("<Button-1>", lambda event: self.root.after(1, self.open_due_date_picker))
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

        self.btn_save = self.create_button(
            self.btn_frame,
            text="Uložit zápis",
            command=self.save_notes,
            variant="primary",
            state=tk.DISABLED,
        )
        self.btn_save.pack(side=tk.RIGHT)
        self.apply_permission_state()


    def create_page_accent(self, parent, color):
        tk.Frame(parent, height=4, bg=color).pack(fill=tk.X, pady=(0, 10))


    def create_section_header(self, parent, title, color=None):
        background = parent.cget("bg")
        tk.Label(
            parent,
            text=title,
            font=(self.FONT, 12, "bold"),
            bg=background,
            fg=color or self.COLORS["text"],
        ).pack(anchor="w")

    def refresh_dashboard_summary(self):
        if not hasattr(self, "dashboard_labels"):
            return

        summary = {
            "open_tasks": 0,
            "open_orders": 0,
            "open_requirements": 0,
            "due_today": 0,
            "overdue": 0,
        }
        today = self.parse_due_date(self.get_today_due_date())
        c = self.conn.cursor()

        c.execute("SELECT due_date, is_resolved FROM agenda_items")
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
            c.execute(f"SELECT due_date, is_resolved FROM {table_name}")
            for due_date, is_resolved in c.fetchall():
                if is_resolved == 1:
                    continue
                summary[key] += 1
                parsed_due = self.parse_due_date(due_date)
                if parsed_due == today:
                    summary["due_today"] += 1
                elif parsed_due and parsed_due < today:
                    summary["overdue"] += 1

        for key, value in summary.items():
            self.dashboard_labels[key].config(text=str(value))


    def apply_permission_state(self):
        if not hasattr(self, "text_notes"):
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
            if self.can_edit():
                if not self.btn_data_settings.winfo_ismapped():
                    pack_options = {"fill": tk.X, "pady": (0, 8)}
                    if hasattr(self, "btn_login"):
                        pack_options["before"] = self.btn_login
                    self.btn_data_settings.pack(**pack_options)
            else:
                self.btn_data_settings.pack_forget()

        if hasattr(self, "btn_people_manager"):
            if self.can_edit():
                if not self.btn_people_manager.winfo_ismapped():
                    pack_options = {"fill": tk.X, "pady": (0, 8)}
                    if hasattr(self, "btn_data_settings"):
                        pack_options["before"] = self.btn_data_settings
                    self.btn_people_manager.pack(**pack_options)
            else:
                self.btn_people_manager.pack_forget()

        for button_name in (
            "btn_add_meeting",
            "btn_copy",
            "btn_add_point",
            "btn_add_item",
        ):
            button = getattr(self, button_name, None)
            if button:
                button.config(state=edit_state)

        for button_name in (
            "btn_edit_date",
            "btn_delete",
            "btn_delete_agenda",
            "btn_save",
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

        self.text_notes.config(state=edit_state)

