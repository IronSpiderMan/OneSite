"""External hook discovery, validation and standalone transactional behavior."""

import os
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from onesite.codegen.model_hooks import (
    BULK_HOOK_ARGUMENTS,
    INSTANCE_HOOK_ARGUMENTS,
    sync_model_hooks,
)
from onesite.codegen.pipeline import generate_code
from onesite.codegen.types import ModelDefinition


ROOT = Path(__file__).resolve().parents[1]


def write_hook(root, name, source):
    path = root / "app/hooks" / f"{name}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def model(key="record", name="Record", source="entities", **extras):
    return ModelDefinition(module_name=key, name=name, source_module=source, **extras)


def bindings(backend):
    return runpy.run_path(str(backend / "app/core/model_hook_registry.py"))["MODEL_HOOKS"]


@pytest.mark.parametrize(
    "name, arguments",
    [(name, arguments | {"obj"}) for name, arguments in INSTANCE_HOOK_ARGUMENTS.items()]
    + [(name, arguments | {"model"}) for name, arguments in BULK_HOOK_ARGUMENTS.items()],
)
def test_all_hook_signatures_are_discovered_without_executing_source(tmp_path, name, arguments):
    write_hook(
        tmp_path, "record",
        "raise AssertionError('hook modules must not execute during sync')\n"
        f"async def {name}(*, {', '.join(sorted(arguments))}, unused=None):\n    pass\n",
    )
    backend = tmp_path / "generated/backend"
    metadata = model()
    sync_model_hooks(tmp_path, backend, [metadata])
    assert bindings(backend) == {
        ("app.models.entities", "Record"): {name: "app.hooks.record"}
    }
    assert metadata.get("has_update_hooks", False) == ("update" in name)


@pytest.mark.parametrize("source, error", [
    ("def on_befor_create(obj): pass\n", "unknown model hook 'on_befor_create'"),
    ("def on_before_create(request): pass\n", "unsupported required parameter 'request'"),
    ("def on_before_create(*, self): pass\n", "unsupported required parameter 'self'"),
    ("def on_after_commit_create(session): pass\n", "unsupported required parameter 'session'"),
    ("def on_after_bulk_delete(obj): pass\n", "unsupported required parameter 'obj'"),
    ("def on_after_commit_bulk_delete(session): pass\n", "unsupported required parameter 'session'"),
    ("def on_before_update(obj, /): pass\n", "cannot be positional-only"),
    ("def on_before_create(): pass\ndef on_before_create(): pass\n", "duplicate model hook"),
    ("on_after_create = None\n", "must be defined as a top-level function"),
    ("from ._helpers import on_after_create\n", "must be defined as a top-level function"),
    ("def on_after_create(: pass\n", "Unable to parse model hooks"),
])
def test_invalid_hooks_fail_before_writing_artifacts(tmp_path, source, error):
    write_hook(tmp_path, "record", source)
    backend = tmp_path / "generated/backend"
    with pytest.raises(ValueError, match=error):
        sync_model_hooks(tmp_path, backend, [model()])
    assert not backend.exists()


def test_model_keys_bind_classes_independently_of_source_filename_and_mirror_helpers(tmp_path):
    source = write_hook(tmp_path, "record", "def on_before_create(obj): pass\n")
    helper = write_hook(tmp_path, "_shared", "def normalize(value): return value.strip()\n")
    package = write_hook(tmp_path, "helpers/__init__", "")
    metadata = model(source="nested.grouped")
    backend = tmp_path / "generated/backend"
    sync_model_hooks(tmp_path, backend, [metadata])
    assert bindings(backend) == {
        ("app.models.nested.grouped", "Record"): {"on_before_create": "app.hooks.record"}
    }
    assert not (source.parent / "__init__.py").exists()  # Source stays developer-owned.
    assert (backend / "app/hooks/_shared.py").read_bytes() == helper.read_bytes()
    assert (backend / "app/hooks/helpers/__init__.py").read_bytes() == package.read_bytes()
    source.unlink()
    helper.unlink()
    sync_model_hooks(tmp_path, backend, [metadata])
    assert bindings(backend) == {}
    assert not (backend / "app/hooks/record.py").exists()
    assert not (backend / "app/hooks/_shared.py").exists()


