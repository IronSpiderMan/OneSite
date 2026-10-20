from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIST_TEMPLATE = ROOT / "src" / "onesite" / "templates" / "codegen" / "frontend_page_list.tsx.j2"
LAYOUT_TEMPLATE = ROOT / "src" / "onesite" / "templates" / "frontend" / "src" / "components" / "Layout.tsx"


def test_list_page_uses_remaining_height_for_scrollable_table() -> None:
    template = LIST_TEMPLATE.read_text(encoding="utf-8")

    assert "flex h-full min-h-0 flex-col gap-6" in template
    assert "flex-1 min-h-0 overflow-hidden border rounded-md" in template
    assert "[&>[data-ui=table-container]]:h-full" in template
    assert '<TableHeader className="sticky top-0 z-20 bg-card shadow-sm">' in template
    assert "shrink-0 flex flex-wrap items-center justify-between" in template


def test_application_shell_has_a_bounded_content_height() -> None:
    template = LAYOUT_TEMPLATE.read_text(encoding="utf-8")

    assert 'cn("h-screen overflow-hidden flex"' in template
    assert 'cn("flex-1 flex flex-col min-w-0 min-h-0"' in template
    assert 'cn("flex-1 min-h-0 p-6 overflow-auto"' in template
