from sqlmodel import Column, Field, JSON, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import _resolve_definition_bindings
from onesite.config import DefinitionBindingConfig, OneSiteConfig


class SensorDefinitionItem(SQLModel):
    label: str = ""


class SensorConfig(SQLModel):
    enabled: bool = True


class SensorDefinition(SQLModel, table=True):
    __tablename__ = "sensor_definition"

    id: int | None = Field(default=None, primary_key=True)
    items: dict[str, SensorDefinitionItem] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )


class BoundSensor(SQLModel, table=True):
    __tablename__ = "test_bound_sensor"
    __onesite__ = OneSiteConfig(
        definition_binding=DefinitionBindingConfig(
            definition_fk="definition_id",
            definitions_field="items",
            instance_config_field="item_config",
            key_policy="definition",
            on_definition_change="merge",
        )
    )

    id: int | None = Field(default=None, primary_key=True)
    definition_id: int | None = Field(
        default=None, foreign_key="sensor_definition.id"
    )
    item_config: dict[str, SensorConfig] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )


def _model(model_cls: type[SQLModel], name: str, module: str):
    result = get_model_fields(model_cls, module)
    return _build_model_dict(name, module, module, result)


def test_definition_binding_resolves_from_entity_fk_and_field_annotations():
    definition = _model(SensorDefinition, "SensorDefinition", "sensor_definition")
    sensor = _model(BoundSensor, "BoundSensor", "bound_sensor")

    _resolve_definition_bindings([definition, sensor])

    assert sensor["definition_binding_meta"] == {
        "definition_fk": "definition_id",
        "definition_model": "SensorDefinition",
        "definition_module": "sensor_definition",
        "definitions_field": "items",
        "config_field": "item_config",
        "config_class": "SensorConfig",
        "config_permissions": "cru",
        "key_policy": "definition",
        "on_definition_change": "merge",
        "protect_definitions_when_used": True,
    }
    assert definition["reverse_definition_bindings"][0]["entity_model"] == "BoundSensor"


def test_definition_binding_is_independent_of_time_series_configuration():
    result = get_model_fields(BoundSensor, "bound_sensor")

    assert result.definition_binding["definition_fk"] == "definition_id"
    assert result.is_timescaledb is False
