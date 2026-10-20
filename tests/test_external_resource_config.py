import pytest

from onesite.codegen.config import (
    SiteConfigError,
    validate_external_resource_providers_config,
)
from onesite.config import ExternalResourceProviderConfig, SiteConfig


def test_external_resource_providers_default_to_empty_mapping():
    config = {}
    validate_external_resource_providers_config(config)
    assert config["providers"] == {}


def test_external_resource_provider_defaults_module_to_provider_name():
    config = {"providers": {"edgeflow": {}}}
    validate_external_resource_providers_config(config)
    assert config["providers"] == {"edgeflow": {"module": "edgeflow"}}


def test_external_resource_provider_requires_safe_module_name():
    with pytest.raises(SiteConfigError, match="valid Python module identifier"):
        validate_external_resource_providers_config(
            {"providers": {"edgeflow": {"module": "edge-flow"}}}
        )


def test_typed_site_config_exposes_provider_configuration():
    config = SiteConfig(
        providers={"edgeflow": ExternalResourceProviderConfig(module="edgeflow")}
    )
    assert config.providers["edgeflow"].module == "edgeflow"
