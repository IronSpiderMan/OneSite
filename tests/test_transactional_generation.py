"""Generation must be reproducible, clean obsolete output, and roll back failures."""

import json

import pytest

from onesite.codegen.pipeline import generate_code
from onesite.codegen.transaction import _publish


MODEL = '''from sqlmodel import SQLModel, Field
class Thing(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
'''


def prepare(root):
    (root / 'app/models').mkdir(parents=True)
    (root / 'app/models/renamable.py').write_text(MODEL)
    (root / 'site_config.py').write_text("from onesite.config import SiteConfig\nconfig=SiteConfig(project_name='before', style='industrial')\n")


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def test_failed_generation_leaves_output_and_scaffolds_unchanged(tmp_path, monkeypatch):
    prepare(tmp_path)
    monkeypatch.chdir(tmp_path)
    generate_code()
    before = snapshot(tmp_path / 'generated')
    (tmp_path / 'site_config.py').write_text("from onesite.config import SiteConfig\nconfig=SiteConfig(project_name='after', style='industrial')\n")
    (tmp_path / 'app/models/broken.py').write_text('not valid python!\n')
    source_before = snapshot(tmp_path / 'app')
    with pytest.raises(Exception, match='Could not import'):
        generate_code()
    assert before == snapshot(tmp_path / 'generated')
    assert source_before == snapshot(tmp_path / 'app')
    assert not (tmp_path / '.onesite-sync.lock').exists()


def test_sync_removes_owned_output_but_keeps_runtime_data(tmp_path, monkeypatch):
    prepare(tmp_path)
    monkeypatch.chdir(tmp_path)
    generate_code()
    generated = tmp_path / 'generated'
    database = generated / 'backend/app.db'
    database.write_bytes(b'preserved database')
    upload = generated / 'backend/uploads/report.txt'
    upload.parent.mkdir()
    upload.write_text('preserved upload')
    dependency = generated / 'frontend/node_modules/example/index.js'
    dependency.parent.mkdir(parents=True)
    dependency.write_text('preserved dependency')
    (tmp_path / 'app/models/renamable.py').unlink()
    generate_code()
    for relative in ['backend/app/models/renamable.py','backend/app/schemas/thing.py',
                     'backend/app/cruds/thing.py','backend/app/api/endpoints/thing.py',
                     'backend/tests/test_thing_api.py','frontend/src/pages/thing/index.tsx',
                     'frontend/src/stores/useThingStore.ts']:
        assert not (generated / relative).exists(), relative
    assert database.read_bytes() == b'preserved database'
    assert upload.read_text() == 'preserved upload'
    assert dependency.read_text() == 'preserved dependency'
    manifest = json.loads((generated / '.onesite-manifest.json').read_text())
    assert all('thing' not in path.lower() for path in manifest['files'])
    once = snapshot(generated)
    generate_code()
    assert once == snapshot(generated)


def test_model_identity_survives_file_rename_and_additional_models(tmp_path, monkeypatch):
    prepare(tmp_path)
    monkeypatch.chdir(tmp_path)
    generate_code()
    old = tmp_path / 'app/models/renamable.py'
    new = old.with_name('grouped.py')
    old.rename(new)
    new.write_text(MODEL + '\nclass Second(SQLModel, table=True):\n    id: int | None = Field(default=None, primary_key=True)\n')
    generate_code()
    backend = tmp_path / 'generated/backend'
    for key, name in [('thing','Thing'),('second','Second')]:
        assert f'class {name}Create' in (backend / f'app/schemas/{key}.py').read_text()
        assert f'from app.models.grouped import {name}' in (backend / f'app/schemas/{key}.py').read_text()
    router = (backend / 'app/api/api.py').read_text()
    assert router.count('include_router(thing.router') == 1
    assert router.count('include_router(second.router') == 1
    assert not (backend / 'app/models/renamable.py').exists()


def test_publish_io_failure_restores_already_changed_files(tmp_path, monkeypatch):
    project = tmp_path / 'real'
    stage = tmp_path / 'stage'
    for root in (project, stage):
        (root / 'generated/backend').mkdir(parents=True)
    (project / 'generated/backend/a.txt').write_text('old a')
    (project / 'generated/backend/b.txt').write_text('old b')
    (stage / 'generated/backend/a.txt').write_text('new a')
    (stage / 'generated/backend/b.txt').write_text('new b')
    before = snapshot(project)
    from onesite.codegen import transaction
    replace = transaction._replace
    failed = False

    def fail_once(path, content):
        nonlocal failed
        if path.name == 'b.txt' and not failed:
            failed = True
            raise OSError('simulated disk failure')
        return replace(path, content)

    monkeypatch.setattr(transaction, '_replace', fail_once)
    with pytest.raises(OSError, match='simulated'):
        _publish(project, stage, {})
    assert snapshot(project) == before


@pytest.mark.parametrize("name, error", [("Thing", "collides"), ("Task", "reserved"), ("Agents", "reserved")])
def test_colliding_model_keys_fail_before_publishing(tmp_path, monkeypatch, name, error):
    prepare(tmp_path)
    monkeypatch.chdir(tmp_path)
    generate_code()
    before = snapshot(tmp_path / 'generated')
    (tmp_path / 'app/models/collision.py').write_text(MODEL.replace("class Thing", f"class {name}").replace('    id:', "    __tablename__ = 'other_thing'\n    id:"))
    with pytest.raises(Exception, match=error):
        generate_code()
    assert before == snapshot(tmp_path / 'generated')
