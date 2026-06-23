# -*- coding: utf-8 -*-

from urllib.parse import quote


def pictogram_data_uri(label):
    return "data:image/svg+xml;utf8," + quote(_pictogram_svg(label), safe="")


def _pictogram_svg(label):
    label_upper = label.upper()
    if label_upper in {"ELEKTRO"}:
        return _warning_svg(label, "⚡")
    if label_upper in {"POŽÁR", "HORKÉ PRÁCE"}:
        return _warning_svg(label, "🔥")
    if label_upper in {"PÁD OSOB", "PÁD PŘEDMĚTU"}:
        return _warning_svg(label, "!")
    if label_upper in {"ZÁKAZ VSTUPU"}:
        return _prohibition_svg(label, "STOP")
    if label_upper in {"OOPP", "HASIVO", "ZÁBRANA", "UZAMKNOUT"}:
        return _mandatory_svg(label)
    return _warning_svg(label, "!")


def _warning_svg(label, symbol):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="110" viewBox="0 0 96 110">
<rect width="96" height="110" rx="8" fill="white"/>
<path d="M48 9 L88 79 H8 Z" fill="#ffd400" stroke="#111" stroke-width="5"/>
<text x="48" y="60" text-anchor="middle" font-family="Arial" font-size="30" font-weight="700">{symbol}</text>
<text x="48" y="101" text-anchor="middle" font-family="Arial" font-size="10" font-weight="700">{_escape_svg(label)}</text>
</svg>"""


def _mandatory_svg(label):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="110" viewBox="0 0 96 110">
<rect width="96" height="110" rx="8" fill="white"/>
<circle cx="48" cy="45" r="34" fill="#0066cc" stroke="#111" stroke-width="3"/>
<path d="M28 48 L42 62 L70 30" fill="none" stroke="white" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
<text x="48" y="101" text-anchor="middle" font-family="Arial" font-size="10" font-weight="700">{_escape_svg(label)}</text>
</svg>"""


def _prohibition_svg(label, symbol):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="110" viewBox="0 0 96 110">
<rect width="96" height="110" rx="8" fill="white"/>
<circle cx="48" cy="45" r="34" fill="white" stroke="#d40000" stroke-width="8"/>
<line x1="25" y1="68" x2="71" y2="22" stroke="#d40000" stroke-width="8" stroke-linecap="round"/>
<text x="48" y="50" text-anchor="middle" font-family="Arial" font-size="16" font-weight="700">{symbol}</text>
<text x="48" y="101" text-anchor="middle" font-family="Arial" font-size="10" font-weight="700">{_escape_svg(label)}</text>
</svg>"""


def _escape_svg(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
