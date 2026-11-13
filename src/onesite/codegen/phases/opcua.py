"""Generate the optional OPC UA browser and wire it to the server detail page."""

from ...project_paths import get_project_paths
from ..render import generate_file


def generate_opcua(models, site_config, cwd, backend_path):
    frontend_path = get_project_paths(cwd).frontend
    runtime = backend_path / "app/core/opcua.py"
    plugin_enabled = "opcua" in site_config.get("plugins", [])
    capability_enabled = any(
        capability["kind"] == "opcua_server"
        for model in models
        for capability in model.get("capabilities", ())
    )
    if plugin_enabled or capability_enabled:
        generate_file("opcua_runtime.py.j2", {}, runtime)
    else:
        runtime.unlink(missing_ok=True)

    capability_api = backend_path / "app/api/endpoints/capability_opcua.py"
    capability_panel = frontend_path / "src/components/capabilities/OpcuaCapability.tsx"
    if capability_enabled:
        generate_file("capability_opcua_api.py.j2", {}, capability_api)
        generate_file("opcua_browse_panel.tsx.j2", {"browse_only": True}, capability_panel)
    else:
        capability_api.unlink(missing_ok=True)
        capability_panel.unlink(missing_ok=True)

    plugin_outputs = {
        "opcua_browse_api.py.j2": backend_path / "app/api/endpoints/opcua_browse.py",
        "opcua_browse_panel.tsx.j2": frontend_path / "src/components/opcua/BrowsePanel.tsx",
    }
    for model in models:
        model["opcua_browse"] = None
    if not plugin_enabled:
        for output in plugin_outputs.values():
            output.unlink(missing_ok=True)
        return
    by_name = {model["name"]: model for model in models}
    required = {
        "OpcuaServer": {
            "id",
            "title",
            "endpoint",
            "auth_type",
            "username",
            "password",
            "security_policy",
            "security_mode",
            "app_uri",
            "cert_path",
            "key_path",
            "server_cert_path",
            "request_timeout_seconds",
        },
        "OpcuaNode": {"id", "title", "nodeid", "opcua_server_id"},
        "OpcuaAc": {"id", "title", "condition_id", "event_notifier_nodeid", "opcua_server_id"},
    }
    for name, fields in required.items():
        model = by_name.get(name)
        if model is None or model.get("frontend_only"):
            raise ValueError(f"opcua plugin requires a backend {name} model")
        missing = fields - {field["name"] for field in model["fields"]}
        if missing:
            raise ValueError(f"opcua plugin {name} is missing fields: {', '.join(sorted(missing))}")
        if (
            model["id_type"] != "int"
            or model["module_name"]
            != {"OpcuaServer": "opcua_server", "OpcuaNode": "opcua_node", "OpcuaAc": "opcua_ac"}[
                name
            ]
        ):
            raise ValueError(
                f"opcua plugin {name} requires the default resource name and integer identity"
            )
    server = by_name["OpcuaServer"]
    if any(
        capability["fields"].get(capability.get("credential")) == "password"
        for capability in server.get("capabilities", ())
    ):
        raise ValueError(
            "OpcuaServer.password is used by the opcua plugin. "
            "Map the capability password to a separate model field."
        )
    server["opcua_browse"] = {
        "node_permissions": by_name["OpcuaNode"]["role_permissions"],
        "ac_permissions": by_name["OpcuaAc"]["role_permissions"],
    }
    for template, output in plugin_outputs.items():
        generate_file(template, {"model": server}, output)
