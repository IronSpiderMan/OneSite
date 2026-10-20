"""Coverage for RTSP-to-HLS preview generation."""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from onesite.codegen.assets import sync_backend_assets, sync_frontend_assets
from onesite.codegen.config import SiteConfigError, validate_video_stream_config
from onesite.codegen.router import update_api_router


def _config(enabled: bool = True) -> dict:
    return {
        "project_name": "RTSP test",
        "secret_key": "test-secret",
        "access_token_expire_minutes": 30,
        "database_url": "sqlite:///./test.db",
        "allowed_origins": ["http://localhost:5173"],
        "upload_dir": "uploads",
        "desktop": {
            "api_url": "http://127.0.0.1:8000/api/v1",
            "version": "0.1.0",
            "identifier": "com.onesite.rtsp-test",
            "width": 1280,
            "height": 800,
        },
        "video_stream": {
            "rtsp": {
                "enabled": enabled,
                "allowed_hosts": ["192.168.1.0/24", "camera.example.com"],
                "connect_timeout_seconds": 8,
            }
        },
    }


def test_rtsp_config_requires_an_explicit_source_allowlist():
    config = {"video_stream": {"rtsp": {"enabled": True}}}
    with pytest.raises(SiteConfigError, match="must contain at least one host or CIDR"):
        validate_video_stream_config(config)


def test_rtsp_backend_endpoint_and_router_are_generated(tmp_path):
    source = tmp_path / "app"
    source.mkdir()
    backend = tmp_path / "generated" / "backend"
    config = _config()

    sync_backend_assets(tmp_path, backend, config)
    endpoint = backend / "app" / "api" / "endpoints" / "video_streams.py"
    content = endpoint.read_text(encoding="utf-8")

    assert "Only RTSP and RTSPS sources are supported" in content
    assert "RTSP source host is not allowed" in content
    assert '"sourceOnDemand": True' in content
    assert '"rtspTransport": "tcp"' in content
    assert "/v3/config/paths/list" in content
    assert "/v3/config/paths/add/" in content
    assert "hmac.new(" in content
    assert "trust_env=False" in content

    router = backend / "app" / "api" / "api.py"
    update_api_router([], router)
    router_content = router.read_text(encoding="utf-8")
    assert "from app.api.endpoints import video_streams" in router_content
    assert 'prefix="/video-streams"' in router_content


def test_rtsp_nginx_proxy_is_opt_in_and_frontend_marks_rtsp_unsupported(tmp_path):
    (tmp_path / "app").mkdir()
    sync_frontend_assets(tmp_path, _config())
    frontend = tmp_path / "generated" / "frontend"

    nginx = (frontend / "nginx.template.conf").read_text(encoding="utf-8")
    player = (
        frontend / "src" / "components" / "ui" / "video-stream-player.tsx"
    ).read_text(encoding="utf-8")

    assert "location /media-hls/" in nginx
    assert "resolver 127.0.0.11 ipv6=off valid=10s;" in nginx
    assert "set $mediamtx_upstream mediamtx:8888;" in nginx
    assert "proxy_pass http://$mediamtx_upstream/;" in nginx
    assert "proxy_redirect / /media-hls/;" in nginx
    assert "['rtsp', 'rtmp', 'srt'].includes(streamType)" in player
    assert "request.post('/video-streams/preview'" not in player
    assert "rtsp_converting" not in player

    disabled_root = tmp_path / "disabled"
    (disabled_root / "app").mkdir(parents=True)
    sync_frontend_assets(disabled_root, _config(enabled=False))
    disabled_nginx = (
        disabled_root / "generated" / "frontend" / "nginx.template.conf"
    ).read_text(encoding="utf-8")
    assert "location /media-hls/" not in disabled_nginx


def test_rtsp_never_adds_mediamtx_to_compose():
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))
    template = environment.get_template("docker-compose.yml.j2")
    common = {
        "project_name": "rtsp-test",
        "backend_image": "backend:test",
        "frontend_image": "frontend:test",
        "frontend_port": 3000,
        "use_pg": False,
    }

    enabled = template.render(config=_config(), **common)
    disabled = template.render(config=_config(enabled=False), **common)

    assert "bluenviron/mediamtx" not in enabled
    assert "MEDIA_MTX_API_URL=http://mediamtx:9997" not in enabled
    assert "bluenviron/mediamtx" not in disabled
