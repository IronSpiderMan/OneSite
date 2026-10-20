import asyncio
import sys
from datetime import timezone
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from typer.testing import CliRunner

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.main import app
from onesite.config import (
    OneSiteConfig,
    ReportDimensionInput,
    ReportInputs,
    ReportMeasureInput,
    ReportsConfig,
)


class ReportOrder(SQLModel, table=True):
    __tablename__ = "test_model_report_order"
    __onesite__ = OneSiteConfig(
        reports=ReportsConfig(
            categories=["cartesian", "multi_cartesian", "composition", "scatter"],
            inputs=ReportInputs(
                x={
                    "created_at": ReportDimensionInput(bins=["none", "day", "month"]),
                    "amount": ReportDimensionInput(),
                },
                y={
                    "amount": ReportMeasureInput(
                        aggregations=["raw", "sum", "avg", "min", "max", "median"]
                    )
                },
                cls=["status"],
                count=["$rows", "status"],
            ),
            filters=["created_at", "status"],
            visible=["admin", "developer"],
        )
    )

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime
    amount: float
    status: str


def test_model_reports_are_normalized_for_codegen():
    result = get_model_fields(ReportOrder, "report_order")
    reports = result.model_site_props["reports"]

    assert reports["categories"] == [
        "cartesian", "multi_cartesian", "composition", "scatter",
    ]
    assert reports["permitted_roles"] == ["admin", "developer"]
    assert reports["inputs"]["x"][0] == {
        "field": "created_at",
        "data_type": "datetime",
        "bins": ["none", "day", "month"],
        "readable_roles": ["user", "admin", "developer"],
    }
    assert reports["inputs"]["count"][0]["field"] == "$rows"
    assert reports["filters"][0] == {
        "field": "created_at",
        "data_type": "datetime",
        "label_key": "models.report_order.fields.created_at",
        "is_enum": False,
        "is_multi_select": False,
        "enum_values": [],
        "is_foreign_key": False,
        "foreign_key": None,
        "readable_roles": ["user", "admin", "developer"],
    }
    assert reports["limits"]["max_rows"] == 5000


def test_model_report_backend_and_frontend_templates_compile():
    result = get_model_fields(ReportOrder, "report_order")
    model = _build_model_dict("ReportOrder", "report_order", "report_order", result)
    model.update(
        min_role_for_read="USER", min_role_for_create="USER", min_role_for_update="USER",
        min_role_for_delete="USER", m2m_fields=[], reverse_m2m=[], inline_relations=[],
        definition_binding_meta=None, reverse_definition_bindings=[], external_resource=None,
        external_resource_dependents=[], has_dynamic_action_states=False,
        has_function_actions=False, schema_imports=[], is_association_table=False,
        show_in_menu=True, custom_importable=False,
    )
    templates = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    env = Environment(loader=FileSystemLoader(templates))
    service = env.get_template("service.py.j2").render(model=model)
    api = env.get_template("api.py.j2").render(model=model)
    schema = env.get_template("schema.py.j2").render(model=model)
    frontend = env.get_template("frontend_service.ts.j2").render(model=model)
    runtime = env.get_template("report_runtime.py.j2").render()
    template_api = env.get_template("report_template_api.py.j2").render(
        report_roles=["admin", "developer"]
    )
    page = env.get_template("model_report_page.tsx.j2").render(report_models=[model], table_report_models=[model])

    compile(service, "service.py", "exec")
    compile(api, "api.py", "exec")
    compile(schema, "schema.py", "exec")
    compile(runtime, "reports.py", "exec")
    compile(template_api, "report_templates.py", "exec")
    assert "get_model_report_catalog" in service
    assert '@router.get("/reports/catalog")' in api
    assert "ReportOrderModelReportQuery" in schema
    assert "getReportOrderModelReportCatalog" in frontend
    assert "ModelReportChart" in page
    assert "getReportOrders as readTableReportOrder" in page
    assert "source.visible[role]" in page
    assert "source.permissions[role]" in page
    assert "field.permissions[role]" in page
    assert "source.load(page, size, filters)" in page
    assert "result?.key === requestKey && source" in page
    assert "ReportDataTable config={block.table}" in page


