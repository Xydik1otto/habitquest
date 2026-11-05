"""Tests: accessibility — aria-labels, keyboard navigation, contrast tokens."""
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_static_html_has_aria_labels_on_key_interactive_elements():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    # every input/select in the static shell is labelled
    for anchor in ("h-name", "h-icon", "h-category", "h-schedule", "h-target",
                   "q-habit", "q-target", "wq-h1", "wq-target",
                   "a-id", "a-name", "a-desc", "a-metric", "a-threshold",
                   "recap-month", "import-file", "lang-switch"):
        line = next(l for l in html.splitlines() if f'id="{anchor}"' in l)
        assert "aria-label=" in line, f"#{anchor} lacks aria-label"
    # landmarks and live region
    assert 'id="main"' in html and "skip-link" in html
    assert "progressbar" in html and "aria-live" in html


def test_dynamic_controls_get_aria_labels_from_js():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'aria-label' in js
    for label in ("— відмітити сьогодні", "Заморозити сьогодні для звички",
                  "Графік серії за 30 днів для звички", "Видалити звичку"):
        assert label in js
    assert 'aria-valuenow' in js  # progressbar is kept in sync


def test_css_has_focus_outline_and_skip_link():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert ":focus-visible" in css and ".skip-link" in css
    # contrast: the darkest text tone on the dark card must still be readable (#888 on #1c1c28 ≈ 4.6:1)
    assert "#888" in css or "#999" in css
