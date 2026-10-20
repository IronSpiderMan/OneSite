"""Regression coverage for generated indexes on reserved SQL identifiers."""

import sqlite3

from onesite.codegen.phases.generate import _render_create_index_sql
from onesite.codegen.render import create_template_environment


def test_generated_index_ddl_quotes_reserved_table_names():
    expected = (
        'CREATE INDEX IF NOT EXISTS "ix_group_department_id_page" '
        'ON "group" ("department_id", "created_at" DESC)'
    )
    sql = _render_create_index_sql(
        "ix_group_department_id_page",
        "group",
        ["department_id", "created_at DESC"],
    )
    assert sql == expected

    source = create_template_environment().get_template("db.py.j2").render(
        background_execution_enabled=False,
        external_resources_enabled=False,
        generated_indexes=[{"sql_literal": repr(sql)}],
        has_timescaledb=False,
        latest_table_imports=[],
        model_imports=[],
        timescaledb_models=[],
    )
    assert repr(expected) in source
    compile(source, "db.py", "exec")

    connection = sqlite3.connect(":memory:")
    connection.execute(
        'CREATE TABLE "group" '
        '(id INTEGER PRIMARY KEY, department_id INTEGER, created_at TEXT)'
    )
    connection.execute(expected)
    index_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        )
    }
    assert "ix_group_department_id_page" in index_names