def test_special_user_templates_include_model_report_contract_and_service():
    result = get_model_fields(ReportOrder, "report_order")
    model = _build_model_dict("User", "user", "user", result)
    model.update(
        reverse_m2m=[], schema_imports=[], reports=result.model_site_props["reports"],
    )
    templates = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    env = Environment(loader=FileSystemLoader(templates))
    schema = env.get_template("user_schema.py.j2").render(model=model)
    service = env.get_template("user_service.py.j2").render(model=model)

    compile(schema, "user_schema.py", "exec")
    compile(service, "user_service.py", "exec")
    assert "class UserModelReportQuery" in schema
    assert "async def get_model_report_catalog" in service
    assert "async def query_model_report" in service


def test_model_report_runtime_executes_allowlisted_aggregate_query(monkeypatch):
    templates = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    runtime = Environment(loader=FileSystemLoader(templates)).get_template(
        "report_runtime.py.j2"
    ).render()
    app_module = ModuleType("app")
    core_module = ModuleType("app.core")
    datetime_module = ModuleType("app.core.datetime")
    datetime_module.to_utc = lambda value: (
        value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    )
    monkeypatch.setitem(sys.modules, "app", app_module)
    monkeypatch.setitem(sys.modules, "app.core", core_module)
    monkeypatch.setitem(sys.modules, "app.core.datetime", datetime_module)
    namespace: dict[str, object] = {}
    exec(compile(runtime, "reports.py", "exec"), namespace)
    report = get_model_fields(ReportOrder, "report_order").model_site_props["reports"]

    async def run_query():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(ReportOrder.__table__.create)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add_all([
                ReportOrder(created_at=datetime(2026, 8, 1, 8), amount=10, status="paid"),
                ReportOrder(created_at=datetime(2026, 8, 1, 9), amount=20, status="paid"),
                ReportOrder(created_at=datetime(2026, 8, 2, 8), amount=5, status="draft"),
            ])
            await session.commit()
            result = await namespace["query_model_report"](
                session,
                source_model=ReportOrder,
                report=report,
                role="admin",
                payload={
                    "category": "cartesian",
                    "chart": "line.smooth",
                    "bindings": {
                        "x": {"field": "created_at", "bin": "day"},
                        "y": {"field": "amount", "aggregation": "sum"},
                    },
                },
            )
        await engine.dispose()
        return result

    result = asyncio.run(run_query())
    assert [row["y"] for row in result["rows"]] == [30.0, 5.0]
    assert result["meta"]["truncated"] is False


