"""Database entry points must register the same table names as web startup."""
from test_access_and_migrations_runtime import db, project, run_python


MODELS = '''from sqlmodel import SQLModel, Field
class AlarmRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    user_id: int | None = Field(default=None, foreign_key="user.id")
class CustomRecord(SQLModel, table=True):
    __tablename__ = "custom_entries"
    id: int | None = Field(default=None, primary_key=True)
'''


def test_db_commands_use_snake_case_names_without_web_startup(tmp_path):
    backend = project(tmp_path, MODELS)
    db(tmp_path, ['current'])
    db(tmp_path, ['revision', '-m', 'initial'])
    db(tmp_path, ['upgrade'])
    db(tmp_path, ['check'])
    run_python(backend, """
import sqlite3
connection = sqlite3.connect('app.db')
tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'alarm_record' in tables, tables
assert 'alarmrecord' not in tables, tables
assert 'custom_entries' in tables, tables
indexes = {row[1] for row in connection.execute("PRAGMA index_list('alarm_record')")}
assert 'ix_alarm_record_user_id_page' in indexes, indexes
""")


def test_direct_database_startup_uses_snake_case_names(tmp_path):
    backend = project(tmp_path, MODELS)
    run_python(backend, """
import asyncio
from app.core.db import init_db, engine
async def initialize():
    try:
        await init_db()
    finally:
        await engine.dispose()
asyncio.run(initialize())
from app.models.entities import AlarmRecord, CustomRecord
assert AlarmRecord.__tablename__ == 'alarm_record'
assert CustomRecord.__tablename__ == 'custom_entries'
""")
