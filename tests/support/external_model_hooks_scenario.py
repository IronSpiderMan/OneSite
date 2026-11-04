"""Run inside the generated backend; OneSite imports are explicitly forbidden."""

# Install the import guard before loading any application modules.
# ruff: noqa: E402

import asyncio
import sys
from types import ModuleType


class NoGeneratorImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"onesite", "onesite_runtime"}:
            raise AssertionError(f"Generated backend imported {fullname}")


sys.meta_path.insert(0, NoGeneratorImports())

from sqlalchemy import func
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import engine, register_models
from app.core.model_hooks import ModelHookContext, invoke_model_hook
from app.hooks._state import events
from app.models.entities import Audit, Record
from app.models.opcua_server import OpcuaServer
from app.schemas.record import RecordCreate, RecordUpdate
from app.schemas.system_config import SystemConfigUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.record import service
from app.services.system_config import service as config_service
from app.services.user import service as user_service


async def expect_failure(awaitable, message):
    try:
        await awaitable
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected failure: {message}")


async def count(session, model):
    return (await session.exec(select(func.count()).select_from(model))).one()


async def main():
    register_models()
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        events.clear()
        created = await service.create(session, RecordCreate(title="  first  "))
        assert created.title == "first" and created.initialized
        assert events == [
            "external.before_create", "model.before_create", "model.after_create",
            "external.after_create", "external.after_commit_create",
        ], events
        assert await count(session, Audit) == 1

        events.clear()
        updated = await service.update(session, created.id, RecordUpdate(title="  second  "))
        assert updated.title == "second"
        # A failed model post-commit method does not prevent the external function.
        assert events == [
            "external.before_update", "model.before_update", "model.after_update",
            "external.after_update", "model.after_commit_update", "external.after_commit_update",
        ], events
        assert await count(session, Audit) == 2

        events.clear()
        await expect_failure(
            service.create(session, RecordCreate(title="  forbidden  ")), "model rejected create",
        )
        assert events == ["external.before_create", "model.before_create"], events
        assert await count(session, Record) == 1

        await expect_failure(
            service.create(session, RecordCreate(title="rollback-create")),
            "external rejected create",
        )
        assert await count(session, Record) == 1
        assert await count(session, Audit) == 2  # Hook writes roll back with the parent.
        await expect_failure(
            service.update(session, created.id, RecordUpdate(title="rollback-update")),
            "external rejected update",
        )
        assert (await session.get(Record, created.id)).title == "second"
        assert await count(session, Audit) == 2

        events.clear()
        await service.delete(session, created.id)
        assert events == [
            "external.before_delete", "model.before_delete", "model.after_delete",
            "external.after_delete", "external.after_commit_delete",
        ], events
        assert await count(session, Record) == 0
        assert await count(session, Audit) == 3

        rolled = await service.create(session, RecordCreate(title="rollback-delete"))
        events.clear()
        await expect_failure(service.delete(session, rolled.id), "external rejected delete")
        assert "external.after_commit_delete" not in events
        assert await session.get(Record, rolled.id) is not None

        first = await service.create(session, RecordCreate(title="bulk-1"))
        second = await service.create(session, RecordCreate(title="bulk-2"))
        events.clear()
        assert await service.bulk_delete(session, [first.id, second.id, first.id, 99999]) == 2
        assert events.count("external.before_delete") == 2
        assert events.count("external.after_commit_delete") == 2
        assert events.index("model.after_bulk_delete") < events.index("external.after_bulk_delete")
        assert events[-2:] == [
            "model.after_commit_bulk_delete", "external.after_commit_bulk_delete",
        ], events

        first = await service.create(session, RecordCreate(title="rollback-bulk"))
        second = await service.create(session, RecordCreate(title="bulk-kept"))
        audit_count = await count(session, Audit)
        events.clear()
        await expect_failure(
            service.bulk_delete(session, [first.id, second.id]), "external rejected bulk delete",
        )
        assert await session.get(Record, first.id) is not None
        assert await session.get(Record, second.id) is not None
        assert await count(session, Audit) == audit_count
        assert "external.after_commit_delete" not in events
        assert "external.after_commit_bulk_delete" not in events

        # Post-commit external failures cannot turn a committed create into a failure.
        post = await service.create(session, RecordCreate(title="post-failure"))
        assert (await session.get(Record, post.id)).title == "post-failure"

        # Specialized built-in User and singleton services use the same dispatcher.
        user = await user_service.create(
            session,
            UserCreate(email="hooks@example.test", password="test-password", full_name="  Alice  "),
        )
        assert user.full_name == "Alice"
        user = await user_service.update(session, user.id, UserUpdate(full_name="  Bob  "))
        assert user.full_name == "Bob"
        config = await config_service.update(session, SystemConfigUpdate(site_name="  Custom  "))
        assert config.site_name == "Custom"

        # Plugin validators still run after project normalization.
        plugin = OpcuaServer(title="PLC", endpoint="  opc.tcp://127.0.0.1:4840  ")
        context = ModelHookContext(operation="create")
        await invoke_model_hook(plugin, "on_before_create", session=session, context=context)
        assert plugin.endpoint == "opc.tcp://127.0.0.1:4840"
        await invoke_model_hook(plugin, "on_after_create", session=session, context=context)
        assert events[-1] == "external.plugin.after_create"
        changes = {"endpoint": "  https://invalid.test  "}
        await expect_failure(
            invoke_model_hook(plugin, "on_before_update", changes=changes), "opc.tcp://",
        )

        # Framework synchronization observes both user handlers' final state.
        resources = ModuleType("app.core.external_resources")

        async def sync_external_resource_change(session, *, target, operation, previous):
            assert target.initialized and target.title == "resource"
            assert operation == "create" and previous is None
            events.append("framework.resource")

        resources.sync_external_resource_change = sync_external_resource_change
        previous = sys.modules.get(resources.__name__)
        sys.modules[resources.__name__] = resources
        try:
            events.clear()
            await service.create(session, RecordCreate(title="  resource  "))
            assert events == [
                "external.before_create", "model.before_create", "model.after_create",
                "external.after_create", "framework.resource", "external.after_commit_create",
            ], events
            events.clear()
            await expect_failure(
                service.create(session, RecordCreate(title="rollback-create")),
                "external rejected create",
            )
            assert "framework.resource" not in events
        finally:
            if previous is None:
                sys.modules.pop(resources.__name__)
            else:
                sys.modules[resources.__name__] = previous

    await engine.dispose()


asyncio.run(main())