def test_site_sync_generates_model_report_page_and_endpoints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "ReportApp"])
    assert created.exit_code == 0, created.output
    project = tmp_path / "ReportApp"
    model_file = project / "app" / "models" / "order.py"
    model_file.write_text(
        "from datetime import datetime\n"
        "from sqlmodel import Field, SQLModel\n\n"
        "class Order(SQLModel, table=True):\n"
        "    __onesite__ = {'reports': {\n"
        "        'categories': ['cartesian', 'multi_cartesian', 'composition', 'scatter'],\n"
        "        'inputs': {\n"
        "            'x': {'created_at': {'bins': ['none', 'day']}, 'amount': {}},\n"
        "            'y': {'amount': {'aggregations': ['raw', 'sum', 'avg']}},\n"
        "            'cls': ['status'], 'count': ['$rows'],\n"
        "        }, 'filters': ['created_at', 'status'],\n"
        "    }}\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    created_at: datetime\n"
        "    amount: float\n"
        "    status: str\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    backend = project / "generated" / "backend" / "app"
    frontend = project / "generated" / "frontend" / "src"
    endpoint = (backend / "api" / "endpoints" / "order.py").read_text(encoding="utf-8")
    template_endpoint = (backend / "api" / "endpoints" / "report_templates.py").read_text(encoding="utf-8")
    template_model = (backend / "models" / "report_template.py").read_text(encoding="utf-8")
    template_service = (frontend / "services" / "report-templates.ts").read_text(encoding="utf-8")
    api_router = (backend / "api" / "api.py").read_text(encoding="utf-8")
    report_page = (frontend / "pages" / "Reports.tsx").read_text(encoding="utf-8")
    report_chart = (frontend / "components" / "visualization-chart.tsx").read_text(encoding="utf-8")
    assert '@router.get("/reports/catalog")' in endpoint
    assert '@router.post("/reports/query")' in endpoint
    assert 'class ReportTemplate(SQLModel, table=True)' in template_model
    assert '@router.get("/", response_model=list[ReportTemplateRead])' in template_endpoint
    assert "ReportTemplate.owner_id == current_user.id" in template_endpoint
    assert 'include_router(report_templates.router, prefix="/report-templates"' in api_router
    assert "createReportTemplate" in template_service
    assert "getOrderModelReportCatalog" in report_page
    assert "item.data_type === 'bool'" in report_page
    assert "item.data_type === 'date' || item.data_type === 'datetime'" in report_page
    assert "item.is_enum" in report_page
    assert "item.is_foreign_key" in report_page
    assert "item.data_type === 'int' || item.data_type === 'float'" in report_page
    assert "item.is_foreign_key || item.data_type" not in report_page
    assert "SearchableSelect" in report_page
    assert "xl:h-full xl:min-h-0 xl:flex-col xl:overflow-hidden" in report_page
    assert "flex-1 space-y-5 overflow-y-auto overscroll-contain" not in report_page
    assert 'data-report-scroll="chart-settings"' in report_page
    assert "<select " not in report_page
    assert "ModelReportChart" in report_chart
    compile((backend / "core" / "reports.py").read_text(encoding="utf-8"), "reports.py", "exec")


def test_report_category_requires_its_input_slots():
    class InvalidReport(SQLModel, table=True):
        __tablename__ = "test_invalid_model_report"
        __onesite__ = {
            "reports": {
                "categories": ["multi_cartesian"],
                "inputs": {
                    "x": {"created_at": {"bins": ["day"]}},
                    "y": {"amount": {"aggregations": ["sum"]}},
                },
            }
        }

        id: int | None = Field(default=None, primary_key=True)
        created_at: datetime
        amount: float

    with pytest.raises(ValueError, match="multi_cartesian.*cls"):
        get_model_fields(InvalidReport, "invalid_report")


def test_report_rejects_numeric_aggregation_on_text():
    class InvalidMeasure(SQLModel, table=True):
        __tablename__ = "test_invalid_report_measure"
        __onesite__ = {
            "reports": {
                "categories": ["cartesian"],
                "inputs": {
                    "x": {"status": {}},
                    "y": {"status": {"aggregations": ["sum"]}},
                },
            }
        }

        id: int | None = Field(default=None, primary_key=True)
        status: str

    with pytest.raises(ValueError, match="numeric aggregation"):
        get_model_fields(InvalidMeasure, "invalid_measure")


def test_report_template_runtime_handles_rolling_dates_and_legacy_crypto(tmp_path):
    """Execute generated helpers, including HTTP/older browser ID generation."""
    import shutil
    import subprocess
    import json

    root = Path(__file__).parents[1]
    node = shutil.which("node")
    compilers = list(root.glob("examples/*/frontend/node_modules/typescript/lib/typescript.js"))
    if not node or not compilers:
        pytest.skip("Node and a frontend TypeScript installation are required")
    editor = (root / "src/onesite/templates/codegen/report_editor.tsx.j2").read_text()
    resolver = editor.split("const ReportEditor:")[0]
    editor_component = editor.split("{% include 'report_table.tsx.j2' %}")[0]
    document_helpers = (root / "src/onesite/templates/codegen/report_document.tsx.j2").read_text().split("const ReportContent:")[0]
    script = tmp_path / "check.cjs"
    script.write_text(
        "const assert = require('node:assert/strict');\n"
        f"const ts = require({json.dumps(str(compilers[0]))});\n"
        f"const source = {json.dumps(resolver)};\n"
        "const js = ts.transpileModule(source, {compilerOptions: {target: ts.ScriptTarget.ES2020}}).outputText;\n"
        f"const editorComponent = {json.dumps(editor_component)};\n"
        "const editorDiagnostics = ts.transpileModule(editorComponent, {compilerOptions: {jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020}, reportDiagnostics: true}).diagnostics || [];\n"
        "assert.equal(editorDiagnostics.length, 0, editorDiagnostics.map(item => String(item.messageText)).join('\\n'));\n"
        f"const documentHelpers = {json.dumps(document_helpers)};\n"
        "const documentJS=ts.transpileModule(documentHelpers,{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;\n"
        "const safeUrl=new Function(documentJS+';return safeReportUrl;')();\n"
        "for(const value of ['javascript:alert(1)','data:text/html,abc','//evil.test','https://ok.test/\\nfoo']) assert.equal(safeUrl(value),undefined);\n"
        "for(const value of ['https://example.com','/images/report.png','#summary','mailto:team@example.com']) assert.equal(safeUrl(value),value);\n"
        "const makeId = new Function('crypto', 'Date', 'Math', js + '; return reportId;');\n"
        "const nativeCrypto = {randomUUID() { assert.equal(this, nativeCrypto); return 'native-uuid'; }};\n"
        "assert.equal(makeId(nativeCrypto, Date, Math)(), 'native-uuid');\n"
        "for (const legacyCrypto of [{}, undefined, {randomUUID: false}]) {\n"
        "  const id = makeId(legacyCrypto, {now: () => 123}, {random: () => 0.5});\n"
        "  const ids = Array.from({length: 1000}, () => id());\n"
        "  assert.equal(new Set(ids).size, 1000);\n"
        "  assert.ok(ids.every(value => typeof value === 'string' && value.length > 0));\n"
        "}\n"
        "const resolve = new Function(js + '; return resolveReportQuery;')();\n"
        "const q = {payload:{filters:{status:'ok',day:{gte:'2000-01-01'}}},relativeDays:{day:7},dateTypes:{day:'date'}};\n"
        "assert.deepEqual(resolve(q,new Date(2026,8,5)).filters,{status:'ok',day:{gte:'2026-08-30',lte:'2026-09-05'}});\n"
        "assert.equal(q.payload.filters.day.gte,'2000-01-01');\n"
        "assert.equal(resolve(q,new Date(2026,8,6)).filters.day.gte,'2026-08-31');\n"
        "assert.equal(resolve(q,new Date(2024,2,1)).filters.day.gte,'2024-02-24');\n"
        "q.dateTypes.day='datetime';\n"
        "assert.equal(resolve(q,new Date(2026,8,6)).filters.day.lte,'2026-09-06T23:59:59.999999');\n"
        "q.relativeDays.day=0; assert.deepEqual(resolve(q).filters.day,{gte:'2000-01-01'});\n"
        "const {resize, reorder, swap} = new Function(js + ';return {resize:resizeReportRow,reorder:reorderReportRows,swap:swapReportBlocks};')();\n"
        "const a={id:'a',text:'alpha',format:'html'}, b={id:'b',text:'beta',query:q}, c={id:'c',text:'gamma'};\n"
        "const rows=[{id:'one',blocks:[a,b,c]},{id:'two',blocks:[{id:'d',text:'delta'}]}];\n"
        "const single=resize(rows,'one','single');\n"
        "assert.deepEqual(single.flatMap(r=>r.blocks).map(b=>b.id),['a','b','c','d']);\n"
        "assert.equal(single[1].blocks[0].query,q); assert.equal(rows[0].blocks.length,3);\n"
        "const expanded=resize(single,'one','thirds'); assert.equal(expanded[0].blocks.length,3);\n"
        "assert.equal(new Set(expanded.flatMap(r=>r.blocks).map(b=>b.id)).size,6);\n"
        "const ordered=reorder(rows,'one','two'); assert.deepEqual(ordered.map(r=>r.id),['two','one']);\n"
        "assert.equal(reorder(rows,'missing','two'),rows);\n"
        "const swapped=swap(rows,'b','d'); assert.equal(swapped[1].blocks[0].id,'b');\n"
        "assert.equal(swapped[1].blocks[0].query,q); assert.equal(rows[0].blocks[1].id,'b');\n"
        "const restore = new Function(js + ';return restoreReportLayout;')();\n"
        "const edited = swapped.map(r=>({...r,blocks:r.blocks.map(b=>b.id==='b'?{...b,text:'new prose',format:'markdown'}:b)}));\n"
        "const restored=restore(rows,edited); assert.equal(restored[0].blocks[1].text,'new prose');\n"
        "assert.equal(restored[0].blocks[1].format,'markdown'); assert.equal(restored[0].blocks[1].query,q);\n"
        "const {pages,remove}=new Function(js+';return {pages:splitReportPages,remove:removeReportRow};')();\n"
        "const paged=[{id:'p1',blocks:[a]},{id:'p2',pageBreak:true,blocks:[b]},{id:'p2b',blocks:[c]}];\n"
        "assert.deepEqual(pages(paged).map(p=>p.map(r=>r.id)),[['p1'],['p2','p2b']]);\n"
        "const deleted=remove(paged,'p2'); assert.deepEqual(pages(deleted).map(p=>p.map(r=>r.id)),[['p1'],['p2b']]);\n"
        "assert.equal(paged[2].pageBreak,undefined); assert.equal(pages([]).length,1);\n"
    )
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)


