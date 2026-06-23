# -*- coding: utf-8 -*-

import json

from .bozppo_config import APP_SETTINGS_FILE


def load_app_settings():
    if not APP_SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_app_settings(settings):
    APP_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    APP_SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
