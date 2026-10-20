"""Regression coverage for FK label queries with incomplete relationship metadata."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).parents[1]


def _load_access(monkeypatch):
    app = ModuleType("app")
    core = ModuleType("app.core")
    policies = ModuleType("app.core.access_policies")
    policies.POLICIES = {
        "category": {
            "permissions": {"developer": "r"},
            "fields": {},
            "owner_field": "",
        }
    }
    monkeypatch.setitem(sys.modules, "app", app)
    monkeypatch.setitem(sys.modules, "app.core", core)
    monkeypatch.setitem(sys.modules, "app.core.access_policies", policies)

    path = ROOT / "src/onesite/templates/backend/app/core/access.py"
    spec = importlib.util.spec_from_file_location("app.core.access", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, "app.core.access", module)
    return module


def test_fk_label_scope_uses_target_table_when_generated_policy_key_is_empty(monkeypatch):
    access = _load_access(monkeypatch)

    class Category:
        __tablename__ = "category"

    statement = object()
    token = access.current_actor.set(SimpleNamespace(role="developer"))
    try:
        assert access.scope_label_statement(statement, Category, "") is statement
    finally:
        access.current_actor.reset(token)


def test_crud_templates_fall_back_to_the_resolved_source_module():
    crud_template = (ROOT / "src/onesite/templates/codegen/crud.py.j2").read_text()
    user_crud_template = (ROOT / "src/onesite/templates/codegen/user_crud.py.j2").read_text()

    assert '"{{ fk.target_service or fk.target_source_module }}"' in crud_template
    assert '"{{ fk_field.target_service or fk_field.target_source_module }}"' in crud_template
    assert '"{{ fk.target_service or fk.target_source_module }}"' in user_crud_template