def test_report_table_uses_list_field_renderers(tmp_path):
    import json
    import shutil
    import subprocess

    root = Path(__file__).parents[1]
    node = shutil.which("node")
    compilers = list(root.glob("examples/*/frontend/node_modules/typescript/lib/typescript.js"))
    if not node or not compilers:
        pytest.skip("Node and a frontend TypeScript installation are required")
    templates = root / "src/onesite/templates/codegen"
    env = Environment(loader=FileSystemLoader(templates))
    fields = [
        {"name": "customer_id", "fk_info": {"label_field": "name", "target_model": "Customer", "target_service": "customer"}},
        *[{"name": kind, "ui_type": kind} for kind in ["datetime", "time", "date", "bool", "image", "images", "file", "video_stream", "location", "int", "float", "str"]],
        {"name": "state", "is_enum": True},
        {"name": "tags", "is_enum": True, "is_multi_select": True},
        {"name": "json", "ui_type": "json", "json_model_schema": {"fields": [{"name": "name", "labelKey": "json.name"}]}, "json_item_schema": None},
    ]
    for field in fields:
        field.update(permissions="r", role_permissions={"user": "r"}, is_search_field=True)
    fields.append({"name": "secret", "ui_type": "str", "is_search_field": True, "permissions": "cu", "role_permissions": {"user": ""}})
    page = env.get_template("model_report_page.tsx.j2").render(
        report_models=[], table_report_models=[{
            "name": "Order", "module_name": "order", "role_visible": {"user": True},
            "role_permissions": {"user": "r"}, "fields": fields,
            "extra_fields": [{"name": "online", "label_key": "online", "component": "online_status", "show_in_list": True}],
        }],
    )
    assert "key: 'secret'" not in page
    for name in ["frontend_list_cell.tsx.j2", "frontend_json_preview.tsx.j2", "frontend_list_extra_cell.tsx.j2"]:
        assert "include '" + name + "'" in (templates / "frontend_page_list.tsx.j2").read_text()
        assert "include '" + name + "'" in (templates / "model_report_page.tsx.j2").read_text()
    for name in ["frontend_list_filter_control.tsx.j2", "frontend_list_filter_values.ts.j2"]:
        assert "include '" + name + "'" in (templates / "frontend_page_list.tsx.j2").read_text()
        assert "include '" + name + "'" in (templates / "report_table_filters.tsx.j2").read_text()
    assert "source.load(page, size, filters)" in page
    assert "window.clearTimeout(timer)" in page
    assert "page: 1, filters:" in page
    assert "JSON.stringify(filters)" in page
    assert "hiddenFields?: string[]" in page
    assert "visibleReportTableFields(availableFields, hiddenFields)" in page
    helpers = (templates / "report_table.tsx.j2").read_text().split("const ReportDataTable:")[0]
    cells = page[page.index("type ReportTableFilterProps"):page.index("type JsonPreviewSchema")]
    datetime = (root / "src/onesite/templates/frontend/src/lib/datetime.ts").read_text().replace('import i18n from "../i18n"', 'const i18n = {language: "en-GB"};').replace("import.meta.env.VITE_TIMEZONE", "'UTC'").replace("export function", "function")
    script = tmp_path / "table.cjs"
    script.write_text(
        "const assert = require('node:assert/strict');\n"
        f"const ts = require({json.dumps(str(compilers[0]))});\n"
        "const compile = s => ts.transpileModule(s,{compilerOptions:{jsx:ts.JsxEmit.React,target:ts.ScriptTarget.ES2020},reportDiagnostics:true});\n"
        f"assert.equal(compile({json.dumps(page)}).diagnostics.length,0);\n"
        f"const js = compile({json.dumps(datetime + helpers + cells)}).outputText;\n"
        "const React={Fragment:'fragment',createElement:(type,props,...children)=>({type,props,children})};\n"
        "const sources=new Function('React','Badge','JsonPreview','readTableOrder',js+';return {sources:tableSources,valid:validReportTableSize,readable:readableReportTableFields,visible:visibleReportTableFields};')(React,'badge','json',()=>{});\n"
        "for(const size of [1,7,35,123,1000]) assert.equal(sources.valid(size),true);\n"
        "for(const size of [0,-1,1.5,NaN,Infinity,Number.MAX_SAFE_INTEGER+1]) assert.equal(sources.valid(size),false);\n"
        "const fields=sources.sources[0].fields; const available=sources.readable(fields,'user');\n"
        "assert.deepEqual(sources.visible(available),available);\n"
        "const saved=JSON.parse(JSON.stringify({hiddenFields:['datetime','customer_id']}));\n"
        "assert.ok(sources.visible(available,saved.hiddenFields).every(f=>!saved.hiddenFields.includes(f.key)));\n"
        "assert.deepEqual(sources.visible(available,available.map(f=>f.key)),[]);\n"
        "assert.deepEqual(sources.visible(available,[]),available);\n"
        "assert.deepEqual(sources.visible(available,['removed_field']),available);\n"
        "const restricted=[{key:'private',permissions:{admin:'r'}},{key:'owner',permissions:{user:'r'},hiddenForUser:true}];\n"
        "assert.deepEqual(sources.visible(sources.readable(restricted,'user'),[]),[]);\n"
        "const build=sources.sources[0].buildFilters;\n"
        "const raw={str:'Alice',bool:'false',datetime_from:'2026-09-01',datetime_to:'2026-09-05',time:'11:02',state:'ready',tags:['a','b'],customer_id:'42',secret:'hidden',unknown:'drop'};\n"
        "const expected={str:'Alice',bool:false,datetime_from:'2026-09-01T00:00:00',datetime_to:'2026-09-05T23:59:59',time:'11:02',state:'ready',tags:['a','b'],customer_id:42};\n"
        "assert.deepEqual(build(raw,'user'),expected);\n"
        "assert.deepEqual(build(JSON.parse(JSON.stringify(raw)),'user'),expected);\n"
        "assert.deepEqual(build(raw,'unknown'),{});\n"
        "assert.deepEqual(build({bool:'__all__',state:'__all__',tags:[],str:'',customer_id:''},'user'),{});\n"
        "assert.deepEqual(build({},'user'),{}); assert.equal(raw.datetime_from,'2026-09-01');\n"
        "const t=(key,fallback)=>({'models.order.enums.state.ready':'Ready','models.order.enums.tags.a':'Tag A','video_stream.stream':'Stream','common.online':'Online'}[key]||fallback||key);\n"
        "const render=(key,value,extra={})=>sources.sources[0].fields.find(f=>f.key===key).render({[key]:value,...extra},t,'Asia/Shanghai');\n"
        "const text=n=>n==null||n===false?'':typeof n==='object'?(n.children||[]).flat(Infinity).map(text).join(''):String(n);\n"
        "assert.equal(text(render('datetime','2026-09-05T11:02:01.141208Z')),'05/09/2026, 19:02:01');\n"
        "assert.equal(text(render('datetime',null)),'-'); assert.equal(text(render('time','11:02:01')),'11:02');\n"
        "assert.equal(text(render('date','2026-09-05')),'2026-09-05');\n"
        "assert.equal(text(render('customer_id',42,{customer_id_label:'Alice'})),'Alice');\n"
        "assert.equal(text(render('customer_id',42)),'ID: 42'); assert.equal(text(render('customer_id',null)),'-');\n"
        "assert.equal(text(render('bool',true)),'Yes'); assert.equal(text(render('bool',false)),'No');\n"
        "assert.equal(text(render('state','ready')),'Ready'); assert.equal(text(render('tags',['a'])),'Tag A');\n"
        "assert.equal(text(render('location',{latitude:31,longitude:121})),'31, 121');\n"
        "assert.equal(text(render('location',null)),'-'); assert.equal(text(render('int',0)),'0'); assert.equal(text(render('float',1.25)),'1.25');\n"
        "assert.equal(text(render('str','hello')),'hello'); assert.equal(text(render('video_stream','rtsp://test')),'Stream');\n"
        "assert.equal(text(render('online',true)),'Online');\n"
        "assert.match(JSON.stringify(render('image','/photo.png')), /photo.png/);\n"
        "assert.equal(text(render('images',['/a.png','/b.png'])),'+1'); assert.equal(text(render('file','/a.pdf')),'File');\n"
        "assert.match(JSON.stringify(render('json',{name:'Alice'})), /json.name/);\n"
    )
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)


