# -*- coding: utf-8 -*-

import sys
from pathlib import Path


APP_TITLE = "Vstupní školení nových zaměstnanců"
PASS_LIMIT = 80
TRAINING_VALID_DAYS = 365
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
SOURCE_DIR = Path(__file__).resolve().parent
APP_ASSET_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
DATA_DIR = Path.home() / "Documents" / "Vstupni_skoleni_zamestnancu"
BACKUP_DIR = DATA_DIR / "zalohy"
APP_SETTINGS_FILE = DATA_DIR / "nastaveni.json"
TRAINING_CONTENT_FILE = DATA_DIR / "skoleni_obsah.json"
RESULTS_FILE = DATA_DIR / "zaznamy_skoleni.csv"
RESULTS_EXCEL_FILE = DATA_DIR / "prehled_proskolenych.xlsx"
CERTIFICATES_DIR = DATA_DIR / "potvrzeni"
OVERVIEW_PRINT_FILE = DATA_DIR / "prehled_proskolenych.html"
HANDOVER_FILE = DATA_DIR / "predani_pracoviste.csv"
HANDOVER_EXCEL_FILE = DATA_DIR / "predani_pracoviste.xlsx"
HANDOVER_DIR = DATA_DIR / "predani_pracoviste"
RISKS_DIR = DATA_DIR / "samostatna_rizika"
LEGACY_RESULTS_FILE = BASE_DIR / "zaznamy_skoleni.csv"
LEGACY_CERTIFICATES_DIR = BASE_DIR / "potvrzeni"
LEGACY_OVERVIEW_PRINT_FILE = BASE_DIR / "prehled_proskolenych.html"
LEGACY_HANDOVER_FILE = BASE_DIR / "predani_pracoviste.csv"
LEGACY_HANDOVER_DIR = BASE_DIR / "predani_pracoviste"
LEGACY_DIST_DIR = SOURCE_DIR / "dist"
LOGO_FILES = [
    APP_ASSET_DIR / "svos_logo.png",
    BASE_DIR / "svos_logo.png",
    SOURCE_DIR / "svos_logo.png",
]
