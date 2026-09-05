"""Alembic entry point usable without the OneSite generator installed."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata, produce_migrations
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.core.db import database_url, register_models

BACKEND = Path(__file__).resolve().parents[2]


def configuration(script_location: str | None = None) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    if script_location:
        config.set_main_option("script_location", script_location.replace("%", "%%"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def configure_context(context, connection=None):
    register_models()
    options = dict(
        target_metadata=SQLModel.metadata,
        compare_type=True,
        render_as_batch=database_url.startswith("sqlite"),
    )
    if connection is None:
        context.configure(url=database_url, literal_binds=True, **options)
    else:
        context.configure(connection=connection, **options)


def run_environment(context):
    def run(connection):
        configure_context(context, connection)
        with context.begin_transaction():
            context.run_migrations()

    if context.is_offline_mode():
        configure_context(context)
        with context.begin_transaction():
            context.run_migrations()
    elif context.config.attributes.get("connection") is not None:
        run(context.config.attributes["connection"])
    else:
        async def online():
            engine = create_async_engine(database_url, poolclass=NullPool)
            try:
                async with engine.connect() as connection:
                    await connection.run_sync(run)
            finally:
                await engine.dispose()
        asyncio.run(online())


def check_startup_revision(connection):
    """Never silently apply schema changes when starting a web worker."""
    config = configuration()
    heads = set(ScriptDirectory.from_config(config).get_heads())
    current = set(MigrationContext.configure(connection).get_current_heads())
    if current != heads:
        raise RuntimeError("Database migration required: run `site db upgrade` before starting the backend")
    return bool(heads)


def baseline(connection, config: Config, message: str):
    """Adopt an existing matching schema with a reproducible initial revision."""
    register_models()
    if ScriptDirectory.from_config(config).get_heads():
        raise RuntimeError("Migration history already exists; use upgrade or revision")
    if not inspect(connection).get_table_names():
        raise RuntimeError("Database is empty; use `site db revision -m initial` then `site db upgrade`")
    differences = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), SQLModel.metadata)
    if differences:
        raise RuntimeError("Existing database differs from the models. Baseline the original model version first")
    # An empty comparison database makes the initial revision recreate the
    # complete schema, instead of recording an empty diff against existing tables.
    empty = create_engine("sqlite://")
    try:
        with empty.connect() as blank:
            migration = produce_migrations(MigrationContext.configure(blank), SQLModel.metadata)
        def initial_revision(context, revision, directives):
            directives[0].upgrade_ops = migration.upgrade_ops
            directives[0].downgrade_ops = migration.downgrade_ops
        command.revision(config, message=message, autogenerate=True, process_revision_directives=initial_revision)
        command.stamp(config, "head")
    finally:
        empty.dispose()


def main():
    parser = argparse.ArgumentParser(description="Manage the generated database with Alembic")
    parser.add_argument("action", choices=["revision", "upgrade", "downgrade", "current", "history", "check", "stamp", "baseline"])
    parser.add_argument("revision", nargs="?")
    parser.add_argument("-m", "--message", default="model changes")
    parser.add_argument("--script-location")
    args = parser.parse_intermixed_args()
    config = configuration(args.script_location)

    async def execute():
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                def run(sync_connection):
                    config.attributes["connection"] = sync_connection
                    if args.action == "baseline":
                        baseline(sync_connection, config, args.message)
                    elif args.action == "revision":
                        if not ScriptDirectory.from_config(config).get_heads() and inspect(sync_connection).get_table_names():
                            raise RuntimeError("Existing database has no migration history. Use `site db baseline` with matching models first")
                        command.revision(config, message=args.message, autogenerate=True)
                    elif args.action == "upgrade":
                        command.upgrade(config, args.revision or "head")
                    elif args.action in {"downgrade", "stamp"}:
                        if not args.revision:
                            raise RuntimeError(f"{args.action} requires an explicit revision")
                        getattr(command, args.action)(config, args.revision)
                    else:
                        getattr(command, args.action)(config)
                await connection.run_sync(run)
        finally:
            await engine.dispose()
    asyncio.run(execute())


if __name__ == "__main__":
    main()
