"""Exercise default plugin hooks against a real transactional database."""

import importlib
from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from onesite.codegen.model_imports import isolated_project_imports
from onesite.codegen.phases.plugin_models import phase_generate_plugin_models
from onesite.codegen.pipeline import generate_code
from onesite_runtime import ReadContext, WriteContext, resolve_read_data, resolve_write_data


@pytest.fixture
def device_backend(tmp_path):
    backend = tmp_path / "backend"
    phase_generate_plugin_models({"plugins": ["device_timeseries"]}, tmp_path, backend)
    return backend


async def _create_connector(session, Connector, title, protocol="mqtt"):
    connector = Connector(title=title, protocol=protocol, endpoint="localhost:1883")
    session.add(connector)
    await session.flush()
    return connector


def _enable_foreign_keys(connection, _record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.mark.asyncio
async def test_device_defaults_initialization_and_value_conversion(device_backend):
    with isolated_project_imports(device_backend):
        Connector = importlib.import_module("app.models.connector").Connector
        DGroup = importlib.import_module("app.models.dgroup").DGroup
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
        tables = [
            cls.__table__
            for cls in (Connector, DGroup, DeviceModel, DeviceModelField, Device, DeviceField, DeviceLatest)
        ]
        async with engine.begin() as connection:
            await connection.run_sync(lambda conn: SQLModel.metadata.create_all(conn, tables=tables))
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                connector = await _create_connector(session, Connector, "mqtt")
                model = DeviceModel(name="sensor")
                session.add(model)
                await session.flush()
                definition = DeviceModelField(
                    device_model_id=model.id, name="temperature", dtype="float32", unit="C",
                )
                await definition.on_before_create(session)
                session.add(definition)
                await session.flush()
                device = Device(name="sensor-1", device_model_id=model.id, connector_id=connector.id)
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
                            session.add(Device(device_model_id=model.id, connector_id=connector.id, **attributes))
                            await session.flush()

                # Initializing fields must not commit independently of the device.
                transient = Device(
                    name="rolled-back", device_model_id=model.id, connector_id=connector.id,
                )
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
async def test_device_deletion_cascades_telemetry_and_can_roll_back(device_backend, delete_mode):
    with isolated_project_imports(device_backend):
        Connector = importlib.import_module("app.models.connector").Connector
        DGroup = importlib.import_module("app.models.dgroup").DGroup
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
        event.listen(engine.sync_engine, "connect", _enable_foreign_keys)

        tables = [cls.__table__ for cls in (Connector, DGroup, *classes)]
        async with engine.begin() as connection:
            await connection.run_sync(lambda conn: SQLModel.metadata.create_all(conn, tables=tables))
        try:
            async with AsyncSession(engine) as session:
                connector = await _create_connector(session, Connector, "mqtt")
                model = DeviceModel(name="shared-model")
                session.add(model)
                await session.flush()
                definition = Definition(
                    device_model_id=model.id, name="temperature", dtype="float32",
                )
                session.add(definition)
                await session.flush()
                devices = [
                    Device(name=name, device_model_id=model.id, connector_id=connector.id)
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


@pytest.mark.asyncio
async def test_generated_device_model_updates_propagate_inline_fields(tmp_path, monkeypatch):
    (tmp_path / "site_config.py").write_text(
        "from onesite.config import SiteConfig\n"
        "config = SiteConfig(project_name='devices', plugins=['device_timeseries'])\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URI", "sqlite+aiosqlite://")
    generate_code()

    with isolated_project_imports(tmp_path / "generated" / "backend"):
        db = importlib.import_module("app.core.db")
        model_crud = importlib.import_module("app.cruds.device_model")
        definition_crud = importlib.import_module("app.cruds.device_model_field")
        device_crud = importlib.import_module("app.cruds.device")
        connector_crud = importlib.import_module("app.cruds.connector")
        model_schemas = importlib.import_module("app.schemas.device_model")
        definition_schemas = importlib.import_module("app.schemas.device_model_field")
        device_schemas = importlib.import_module("app.schemas.device")
        connector_schemas = importlib.import_module("app.schemas.connector")
        Connector = importlib.import_module("app.models.connector").Connector
        DGroup = importlib.import_module("app.models.dgroup").DGroup
        Device = importlib.import_module("app.models.device").Device
        DeviceModel = importlib.import_module("app.models.device_model").DeviceModel
        Definition = importlib.import_module("app.models.device_model_field").DeviceModelField
        DeviceField = importlib.import_module("app.models.device_field").DeviceField
        History = importlib.import_module("app.models.device_history").DeviceHistory
        Latest = importlib.import_module("app.models.device_history_latest").DeviceLatest
        tables = [
            cls.__table__
            for cls in (Connector, DGroup, Device, DeviceModel, Definition, DeviceField, History, Latest)
        ]
        try:
            async with db.engine.begin() as connection:
                assert (await connection.execute(text("PRAGMA foreign_keys"))).scalar_one() == 1
                await connection.run_sync(lambda conn: SQLModel.metadata.create_all(conn, tables=tables))
            async with AsyncSession(db.engine, expire_on_commit=False) as session:
                model = await model_crud.create(session, model_schemas.DeviceModelCreate(name="sensor"))
                other_model = await model_crud.create(
                    session, model_schemas.DeviceModelCreate(
                        name="other-sensor", device_model_fields=[{"name": "temp", "dtype": "float32"}],
                    ),
                )
                opcua = await connector_crud.create(
                    session, connector_schemas.ConnectorCreate(
                        title="opcua-a", protocol="opcua", endpoint="opc.tcp://localhost:4840",
                    ),
                )
                same_protocol = await _create_connector(session, Connector, "opcua-b", "opcua")
                mqtt = await _create_connector(session, Connector, "mqtt")
                first, second, unrelated = [
                    await device_crud.create(
                        session, device_schemas.DeviceCreate(
                            name=name, device_model_id=parent.id, connector_id=opcua.id,
                        ),
                    )
                    for name, parent in (("first", model), ("second", model), ("unrelated", other_model))
                ]
                model_id, other_model_id = model.id, other_model.id
                first_id, second_id, unrelated_id = first.id, second.id, unrelated.id
                same_protocol_id = same_protocol.id
                mqtt_id = mqtt.id

                await device_crud.update(
                    session, first, device_schemas.DeviceUpdate(connector_id=same_protocol_id),
                )
                assert first.connector_id == same_protocol_id
                with pytest.raises(ValueError, match="协议"):
                    await device_crud.update(
                        session, first, device_schemas.DeviceUpdate(connector_id=mqtt_id),
                    )
                first = await session.get(Device, first_id)
                assert first.connector_id == same_protocol_id
                with pytest.raises(ValueError, match="不能更换设备模型"):
                    await device_crud.update(
                        session, first, device_schemas.DeviceUpdate(device_model_id=other_model_id),
                    )
                with pytest.raises(ValueError, match="协议"):
                    await connector_crud.update(
                        session, await session.get(Connector, same_protocol_id),
                        connector_schemas.ConnectorUpdate(protocol="mqtt"),
                    )
                connector = await session.get(Connector, same_protocol_id)
                assert connector.protocol == "opcua"
                connector = await connector_crud.update(
                    session, connector, connector_schemas.ConnectorUpdate(title="edited"),
                )
                assert connector.title == "edited"

                await model_crud.update(
                    session, await session.get(DeviceModel, model_id),
                    model_schemas.DeviceModelUpdate(
                        name="new-name", description="safe edit",
                        device_model_fields=[{"name": "temp", "dtype": "float32", "unit": "C"}],
                    ),
                )
                model = await session.get(DeviceModel, model_id)
                assert (model.name, model.description) == ("new-name", "safe edit")
                definition = (await session.exec(
                    select(Definition).where(Definition.device_model_id == model_id),
                )).one()
                definition_id = definition.id
                assert set((await session.exec(
                    select(DeviceField.device_id).where(DeviceField.device_model_field_id == definition_id),
                )).all()) == {first_id, second_id}
                field = await session.get(DeviceField, (first_id, "temp"))
                field.address = "custom-address"
                field.value = {"value": 11.5}
                reported_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
                for device_id in (first_id, second_id, unrelated_id):
                    payload = dict(
                        device_id=device_id, metric="temp", value={"value": 12.5}, reported_at=reported_at,
                    )
                    session.add_all([History(**payload), Latest(**payload)])
                await session.commit()

                await model_crud.update(
                    session, model, model_schemas.DeviceModelUpdate(
                        device_model_fields=[
                            {"id": definition_id, "name": "temperature", "dtype": "float64", "unit": "°C"},
                        ],
                    ),
                )
                fields = (await session.exec(
                    select(DeviceField).where(DeviceField.device_model_field_id == definition_id),
                )).all()
                assert {
                    (item.device_id, item.name, item.dtype, item.unit, item.address) for item in fields
                } == {
                    (first_id, "temperature", "float64", "°C", "custom-address"),
                    (second_id, "temperature", "float64", "°C", "temp"),
                }
                field = await session.get(DeviceField, (first_id, "temperature"))
                assert field.value == {"value": 11.5}
                for cls in (History, Latest):
                    rows = (await session.exec(select(cls))).all()
                    assert {(row.device_id, row.metric) for row in rows} == {
                        (first_id, "temperature"), (second_id, "temperature"), (unrelated_id, "temp"),
                    }
                    assert all(
                        row.value == {"value": 12.5}
                        and row.reported_at.replace(tzinfo=timezone.utc) == reported_at
                        for row in rows
                    )

                # Incompatible history alone must block the change.
                field.value = None
                for device_id in (first_id, second_id):
                    (await session.get(Latest, (device_id, "temperature"))).value = {"value": True}
                await session.commit()
                with pytest.raises(ValueError, match="bool|数据类型"):
                    await model_crud.update(
                        session, model, model_schemas.DeviceModelUpdate(
                            name="rolled-back",
                            device_model_fields=[{"id": definition_id, "dtype": "bool"}],
                        ),
                    )
                model = await session.get(DeviceModel, model_id)
                assert model.name == "new-name"
                assert (await session.get(Definition, definition_id)).dtype == "float64"
                with pytest.raises(ValueError, match="已被设备使用"):
                    await model_crud.update(
                        session, model, model_schemas.DeviceModelUpdate(
                            name="also-rolled-back",
                            device_model_fields=[{"name": "rolled-back-field", "dtype": "str"}],
                        ),
                    )
                assert (await session.get(DeviceModel, model_id)).name == "new-name"
                assert await session.get(Definition, definition_id) is not None
                assert (await session.exec(
                    select(DeviceField).where(DeviceField.name == "rolled-back-field"),
                )).first() is None
                with pytest.raises(ValueError, match="已被设备使用"):
                    await definition_crud.update(
                        session, await session.get(Definition, definition_id),
                        definition_schemas.DeviceModelFieldUpdate(device_model_id=other_model_id),
                    )
                with pytest.raises(ValueError, match="已被设备使用"):
                    await model_crud.delete(session, model_id)

                direct = await definition_crud.create(
                    session, definition_schemas.DeviceModelFieldCreate(
                        device_model_id=model_id, name="pressure", dtype="float32",
                    ),
                )
                await definition_crud.update(
                    session, direct, definition_schemas.DeviceModelFieldUpdate(unit="kPa"),
                )
                assert set((await session.exec(
                    select(DeviceField.device_id, DeviceField.unit)
                    .where(DeviceField.device_model_field_id == direct.id),
                )).all()) == {(first_id, "kPa"), (second_id, "kPa")}
        finally:
            await db.engine.dispose()