def test_report_mermaid_async_rendering(tmp_path):
    """Check success, errors and discarded async work without a browser engine."""
    import json
    import shutil
    import subprocess

    root = Path(__file__).parents[1]
    compilers = list(root.glob('examples/*/frontend/node_modules/typescript/lib/typescript.js'))
    node = shutil.which('node')
    if not node or not compilers:
        pytest.skip('Node and TypeScript are required')
    document = (root / 'src/onesite/templates/codegen/report_document.tsx.j2').read_text()
    component = document.split('const ReportMermaid:')[1].split('const REPORT_DOCUMENT_CSS')[0]
    script = tmp_path / 'mermaid.cjs'
    script.write_text(
        "const assert=require('node:assert/strict');\n"
        f"const ts=require({json.dumps(str(compilers[0]))});\n"
        f"const source={json.dumps('const ReportMermaid:' + component)};\n"
        "const js=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.React,target:ts.ScriptTarget.ES2020}}).outputText;\n"
        "let state=null,effect,cleanup; const pending=[];\n"
        "const React={createElement:(type,props,...children)=>({type,props,children})};\n"
        "const engine={render:(id,text)=>new Promise((resolve,reject)=>pending.push({id,text,resolve,reject}))};\n"
        "const Image=class{async decode(){assert.ok(this.src.startsWith('data:image/svg+xml;'));}};\n"
        "const render=new Function('React','useTranslation','useState','useEffect','loadReportMermaid','reportId','Image',js+';return ReportMermaid;')(React,()=>({t:(k,f)=>f}),()=>[state,v=>state=v],fn=>effect=fn,async()=>engine,()=>String(pending.length),Image);\n"
        "const flush=()=>new Promise(resolve=>setImmediate(resolve));\n"
        "(async()=>{\n"
        "assert.equal(render({text:'first'}).props['data-mermaid-ready'],'false'); cleanup=effect(); await flush();\n"
        "cleanup(); render({text:'second'}); effect(); await flush();\n"
        "pending[1].resolve({svg:'<svg>中文</svg>'}); await flush();\n"
        "assert.equal(state.source,'second'); assert.ok(decodeURIComponent(state.image).includes('中文'));\n"
        "pending[0].resolve({svg:'<svg>old</svg>'}); await flush(); assert.equal(state.source,'second');\n"
        "assert.equal(render({text:'second'}).props['data-mermaid-ready'],'true');\n"
        "assert.equal(render({text:'invalid'}).props['data-mermaid-ready'],'false'); effect(); await flush();\n"
        "pending[2].reject(new Error('syntax error')); await flush(); assert.equal(state.error,'syntax error');\n"
        "assert.equal(render({text:'invalid'}).props['data-mermaid-ready'],'false');\n"
        "})().catch(error=>{console.error(error);process.exitCode=1;});\n"
    )
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)


