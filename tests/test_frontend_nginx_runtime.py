import re
from pathlib import Path


TEMPLATES = Path(__file__).parents[1] / "src" / "onesite" / "templates"


def test_frontend_entrypoint_renders_only_domain_in_nginx_config():
    entrypoint = (TEMPLATES / "frontend" / "entrypoint.sh").read_text(
        encoding="utf-8"
    )

    assert 'DOMAIN="${DOMAIN:-backend}"' in entrypoint
    assert "envsubst '${DOMAIN}'" in entrypoint


def test_frontend_image_does_not_install_unrendered_nginx_config():
    dockerfile = (TEMPLATES / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    assert (
        "COPY nginx.template.conf /etc/nginx/templates/default.conf.template"
        in dockerfile
    )
    assert "COPY nginx.template.conf /etc/nginx/conf.d/default.conf" not in dockerfile


def test_generated_nginx_template_only_substitutes_domain():
    nginx_template = (
        TEMPLATES / "codegen" / "frontend_nginx.conf.j2"
    ).read_text(encoding="utf-8")

    assert set(re.findall(r"\$\{([A-Z_]+)\}", nginx_template)) == {"DOMAIN"}
    assert "try_files /config.js =404;" in nginx_template
