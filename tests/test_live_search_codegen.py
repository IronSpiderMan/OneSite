"""Regression coverage for debounced list filtering."""

from pathlib import Path


TEMPLATE = (
    Path(__file__).parents[1]
    / "src"
    / "onesite"
    / "templates"
    / "codegen"
    / "frontend_page_list.tsx.j2"
)


def test_list_search_reacts_to_filter_changes_with_debounce():
    template = TEMPLATE.read_text(encoding="utf-8")

    assert "const searchListenerReady = useRef(false);" in template
    assert "const timer = setTimeout(applySearch, 300);" in template
    assert "}, [searchValues]);" in template
    assert 'onClick={applySearch}' not in template


def test_list_search_grid_and_fields_can_shrink_without_overflow():
    template = TEMPLATE.read_text(encoding="utf-8")

    assert "overflow-y-auto overflow-x-hidden" in template
    assert "sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4" in template
    assert "include 'frontend_list_filter_control.tsx.j2'" in template
    template = (TEMPLATE.parent / "frontend_list_filter_control.tsx.j2").read_text(encoding="utf-8")
    assert "grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]" in template
    assert 'className="min-w-0 space-y-2"' in template
