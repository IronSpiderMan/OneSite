"""Regression coverage for generated User deletion safeguards."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def _user_model():
    return {
        "name": "User",
        "module_name": "user",
        "source_module": "user",
        "lower_name": "user",
        "fields": [],
        "id_type": "int",
        "is_notification_table": False,
        "role_permissions": {"user":"r", "admin":"crud", "developer":"crud"},
        "min_role_for_read": "USER",
        "min_role_for_create": "ADMIN",
        "min_role_for_update": "ADMIN",
        "min_role_for_delete": "ADMIN",
    }


def test_generated_user_api_protects_self_and_initial_administrator():
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    api = Environment(loader=FileSystemLoader(template_dir)).get_template("api.py.j2").render(
        model=_user_model()
    )

    compile(api, "generated_user_api.py", "exec")
    assert "from app.core.config import settings" in api
    assert api.count("You cannot delete your own account") == 2
    assert api.count("The initial administrator cannot be deleted") == 2
    assert "current_user: User = Depends(deps.get_current_user)" in api
    assert "Validate the full request before deleting anything" in api
