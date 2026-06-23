# -*- coding: utf-8 -*-

import csv
import datetime as dt
import webbrowser
from tkinter import messagebox

from .bozppo_config import CERTIFICATES_DIR, PASS_LIMIT, RESULTS_EXCEL_FILE, RESULTS_FILE, TRAINING_VALID_DAYS
from .bozppo_excel import write_xlsx
from .bozppo_storage import backup_file


class TrainingResultsMixin:
    def evaluate_test(self):
        if not self._validate_identity():
            self.notebook.select(0)
            return

        unanswered = [index + 1 for index, answer in enumerate(self.answers) if answer.get() == -1]
        if unanswered:
            messagebox.showwarning("Nevyplněný test", f"Doplňte odpovědi u otázek: {', '.join(map(str, unanswered))}.")
            return

        correct = sum(
            1 for index, question in enumerate(self.test_questions) if self.answers[index].get() == question["answer"]
        )
        percent = round(correct / len(self.test_questions) * 100)
        passed = percent >= PASS_LIMIT
        result = "SPLNĚNO" if passed else "NESPLNĚNO"
        if self._has_result_today() and not messagebox.askyesno(
            "Duplicitní záznam",
            "Stejný pracovník ze stejné firmy už má dnes uložené školení. Chcete uložit další záznam?",
        ):
            return

        summary = self._build_summary(correct, percent, result)
        self._show_result(summary, percent, result)
        self._save_result(correct, percent, result)
        self.last_certificate_path = self._save_certificate(correct, percent, result) if passed else None
        self.open_certificate_button.configure(state="normal" if self.last_certificate_path else "disabled")
        self.load_overview()
        self.notebook.select(3)

        if passed:
            messagebox.showinfo(
                "Test splněn",
                "Školení bylo úspěšně dokončeno. Záznam i potvrzení o proškolení byly uloženy.",
            )
        else:
            messagebox.showwarning("Test nesplněn", "Test nebyl splněn. Projděte školení znovu a test opakujte.")


    def _validate_identity(self):
        missing = []
        if not self.worker_name.get().strip():
            missing.append("jméno pracovníka")
        if not self.company_name.get().strip():
            missing.append("externí firma")
        if not self.trainer_name.get().strip():
            missing.append("školitel")
        if missing:
            messagebox.showwarning("Chybí údaje", "Doplňte prosím: " + ", ".join(missing) + ".")
            return False
        return True


    def _build_summary(self, correct, percent, result):
        lines = [
            f"Pracovník: {self.worker_name.get().strip()}",
            f"Firma: {self.company_name.get().strip()}",
            f"Školitel: {self.trainer_name.get().strip()}",
            f"Datum: {dt.datetime.now().strftime('%d.%m.%Y %H:%M')}",
            f"Výsledek: {result}",
            f"Skóre: {correct}/{len(self.test_questions)} ({percent} %)",
            "",
            "Přehled odpovědí:",
        ]

        for index, question in enumerate(self.test_questions):
            selected = self.answers[index].get()
            correct_answer = question["answer"]
            mark = "OK" if selected == correct_answer else "CHYBA"
            lines.extend(
                [
                    f"{index + 1}. {question['text']}",
                    f"   Odpověď: {question['options'][selected]}",
                    f"   Správně: {question['options'][correct_answer]} [{mark}]",
                ]
            )
        return "\n".join(lines)


    def _show_result(self, summary, percent, result):
        color = "#1b5e20" if result == "SPLNĚNO" else "#b71c1c"
        self.result_label.configure(text=f"{result} - {percent} %", foreground=color)
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", summary)
        self.detail_text.configure(state="disabled")


    def _has_result_today(self):
        worker = self.worker_name.get().strip().casefold()
        company = self.company_name.get().strip().casefold()
        today = dt.date.today()
        for row in self._read_result_rows():
            if row["pracovnik"].strip().casefold() != worker:
                continue
            if row["firma"].strip().casefold() != company:
                continue
            if self._result_date(row["datum"]) == today:
                return True
        return False


    def _save_result(self, correct, percent, result):
        now = dt.datetime.now()
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_exists = RESULTS_FILE.exists()
        backup_file(RESULTS_FILE)
        with RESULTS_FILE.open("a", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            if not file_exists:
                writer.writerow(
                    [
                        "datum",
                        "pracovník",
                        "firma",
                        "školitel",
                        "správně",
                        "celkem",
                        "procenta",
                        "výsledek",
                    ]
                )
            writer.writerow(
                [
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    self.worker_name.get().strip(),
                    self.company_name.get().strip(),
                    self.trainer_name.get().strip(),
                    correct,
                    len(self.test_questions),
                    percent,
                    result,
                ]
            )
        self.notify_data_changed()


    def _save_certificate(self, correct, percent, result):
        CERTIFICATES_DIR.mkdir(exist_ok=True)
        now = dt.datetime.now()
        worker = self.worker_name.get().strip()
        company = self.company_name.get().strip()
        trainer = self.trainer_name.get().strip()
        file_stem = self._safe_filename(f"{now:%Y-%m-%d_%H-%M}_{worker}_{company}")
        certificate_path = CERTIFICATES_DIR / f"{file_stem}.html"
        row = {
            "datum": now.strftime("%d.%m.%Y %H:%M"),
            "pracovnik": worker,
            "firma": company,
            "skolitel": trainer,
            "spravne": correct,
            "celkem": len(self.test_questions),
            "procenta": percent,
            "vysledek": result,
        }
        html = self._build_certificate_html(row)
        certificate_path.write_text(html, encoding="utf-8")
        return certificate_path


    def open_certificate(self):
        if not self.last_certificate_path or not self.last_certificate_path.exists():
            messagebox.showwarning("Potvrzení nenalezeno", "Nejprve úspěšně vyhodnoťte test.")
            return
        webbrowser.open(self.last_certificate_path.as_uri())


    def load_overview(self):
        if not hasattr(self, "overview_tree"):
            return

        for item in self.overview_tree.get_children():
            self.overview_tree.delete(item)

        rows = self._read_result_rows()
        self._add_attempt_numbers(rows)
        passed_count = sum(1 for row in rows if self._normalize_result(row["vysledek"]) == "SPLNĚNO")
        failed_count = sum(1 for row in rows if self._normalize_result(row["vysledek"]) == "NESPLNĚNO")

        filtered_rows = self._filter_overview_rows(rows)

        for row in reversed(filtered_rows):
            validity = self._training_validity(row)
            self.overview_tree.insert(
                "",
                "end",
                values=(
                    row["datum"],
                    row["pracovnik"],
                    row["firma"],
                    row["skolitel"],
                    row.get("pokus", ""),
                    f"{row['spravne']}/{row['celkem']}",
                    row["procenta"],
                    self._normalize_result(row["vysledek"]),
                    validity,
                ),
            )

        if rows:
            self.overview_summary.set(
                f"Celkem záznamů: {len(rows)} | Zobrazeno: {len(filtered_rows)} | Splněno: {passed_count} | Nesplněno: {failed_count}"
            )
        else:
            self.overview_summary.set("Zatím nejsou uložené žádné záznamy o proškolení.")


    def _filter_overview_rows(self, rows):
        query = self.overview_search.get().strip().casefold()
        result_filter = self.overview_result_filter.get()
        validity_filter = self.overview_validity_filter.get()
        filtered = []
        for row in rows:
            if query:
                searchable = " ".join(
                    str(row.get(key, "")) for key in ("datum", "pracovnik", "firma", "skolitel", "vysledek")
                ).casefold()
                if query not in searchable:
                    continue
            if result_filter != "Vše" and self._normalize_result(row.get("vysledek", "")) != result_filter:
                continue
            validity = self._training_validity(row)
            if validity_filter != "Vše" and validity_filter not in validity:
                continue
            filtered.append(row)
        return filtered


    @staticmethod
    def _add_attempt_numbers(rows):
        attempts = {}
        for row in rows:
            key = (row["pracovnik"].strip().casefold(), row["firma"].strip().casefold())
            attempts[key] = attempts.get(key, 0) + 1
            row["pokus"] = attempts[key]


    def _training_validity(self, row):
        if self._normalize_result(row.get("vysledek", "")) != "SPLNĚNO":
            return "Nesplněno"

        completed_at = self._result_date(row.get("datum", ""))
        if not completed_at:
            return "Neznámá"

        days_left = TRAINING_VALID_DAYS - (dt.date.today() - completed_at).days
        if days_left < 0:
            return "Propadlé"
        if days_left <= 30:
            return f"Končí ({days_left} dnů)"
        return f"Platné ({days_left} dnů)"


    @staticmethod
    def _normalize_result(value):
        text = str(value).strip().upper()
        replacements = {
            "SPLNÄšNO": "SPLNĚNO",
            "NESPLNÄšNO": "NESPLNĚNO",
        }
        return replacements.get(text, text)


    @staticmethod
    def _result_date(value):
        value = str(value).strip()
        for date_format in ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
            try:
                return dt.datetime.strptime(value, date_format).date()
            except ValueError:
                continue
        return None


    def _read_result_rows(self):
        if not RESULTS_FILE.exists():
            return []

        rows = []
        with RESULTS_FILE.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file, delimiter=";")
            next(reader, None)
            for values in reader:
                if len(values) < 8:
                    continue
                rows.append(
                    {
                        "datum": values[0],
                        "pracovnik": values[1],
                        "firma": values[2],
                        "skolitel": values[3],
                        "spravne": values[4],
                        "celkem": values[5],
                        "procenta": values[6],
                        "vysledek": values[7],
                    }
                )
        return rows


    def open_results_file(self):
        if not RESULTS_FILE.exists():
            messagebox.showwarning("Soubor nenalezen", "Zatím nebyl vytvořen žádný záznam o školení.")
            return
        webbrowser.open(RESULTS_FILE.as_uri())


    def export_results_excel(self):
        rows = self._filter_overview_rows(self._read_result_rows())
        if not rows:
            messagebox.showwarning("Přehled je prázdný", "Není co exportovat do Excelu.")
            return

        headers = ["Datum", "Pracovník", "Firma", "Školitel", "Pokus", "Skóre", "%", "Výsledek", "Platnost"]
        data = [
            [
                row["datum"],
                row["pracovnik"],
                row["firma"],
                row["skolitel"],
                row.get("pokus", ""),
                f"{row['spravne']}/{row['celkem']}",
                row["procenta"],
                self._normalize_result(row["vysledek"]),
                self._training_validity(row),
            ]
            for row in reversed(rows)
        ]
        write_xlsx(RESULTS_EXCEL_FILE, "Proskoleni", headers, data)
        webbrowser.open(RESULTS_EXCEL_FILE.as_uri())


    def reset_form(self):
        self.worker_name.set("")
        self.company_name.set("")
        self.trainer_name.set("")
        self.last_certificate_path = None
        self.open_certificate_button.configure(state="disabled")
        for answer in self.answers:
            answer.set(-1)
        self.result_label.configure(text="Test zatím nebyl vyhodnocen.", foreground="black")
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", "Po vyhodnocení se zde zobrazí souhrn odpovědí.")
        self.detail_text.configure(state="disabled")
        self.notebook.select(0)
