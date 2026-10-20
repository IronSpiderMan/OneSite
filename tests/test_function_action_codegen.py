"""Coverage for function-based model actions and dynamic availability."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.phases.introspect_models import _introspect_module
from onesite.codegen.phases.relationships import phase_resolve_relationships
from onesite.codegen.phases.sync_models import phase_sync_models
from onesite_runtime import (
    ActionContext,
    ActionState,
    action,
    evaluate_action_state,
    invoke_action_callable,
)


class FunctionActionModel(SQLModel, table=True):
    __tablename__ = "test_function_action_model"

    id: int | None = Field(default=None, primary_key=True)
    enabled: bool = False

    @action(permissions="da", label="Toggle", unavailable="disable")
    def toggle_enabled(self, *, context: ActionContext):
        self.enabled = not self.enabled

    @toggle_enabled.available
    async def can_toggle_enabled(self, *, current_user):
        return ActionState(
            visible=True,
            enabled=not self.enabled,
            reason=None if not self.enabled else f"Disabled for {current_user}",
        )


class StaticConditionActionModel(SQLModel, table=True):
    __tablename__ = "test_static_condition_action_model"

    id: int | None = Field(default=None, primary_key=True)
    status: str = "draft"

    @action(condition={"field": "status", "op": "eq", "value": "draft"})
    def publish(self):
        self.status = "published"


class ActionParent(SQLModel, table=True):
    __tablename__ = "test_action_parent"

    id: int | None = Field(default=None, primary_key=True)
    name: str


class ActionChild(SQLModel, table=True):
    __tablename__ = "test_action_child"

    id: int | None = Field(default=None, primary_key=True)
    action_parent_id: int = Field(
        foreign_key="test_action_parent.id",
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "target_service": "action_parent",
                    "reverse": {"editor": "table"},
                }
            }
        },
    )
    enabled: bool = False

    @action(unavailable="disable")
    def toggle(self):
        self.enabled = not self.enabled

    @toggle.available
    def can_toggle(self):
        return not self.enabled


def _model(model_class: type[SQLModel], module_name: str):
    models = _introspect_module(
        SimpleNamespace(**{model_class.__name__: model_class}),
        module_name,
    )
    assert models is not None
    return models[0]


def _render(template_name: str, model) -> str:
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(template_dir)).get_template(
        template_name
    ).render(model=model)


def test_function_action_metadata_is_extracted_and_normalized():
    model = _model(FunctionActionModel, "function_action_model")
    action_config = model.actions["toggle_enabled"]

    assert action_config == {
        "function": True,
        "handler": "toggle_enabled",
        "permissions": "da",
        "label": "Toggle",
        "unavailable": "disable",
        "condition": None,
        "availability_handler": "can_toggle_enabled",
        "dynamic_availability": True,
    }
    assert model.has_function_actions is True
    assert model.has_dynamic_action_states is True


def test_function_action_backend_uses_orm_object_guard_and_transaction():
    api = _render("api.py.j2", _model(FunctionActionModel, "function_action_model"))

    assert '@router.post("/action-states")' in api
    assert "objects = (await session.exec(statement)).all()" in api
    assert "obj = await crud.get(session, id)" in api
    assert 'availability_handler="can_toggle_enabled"' in api
    assert 'getattr(obj, "toggle_enabled")' in api
    assert "await session.commit()" in api
    assert "await session.rollback()" in api
    assert "status_code=409" in api


def test_dynamic_action_state_is_loaded_by_list_and_detail_pages():
    model = _model(FunctionActionModel, "function_action_model")
    service = _render("frontend_service.ts.j2", model)
    list_page = _render("frontend_page_list.tsx.j2", model)
    detail_page = _render("frontend_page_detail.tsx.j2", model)

    assert "getFunctionActionModelActionStates" in service
    assert "`${API_URL}/action-states`" in service
    assert "getFunctionActionModelActionStates(ids)" in list_page
    assert 'actionStates[String(item.id)]?.["toggle_enabled"]' in list_page
    assert "disabled={!actionStates" in list_page
    assert "getFunctionActionModelActionStates([currentItem.id])" in detail_page
    assert 'actionStates[String(currentItem.id)]?.["toggle_enabled"]' in detail_page


def test_reverse_relation_action_table_loads_dynamic_states():
    parent = _model(ActionParent, "action_parent")
    child = _model(ActionChild, "action_child")
    phase_resolve_relationships([parent, child])

    relation = next(
        item for item in parent.reverse_foreign_keys
        if item["source_model"] == "ActionChild"
    )
    assert relation["has_dynamic_action_states"] is True

    detail_page = _render("frontend_page_detail.tsx.j2", parent)
    assert "getActionChildActionStates" in detail_page
    assert "setActionChildActionStates(states)" in detail_page
    assert 'ActionStates[String(item.id)]?.["toggle"]' in detail_page


def test_static_function_condition_keeps_existing_frontend_and_backend_checks():
    model = _model(StaticConditionActionModel, "static_condition_action_model")
    api = _render("api.py.j2", model)
    page = _render("frontend_page_list.tsx.j2", model)

    assert model.has_function_actions is True
    assert model.has_dynamic_action_states is False
    assert 'condition = action_data.get("condition")' in api
    assert 'const cond = {"field": "status", "op": "eq", "value": "draft"}' in page
    assert "ActionContext" in api
    assert "availability_handler=None" in api
    assert "availability_handler=null" not in api
    assert "/action-states" not in api


def test_decorated_action_and_availability_are_invoked_with_named_context():
    obj = FunctionActionModel(id=1)
    context = ActionContext(session=object(), user="admin-user", action_name="toggle_enabled")

    initial = asyncio.run(
        evaluate_action_state(
            obj,
            availability_handler="can_toggle_enabled",
            unavailable="disable",
            context=context,
        )
    )
    assert initial == ActionState(visible=True, enabled=True)

    asyncio.run(invoke_action_callable(obj.toggle_enabled, context))
    assert obj.enabled is True

    unavailable = asyncio.run(
        evaluate_action_state(
            obj,
            availability_handler="can_toggle_enabled",
            unavailable="disable",
            context=context,
        )
    )
    assert unavailable.enabled is False
    assert unavailable.reason == "Disabled for admin-user"


def test_action_rejects_dynamic_and_static_conditions_together():
    class InvalidActionModel(SQLModel, table=True):
        __tablename__ = "test_invalid_action_model"
        id: int | None = Field(default=None, primary_key=True)

        @action(condition={"field": "id", "op": "is_not_null"})
        def run(self):
            pass

        @run.available
        def can_run(self):
            return True

    with pytest.raises(ValueError, match="cannot define both"):
        _model(InvalidActionModel, "invalid_action_model")


def test_function_action_cannot_duplicate_legacy_configuration():
    class DuplicateActionModel(SQLModel, table=True):
        __tablename__ = "test_duplicate_action_model"
        __onesite__ = {"actions": {"run": {"data": {"id": "{{value}}"}}}}
        id: int | None = Field(default=None, primary_key=True)

        @action
        def run(self):
            pass

    with pytest.raises(ValueError, match="both __onesite__ and decorated methods"):
        _model(DuplicateActionModel, "duplicate_action_model")


def test_action_runtime_is_copied_into_generated_app(tmp_path):
    backend_path = tmp_path / "generated" / "backend"

    phase_sync_models(tmp_path, backend_path)

    runtime_path = backend_path / "app" / "core" / "action_runtime.py"
    assert runtime_path.exists()
    assert "def action(" in runtime_path.read_text(encoding="utf-8")
    assert not (backend_path / "onesite_runtime").exists()