def test_report_mermaid_engine_uses_image_compatible_labels(tmp_path):
    """Protect the configuration that fixes SVG image decoding of <br> labels."""
    import json
    import shutil
    import subprocess

    root = Path(__file__).parents[1]
    compilers = list(root.glob('examples/*/frontend/node_modules/typescript/lib/typescript.js'))
    node = shutil.which('node')
    if not node or not compilers:
        pytest.skip('Node and TypeScript are required')
    document = (root / 'src/onesite/templates/codegen/report_document.tsx.j2').read_text()
    loader = document[document.index('let reportMermaidEngine:'):document.index('const ReportMermaid:')]
    script = tmp_path / 'mermaid-config.cjs'
    script.write_text(
        "const assert=require('node:assert/strict');\n"
        f"const ts=require({json.dumps(str(compilers[0]))});\n"
        f"const source={json.dumps(loader)};\n"
        "const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText.replace(\"import('mermaid')\",'load()');\n"
        "let calls=0,config; const engine={initialize:value=>config=value};\n"
        "const get=new Function('load',js+';return loadReportMermaid;')(async()=>{calls++;return {default:engine};});\n"
        "(async()=>{await Promise.all([get(),get()]);assert.equal(calls,1);assert.equal(config.htmlLabels,false);assert.equal(config.securityLevel,'strict');assert.ok(config.secure.includes('htmlLabels'));assert.equal(config.suppressErrorRendering,true);})().catch(e=>{console.error(e);process.exitCode=1;});\n"
    )
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)


