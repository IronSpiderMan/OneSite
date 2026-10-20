"""Regression coverage for transactional model lifecycle hooks."""

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Optional

from jinja2 import Environment, FileSystemLoader
import pytest
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import (
    _build_model_dict,
    _validate_service_hooks,
)


class HookedRecord(SQLModel, table=True):
    __tablename__ = "test_hooked_record"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    async def on_before_create(self, session):
        self.name = self.name.strip()

    async def on_after_update(self, session, old, context):
        pass

    @classmethod
    async def on_after_bulk_delete(cls, session, olds, context):
        pass

    @classmethod
    async def on_after_commit_bulk_delete(cls, olds, context):
        pass

def _model():
    result = get_model_fields(HookedRecord, "hooked_record")
    model = _build_model_dict(
        "HookedRecord",
        "hooked_record",
        "hooked_record",
        result,
    )
    model.update(
        m2m_fields=[],
        reverse_m2m=[],
        reverse_definition_bindings=[],
        definition_binding_meta=None,
        is_timescaledb=False,
        is_notification_table=False,
    )
    return model


def test_regular_crud_and_service_render_with_transaction_boundaries():
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    model = _model()

    crud = environment.get_template("crud.py.j2").render(
        model=model,
        is_postgresql=False,
    )
    service = environment.get_template("service.py.j2").render(model=model)

    compile(crud, "generated_crud.py", "exec")
    compile(service, "generated_service.py", "exec")
    assert '"on_before_create"' in crud
    assert '"on_after_update"' in crud
    assert "await session.flush()" in crud
    assert "auto_commit: bool = True" in crud
    assert "@transactional_write" in crud
    assert "await crud.create(session, obj_in)" in service
    assert '"on_after_commit_delete"' in service
    assert '"on_after_bulk_delete"' in service
    assert '"on_after_commit_bulk_delete"' in service
    assert 'operation="bulk_delete"' in service
    assert "publish_model_background_hook" not in service


def test_external_resource_service_uses_standard_crud_transaction():
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    model = _model()
    model["external_resource"] = {
        "provider": "edgeflow",
        "resource": "records",
        "identity_field": "id",
    }

    service = environment.get_template("service.py.j2").render(model=model)

    compile(service, "generated_external_service.py", "exec")
    assert "await enqueue_external_resource_change(" not in service
    assert "from app.core.external_resources" not in service
    assert "await crud.create(session, obj_in)" in service
    assert "await crud.update(session, db_obj, obj_in)" in service
    assert "await crud.delete(session, id)" in service


def test_specialized_user_and_singleton_services_render_valid_python():
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    model = _model()

    for template_name in (
        "user_crud.py.j2",
        "user_service.py.j2",
        "singleton_crud.py.j2",
        "singleton_service.py.j2",
    ):
        rendered = environment.get_template(template_name).render(
            model=model,
            is_postgresql=False,
        )
        compile(rendered, template_name, "exec")


def test_singleton_crud_recovers_when_another_request_creates_the_row():
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))

    rendered = environment.get_template("singleton_crud.py.j2").render(model=_model())

    assert "Another request may have created the singleton" in rendered
    assert "result = await session.exec(statement)" in rendered
    assert "if not db_obj:" in rendered


def test_external_sync_is_hidden_from_specialized_services():
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    model = _model()
    model["external_resource"] = {
        "provider": "edgeflow",
        "resource": "records",
        "identity_field": "id",
    }

    for template_name in ("user_service.py.j2", "singleton_service.py.j2"):
        rendered = environment.get_template(template_name).render(model=model)
        compile(rendered, template_name, "exec")
        assert "await enqueue_external_resource_change(" not in rendered
        assert "from app.core.external_resources" not in rendered


def test_hook_invoker_supports_partial_signatures_and_async_methods():
    helper_path = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "backend"
        / "app"
        / "core"
        / "model_hooks.py"
    )
    spec = importlib.util.spec_from_file_location("generated_model_hooks", helper_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class Target:
        called = False

        async def on_after_create(self, context):
            self.called = context.operation == "create"

    target = Target()
    context = module.ModelHookContext(operation="create")
    asyncio.run(
        module.invoke_model_hook(
            target,
            "on_after_create",
            session=object(),
            context=context,
        )
    )

    assert target.called is True


def test_hook_invoker_runs_hidden_external_hook_without_user_method(monkeypatch):
    helper_path = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "backend"
        / "app"
        / "core"
        / "model_hooks.py"
    )
    spec = importlib.util.spec_from_file_location("generated_hidden_hooks", helper_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    app_module = ModuleType("app")
    app_module.__path__ = []
    core_module = ModuleType("app.core")
    core_module.__path__ = []
    runtime_module = ModuleType("app.core.external_resources")
    calls = []

    async def sync_external_resource_change(session, **values):
        calls.append((session, values))

    runtime_module.sync_external_resource_change = sync_external_resource_change
    monkeypatch.setitem(sys.modules, "app", app_module)
    monkeypatch.setitem(sys.modules, "app.core", core_module)
    monkeypatch.setitem(
        sys.modules, "app.core.external_resources", runtime_module
    )

    target = object()
    session = object()
    asyncio.run(
        module.invoke_model_hook(
            target,
            "on_after_create",
            session=session,
            context=module.ModelHookContext(operation="create"),
        )
    )

    assert calls == [
        (
            session,
            {"target": target, "operation": "create", "previous": None},
        )
    ]


def test_transactional_hook_signature_is_validated_during_introspection():
    class InvalidTransactionalHook(SQLModel, table=True):
        __tablename__ = "test_invalid_transactional_hook"

        id: Optional[int] = Field(default=None, primary_key=True)

        async def on_after_create(self, request):
            pass

    with pytest.raises(ValueError, match="unsupported required parameter 'request'"):
        _validate_service_hooks(InvalidTransactionalHook)


def test_bulk_delete_hooks_must_be_classmethods():
    class InvalidBulkDeleteHook:
        async def on_after_bulk_delete(self, session, olds, context):
            pass

    with pytest.raises(ValueError, match="must be a classmethod"):
        _validate_service_hooks(InvalidBulkDeleteHook)


def test_bulk_delete_hook_invoker_supports_model_class_targets():
    helper_path = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "backend"
        / "app"
        / "core"
        / "model_hooks.py"
    )
    spec = importlib.util.spec_from_file_location(
        "generated_bulk_model_hooks", helper_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class Target:
        called_with = None

        @classmethod
        async def on_after_bulk_delete(cls, olds, context):
            cls.called_with = (olds, context.operation)

    olds = [{"id": 1}, {"id": 2}]
    context = module.ModelHookContext(operation="bulk_delete")
    asyncio.run(
        module.invoke_model_hook(
            Target,
            "on_after_bulk_delete",
            session=object(),
            olds=olds,
            context=context,
        )
    )

    assert Target.called_with == (olds, "bulk_delete")
