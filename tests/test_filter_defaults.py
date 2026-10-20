"""Filter default validation and generated first-request behavior."""
from datetime import datetime
from pathlib import Path
import subprocess

import pytest
from sqlmodel import Field, SQLModel
from onesite.codegen.filter_defaults import validate_filter_default
from onesite.codegen.introspect import get_model_fields
from test_frontend_request_cache import model, TEMPLATES
from jinja2 import Environment, FileSystemLoader
from test_visualizations_codegen import _models
from onesite.codegen.visualizations import compile_visualizations
from onesite.visualization import chart, count, dim


@pytest.mark.parametrize('value,field,kind', [
    (False, {'ui_type': 'bool'}, None),
    (0, {'ui_type': 'int'}, 'select'),
    (['a'], {'is_enum': True, 'enum_values': ['a']}, 'multi_select'),
    ({'period': 'this_month'}, {'ui_type': 'datetime'}, 'date_range'),
    ({'min': 0, 'max': 2}, {'ui_type': 'int'}, 'number_range'),
])
def test_valid_defaults_preserve_types(value, field, kind):
    assert validate_filter_default(value, field, 'Example.field', kind) == value


@pytest.mark.parametrize('value,field,kind', [
    ('false', {'ui_type': 'bool'}, None),
    (True, {'ui_type': 'int'}, None),
    (['b'], {'is_enum': True, 'enum_values': ['a']}, 'multi_select'),
    ({'period': 'bad'}, {'ui_type': 'datetime'}, 'date_range'),
    ({'period': []}, {'ui_type': 'datetime'}, 'date_range'),
    ({'period': 'today'}, {'ui_type': 'str'}, None),
    ({'start': {'start': '2026-01-01'}}, {'ui_type': 'datetime'}, 'date_range'),
    ({'start': 'bad'}, {'ui_type': 'datetime'}, 'date_range'),
    ({'min': 3, 'max': 1}, {'ui_type': 'int'}, 'number_range'),
])
def test_invalid_defaults_have_context(value, field, kind):
    with pytest.raises(ValueError, match='Example.field'):
        validate_filter_default(value, field, 'Example.field', kind)


def test_introspection_and_first_request_defaults():
    class DefaultFilterRecord(SQLModel, table=True):
        id: int | None = Field(default=None, primary_key=True)
        enabled: bool = Field(default=True, sa_column_kwargs={'info': {'site_props': {'is_search_field': True, 'filter_default': False}}})
        created_at: datetime = Field(sa_column_kwargs={'info': {'site_props': {'is_search_field': True, 'filter_default': {'period': 'this_month'}}}})
    result = get_model_fields(DefaultFilterRecord, 'default_filter_record')
    assert next(f for f in result.fields if f.name == 'enabled').filter_default is False
    metadata = model()
    metadata['fields'][1]['is_search_field'] = True
    metadata['fields'][1]['filter_default'] = 'active'
    rendered = Environment(loader=FileSystemLoader(TEMPLATES)).get_template('frontend_page_list.tsx.j2').render(model=metadata)
    assert 'getDefaultSearchValues()' in rendered
    assert 'void ensureList(scopeFilters, buildSearchFilters(values), values);' in rendered
    assert 'onClick={() => setSearchValues({})}' in rendered
    assert 'setSearchValues(getDefaultSearchValues())' in rendered
    assert "delete next[" in rendered


def test_visualization_compiles_defaults():
    specs = compile_visualizations([chart('orders', title='Orders', model='VizOrder', preset='pie.donut', category=dim('status'), value=count(), filters=[{'key': 'level', 'field': 'level', 'default': 'LOW'}]).to_dict()], _models())
    assert specs[0]['filters'][0]['default'] == 'LOW'


def test_calendar_defaults_execute_in_typescript():
    root = Path(__file__).parents[1]
    ts = root / 'examples/onesite_full_test/frontend/node_modules/typescript/lib/typescript.js'
    if not ts.exists():
        pytest.skip('local TypeScript compiler unavailable')
    source = root / 'src/onesite/templates/frontend/src/utils/filterDefaults.ts'
    script = '''const ts = require(process.argv[1]); const fs = require('fs');
const code = ts.transpileModule(fs.readFileSync(process.argv[2], 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const m = {exports:{}}; new Function('exports', 'module', code)(m.exports,m);
const now = new Date(2026,0,1,12);
const resolve = p => m.exports.resolveFilterDefault({period:p},now);
const assert = require('assert');
assert.deepStrictEqual(resolve('last_month'), {start:'2025-12-01T00:00:00',end:'2025-12-31T23:59:59'});
assert.deepStrictEqual(resolve('this_week'), {start:'2025-12-29T00:00:00',end:'2026-01-04T23:59:59'});
assert.strictEqual(resolve('last_7_days').start,'2025-12-26T00:00:00');
assert.deepStrictEqual(m.exports.visualizationFilterDefaults({filters:[{key:'b',type:'select',default:false},{key:'n',type:'select',default:0}]}),{b:'false',n:'0'});
'''
    subprocess.run(['node', '-e', script, str(ts), str(source)], check=True)


def test_date_range_reaches_generated_backend():
    from test_date_field_codegen import DateModel
    from onesite.codegen.phases.introspect_models import _build_model_dict
    metadata = _build_model_dict('DateModel', 'date_model', 'date_model', get_model_fields(DateModel, 'date_model'))
    field = next(f for f in metadata['fields'] if f['name'] == 'due_date')
    field['is_search_field'] = True
    field['filter_default'] = {'period': 'today'}
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    import ast
    for name in ('api.py.j2', 'service.py.j2', 'crud.py.j2'):
        rendered = env.get_template(name).render(model=metadata)
        ast.parse(rendered)
        assert 'due_date_from: Optional[date]' in rendered
        assert 'due_date_to: Optional[date]' in rendered
    frontend = env.get_template('frontend_page_list.tsx.j2').render(model=metadata)
    assert "next['due_date_from'] = `${searchValues['due_date_from']}`" in frontend