@pytest.mark.parametrize("extras", [{"frontend_only": True}, {"is_link_table": True}])
def test_models_without_generated_cud_cannot_silently_register_hooks(tmp_path, extras):
    write_hook(tmp_path, "record", "def on_after_create(obj): pass\n")
    with pytest.raises(ValueError, match="has no generated CUD lifecycle"):
        sync_model_hooks(tmp_path, tmp_path / "generated/backend", [model(**extras)])


def test_association_models_with_generated_cud_accept_hooks(tmp_path):
    write_hook(tmp_path, "record", "def on_after_create(obj): pass\n")
    backend = tmp_path / "generated/backend"
    sync_model_hooks(
        tmp_path, backend, [model(is_link_table=True, is_association_table=True)],
    )
    assert ("app.models.entities", "Record") in bindings(backend)


def test_unknown_or_disabled_plugin_model_fails_with_available_keys(tmp_path):
    write_hook(tmp_path, "opcua_server", "def on_before_create(obj): pass\n")
    with pytest.raises(ValueError, match="unknown hook target model 'opcua_server'.*record"):
        sync_model_hooks(tmp_path, tmp_path / "generated/backend", [model()])


MODELS = '''from sqlmodel import Field, SQLModel

def record_event(name):
    from app.hooks._state import events
    events.append(name)

class Record(SQLModel, table=True):
    __tablename__ = 'different_table_name'
    id: int | None = Field(default=None, primary_key=True)
    title: str
    initialized: bool = False

    def on_before_create(self):
        record_event('model.before_create')
        assert self.title == self.title.strip()
        if self.title == 'forbidden':
            raise ValueError('model rejected create')

    def on_after_create(self):
        record_event('model.after_create')
        self.initialized = True

    def on_before_update(self, changes):
        record_event('model.before_update')
        assert changes['title'] == changes['title'].strip()

    def on_after_update(self):
        record_event('model.after_update')

    def on_after_commit_update(self):
        record_event('model.after_commit_update')
        raise ValueError('model post-commit failure')

    def on_before_delete(self):
        record_event('model.before_delete')

    def on_after_delete(self):
        record_event('model.after_delete')

    @classmethod
    def on_after_bulk_delete(cls):
        record_event('model.after_bulk_delete')

    @classmethod
    def on_after_commit_bulk_delete(cls):
        record_event('model.after_commit_bulk_delete')

class Audit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    record_id: int
    action: str
'''

RECORD_HOOKS = '''from app.models.entities import Audit
from ._state import events

def on_before_create(obj, context):
    events.append('external.before_create')
    assert context.operation == 'create'
    obj.title = obj.title.strip()

async def on_after_create(obj, *, session):
    events.append('external.after_create')
    assert obj.initialized
    session.add(Audit(record_id=obj.id, action='create'))
    if obj.title == 'rollback-create':
        raise ValueError('external rejected create')

def on_after_commit_create(obj):
    events.append('external.after_commit_create')
    if obj.title == 'post-failure':
        raise ValueError('external post-commit failure')

def on_before_update(changes, old, context):
    events.append('external.before_update')
    assert old['title'] != changes['title']
    assert 'title' in context.changed_fields
    changes['title'] = changes['title'].strip()

async def on_after_update(obj, session):
    events.append('external.after_update')
    session.add(Audit(record_id=obj.id, action='update'))
    if obj.title == 'rollback-update':
        raise ValueError('external rejected update')

def on_after_commit_update(obj, *, old, changes):
    events.append('external.after_commit_update')
    assert old['title'] != obj.title

def on_before_delete(obj, old):
    events.append('external.before_delete')
    assert obj.id == old['id']

async def on_after_delete(obj, session, old):
    events.append('external.after_delete')
    session.add(Audit(record_id=obj.id, action='delete'))
    if old['title'] == 'rollback-delete':
        raise ValueError('external rejected delete')

def on_after_commit_delete(old):
    events.append('external.after_commit_delete')

async def on_after_bulk_delete(model, *, session, olds, context):
    events.append('external.after_bulk_delete')
    assert model.__name__ == 'Record' and context.operation == 'bulk_delete'
    assert len(olds) == 2
    if any(old['title'] == 'rollback-bulk' for old in olds):
        raise ValueError('external rejected bulk delete')

def on_after_commit_bulk_delete(model, olds):
    events.append('external.after_commit_bulk_delete')
    assert model.__name__ == 'Record' and len(olds) == 2
'''


