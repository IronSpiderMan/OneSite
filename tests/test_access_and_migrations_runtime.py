"""Behavioral tests of complete generated applications in isolated interpreters."""

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]


def run_python(cwd, code, *, success=True):
    result = subprocess.run(
        [sys.executable, '-c', code], cwd=cwd,
        env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
        capture_output=True, text=True, timeout=90,
    )
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


def project(tmp_path, models):
    source = tmp_path / 'app/models'
    source.mkdir(parents=True)
    (source / 'entities.py').write_text(models)
    (tmp_path / 'site_config.py').write_text(
        "from onesite.config import SiteConfig\nconfig=SiteConfig(project_name='test', style='industrial')\n"
    )
    sync(tmp_path)
    return tmp_path / 'generated/backend'


def sync(root, *, success=True):
    return run_python(root, 'from onesite.generator import generate_code; generate_code()', success=success)


ACCESS_MODELS = '''from sqlmodel import SQLModel, Field
class SecretRecord(SQLModel, table=True):
    __tablename__ = 'secret_record'
    __onesite__ = {'permissions': {'user':'crud', 'admin':'r', 'developer':'r'}}
    id: int | None = Field(default=None, primary_key=True)
    title: str
    secret: str = Field(default='private', sa_column_kwargs={'info': {'site_props': {'permissions': {'user':'', 'admin':'cru', 'developer':'cru'}}}})
class ReadOnlyRecord(SQLModel, table=True):
    __tablename__ = 'read_only_record'
    __onesite__ = {'permissions': {'user':'r', 'admin':'r', 'developer':'r'}}
    id: int | None = Field(default=None, primary_key=True)
    title: str = 'readonly'
class SubmitOnly(SQLModel, table=True):
    __tablename__ = 'submit_only'
    __onesite__ = {'permissions': {'user':'c', 'admin':'r', 'developer':'crud'}}
    id: int | None = Field(default=None, primary_key=True)
    title: str
class OwnedFolder(SQLModel, table=True):
    __tablename__ = 'owned_folder'
    __onesite__ = {'owner_field':'owner_id', 'union_key':['code','batch']}
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key='user.id')
    code: str
    batch: str
class InlineChild(SQLModel, table=True):
    __tablename__ = 'inline_child'
    __onesite__ = {'owner_field': 'owner_id'}
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key='user.id')
    folder_id: int = Field(foreign_key='owned_folder.id', sa_column_kwargs={'info': {'site_props': {'reverse': {'editor':'inline', 'on_remove':'delete'}}}})
    title: str
    secret: str = Field(default='private', sa_column_kwargs={'info': {'site_props': {'permissions': {'user':'', 'admin':'cru', 'developer':'cru'}}}})
class VisibleTag(SQLModel, table=True):
    __tablename__ = 'visible_tag'
    __onesite__ = {'owner_field':'owner_id'}
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key='user.id')
    title: str = Field(sa_column_kwargs={'info': {'site_props': {'permissions': {'user':'cu', 'admin':'cru', 'developer':'cru'}}}})
class FolderTag(SQLModel, table=True):
    __tablename__ = 'folder_tag'
    __onesite__ = {'is_link_table':True, 'm2m': {'directions':[{'from':'owned_folder', 'to':'visible_tag', 'editor':'select'}]}}
    folder_id: int = Field(foreign_key='owned_folder.id', primary_key=True)
    tag_id: int = Field(foreign_key='visible_tag.id', primary_key=True)
    order: int = 0
class PrivateTag(SQLModel, table=True):
    __tablename__ = 'private_tag'
    __onesite__ = {'permissions': {'user':'', 'admin':'crud', 'developer':'crud'}}
    id: int | None = Field(default=None, primary_key=True)
    title: str
class FolderPrivateTag(SQLModel, table=True):
    __tablename__ = 'folder_private_tag'
    __onesite__ = {'is_link_table':True, 'm2m': {'directions':[{'from':'owned_folder', 'to':'private_tag', 'editor':'select'}]}}
    folder_id: int = Field(foreign_key='owned_folder.id', primary_key=True)
    tag_id: int = Field(foreign_key='private_tag.id', primary_key=True)
'''


