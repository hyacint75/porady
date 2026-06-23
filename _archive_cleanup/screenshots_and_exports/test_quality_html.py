from porady_quality import default_data
from porady_quality_export import _build_html


def test_export_html():
    content = _build_html(default_data())
    assert "<!doctype html>" in content
    assert "VYHODNOCENÍ KVALITY ZA KVĚTEN 2026" not in content
    assert "Vyhodnocení kvality za květen 2026" in content
    assert "Nápravná a preventivní opatření" in content
    assert "Kaas Petr" in content
    assert "@media print" in content


if __name__ == "__main__":
    test_export_html()
    print("OK: HTML export prošel kontrolou.")