def test_report_image_sources_are_isolated_and_validated(tmp_path):
    import json
    import shutil
    import subprocess

    root = Path(__file__).parents[1]
    compilers = list(root.glob('examples/*/frontend/node_modules/typescript/lib/typescript.js'))
    node = shutil.which('node')
    if not node or not compilers:
        pytest.skip('Node and TypeScript are required')
    document = (root / 'src/onesite/templates/codegen/report_document.tsx.j2').read_text()
    source = document.split('const renderReportHtml')[0] + 'const ReportImage:' + document.split('const ReportImage:')[1].split('// Load the diagram engine')[0]
    script = tmp_path / 'images.cjs'
    script.write_text(
        "const assert=require('node:assert/strict');\n"
        f"const ts=require({json.dumps(str(compilers[0]))});\n"
        f"const source={json.dumps(source)};\n"
        "const js=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.React,target:ts.ScriptTarget.ES2020}}).outputText;\n"
        "const React={createElement:(type,props,...children)=>({type,props,children})};\n"
        "let failed=''; const DOMParser=class{parseFromString(text){return {querySelector:()=>text==='broken',documentElement:{localName:text==='html'?'html':'svg',namespaceURI:'http://www.w3.org/2000/svg'}};}};\n"
        "const render=new Function('React','useTranslation','useState','DOMParser',js+';return ReportImage;')(React,()=>({t:(k,f)=>f}),()=>[failed,v=>failed=v],DOMParser);\n"
        "for(const text of ['javascript:alert(1)','data:text/html,x','//example.com/x','mailto:a@b']) assert.equal(render({text,format:'image'}).props.role,'alert');\n"
        "const image=render({text:'https://example.com/a.png',format:'image',alt:'Description'}).children[0];\n"
        "assert.equal(image.props.alt,'Description'); image.props.onError(); assert.equal(render({text:image.props.src,format:'image'}).props.role,'alert');\n"
        "for(const text of ['broken','html']) assert.equal(render({text,format:'svg'}).props.role,'alert');\n"
        "const svg=render({text:'<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>',format:'svg'}).children[0];\n"
        "assert.equal(svg.type,'img'); assert.ok(svg.props.src.startsWith('data:image/svg+xml;'));\n"
    )
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)


