"""Execute generated time ordering against SQLite, including pagination."""
import ast
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class TimeSortRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime
    observed_at: Optional[datetime] = None
    day: date
    clock: time
    name: str = "example"


ENV = Environment(loader=FileSystemLoader(
    Path(__file__).parents[1] / "src/onesite/templates/codegen"
))


def model_metadata():
    model = _build_model_dict("TimeSortRecord", "time_sort_record", "time_sort_record",
                             get_model_fields(TimeSortRecord, "time_sort_record"))
    model.update(min_role="USER", min_role_for_read="USER", min_role_for_create="USER",
                 min_role_for_update="USER", min_role_for_delete="USER")
    return model


@pytest.mark.asyncio
@pytest.mark.parametrize("template", ["crud.py.j2", "user_crud.py.j2"])
@pytest.mark.parametrize("default_order_field", [None, "clock"])
async def test_generated_ordering_and_pagination(template, default_order_field):
    model = model_metadata()
    model["default_order_field"] = default_order_field
    code = ENV.get_template(template).render(model=model)
    tree = ast.parse(code)
    function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "get_multi")
    namespace = dict(Optional=Optional, List=List, Dict=Dict, Any=Any,
                     AsyncSession=Any, TimeSortRecord=TimeSortRecord, User=TimeSortRecord,
                     select=select, col=col, _apply_filters=lambda stmt, **kwargs: stmt)
    exec(compile(ast.Module(body=[function], type_ignores=[]), "generated_crud", "exec"), namespace)
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for id, observed in [(1, 3), (2, 1), (3, 1), (4, None)]:
            session.add(TimeSortRecord(id=id, created_at=datetime(2026, 1, id),
                observed_at=datetime(2026, 1, observed) if observed else None,
                day=date(2026, 1, 5-id), clock=time(id)))
        session.commit()

        class AsyncAdapter:
            async def exec(self, statement):
                return session.exec(statement)

        async def ids(**kwargs):
            return [item.id for item in await namespace["get_multi"](AsyncAdapter(), **kwargs)]

        assert await ids() == [4, 3, 2, 1]
        assert await ids(sort_by="observed_at", sort_order="asc", size=2) == [2, 3]
        assert await ids(sort_by="observed_at", sort_order="asc", size=2, page=2) == [1, 4]
        assert await ids(sort_by="observed_at", sort_order="desc") == [1, 2, 3, 4]
        assert await ids(sort_by="day", sort_order="asc") == [4, 3, 2, 1]
        assert await ids(sort_by="clock", sort_order="desc", size=-1) == [4, 3, 2, 1]
        for kwargs in ({"sort_by": "name"}, {"sort_by": "id; DROP TABLE x"},
                       {"sort_by": "created_at", "sort_order": "wrong"}):
            with pytest.raises(ValueError, match="Invalid time sort"):
                await ids(**kwargs)
    engine.dispose()


def test_templates_compile_and_forward_sorting():
    model = model_metadata()
    for template in ("api.py.j2", "crud.py.j2", "user_crud.py.j2", "service.py.j2", "user_service.py.j2"):
        rendered = ENV.get_template(template).render(model=model)
        ast.parse(rendered)
        assert "sort_by=sort_by" in rendered
        assert "sort_order=sort_order" in rendered
    page = ENV.get_template("frontend_page_list.tsx.j2").render(model=model)
    for name in ("created_at", "observed_at", "day", "clock"):
        assert f"void setSorting('{name}', 'asc')" in page
    assert "void setSorting('name'" not in page
    assert "else void setSorting();" in page
    assert "aria-sort=" in page


@pytest.mark.asyncio
async def test_api_rejects_invalid_sort_parameters():
    from types import SimpleNamespace
    from typing import Literal

    from fastapi import Depends, FastAPI, HTTPException, Query
    import json
    from urllib.parse import urlencode

    tree = ast.parse(ENV.get_template("api.py.j2").render(model=model_metadata()))
    function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == f"read_{model_metadata()['lower_name']}s")
    function.decorator_list = []
    calls = []

    async def get_multi(session, **kwargs):
        calls.append(kwargs)
        return kwargs

    namespace = dict(Optional=Optional, Literal=Literal, Any=Any, AsyncSession=Any,
                     Depends=Depends, HTTPException=HTTPException, Query=Query,
                     datetime=datetime, date=date, time=time, List=List,
                     db=SimpleNamespace(get_session=lambda: None),
                     service=SimpleNamespace(get_multi=get_multi))
    exec(compile(ast.Module(body=[function], type_ignores=[]), "generated_api", "exec"), namespace)
    app = FastAPI()
    app.get("/")(namespace[function.name])
    async def request(params=None):
        messages = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            messages.append(message)

        await app({"type": "http", "method": "GET", "path": "/", "root_path": "",
                   "query_string": urlencode(params or {}).encode(), "headers": [],
                   "scheme": "http", "server": ("test", 80), "client": ("test", 1),
                   "http_version": "1.1"}, receive, send)
        status = next(m["status"] for m in messages if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return status, json.loads(body)

    assert (await request())[1]["sort_by"] is None
    status, body = await request({"sort_by": "observed_at", "sort_order": "desc", "page": 2})
    assert status == 200
    assert body["sort_order"] == "desc"
    assert body["page"] == 2
    for params in ({"sort_by": "name"}, {"sort_by": "created_at", "sort_order": "bad"}):
        assert (await request(params))[0] == 422
    assert len(calls) == 2