def test_generated_hooks_run_standalone_with_transactions_builtin_and_plugin_models(
    tmp_path, monkeypatch,
):
    source = tmp_path / "app/models/entities.py"
    source.parent.mkdir(parents=True)
    source.write_text(MODELS)
    (tmp_path / "site_config.py").write_text(
        "from onesite.config import SiteConfig\n"
        "config = SiteConfig(project_name='hooks', plugins=['opcua'], style='industrial')\n"
    )
    write_hook(tmp_path, "record", RECORD_HOOKS)
    write_hook(tmp_path, "_state", "events = []\n")
    write_hook(tmp_path, "user", '''def on_before_create(obj):
    obj.full_name = obj.full_name.strip()
def on_before_update(changes):
    changes['full_name'] = changes['full_name'].strip()
''')
    write_hook(tmp_path, "system_config", '''def on_before_update(changes):
    changes['site_name'] = changes['site_name'].strip()
''')
    write_hook(tmp_path, "opcua_server", '''def on_before_create(obj):
    obj.endpoint = obj.endpoint.strip()
def on_before_update(changes):
    changes['endpoint'] = changes['endpoint'].strip()
def on_after_create(obj):
    from ._state import events
    events.append('external.plugin.after_create')
    assert obj.security_mode == 'None'
''')
    monkeypatch.chdir(tmp_path)
    generate_code()
    backend = tmp_path / "generated/backend"
    assert not (source.parent / "user.py").exists()
    assert not (source.parent / "opcua_server.py").exists()
    store = (tmp_path / "generated/frontend/src/stores/useRecordStore.ts").read_text()
    assert " || true" in store  # External update hooks invalidate the cached list too.
    user_store = tmp_path / "generated/frontend/src/stores/useUserStore.ts"
    assert " || true" in user_store.read_text()  # User has no model-owned update method.
    assert ("app.models.entities", "Record") in bindings(backend)
    scenario = (ROOT / "tests/support/external_model_hooks_scenario.py").read_text()
    result = subprocess.run(
        [sys.executable, "-B", "-c", scenario], cwd=backend,
        env={**os.environ, "PYTHONPATH": ""}, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    # A bad hook must not replace the last successful generated application.
    before = {
        path.relative_to(backend): path.read_bytes()
        for path in backend.rglob("*.py") if "__pycache__" not in path.parts
    }
    write_hook(tmp_path, "user", "def on_before_create(unknown): pass\n")
    with pytest.raises(ValueError, match="unsupported required parameter 'unknown'"):
        generate_code()
    assert before == {
        path.relative_to(backend): path.read_bytes()
        for path in backend.rglob("*.py") if "__pycache__" not in path.parts
    }
    # Removing a hook removes its generated copy and binding on the next sync.
    (tmp_path / "app/hooks/user.py").unlink()
    generate_code()
    assert not (backend / "app/hooks/user.py").exists()
    assert ("app.models.user", "User") not in bindings(backend)
    assert " || true" not in user_store.read_text()