def test_report_chart_enum_labels_preserve_grouped_values(tmp_path):
    import json
    import shutil
    import subprocess

    root = Path(__file__).parents[1]
    compilers = list(root.glob('examples/*/frontend/node_modules/typescript/lib/typescript.js'))
    node = shutil.which('node')
    if not node or not compilers:
        pytest.skip('Node and TypeScript are required')
    source = (root / 'src/onesite/templates/codegen/frontend_visualization_chart.tsx.j2').read_text()
    helpers = source[source.index('const COLORS'):source.index('const lineOption')]
    option = source[source.index('const modelReportOption'):source.index('export const ModelReportChart')]
    script = tmp_path / 'enum-chart.cjs'
    script.write_text(
        "const assert=require('node:assert/strict');\n"
        f"const ts=require({json.dumps(str(compilers[0]))});\n"
        f"const source={json.dumps(helpers + option)};\n"
        "const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;\n"
        "const build=new Function(js+';return modelReportOption;')();\n"
        "const translate=(slot,value)=>({MEDIUM:'中',HIGH:'高',OPEN:'开启'}[value]||String(value));\n"
        "const pie=build('pie.basic',[{cls:'MEDIUM',value:12}],translate); assert.deepEqual(pie.series[0].data,[{name:'中',value:12}]);\n"
        "const rows=[{cls:'MEDIUM',x:'OPEN',y:7},{cls:'HIGH',x:'OPEN',y:9}];\n"
        "const bar=build('bar.basic',rows,translate); assert.deepEqual(bar.xAxis.data,['开启']); assert.equal(bar.series[0].name,'中 · Y'); assert.deepEqual(bar.series.map(s=>s.data),[[7],[9]]);\n"
        "const scatter=build('scatter.category',rows,translate); assert.equal(scatter.series[1].name,'高'); assert.deepEqual(scatter.series[1].data,[['OPEN',9]]);\n"
        "assert.equal(build('pie.basic',[{cls:'UNKNOWN',value:1}],translate).series[0].data[0].name,'UNKNOWN'); assert.equal(rows[0].cls,'MEDIUM');\n"
    )
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)
