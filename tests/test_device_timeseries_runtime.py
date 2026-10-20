"""Exercise default plugin hooks against a real transactional database."""

import importlib
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from onesite.codegen.model_imports import isolated_project_imports
from onesite.codegen.phases.plugin_models import phase_generate_plugin_models
from onesite_runtime import ReadContext, WriteContext, resolve_read_data, resolve_write_data


@pytest.mark.asyncio
async def test_device_defaults_initialization_freeze_and_value_conversion(tmp_path):
    backend = tmp_path / "backend"
    phase_generate_plugin_models({"plugins": ["device_timeseries"]}, tmp_path, backend)
    with isolated_project_imports(backend):
        DeviceModel = importlib.import_module("app.models.device_model").DeviceModel
        Device = importlib.import_module("app.models.device").Device
        DeviceModelField = importlib.import_module(
            "app.models.device_model_field"
        ).DeviceModelField
        DeviceField = importlib.import_module("app.models.device_field").DeviceField
        DeviceLatest = importlib.import_module(
            "app.models.device_history_latest"
        ).DeviceLatest
        engine = create_async_engine("sqlite+aiosqlite://")
        tables = [cls.__table__ for cls in (DeviceModel, DeviceModelField, Device, DeviceField, DeviceLatest)]
        async with engine.begin() as connection:
            await connection.run_sync(lambda conn: SQLModel.metadata.create_all(conn, tables=tables))
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                model = DeviceModel(name="sensor")
                unused = DeviceModel(name="unused")
                session.add_all([model, unused])
                await session.flush()
                definition = DeviceModelField(
                    device_model_id=model.id, name="temperature", dtype="float32", unit="C",
                )
                await definition.on_before_create(session)
                session.add(definition)
                await session.flush()
                await definition.on_before_update(session, {"unit": "Celsius"})
                await definition.on_before_delete(session)
                device = Device(name="sensor-1", device_model_id=model.id, protocol="mqtt")
                from uuid import UUID
                assert UUID(device.id).version == 4
                assert device.timeout == device.heartbeat_interval_seconds == 60
                await device.on_before_create(session)
                session.add(device)
                await session.flush()
                await device.on_after_create(session)
                await device.on_after_create(session)  # Repeat is idempotent.
                fields = (await session.exec(select(DeviceField))).all()
                assert len(fields) == 1
                field = fields[0]
                assert (field.name, field.dtype, field.unit, field.address) == (
                    "temperature", "float32", "C", "temperature",
                )
                with pytest.raises(ValueError, match="不能手工创建"):
                    await field.on_before_create()
                with pytest.raises(ValueError, match="不能更换"):
                    await device.on_before_update({"device_model_id": unused.id})
                await device.on_before_update({"name": "renamed"})
                with pytest.raises(ValueError, match="已被设备使用"):
                    await definition.on_before_update(session, {"name": "new"})
                with pytest.raises(ValueError, match="已被设备使用"):
                    await definition.on_before_delete(session)
                with pytest.raises(ValueError, match="已被设备使用"):
                    await definition.on_before_update(session, {"device_model_id": unused.id})
                added = DeviceModelField(device_model_id=model.id, name="extra", dtype="str")
                with pytest.raises(ValueError, match="已被设备使用"):
                    await added.on_before_create(session)
                moving = DeviceModelField(device_model_id=unused.id, name="moving", dtype="str")
                with pytest.raises(ValueError, match="已被设备使用"):
                    await moving.on_before_update(session, {"device_model_id": model.id})

                # Current telemetry comes from latest, not the stored command.
                field.value = {"value": 999}
                assert await field.present_value(field.value, session) == ""
                latest = DeviceLatest(
                    device_id=device.id, metric=field.name,
                    value={"value": 1.234}, reported_at=datetime.now(timezone.utc),
                )
                session.add(latest)
                await session.flush()
                for source in ("list", "detail", "relation"):
                    data = await resolve_read_data(
                        field, {"value": field.value},
                        ReadContext(session=session, source=source),
                    )
                    assert data["value"] == "1.23"
                    assert field.value == {"value": 999}
                for payload, expected in (
                    ({"value": 0}, "0"), ({"value": False}, "False"),
                    ({"value": None}, ""), ({"value": "ready"}, "ready"),
                ):
                    latest.value = payload
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(latest, "value")
                    await session.flush()
                    assert await field.present_value(None, session) == expected
                # Both parts of the identity must match.
                other = DeviceField(
                    device_id="other-device", name=field.name,
                    device_model_field_id=definition.id, dtype="float32",
                )
                assert await other.present_value({"value": 999}, session) == ""
                other.device_id = device.id
                other.name = "other-metric"
                assert await other.present_value({"value": 999}, session) == ""
                field.value = {"value": 12.5}
                context = WriteContext(session=session, operation="update")
                assert await resolve_write_data(field, {"value": "2.75"}, context) == {
                    "value": {"value": 2.75}
                }
                assert await resolve_write_data(field, {"value": " "}, context) == {
                    "value": {"value": 12.5}
                }
                field.dtype = "bool"
                assert field.persist_value("false", context) == {"value": False}
                with pytest.raises(ValueError):
                    field.persist_value("invalid", context)
                field.dtype = "int32"
                assert field.persist_value("42", context) == {"value": 42}
                await session.commit()

                for attributes in (
                    {"name": "sensor-1"},
                    {"name": "bad-timeout", "timeout": 0},
                    {"name": "bad-heartbeat", "heartbeat_interval_seconds": 0},
                ):
                    with pytest.raises(IntegrityError):
                        async with session.begin_nested():
                            session.add(Device(device_model_id=model.id, protocol="mqtt", **attributes))
                            await session.flush()

                # Initializing fields must not commit independently of the device.
                transient = Device(name="rolled-back", device_model_id=model.id, protocol="mqtt")
                await transient.on_before_create(session)
                session.add(transient)
                await session.flush()
                await transient.on_after_create(session)
                transient_id = transient.id
                await session.rollback()
                assert await session.get(Device, transient_id) is None
                assert not (await session.exec(
                    select(DeviceField).where(DeviceField.device_id == transient_id)
                )).all()
        finally:
            await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("delete_mode", ["orm", "sql"])
