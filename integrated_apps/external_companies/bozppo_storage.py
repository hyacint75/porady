# -*- coding: utf-8 -*-

import datetime as dt
import shutil

from .bozppo_config import (
    BACKUP_DIR,
    CERTIFICATES_DIR,
    DATA_DIR,
    HANDOVER_DIR,
    HANDOVER_FILE,
    LEGACY_CERTIFICATES_DIR,
    LEGACY_DIST_DIR,
    LEGACY_HANDOVER_DIR,
    LEGACY_HANDOVER_FILE,
    LEGACY_OVERVIEW_PRINT_FILE,
    LEGACY_RESULTS_FILE,
    OVERVIEW_PRINT_FILE,
    RESULTS_FILE,
)


def prepare_data_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _copy_first_existing_file((LEGACY_RESULTS_FILE, LEGACY_DIST_DIR / "zaznamy_skoleni.csv"), RESULTS_FILE)
    _copy_first_existing_file((LEGACY_HANDOVER_FILE, LEGACY_DIST_DIR / "predani_pracoviste.csv"), HANDOVER_FILE)
    _copy_first_existing_file((LEGACY_OVERVIEW_PRINT_FILE, LEGACY_DIST_DIR / "prehled_proskolenych.html"), OVERVIEW_PRINT_FILE)
    _copy_first_existing_dir((LEGACY_CERTIFICATES_DIR, LEGACY_DIST_DIR / "potvrzeni"), CERTIFICATES_DIR)
    _copy_first_existing_dir((LEGACY_HANDOVER_DIR, LEGACY_DIST_DIR / "predani_pracoviste"), HANDOVER_DIR)

def _copy_first_existing_file(sources, target):
    for source in sources:
        if _copy_file_if_missing(source, target):
            return True
    return False

def _copy_first_existing_dir(sources, target):
    for source in sources:
        if _copy_dir_if_missing(source, target):
            return True
    return False

def _copy_file_if_missing(source, target):
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True
    return False

def _copy_dir_if_missing(source, target):
    if source.exists() and not target.exists():
        shutil.copytree(source, target)
        return True
    return False

def backup_file(path):
    if not path.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = BACKUP_DIR / f"{path.stem}_{timestamp}{path.suffix}"
    shutil.copy2(path, backup_path)

def parse_czech_date(value):
    value = value.strip()
    if not value:
        return None
    for date_format in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None
