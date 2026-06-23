# -*- coding: utf-8 -*-

import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk

from .bozppo_config import LOGO_FILES, PASS_LIMIT, RESULTS_FILE, TRAINING_VALID_DAYS
from .bozppo_content import save_training_sections
from .bozppo_templates import HANDOVER_TEMPLATES


class TrainingAppUiMixin:
    def _configure_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#eef2f6")
        self.style.configure("Header.TFrame", background="#182433")
        self.style.configure("Header.TLabel", background="#182433", foreground="white", font=("Segoe UI", 18, "bold"))
        self.style.configure("SubHeader.TLabel", background="#182433", foreground="#cfd8dc", font=("Segoe UI", 10))
        self.style.configure("TLabel", background="#eef2f6", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background="#eef2f6", font=("Segoe UI", 14, "bold"))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Result.TLabel", background="#eef2f6", font=("Segoe UI", 12, "bold"))


    def _load_logo(self):
        for logo_file in LOGO_FILES:
            if not logo_file.exists():
                continue
            try:
                return tk.PhotoImage(file=str(logo_file)).subsample(2, 2)
            except tk.TclError:
                continue
        return None


    def _build_layout(self):
        header = ttk.Frame(self, style="Header.TFrame", padding=(18, 14))
        header.pack(fill="x")
        self.logo_image = self._load_logo()
        if self.logo_image:
            logo_box = tk.Frame(header, background="white", padx=8, pady=6)
            logo_box.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 18))
            tk.Label(logo_box, image=self.logo_image, background="white", borderwidth=0).pack()
        else:
            tk.Label(
                header,
                text="SVOS",
                background="white",
                foreground="#231f1c",
                font=("Segoe UI", 20, "bold"),
                padx=16,
                pady=8,
            ).grid(
                row=0,
                column=0,
                rowspan=2,
                sticky="nw",
                padx=(0, 18),
            )
        ttk.Label(header, text="Vstupní školení nových zaměstnanců", style="Header.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(
            header,
            text="Projít kapitoly, vyplnit test a uložit záznam o absolvování.",
            style="SubHeader.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))
        header.columnconfigure(1, weight=1)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill="both", expand=True)

        self._build_info_tab()
        self._build_training_tab()
        self._build_test_tab()
        self._build_results_tab()
        self._build_overview_tab()
        self._build_topics_tab()


    def _build_info_tab(self):
        tab = ttk.Frame(self, padding=18)
        self.notebook.add(tab, text="Údaje")

        ttk.Label(tab, text="Údaje pro záznam", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

        fields = [
            ("Jméno a příjmení zaměstnance", self.worker_name),
            ("Oddělení / pracoviště", self.company_name),
            ("Školitel / nadřízený", self.trainer_name),
        ]
        for row, (label, variable) in enumerate(fields, start=1):
            ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", pady=(18, 4))
            ttk.Entry(tab, textvariable=variable, width=48).grid(row=row, column=1, sticky="ew", pady=(18, 4))

        ttk.Label(
            tab,
            text=(
                "Před testem projděte obsah školení. Po úspěšném splnění testu se záznam uloží "
                f"do souboru {RESULTS_FILE.name}."
            ),
            wraplength=720,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(28, 10))

        ttk.Button(tab, text="Pokračovat na školení", command=lambda: self.notebook.select(1)).grid(
            row=5, column=0, sticky="w", pady=16
        )
        ttk.Button(tab, text="Uložit výchozí údaje", command=self.save_current_defaults).grid(
            row=5, column=1, sticky="e", pady=16
        )
        ttk.Button(tab, text="Otevřít obsah školení", command=self.open_training_content_file).grid(
            row=6, column=0, sticky="w", pady=(0, 16)
        )
        tab.columnconfigure(1, weight=1)


    def _build_training_tab(self):
        tab = ttk.Frame(self, padding=0)
        self.notebook.add(tab, text="Školení")

        canvas = tk.Canvas(tab, background="#f6f7f9", highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, padding=18)

        content.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.training_content = content
        self._populate_training_tab()


    def _populate_training_tab(self):
        for child in self.training_content.winfo_children():
            child.destroy()

        ttk.Label(self.training_content, text="Obsah školení", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        for title, text in self.training_sections:
            frame = ttk.LabelFrame(self.training_content, text=title, padding=12)
            frame.pack(fill="x", expand=True, pady=8)
            if text:
                ttk.Label(frame, text=text, wraplength=850, justify="left").pack(anchor="w")

        ttk.Button(self.training_content, text="Přejít na test", command=lambda: self.notebook.select(2)).pack(anchor="w", pady=18)


    def _build_test_tab(self):
        tab = ttk.Frame(self, padding=0)
        self.notebook.add(tab, text="Test")

        canvas = tk.Canvas(tab, background="#f6f7f9", highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, padding=18)

        content.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(content, text=f"Test znalosti - limit {PASS_LIMIT} %", style="Title.TLabel").pack(anchor="w")
        ttk.Label(content, text="U každé otázky vyberte jednu správnou odpověď.", wraplength=850).pack(
            anchor="w", pady=(4, 14)
        )

        for index, question in enumerate(self.test_questions):
            frame = ttk.LabelFrame(content, text=f"Otázka {index + 1}", padding=12)
            frame.pack(fill="x", expand=True, pady=8)
            ttk.Label(frame, text=question["text"], wraplength=850, justify="left").pack(anchor="w", pady=(0, 8))
            for option_index, option in enumerate(question["options"]):
                ttk.Radiobutton(
                    frame,
                    text=option,
                    value=option_index,
                    variable=self.answers[index],
                ).pack(anchor="w", pady=2)

        ttk.Button(content, text="Vyhodnotit test", style="Accent.TButton", command=self.evaluate_test).pack(
            anchor="w", pady=18
        )


    def _build_results_tab(self):
        tab = ttk.Frame(self, padding=18)
        self.notebook.add(tab, text="Výsledek")

        ttk.Label(tab, text="Výsledek školení", style="Title.TLabel").pack(anchor="w")
        self.result_label = ttk.Label(tab, text="Test zatím nebyl vyhodnocen.", style="Result.TLabel")
        self.result_label.pack(anchor="w", pady=(20, 8))

        self.detail_text = tk.Text(tab, height=18, wrap="word", font=("Consolas", 10))
        self.detail_text.pack(fill="both", expand=True, pady=8)
        self.detail_text.insert("1.0", "Po vyhodnocení se zde zobrazí souhrn odpovědí.")
        self.detail_text.configure(state="disabled")

        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="Zpět na test", command=lambda: self.notebook.select(2)).pack(side="left")
        self.open_certificate_button = ttk.Button(
            actions,
            text="Otevřít potvrzení",
            command=self.open_certificate,
            state="disabled",
        )
        self.open_certificate_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Nový zaměstnanec", command=self.reset_form).pack(side="left", padx=8)


    def _build_overview_tab(self):
        tab = ttk.Frame(self, padding=18)
        self.notebook.add(tab, text="Přehled")

        header = ttk.Frame(tab)
        header.pack(fill="x")
        ttk.Label(header, text="Přehled proškolených zaměstnanců", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Obnovit", command=self.load_overview).pack(side="right")
        ttk.Button(header, text="Otevřít CSV", command=self.open_results_file).pack(side="right", padx=8)
        ttk.Button(header, text="Export Excel", command=self.export_results_excel).pack(side="right")
        ttk.Button(header, text="Tisk přehledu", command=self.print_overview).pack(side="right")
        ttk.Button(header, text="Tisk potvrzení", command=self.print_selected_certificate).pack(side="right", padx=8)

        filters = ttk.Frame(tab)
        filters.pack(fill="x", pady=(12, 4))
        ttk.Label(filters, text="Hledat").pack(side="left")
        search_entry = ttk.Entry(filters, textvariable=self.overview_search, width=30)
        search_entry.pack(side="left", padx=(6, 14))
        search_entry.bind("<KeyRelease>", lambda event: self.load_overview())
        ttk.Label(filters, text="Výsledek").pack(side="left")
        result_filter = ttk.Combobox(
            filters,
            textvariable=self.overview_result_filter,
            values=("Vše", "SPLNĚNO", "NESPLNĚNO"),
            width=12,
            state="readonly",
        )
        result_filter.pack(side="left", padx=(6, 14))
        result_filter.bind("<<ComboboxSelected>>", lambda event: self.load_overview())
        ttk.Label(filters, text=f"Platnost ({TRAINING_VALID_DAYS} dní)").pack(side="left")
        validity_filter = ttk.Combobox(
            filters,
            textvariable=self.overview_validity_filter,
            values=("Vše", "Platné", "Končí", "Propadlé", "Nesplněno"),
            width=12,
            state="readonly",
        )
        validity_filter.pack(side="left", padx=(6, 8))
        validity_filter.bind("<<ComboboxSelected>>", lambda event: self.load_overview())

        ttk.Label(tab, textvariable=self.overview_summary).pack(anchor="w", pady=(12, 8))

        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True)

        columns = ("datum", "pracovnik", "firma", "skolitel", "pokus", "skore", "procenta", "vysledek", "platnost")
        self.overview_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)
        headings = {
            "datum": "Datum",
            "pracovnik": "Zaměstnanec",
            "firma": "Oddělení",
            "skolitel": "Školitel",
            "pokus": "Pokus",
            "skore": "Skóre",
            "procenta": "%",
            "platnost": "Platnost",
            "vysledek": "Výsledek",
        }
        widths = {
            "datum": 145,
            "pracovnik": 190,
            "firma": 170,
            "skolitel": 170,
            "pokus": 65,
            "skore": 70,
            "procenta": 55,
            "platnost": 120,
            "vysledek": 100,
        }
        for column in columns:
            self.overview_tree.heading(column, text=headings[column])
            self.overview_tree.column(column, width=widths[column], anchor="w", stretch=column in {"pracovnik", "firma", "skolitel"})

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.overview_tree.yview)
        self.overview_tree.configure(yscrollcommand=scrollbar.set)
        self.overview_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_overview()


    def _build_handover_tab(self):
        tab = ttk.Frame(self, padding=0)
        self.notebook.add(tab, text="Předání pracoviště")

        canvas = tk.Canvas(tab, background="#f6f7f9", highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, padding=18)

        content.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(content, text="Formulář předání pracoviště", style="Title.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 12)
        )

        ttk.Label(content, text="Typ práce / šablona").grid(row=1, column=0, sticky="w", pady=(8, 3), padx=(0, 8))
        template_box = ttk.Combobox(
            content,
            textvariable=self.handover_template,
            values=tuple(HANDOVER_TEMPLATES.keys()),
            width=34,
            state="readonly",
        )
        template_box.grid(row=1, column=1, sticky="ew", pady=(8, 3), padx=(0, 18))
        template_box.bind("<<ComboboxSelected>>", lambda event: self.apply_handover_template())
        ttk.Button(content, text="Použít šablonu", command=self.apply_handover_template).grid(
            row=1, column=2, sticky="w", pady=(8, 3), padx=(0, 8)
        )

        fields = [
            ("Pracoviště / zakázka", self.handover_workplace),
            ("Místo výkonu práce", self.handover_location),
            ("Objednatel / provoz", self.handover_customer),
            ("Dodavatel / firma", self.handover_company),
            ("Práce od", self.handover_work_from),
            ("Práce do", self.handover_work_to),
            ("Předal", self.handover_handed_by),
            ("Převzal", self.handover_taken_by),
        ]

        for index, (label, variable) in enumerate(fields, start=1):
            row = 2 + (index - 1) // 2
            column = 0 if index % 2 else 2
            ttk.Label(content, text=label).grid(row=row, column=column, sticky="w", pady=(8, 3), padx=(0, 8))
            ttk.Entry(content, textvariable=variable, width=34).grid(
                row=row, column=column + 1, sticky="ew", pady=(8, 3), padx=(0, 18)
            )

        text_specs = [
            ("Rozsah předávaných prací", "handover_scope_text"),
            ("Rizika pracoviště", "handover_risks_text"),
            ("Bezpečnostní opatření a OOPP", "handover_measures_text"),
            ("Požární ochrana / horké práce", "handover_fire_text"),
            ("Předaná dokumentace a povolení", "handover_docs_text"),
            ("Poznámky", "handover_notes_text"),
        ]
        start_row = 7
        for offset, (label, attr_name) in enumerate(text_specs):
            row = start_row + offset * 2
            ttk.Label(content, text=label).grid(row=row, column=0, columnspan=4, sticky="w", pady=(12, 3))
            text = tk.Text(content, height=4, wrap="word", font=("Segoe UI", 10))
            text.grid(row=row + 1, column=0, columnspan=4, sticky="ew", pady=(0, 4), padx=(0, 18))
            setattr(self, attr_name, text)

        self.handover_risks_text.insert(
            "1.0",
            "Pohyb osob a vozidel, manipulace s materiálem, práce ve výškách, elektrická zařízení, hluk, prach.",
        )
        self.handover_measures_text.insert(
            "1.0",
            "Dodržovat pokyny odpovědné osoby, používat předepsané OOPP, udržovat pořádek, nezastavovat únikové cesty.",
        )
        self.handover_fire_text.insert(
            "1.0",
            "Dodržovat zákaz kouření a manipulace s otevřeným ohněm mimo povolená místa. Horké práce pouze na povolení.",
        )

        self.apply_handover_template()

        actions = ttk.Frame(content)
        actions.grid(row=start_row + len(text_specs) * 2, column=0, columnspan=4, sticky="w", pady=18)
        ttk.Button(actions, text="Uložit a otevřít protokol", command=self.save_handover).pack(side="left")
        self.open_handover_button = ttk.Button(
            actions,
            text="Otevřít poslední protokol",
            command=self.open_handover,
            state="disabled",
        )
        self.open_handover_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Vyčistit formulář", command=self.reset_handover).pack(side="left")
        ttk.Button(actions, text="Uložit výchozí údaje", command=self.save_current_defaults).pack(side="left", padx=8)

        content.columnconfigure(1, weight=1)
        content.columnconfigure(3, weight=1)


    def _build_risks_tab(self):
        tab = ttk.Frame(self, padding=18)
        self.notebook.add(tab, text="Rizika")

        ttk.Label(tab, text="Samostatná rizika", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        fields = [
            ("Název dokumentu", self.risk_document_title),
            ("Pracoviště / zakázka", self.risk_workplace),
            ("Dodavatel / firma", self.risk_company),
            ("Datum předání / převzetí", self.risk_handover_date),
            ("Předal", self.risk_handed_by),
            ("Převzal", self.risk_taken_by),
        ]
        for row, (label, variable) in enumerate(fields, start=1):
            ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", pady=(8, 3), padx=(0, 8))
            ttk.Entry(tab, textvariable=variable, width=46).grid(
                row=row, column=1, columnspan=2, sticky="ew", pady=(8, 3)
            )

        ttk.Label(tab, text="Typy prací / rizik").grid(row=7, column=0, sticky="nw", pady=(16, 3), padx=(0, 8))
        choices = ttk.LabelFrame(tab, text="Vyberte jednu nebo více oblastí", padding=10)
        choices.grid(row=7, column=1, columnspan=2, sticky="ew", pady=(12, 3))
        self.risk_template_vars = {}
        for index, name in enumerate(HANDOVER_TEMPLATES):
            variable = tk.BooleanVar(value=False)
            self.risk_template_vars[name] = variable
            ttk.Checkbutton(choices, text=name, variable=variable).grid(
                row=index // 2, column=index % 2, sticky="w", padx=(0, 18), pady=3
            )

        actions = ttk.Frame(tab)
        actions.grid(row=8, column=1, columnspan=2, sticky="w", pady=(12, 8))
        ttk.Button(actions, text="Sestavit rizika", command=self.build_standalone_risks).pack(side="left")
        ttk.Button(actions, text="Tisk / uložit jako PDF", command=self.print_standalone_risks).pack(side="left", padx=8)
        ttk.Button(actions, text="Vyčistit", command=self.clear_standalone_risks).pack(side="left")

        ttk.Label(tab, text="Sestavený text").grid(row=9, column=0, sticky="nw", pady=(8, 3), padx=(0, 8))
        self.risk_output_text = tk.Text(tab, height=18, wrap="word", font=("Segoe UI", 10))
        self.risk_output_text.grid(row=9, column=1, columnspan=2, sticky="nsew", pady=(8, 3))

        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(9, weight=1)


    def _build_handover_overview_tab(self):
        tab = ttk.Frame(self, padding=18)
        self.notebook.add(tab, text="Přehled předání")

        header = ttk.Frame(tab)
        header.pack(fill="x")
        ttk.Label(header, text="Přehled vydaných předání pracovišť", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Obnovit", command=self.load_handover_overview).pack(side="right")
        ttk.Button(header, text="Otevřít CSV", command=self.open_handover_csv).pack(side="right", padx=8)
        ttk.Button(header, text="Export Excel", command=self.export_handover_excel).pack(side="right")
        ttk.Button(header, text="Tisk přehledu", command=self.print_handover_overview).pack(side="right")
        ttk.Button(header, text="Tisk předání", command=self.print_selected_handover).pack(side="right", padx=8)

        ttk.Label(tab, textvariable=self.handover_overview_summary).pack(anchor="w", pady=(12, 8))

        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True)

        columns = ("datum", "pracoviste", "firma", "termin", "predal", "prevzal")
        self.handover_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)
        headings = {
            "datum": "Datum",
            "pracoviste": "Pracoviště / zakázka",
            "firma": "Dodavatel",
            "termin": "Termín",
            "predal": "Předal",
            "prevzal": "Převzal",
        }
        widths = {
            "datum": 145,
            "pracoviste": 230,
            "firma": 170,
            "termin": 140,
            "predal": 150,
            "prevzal": 150,
        }
        for column in columns:
            self.handover_tree.heading(column, text=headings[column])
            self.handover_tree.column(column, width=widths[column], anchor="w", stretch=column in {"pracoviste", "firma"})

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.handover_tree.yview)
        self.handover_tree.configure(yscrollcommand=scrollbar.set)
        self.handover_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_handover_overview()


    def _build_topics_tab(self):
        tab = ttk.Frame(self, padding=18)
        self.notebook.add(tab, text="Témata")

        header = ttk.Frame(tab)
        header.pack(fill="x")
        ttk.Label(header, text="Témata školení", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Otevřít JSON", command=self.open_training_content_file).pack(side="right")

        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True, pady=(12, 0))

        list_frame = ttk.Frame(body)
        list_frame.pack(side="left", fill="both")
        self.topic_list = tk.Listbox(list_frame, width=38, height=20, exportselection=False)
        self.topic_list.pack(side="left", fill="both", expand=True)
        topic_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.topic_list.yview)
        self.topic_list.configure(yscrollcommand=topic_scrollbar.set)
        topic_scrollbar.pack(side="right", fill="y")
        self.topic_list.bind("<<ListboxSelect>>", self._on_topic_select)

        editor = ttk.Frame(body, padding=(18, 0, 0, 0))
        editor.pack(side="left", fill="both", expand=True)
        ttk.Label(editor, text="Název tématu").pack(anchor="w")
        ttk.Entry(editor, textvariable=self.topic_title).pack(fill="x", pady=(4, 12))
        ttk.Label(editor, text="Text tématu").pack(anchor="w")
        self.topic_text = tk.Text(editor, height=14, wrap="word", font=("Segoe UI", 10))
        self.topic_text.pack(fill="both", expand=True, pady=(4, 12))

        actions = ttk.Frame(editor)
        actions.pack(fill="x")
        ttk.Button(actions, text="Nové téma", command=self.new_topic).pack(side="left")
        ttk.Button(actions, text="Uložit téma", command=self.save_topic).pack(side="left", padx=8)
        ttk.Button(actions, text="Smazat", command=self.delete_topic).pack(side="left")
        ttk.Button(actions, text="Nahoru", command=lambda: self.move_topic(-1)).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Dolů", command=lambda: self.move_topic(1)).pack(side="right")

        self.refresh_topic_list()


    def refresh_topic_list(self, select_index=None):
        self.topic_list.delete(0, "end")
        for index, (title, _text) in enumerate(self.training_sections, start=1):
            self.topic_list.insert("end", f"{index}. {title}")
        if self.training_sections:
            if select_index is None:
                select_index = 0
            select_index = max(0, min(select_index, len(self.training_sections) - 1))
            self.topic_list.selection_set(select_index)
            self.topic_list.activate(select_index)
            self.load_topic(select_index)
        else:
            self.topic_title.set("")
            self.topic_text.delete("1.0", "end")


    def _selected_topic_index(self):
        selection = self.topic_list.curselection()
        if not selection:
            return None
        return selection[0]


    def _on_topic_select(self, _event=None):
        index = self._selected_topic_index()
        if index is not None:
            self.load_topic(index)


    def load_topic(self, index):
        title, text = self.training_sections[index]
        self.topic_title.set(title)
        self.topic_text.delete("1.0", "end")
        self.topic_text.insert("1.0", text)


    def new_topic(self):
        self.topic_list.selection_clear(0, "end")
        self.topic_title.set("")
        self.topic_text.delete("1.0", "end")


    def save_topic(self):
        title = self.topic_title.get().strip()
        text = self.topic_text.get("1.0", "end").strip()
        if not title:
            messagebox.showwarning("Chybí název", "Zadejte název tématu.")
            return

        index = self._selected_topic_index()
        if index is None:
            self.training_sections.append((title, text))
            index = len(self.training_sections) - 1
        else:
            self.training_sections[index] = (title, text)
        save_training_sections(self.training_sections)
        self._populate_training_tab()
        self.refresh_topic_list(index)
        messagebox.showinfo("Téma uloženo", "Téma školení bylo uloženo.")


    def delete_topic(self):
        index = self._selected_topic_index()
        if index is None:
            messagebox.showwarning("Není vybráno téma", "Nejprve vyberte téma ke smazání.")
            return
        if not messagebox.askyesno("Smazat téma", "Opravdu chcete vybrané téma odstranit?"):
            return
        del self.training_sections[index]
        save_training_sections(self.training_sections)
        self._populate_training_tab()
        self.refresh_topic_list(min(index, len(self.training_sections) - 1) if self.training_sections else None)


    def move_topic(self, direction):
        index = self._selected_topic_index()
        if index is None:
            return
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.training_sections):
            return
        self.training_sections[index], self.training_sections[new_index] = (
            self.training_sections[new_index],
            self.training_sections[index],
        )
        save_training_sections(self.training_sections)
        self._populate_training_tab()
        self.refresh_topic_list(new_index)
