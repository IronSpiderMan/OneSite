"""Exercise generated stores, including request counts and out-of-order responses."""

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.phases.introspect_models import _introspect_module

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "src/onesite/templates/codegen"


class RequestItem(SQLModel, table=True):
    __tablename__ = "test_request_cache_item"
    __onesite__ = {"page_edit": True, "actions": {"enable": {"toggle": "enabled"}}}

    id: int | None = Field(default=None, primary_key=True)
    name: str
    enabled: bool = False


def model():
    return _introspect_module(SimpleNamespace(RequestItem=RequestItem), "request_item")[0]


def test_generated_pages_share_mutation_results_and_restore_lists():
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    metadata = model()
    listing = env.get_template("frontend_page_list.tsx.j2").render(model=metadata)
    detail = env.get_template("frontend_page_detail.tsx.j2").render(model=metadata)
    create = env.get_template("frontend_page_create.tsx.j2").render(model=metadata)
    service = env.get_template("frontend_service.ts.j2").render(model=metadata)
    update = service.split("export const updateRequestItem =", 1)[1].split("};", 1)[0]
    assert "markDataChanged();" in update
    detail_query = service.split("export const getRequestItem =", 1)[1].split("};", 1)[0]
    assert "markDataChanged();" not in detail_query
    assert "void ensureList(scopeFilters);" in listing
    assert "fetchData(1, 20, scopeFilters)" not in listing
    assert "store.canRestoreList(scopeFilters) ? store.listSearchValues : {}" in listing
    assert "await runAction(() => performRequestItemEnable(item.id)" in listing
    assert "await runAction(() => performRequestItemEnable(currentItem.id)" in detail
    assert "await fetchItem(currentItem!.id)" not in detail
    assert "await createItem(writablePayload(values, 'c'), { refreshList: false });" in create


def test_update_hooks_disable_local_only_list_updates():
    class HookedRequestItem(SQLModel, table=True):
        __tablename__ = "test_hooked_request_cache_item"
        id: int | None = Field(default=None, primary_key=True)

        def on_after_update(self, *, session, old, changes, context):
            pass

    metadata = _introspect_module(
        SimpleNamespace(HookedRequestItem=HookedRequestItem), "hooked_request_item"
    )[0]
    assert metadata.has_update_hooks is True
    assert model().has_update_hooks is False


def test_generated_store_request_lifecycle(tmp_path):
    node = shutil.which("node")
    compilers = list(ROOT.glob("examples/*/frontend/node_modules/typescript/lib/typescript.js"))
    if not node or not compilers:
        pytest.skip("Node and a local TypeScript compiler are required")
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    for variant, extras in {
        "normal": {},
        "resolver": {"has_read_resolvers": True},
        "tree": {"is_tree": True},
        "ordered": {"default_order_field": "rank"},
        "owner": {"owner_field": "owner_id"},
        "hook": {"has_update_hooks": True},
    }.items():
        metadata = model()
        metadata.update(extras)
        (tmp_path / f"{variant}.ts").write_text(
            env.get_template("frontend_store.ts.j2").render(model=metadata)
        )
    checked = subprocess.run(
        [node, str(ROOT / "tests/support/check_frontend_request_cache.cjs"),
         str(compilers[0]), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
