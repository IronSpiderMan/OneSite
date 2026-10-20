"""Generated private uploads must never be served as public assets."""
from pathlib import Path
import stat
import sys
import types
from typing import Optional
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict

ROOT = Path(__file__).parents[1]
TEMPLATES = ROOT / 'src/onesite/templates/codegen'


class PrivateFileRecord(SQLModel, table=True):
    __tablename__ = 'test_private_file_record'
    __onesite__ = {'page_edit': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    key_file: Optional[str] = Field(default=None, sa_column_kwargs={'info': {'site_props': {'component': 'file', 'private': True}}})
    public_file: Optional[str] = Field(default=None, sa_column_kwargs={'info': {'site_props': {'component': 'file'}}})


def test_private_file_metadata_and_editor_codegen():
    fields = get_model_fields(PrivateFileRecord, 'test_private_file_record')
    private = next(f for f in fields.fields if f.name == 'key_file')
    assert private.private_upload and not private.allow_download
    model = _build_model_dict('PrivateFileRecord', 'test_private_file_record', 'test_private_file_record', fields)
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    for template in ('frontend_page_create.tsx.j2', 'frontend_page_detail.tsx.j2', 'frontend_page_list.tsx.j2'):
        model['page_edit'] = template != 'frontend_page_list.tsx.j2'
        text = env.get_template(template).render(model=model, models=[model], config={})
        assert "privateUpload={ { model: 'test_private_file_record', field: 'key_file' } }" in text


@pytest.fixture
def upload_app(tmp_path, monkeypatch):
    settings = SimpleNamespace(UPLOAD_DIR=str(tmp_path/'uploads'), PRIVATE_UPLOAD_DIR=str(tmp_path/'private'), PRIVATE_UPLOAD_MAX_BYTES=16)
    Path(settings.UPLOAD_DIR).mkdir()
    def user(authorization: Optional[str] = Header(default=None)):
        if not authorization:
            raise HTTPException(401)
        return SimpleNamespace(role=authorization)
    grants = {'developer': 'cru', 'admin': 'r', 'user': ''}
    modules = {
        'app.core.config': {'settings': settings},
        'app.core.deps': {'get_current_user': user},
        'app.core.access': {'role_of': lambda u: u.role},
        'app.core.access_policies': {'POLICIES': {'test_private_file_record': {'permissions': grants, 'fields': {'key_file': grants}}}},
    }
    for name, attrs in modules.items():
        module = types.ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    namespace = {'__name__': 'test_generated_upload'}
    source = Environment(loader=FileSystemLoader(str(TEMPLATES))).get_template('backend_api_upload.py.j2').render(config={})
    exec(compile(source, 'generated_upload.py', 'exec'), namespace)
    app = FastAPI()
    app.include_router(namespace['router'], prefix='/api/v1')
    app.mount('/uploads', StaticFiles(directory=settings.UPLOAD_DIR))
    return TestClient(app), settings


def test_private_upload_permissions_and_nonpublic_storage(upload_app):
    client, settings = upload_app
    url = '/api/v1/upload/private/test_private_file_record/key_file'
    assert client.post(url, files={'file': ('key.pem', b'secret')}).status_code == 401
    assert client.post(url, headers={'authorization': 'admin'}, files={'file': ('key.pem', b'secret')}).status_code == 403
    response = client.post(url, headers={'authorization': 'developer'}, files={'file': ('../../key.pem', b'secret')})
    assert response.status_code == 200
    data = response.json()
    saved = Path(settings.PRIVATE_UPLOAD_DIR)/data['filename']
    assert saved.read_bytes() == b'secret'
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    assert data['filename'].endswith('.pem') and '/' not in data['filename']
    assert not list(Path(settings.UPLOAD_DIR).iterdir())
    assert client.get(data['url']).status_code == 404
    assert client.get('/uploads/'+data['filename']).status_code == 404


def test_private_upload_rejects_wrong_field_and_cleans_failed_files(upload_app):
    client, settings = upload_app
    headers = {'authorization': 'developer'}
    base = '/api/v1/upload/private/test_private_file_record/'
    assert client.post(base+'public_file', headers=headers, files={'file': ('key.pem', b'secret')}).status_code == 404
    for payload, status in ((b'',400), (b'x'*17,413)):
        assert client.post(base+'key_file', headers=headers, files={'file': ('key.pem',payload)}).status_code == status
    assert not list(Path(settings.PRIVATE_UPLOAD_DIR).iterdir())
    # An authenticated public upload retains the established URL contract.
    response = client.post('/api/v1/upload', headers=headers, files={'file': ('cert.pem',b'public')})
    assert response.status_code == 200
    assert client.get(response.json()['url']).content == b'public'


def test_private_upload_rejects_public_storage_configuration(upload_app):
    client, settings = upload_app
    settings.PRIVATE_UPLOAD_DIR = str(Path(settings.UPLOAD_DIR)/'secret')
    response = client.post('/api/v1/upload/private/test_private_file_record/key_file', headers={'authorization':'developer'}, files={'file':('key.pem',b'secret')})
    assert response.status_code == 500
    assert not list(Path(settings.UPLOAD_DIR).iterdir())