async def test_device_deletion_cascades_telemetry_and_can_roll_back(tmp_path, delete_mode):
    from datetime import datetime, timezone

    from sqlalchemy import event, text

    backend = tmp_path / "backend"
    phase_generate_plugin_models({"plugins": ["device_timeseries"]}, tmp_path, backend)
    with isolated_project_imports(backend):
        classes = [
            getattr(importlib.import_module(f"app.models.{module}"), name)
            for module, name in (
                ("device_model", "DeviceModel"),
                ("device_model_field", "DeviceModelField"),
                ("device", "Device"),
                ("device_field", "DeviceField"),
                ("device_history", "DeviceHistory"),
                ("device_history_latest", "DeviceLatest"),
            )
        ]
        DeviceModel, Definition, Device, DeviceField, History, Latest = classes
        engine = create_async_engine("sqlite+aiosqlite://")

        @event.listens_for(engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        tables = [cls.__table__ for cls in classes]
        async with engine.begin() as connection:
            await connection.run_sync(lambda conn: SQLModel.metadata.create_all(conn, tables=tables))
        try:
            async with AsyncSession(engine) as session:
                model = DeviceModel(name="shared-model")
                session.add(model)
                await session.flush()
                definition = Definition(
                    device_model_id=model.id, name="temperature", dtype="float32",
                )
                session.add(definition)
                await session.flush()
                devices = [
                    Device(name=name, device_model_id=model.id, protocol="mqtt")
                    for name in ("delete-me", "keep-me")
                ]
                ids = [device.id for device in devices]
                session.add_all(devices)
                await session.flush()
                for device in devices:
                    await device.on_after_create(session)
                    payload = dict(
                        device_id=device.id, metric="temperature",
                        value={"value": 12.5}, reported_at=datetime.now(timezone.utc),
                    )
                    session.add_all([History(**payload), Latest(**payload)])
                await session.commit()

                async def delete_device():
                    if delete_mode == "orm":
                        device = await session.get(Device, ids[0])
                        await session.delete(device)
                    else:
                        await session.execute(
                            text("DELETE FROM device WHERE id = :id"), {"id": ids[0]}
                        )
                    await session.flush()

                async def assert_remaining(expected):
                    assert set((await session.exec(select(Device.id))).all()) == expected
                    for cls in (DeviceField, History, Latest):
                        assert set((await session.exec(select(cls.device_id))).all()) == expected
                    # Device deletion does not remove the shared model or its definition.
                    assert len((await session.exec(select(DeviceModel.id))).all()) == 1
                    assert len((await session.exec(select(Definition.id))).all()) == 1

                await delete_device()
                await assert_remaining({ids[1]})
                await session.rollback()
                await assert_remaining(set(ids))
                await delete_device()
                await session.commit()
                await assert_remaining({ids[1]})
        finally:
            await engine.dispose()
