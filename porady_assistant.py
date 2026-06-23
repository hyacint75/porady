# -*- coding: utf-8 -*-

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from porady_widgets import configure_treeview_sorting


APP_NAME = "Virtuální asistent"


class VirtualAssistant(tk.Toplevel):
    def __init__(
        self,
        parent,
        *,
        collect_search_rows,
        open_search_result,
        collect_deadlines,
        app_actions,
        on_home=None,
        colors=None,
        font="Segoe UI",
    ):
        super().__init__(parent)
        self.parent = parent
        self.collect_search_rows = collect_search_rows
        self.open_search_result = open_search_result
        self.collect_deadlines = collect_deadlines
        self.app_actions = app_actions
        self.on_home = on_home
        self.COLORS = colors or {}
        self.FONT = font
        self.query_var = tk.StringVar()
        self.last_results = []

        self.title(APP_NAME)
        self.geometry("980x680")
        self.minsize(820, 560)
        self.configure(bg=self.color("app_bg", "#eef2f6"))
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.configure_styles()
        self.create_layout()
        self.after(1, self.center_on_parent)
        self.say_assistant(
            "Dobrý den. Umím poradit s aplikací, vyhledat záznamy, ukázat termíny "
            "nebo otevřít některý modul. Zkuste třeba „najdi Kaas“, „termíny“ "
            "nebo „otevři změnové řízení“."
        )

    def color(self, key, fallback):
        return self.COLORS.get(key, fallback)

    def configure_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("Assistant.Treeview", rowheight=27, font=(self.FONT, 10))
        self.style.configure("Assistant.Treeview.Heading", font=(self.FONT, 10, "bold"))

    def center_on_parent(self):
        self.update_idletasks()
        parent = self.parent.winfo_toplevel()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def close(self):
        self.destroy()
        if self.on_home:
            self.on_home()

    def create_button(self, parent, text, command, variant="secondary"):
        variants = {
            "primary": ("#2563eb", "white", "#1d4ed8", (self.FONT, 10, "bold")),
            "secondary": ("#e6edf7", self.color("text", "#17202a"), "#d7e3f3", (self.FONT, 10)),
        }
        bg, fg, active_bg, font = variants[variant]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            font=font,
            relief=tk.FLAT,
            borderwidth=0,
            padx=14,
            pady=8,
            cursor="hand2",
        )

    def create_layout(self):
        shell = tk.Frame(self, bg=self.color("app_bg", "#eef2f6"), padx=22, pady=22)
        shell.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(shell, bg=self.color("app_bg", "#eef2f6"))
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=APP_NAME,
            font=(self.FONT, 22, "bold"),
            bg=self.color("app_bg", "#eef2f6"),
            fg=self.color("text", "#17202a"),
        ).pack(side=tk.LEFT)
        self.create_button(header, "← Rozcestník", self.close).pack(side=tk.RIGHT)

        panel = tk.Frame(
            shell,
            bg="white",
            padx=18,
            pady=18,
            highlightthickness=1,
            highlightbackground=self.color("border", "#d7dee8"),
        )
        panel.pack(fill=tk.BOTH, expand=True, pady=(18, 0))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        panel.rowconfigure(3, weight=1)

        quick = tk.Frame(panel, bg="white")
        quick.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        quick_items = (
            ("Termíny", "termíny"),
            ("Hledat otevřené položky", "najdi otevřené"),
            ("Změnové řízení", "otevři změnové řízení"),
            ("Jak založit podnět", "jak založit podnět"),
            ("Nápověda", "nápověda"),
        )
        for text, command_text in quick_items:
            self.create_button(
                quick,
                text,
                lambda value=command_text: self.run_prompt(value),
            ).pack(side=tk.LEFT, padx=(0, 8), pady=(0, 4))

        self.chat = tk.Text(
            panel,
            height=13,
            wrap="word",
            font=(self.FONT, 10),
            bg="#f8fafc",
            fg=self.color("text", "#17202a"),
            relief=tk.SOLID,
            borderwidth=1,
            padx=12,
            pady=10,
        )
        self.chat.grid(row=1, column=0, sticky="nsew")
        self.chat.tag_configure("assistant", foreground="#1d4ed8", font=(self.FONT, 10, "bold"))
        self.chat.tag_configure("user", foreground="#0f766e", font=(self.FONT, 10, "bold"))
        self.chat.configure(state="disabled")

        entry_row = tk.Frame(panel, bg="white")
        entry_row.grid(row=2, column=0, sticky="ew", pady=(12, 12))
        entry_row.columnconfigure(0, weight=1)
        entry = ttk.Entry(entry_row, textvariable=self.query_var, font=(self.FONT, 11))
        entry.grid(row=0, column=0, sticky="ew", ipady=4)
        entry.bind("<Return>", lambda _event: self.submit())
        self.create_button(entry_row, "Odeslat", self.submit, "primary").grid(row=0, column=1, padx=(10, 0))

        result_frame = tk.Frame(panel, bg="white")
        result_frame.grid(row=3, column=0, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        columns = ("source", "type", "title", "date", "detail")
        self.results_tree = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Assistant.Treeview",
        )
        for key, label, width in (
            ("source", "Aplikace", 150),
            ("type", "Typ", 140),
            ("title", "Název", 280),
            ("date", "Datum", 110),
            ("detail", "Podrobnosti", 360),
        ):
            self.results_tree.heading(key, text=label)
            self.results_tree.column(key, width=width, anchor="w")
        configure_treeview_sorting(self.results_tree, column_types={"date": "date"})
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_tree.bind("<Double-1>", lambda _event: self.open_selected_result())
        self.results_tree.bind("<Return>", lambda _event: self.open_selected_result())

        bottom = tk.Frame(panel, bg="white")
        bottom.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        self.create_button(bottom, "Otevřít vybrané", self.open_selected_result, "primary").pack(side=tk.LEFT)
        self.create_button(bottom, "Vyčistit", self.clear_chat).pack(side=tk.LEFT, padx=(8, 0))

        entry.focus_set()

    def submit(self):
        query = self.query_var.get().strip()
        if not query:
            return
        self.query_var.set("")
        self.run_prompt(query)

    def run_prompt(self, query):
        self.say_user(query)
        response = self.handle_query(query)
        if response:
            self.say_assistant(response)

    def say_user(self, message):
        self.append_chat("Vy: ", message, "user")

    def say_assistant(self, message):
        self.append_chat("Asistent: ", message, "assistant")

    def append_chat(self, prefix, message, tag):
        self.chat.configure(state="normal")
        self.chat.insert(tk.END, prefix, tag)
        self.chat.insert(tk.END, message.strip() + "\n\n")
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def clear_chat(self):
        self.chat.configure(state="normal")
        self.chat.delete("1.0", tk.END)
        self.chat.configure(state="disabled")
        self.clear_results()
        self.say_assistant("Historie je prázdná. Jak můžu pomoct?")

    def handle_query(self, raw_query):
        query = raw_query.strip()
        normalized = query.casefold()

        if normalized in {"ahoj", "dobrý den", "dobry den", "čau", "cau"}:
            return "Dobrý den. Můžu hledat záznamy, otevřít modul nebo vysvětlit postupy v aplikaci."

        if any(word in normalized for word in ("nápověda", "napoveda", "pomoc", "co umíš", "co umis")):
            return (
                "Umím například: „najdi text“, „termíny“, „otevři změnové řízení“, "
                "„otevři kvalitu“, „jak založit podnět“ nebo „co je po termínu“. "
                "Výsledky hledání se zobrazí dole a vybraný řádek lze otevřít."
            )

        if "term" in normalized or "po term" in normalized or "deadline" in normalized:
            return self.show_deadlines(only_overdue="po term" in normalized)

        opened = self.try_open_module(normalized)
        if opened:
            return opened

        if "jak" in normalized and ("podnět" in normalized or "podnet" in normalized or "změn" in normalized or "zmen" in normalized):
            return (
                "Ve Změnovém řízení klikněte na Admin, přihlaste se, zvolte Nový podnět, "
                "doplňte oblast, současný stav, návrh změny, zdůvodnění a dopady. "
                "Číslo podnětu se přidělí automaticky."
            )

        search_query = self.extract_search_query(query)
        if search_query:
            return self.search(search_query)

        return self.search(query)

    def try_open_module(self, normalized):
        action_map = (
            (("změnové", "zmenove", "podnět", "podnet"), "change_management", "Otevírám Změnové řízení."),
            (("zakázk", "zakazk"), "job_evaluation", "Otevírám Vyhodnocení zakázky."),
            (("kvalit",), "quality", "Otevírám Vyhodnocení kvality."),
            (("požadav", "pozadav"), "requirements", "Otevírám Požadavky."),
            (("problém", "problem", "opatřen", "opatren"), "problems", "Otevírám Problémy a opatření."),
            (("porad", "zápis", "zapis"), "meetings", "Otevírám Porady a zápisy."),
            (("extern",), "external_companies", "Otevírám Externí firmy."),
            (("vstupní", "vstupni", "školen", "skolen"), "entry_training", "Otevírám Vstupní školení."),
        )
        wants_open = any(word in normalized for word in ("otevři", "otevri", "spusť", "spust", "ukaž", "ukaz"))
        if not wants_open:
            return ""
        for keywords, action_key, message in action_map:
            if any(keyword in normalized for keyword in keywords):
                action = self.app_actions.get(action_key)
                if action:
                    action()
                    return message
        return ""

    @staticmethod
    def extract_search_query(query):
        normalized = query.casefold().strip()
        prefixes = ("najdi ", "hledej ", "vyhledej ", "najít ", "najit ", "hledat ")
        for prefix in prefixes:
            if normalized.startswith(prefix):
                return query[len(prefix):].strip()
        return ""

    def search(self, query):
        rows = self.collect_search_rows(query, include_metadata=True)
        rows = rows[:25]
        self.show_results(rows)
        if not rows:
            return f"Pro dotaz „{query}“ jsem nenašel žádný záznam."
        preview = []
        for row in rows[:5]:
            source, record_type, title, event_date, _detail = row["display"]
            date_part = f" ({event_date})" if event_date else ""
            preview.append(f"{source} / {record_type}: {title}{date_part}")
        return "Našel jsem tyto výsledky:\n" + "\n".join(f"- {item}" for item in preview)

    def show_results(self, rows):
        self.clear_results()
        self.last_results = rows
        for index, row in enumerate(rows):
            source, record_type, title, event_date, detail = row["display"]
            self.results_tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    source,
                    record_type,
                    self.short_text(title, 80),
                    event_date,
                    self.short_text(detail, 110),
                ),
            )

    def clear_results(self):
        self.results_tree.delete(*self.results_tree.get_children())
        self.last_results = []

    def open_selected_result(self):
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning(APP_NAME, "Vyberte výsledek ze seznamu.", parent=self)
            return
        index = int(selection[0])
        if index >= len(self.last_results):
            return
        self.open_search_result(self.last_results[index], self)

    def show_deadlines(self, only_overdue=False):
        today = date.today()
        records = []
        for due_date, record_type, title, owner in self.collect_deadlines():
            days = (due_date - today).days
            if only_overdue and days >= 0:
                continue
            records.append((days, due_date, record_type, title, owner))
        records = records[:12]
        if not records:
            return "Nenašel jsem žádné termíny po termínu." if only_overdue else "Nenašel jsem žádné společné termíny."
        lines = []
        for days, due_date, record_type, title, owner in records:
            state = f"{abs(days)} dnů po termínu" if days < 0 else ("dnes" if days == 0 else f"za {days} dnů")
            owner_part = f" / {owner}" if owner else ""
            lines.append(f"{due_date.strftime('%d.%m.%Y')} ({state}) - {record_type}: {title}{owner_part}")
        return "Nejbližší termíny:\n" + "\n".join(f"- {line}" for line in lines)

    @staticmethod
    def short_text(value, max_length):
        text = " ".join(str(value or "").split())
        return text if len(text) <= max_length else text[: max_length - 1] + "…"
