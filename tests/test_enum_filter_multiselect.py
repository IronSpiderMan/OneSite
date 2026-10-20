"""Scalar enum filters accept multiple values without changing stored fields."""
import ast
from enum import Enum
from types import SimpleNamespace
from typing import List, Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from onesite.codegen.filter_defaults import validate_filter_default
from onesite.codegen.phases.introspect_models import _introspect_module
from test_frontend_request_cache import TEMPLATES


class FilterStatus(str, Enum):
    pending = 'pending'
    running = 'running'
    completed = 'completed'


class EnumFilterItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: FilterStatus = Field(sa_column_kwargs={'info': {'site_props': {
        'is_search_field': True, 'filter_default': ['pending', 'running'],
    }}})
    enabled: bool = Field(default=True, sa_column_kwargs={'info': {'site_props': {'is_search_field': True}}})


def test_generated_enum_filters_execute_with_or_and_pagination_counts():
    metadata = _introspect_module(SimpleNamespace(EnumFilterItem=EnumFilterItem), 'enum_filter_item')[0]
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    for name in ('api.py.j2', 'service.py.j2', 'crud.py.j2'):
        source = env.get_template(name).render(model=metadata)
        tree = ast.parse(source)
        assert 'status: Optional[List[str]]' in source
        if name == 'crud.py.j2':
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_apply_filters')
            namespace = dict(Optional=Optional, List=List, EnumFilterItem=EnumFilterItem, col=col)
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<filters>', 'exec'), namespace)
            apply = namespace['_apply_filters']
            # Both list and count call the same filtering function.
            assert source.count('statement = _apply_filters(') == 2
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([EnumFilterItem(status=s, enabled=e) for s, e in [
            (FilterStatus.pending, True), (FilterStatus.running, True),
            (FilterStatus.completed, True), (FilterStatus.running, False),
        ]])
        session.commit()
        for values, enabled, expected in [
            (['pending', 'running'], True, 2), (['pending'], None, 1),
            ('pending', None, 1), ([], None, 4), (None, None, 4),
        ]:
            statement = apply(select(EnumFilterItem), status=values, enabled=enabled)
            assert len(session.exec(statement).all()) == expected
            assert len(session.exec(statement.limit(1)).all()) == 1
    page = env.get_template('frontend_page_list.tsx.j2').render(model=metadata)
    assert "if (values.length > 0) next['status'] = values;" in page
    assert "(Array.isArray(value) ? value : [value]).map(String)" in page
    control = env.get_template('frontend_list_filter_control.tsx.j2').render(
        model=metadata, field=next(f for f in metadata.fields if f.name == 'status'), ns={'search_field_count': 2})
    assert '<SearchableSelect' in control and 'multiple={true}' in control
    assert '<SelectItem' not in control


def test_scalar_enum_defaults_accept_single_and_multiple_values():
    field = {'is_enum': True, 'enum_values': ['pending', 'running']}
    for value in ('pending', ['pending', 'running'], []):
        assert validate_filter_default(value, field, 'Item.status') == value
    with pytest.raises(ValueError, match='Item.status'):
        validate_filter_default(['unknown'], field, 'Item.status')


def test_generated_api_parses_repeated_and_legacy_query_parameters():
    from fastapi import FastAPI, Query
    from fastapi.testclient import TestClient

    metadata = _introspect_module(SimpleNamespace(EnumFilterItem=EnumFilterItem), 'enum_filter_item')[0]
    source = Environment(loader=FileSystemLoader(TEMPLATES)).get_template('api.py.j2').render(model=metadata)
    # Use the generated parameter annotation and default in a minimal route,
    # isolating query parsing from authentication and database dependencies.
    tree = ast.parse(source)
    for function in tree.body:
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for argument, default in zip(function.args.args[-len(function.args.defaults):], function.args.defaults):
            if argument.arg == 'status':
                parameter = f'status: {ast.unparse(argument.annotation)} = {ast.unparse(default)}'
                break
        else:
            continue
        break
    namespace = dict(Optional=Optional, List=List, Query=Query)
    exec(f'def endpoint({parameter}):\n    return status', namespace)
    app = FastAPI()
    app.get('/')(namespace['endpoint'])
    with TestClient(app) as client:
        assert client.get('/?status=pending&status=running').json() == ['pending', 'running']
        assert client.get('/?status=pending').json() == ['pending']
        assert client.get('/').json() is None
