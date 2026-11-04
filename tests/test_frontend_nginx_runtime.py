import re
from pathlib import Path

from jinja2 import Template


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


def test_opcua_discovery_proxy_allows_scan_deadline_without_changing_other_api_timeouts():
    for path, upstream in (
        (TEMPLATES / "codegen" / "frontend_nginx.conf.j2", "http://${DOMAIN}/api/v1/opcua/"),
        (TEMPLATES / "frontend" / "nginx.template.conf", "http://backend"),
    ):
        config = Template(path.read_text(encoding="utf-8")).render(config={})
        opcua = re.search(r"location /api/v1/opcua/ \{\n(.*?)^    \}", config, re.M | re.S)
        general = re.search(r"location /api/v1/ \{\n(.*?)^    \}", config, re.M | re.S)
        assert opcua is not None and general is not None
        timeout = re.search(r"proxy_read_timeout (\d+)s;", opcua[1])
        assert timeout is not None and int(timeout[1]) > 120
        assert "proxy_read_timeout" not in general[1]
        assert f"proxy_pass {upstream};" in opcua[1]
        # The specific route must retain the normal API's forwarding headers.
        headers = re.findall(r"proxy_set_header [^;]+;", general[1])
        assert headers and all(header in opcua[1] for header in headers)