def test_generated_api_enforces_role_field_owner_relationship_and_upload_auth(tmp_path):
    backend = project(tmp_path, ACCESS_MODELS)
    user_model = tmp_path / 'app/models/user.py'
    user_model.write_text((ROOT / 'src/onesite/templates/models/user.py').read_text() + "\n    private_note: Optional[str] = Field(default=None, sa_column_kwargs={'info': {'site_props': {'permissions': {'user':'', 'admin':'cru', 'developer':'cru'}}}})\n")
    sync(tmp_path)
    script = (ROOT / 'tests/support/access_scenario.py').read_text()
    run_python(backend, script)


def db(root, action, *, success=True):
    return _db(root, action, success)


def _db(root, arguments, success):
    result = subprocess.run(
        [sys.executable, '-c', 'from onesite.main import app; app()', 'db', *arguments],
        cwd=root, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
        capture_output=True, text=True, timeout=90,
    )
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


MIGRATION_MODEL = '''from sqlmodel import SQLModel, Field
class Entry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
'''


def test_alembic_revision_upgrade_and_downgrade_preserve_existing_rows(tmp_path):
    backend = project(tmp_path, MIGRATION_MODEL)
    db(tmp_path, ['revision', '-m', 'initial'])
    db(tmp_path, ['upgrade'])
    run_python(backend, "import sqlite3; c=sqlite3.connect('app.db'); c.execute(\"INSERT INTO entry(title) VALUES ('keep me')\"); c.commit()")
    source = tmp_path / 'app/models/entities.py'
    source.write_text(MIGRATION_MODEL + '    note: str | None = None\n')
    db(tmp_path, ['revision', '-m', 'add note'])
    # Web startup must fail clearly until the explicit upgrade is applied.
    result = run_python(backend, 'import asyncio; from app.core.db import init_db; asyncio.run(init_db())', success=False)
    assert result.returncode != 0
    assert 'site db upgrade' in result.stderr
    db(tmp_path, ['upgrade'])
    db(tmp_path, ['check'])
    run_python(backend, "import sqlite3; c=sqlite3.connect('app.db'); assert c.execute('select title,note from entry').fetchall()==[('keep me',None)]")
    db(tmp_path, ['downgrade', '-1'])
    run_python(backend, "import sqlite3; c=sqlite3.connect('app.db'); assert c.execute('select title from entry').fetchall()==[('keep me',)]; assert 'note' not in [r[1] for r in c.execute('pragma table_info(entry)')]")
    assert len(list((tmp_path / 'app/migrations/versions').glob('*.py'))) == 2
    history = {p.name: p.read_bytes() for p in (tmp_path / 'app/migrations/versions').glob('*.py')}
    sync(tmp_path)
    assert history == {p.name: p.read_bytes() for p in (backend / 'migrations/versions').glob('*.py')}


def test_alembic_baseline_adopts_existing_matching_database(tmp_path):
    backend = project(tmp_path, MIGRATION_MODEL)
    run_python(backend, 'import asyncio; from app.core.db import init_db; asyncio.run(init_db())')
    run_python(backend, "import sqlite3; c=sqlite3.connect('app.db'); c.execute(\"INSERT INTO entry(title) VALUES ('legacy')\"); c.commit()")
    db(tmp_path, ['baseline'])
    db(tmp_path, ['check'])
    run_python(backend, "import sqlite3; c=sqlite3.connect('app.db'); assert c.execute('select title from entry').fetchone()[0]=='legacy'; assert c.execute('select version_num from alembic_version').fetchone()")
    # The baseline is a real initial migration that also builds a new database.
    (backend / 'app.db').rename(backend / 'legacy.db')
    db(tmp_path, ['upgrade'])
    run_python(backend, "import sqlite3; c=sqlite3.connect('app.db'); assert c.execute('select count(*) from entry').fetchone()[0]==0")
