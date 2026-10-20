"""Swagger documentation serves its dependencies locally, including behind a proxy."""

import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient


BACKEND = Path(__file__).resolve().parents[1] / 'src/onesite/templates/backend'
spec = importlib.util.spec_from_file_location('offline_docs', BACKEND / 'app/core/docs.py')
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


@pytest.mark.parametrize('root_path', ['', '/service'])
def test_docs_and_assets_are_available_offline(root_path):
    app = FastAPI(docs_url=None, openapi_url='/api/v1/openapi.json', root_path=root_path)
    docs.register_docs(app)
    app.mount('/static', StaticFiles(directory=BACKEND / 'static'), name='static')
    with TestClient(app) as client:
        response = client.get(root_path + '/docs')
        assert response.status_code == 200
        html = response.text
        assert 'https://' not in html
        assert 'http://' not in html
        assert f"{root_path}/api/v1/openapi.json" in html
        assert f"{root_path}/docs/oauth2-redirect" in html
        assert '"validatorUrl": null' in html
        for asset in ['swagger-ui-bundle.js', 'swagger-ui.css', 'favicon-32x32.png']:
            url = f'{root_path}/static/swagger-ui/{asset}'
            assert url in html
            asset_response = client.get(url)
            assert asset_response.status_code == 200
            assert asset_response.content == (BACKEND / 'static/swagger-ui' / asset).read_bytes()
        assert client.get(root_path + '/docs/oauth2-redirect').status_code == 200
        assert client.get(root_path + '/api/v1/openapi.json').status_code == 200
        assert '/docs' not in app.openapi()['paths']


def test_sync_bundles_docs_and_static_assets(tmp_path):
    from onesite.codegen.assets import sync_backend_assets

    (tmp_path / 'app').mkdir()
    backend = tmp_path / 'generated/backend'
    sync_backend_assets(tmp_path, backend, {'project_name': 'Offline docs', 'allowed_origins': []})
    assert (backend / 'app/core/docs.py').read_bytes() == (BACKEND / 'app/core/docs.py').read_bytes()
    for asset in (BACKEND / 'static/swagger-ui').iterdir():
        assert (backend / 'static/swagger-ui' / asset.name).read_bytes() == asset.read_bytes()
    main = (backend / 'app/main.py').read_text()
    assert 'docs_url=None' in main
    assert 'register_docs(app)' in main
    assert 'COPY --from=production-builder /app/static/ /app/static/' in (backend / 'Dockerfile').read_text()
