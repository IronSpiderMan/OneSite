from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_RESOURCES_TEMPLATE = (
    ROOT
    / "src"
    / "onesite"
    / "templates"
    / "codegen"
    / "frontend_external_resources_page.tsx.j2"
)


def test_external_resources_provider_table_stays_scrollable() -> None:
    template = EXTERNAL_RESOURCES_TEMPLATE.read_text(encoding="utf-8")

    assert 'className="flex h-full min-h-0 flex-col gap-5 p-6"' in template
    assert 'className="min-h-0 flex-1 overflow-auto rounded-lg border bg-card"' in template
    assert 'className="sticky top-0 z-20 border-b bg-muted text-left shadow-sm"' in template
    assert "ExternalProviderState" in template
    assert "row.provider" in template
    assert "entity_id" not in template
