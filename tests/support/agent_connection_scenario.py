"""SSE disconnects must release pool connections without cancelling SQL work."""

import asyncio

from sqlalchemy import event, text
from sqlmodel.ext.asyncio.session import AsyncSession


async def check_connections(app, agents, db, url, authorization):
    original_rows = agents.rows
    invalidated = []

    def on_invalidate(connection, record, exception):
        invalidated.append(exception)

    event.listen(db.engine.sync_engine, "invalidate", on_invalidate)
    try:
        for _ in range(3):
            response_started = asyncio.Event()
            polling = asyncio.Event()
            disconnect = asyncio.Event()
            query_finished = asyncio.Event()
            received_request = False

            async def slow_rows(session, id):
                result = await original_rows(session, id)
                if response_started.is_set():
                    polling.set()
                    if db.engine.dialect.name == "postgresql":
                        await session.execute(text("SELECT pg_sleep(0.1)"))
                    else:
                        await asyncio.sleep(0.1)
                    query_finished.set()
                return result

            agents.rows = slow_rows

            async def receive():
                nonlocal received_request
                if not received_request:
                    received_request = True
                    return {"type": "http.request", "body": b"", "more_body": False}
                await disconnect.wait()
                return {"type": "http.disconnect"}

            async def send(message):
                if message["type"] == "http.response.start":
                    assert message["status"] == 200
                    response_started.set()

            path = url + "/events"
            scope = {
                "type": "http", "asgi": {"version": "3.0", "spec_version": "2.0"},
                "http_version": "1.1", "method": "GET", "scheme": "http",
                "path": path, "raw_path": path.encode(), "query_string": b"",
                "root_path": "", "headers": [(b"authorization", authorization.encode())],
                "client": ("127.0.0.1", 12345), "server": ("test", 80),
            }
            task = asyncio.create_task(app(scope, receive, send))
            try:
                await asyncio.wait_for(polling.wait(), 5)
                disconnect.set()  # Cancel the SSE response while it owns a DB connection.
                await asyncio.wait_for(task, 5)
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            assert query_finished.is_set(), "SSE disconnect cancelled an in-flight database snapshot"
            assert not invalidated, f"SSE disconnect invalidated pooled connections: {invalidated}"
            assert db.engine.pool.checkedout() == 0
            async with AsyncSession(db.engine) as session:
                assert (await session.execute(text("SELECT 1"))).scalar_one() == 1
    finally:
        agents.rows = original_rows
        event.remove(db.engine.sync_engine, "invalidate", on_invalidate)

    if db.engine.dialect.name == "postgresql":
        # Force the same driver error as the report: a closed, idle pooled connection.
        # Dispose only this test app's pool so the next checkout must select this connection.
        await db.engine.dispose()
        async with db.engine.connect() as connection:
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
        driver.terminate()
        assert driver.is_closed()
        async with AsyncSession(db.engine) as session:
            assert (await session.execute(text("SELECT 1"))).scalar_one() == 1
