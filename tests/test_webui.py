"""Independent Studio tests, including real CLI generation and process cleanup."""

import copy
import importlib.util
import io
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("onesite_studio_test", ROOT / "webui.py")
webui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webui)


@pytest.fixture
def studio(tmp_path):
    app = webui.Studio(tmp_path / "projects")
    yield app
    app.close()


def sample_model():
    return {
        "name": "StudioProduct",
        "table": True,
        "config": {
            "permissions": {"user": "r", "admin": "crud", "developer": "crud"},
            "list_mode": "grid",
            "exportable": True,
        },
        "fields": [
            {
                "name": "id",
                "type": "Optional[int]",
                "value": None,
                "kwargs": {"default": "None", "primary_key": "True"},
                "props": {},
            },
            {
                "name": "name",
                "type": "str",
                "value": None,
                "kwargs": {"max_length": "80"},
                "props": {"is_search_field": True, "permissions": "cru"},
            },
        ],
        "hooks": "async def on_before_create(self, session, context):\n    self.name = self.name.strip()",
    }


def wait_job(job, timeout=30):
    deadline = time.monotonic() + timeout
    while job.finished is None and time.monotonic() < deadline:
        time.sleep(0.05)
    assert job.finished is not None, job.snapshot()
    return "".join(v["text"] for v in job.snapshot()["logs"])


def test_create_edit_save_and_real_cli_sync(studio):
    assert studio.python == sys.executable  # Preserve venv symlinks.
    p = studio.create("Catalog")
    assert "app/models/user.py" in p["files"]
    assert "site_config.py" in p["files"]
    assert not any(k.startswith("generated/") for k in p["files"])
    source = webui.render_model(sample_model())
    p["files"]["app/models/studio_product.py"] = source
    saved = studio.save("Catalog", p["files"], p["revision"])
    response = studio.start("Catalog", "sync", {}, saved["revision"])
    job = studio.jobs[response["id"]]
    logs = wait_job(job)
    assert job.code == 0, logs
    backend = studio.root / "Catalog/generated/backend/app"
    frontend = studio.root / "Catalog/generated/frontend/src"
    assert (studio.root / "Catalog/app/models/studio_product.py").read_text() == source
    generated_model = (backend / "models/studio_product.py").read_text()
    assert "async def on_before_create" in generated_model
    assert "self.name = self.name.strip()" in generated_model
    assert "StudioProduct" in (backend / "schemas/studio_product.py").read_text()
    assert (frontend / "services/studio_product.ts").exists()
    assert (frontend / "Routes.tsx").exists()


def test_config_roundtrip_keeps_env_expressions_and_does_not_execute(tmp_path):
    marker = tmp_path / "should_not_exist"
    source = (
        "from onesite.config import SiteConfig, env, sqlite_url\n"
        f"open({str(marker)!r}, 'w').write('never')\n"
        "config = SiteConfig(project_name='Original', database_url=sqlite_url(), "
        "secret_key=env('SECRET_KEY', default='changeme'), "
        "extra={'TIMEZONE': 'Asia/Shanghai'})\n"
    )
    parsed = webui.parse_config(source)
    parsed["values"]["project_name"] = "Updated"
    rendered = webui.render_config(parsed)
    assert "env('SECRET_KEY', default='changeme')" in rendered
    assert "Updated" in rendered
    assert not marker.exists()


def test_model_roundtrip_keeps_methods_metadata_and_complex_field_values():
    source = webui.render_model(sample_model())
    parsed = webui.parse_model(source)
    parsed["fields"].append(
        {
            "name": "related",
            "type": "list[str]",
            "value": "Relationship(back_populates='owner')",
            "kwargs": {},
            "props": {},
        }
    )
    result = webui.parse_model(webui.render_model(parsed))
    assert result["config"] == parsed["config"]
    assert result["hooks"] == parsed["hooks"]
    assert result["fields"][-1]["value"] == "Relationship(back_populates='owner')"
    assert result["fields"][1]["props"]["permissions"] == "cru"


def test_complex_inheritance_stays_source_only():
    source = (ROOT / "src/onesite/templates/models/user.py").read_text()
    with pytest.raises(webui.EditorError, match="多个类"):
        webui.parse_model(source)


def test_json_column_combines_visual_props_with_sqlalchemy_metadata():
    model = sample_model()
    model["fields"].append(
        {
            "name": "settings",
            "type": "dict[str, Any]",
            "value": None,
            "kwargs": {
                "default_factory": "dict",
                "sa_column": "Column(JSON, info={'custom': 42, 'site_props': {'label': 'Settings'}})",
            },
            "props": {"component": "json", "permissions": "cru"},
        }
    )
    source = webui.render_model(model)
    assert "'custom': 42" in source
    assert "'label': 'Settings'" in source
    assert "'permissions': 'cru'" in source
    assert "sa_column_kwargs" not in source.split("settings:", 1)[1]
    parsed = webui.parse_model(source)
    assert parsed["fields"][-1]["props"]["permissions"] == "cru"
    assert "'custom': 42" in webui.render_model(parsed)


def test_save_merges_sync_scaffolds_but_rejects_overlapping_edits(studio):
    p = studio.create("Merge")
    baseline = copy.deepcopy(p["files"])
    scaffold = studio.root / "Merge/app/utils/scaffold.py"
    scaffold.write_text("# added by sync\n")
    p["files"]["app/models/product.py"] = webui.render_model(sample_model())
    merged = studio.save("Merge", p["files"], p["revision"], baseline)
    assert merged["files"]["app/utils/scaffold.py"] == "# added by sync\n"
    baseline = copy.deepcopy(merged["files"])
    scaffold.write_text("# external edit\n")
    merged["files"]["app/utils/scaffold.py"] = "# local edit\n"
    with pytest.raises(webui.EditorError, match="同时在网页和磁盘"):
        studio.save("Merge", merged["files"], merged["revision"], baseline)
    assert scaffold.read_text() == "# external edit\n"


@pytest.mark.parametrize("name", ["../escape", "/tmp/escape", "bad/name", "a;touch pwn", "a\\b"])
def test_project_paths_cannot_escape(studio, name):
    with pytest.raises(webui.EditorError):
        studio.project(name, False)


def test_save_conflict_validation_and_symlink_protection(studio, tmp_path):
    p = studio.create("Safe")
    current = copy.deepcopy(p["files"])
    current["app/models/bad.py"] = "class Broken("
    with pytest.raises(webui.EditorError):
        studio.save("Safe", current, p["revision"])
    assert not (studio.root / "Safe/app/models/bad.py").exists()
    target = studio.root / "Safe/site_config.py"
    target.write_text(target.read_text() + "\n# external edit\n")
    with pytest.raises(webui.EditorError, match="磁盘内容"):
        studio.save("Safe", p["files"], p["revision"])
    p = studio.read("Safe")
    (studio.root / "Safe/app/outside").symlink_to(tmp_path, target_is_directory=True)
    p["files"]["app/outside/escape.py"] = "pass\n"
    with pytest.raises(webui.EditorError, match="符号链接"):
        studio.save("Safe", p["files"], p["revision"])
    assert not (tmp_path / "escape.py").exists()
    for path in ("../escape.py", "generated/backend/app/main.py", "app/../../escape.py"):
        assert not webui.is_editable(path)


def test_save_rolls_back_if_replace_fails(studio, monkeypatch):
    p = studio.create("Rollback")
    original = dict(p["files"])
    p["files"]["site_config.py"] += "\n# edited\n"
    p["files"]["app/utils/new.py"] = "pass\n"
    replace = os.replace
    calls = []

    def fail_second(src, dest):
        calls.append(dest)
        if len(calls) == 2:
            raise OSError("simulated write error")
        replace(src, dest)

    monkeypatch.setattr(webui.os, "replace", fail_second)
    with pytest.raises(OSError, match="simulated"):
        studio.save("Rollback", p["files"], p["revision"])
    assert studio.read("Rollback")["files"] == original


def test_http_boundary_blocks_cross_origin_and_missing_token(studio):
    handler = object.__new__(webui.Handler)
    handler.server = SimpleNamespace(studio=studio, server_address=("127.0.0.1", 8765))
    handler.headers = {"Host": "127.0.0.1:8765", "X-Studio-Token": studio.token}
    handler.guard(api=True)
    for invalid in (
        {"Host": "attacker.example:8765"},
        {"Origin": "https://attacker.example"},
        {"X-Studio-Token": "wrong"},
        {"Sec-Fetch-Site": "cross-site"},
    ):
        handler.headers = {"Host": "127.0.0.1:8765", "X-Studio-Token": studio.token, **invalid}
        with pytest.raises(webui.EditorError) as exc:
            handler.guard(api=True)
        assert exc.value.status == 403


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group behavior")
def test_stop_cleans_reload_children_and_streams_partial_lines(studio, tmp_path):
    stopped = tmp_path / "child-stopped"
    ready = tmp_path / "child-ready"
    child_code = (
        "import signal, time; from pathlib import Path; "
        f"signal.signal(signal.SIGTERM, lambda *_: (Path({str(stopped)!r}).touch(), exit(0))); "
        f"Path({str(ready)!r}).touch(); time.sleep(60)"
    )
    script = (
        "import subprocess, sys, time\nfrom pathlib import Path\n"
        f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
        f"while not Path({str(ready)!r}).exists(): time.sleep(0.01)\n"
        "print(child.pid, flush=True)\n"
        "print('partial-without-newline', end='', flush=True)\n"
        "time.sleep(60)\n"
    )
    job = webui.Job("Test", "run", [sys.executable, "-c", script], tmp_path, studio.env)
    studio.jobs[job.id] = job
    deadline = time.monotonic() + 5
    output = ""
    while "partial-without-newline" not in output and time.monotonic() < deadline:
        time.sleep(0.02)
        output = "".join(line["text"] for line in job.snapshot()["logs"])
    assert "partial-without-newline" in output
    job.stop()
    wait_job(job, 6)
    assert job.code != 0
    assert stopped.exists(), "The child must receive SIGTERM along with the CLI leader"


def test_run_uses_real_cli_arguments_and_rejects_overlap(studio, monkeypatch):
    p = studio.create("Runner")
    with pytest.raises(webui.EditorError, match="Sync"):
        studio.start("Runner", "run", {}, p["revision"])
    for name in ("generated/backend/app/api/api.py", "generated/frontend/src/Routes.tsx"):
        target = studio.root / "Runner" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    captured = []

    def popen(argv, **kwargs):
        captured.append((argv, kwargs))
        return SimpleNamespace(stdout=io.BytesIO(b""), wait=lambda: 0, pid=123456789)

    monkeypatch.setattr(webui.subprocess, "Popen", popen)
    response = studio.start("Runner", "run", {"component": "backend"}, p["revision"])
    wait_job(studio.jobs[response["id"]])
    assert captured[0][0][-6:] == ["run", ".", "--component", "backend", "--host", "127.0.0.1"]
    job = SimpleNamespace(project="Runner", finished=None)
    studio.jobs["busy"] = job
    try:
        with pytest.raises(webui.EditorError, match="已有命令"):
            studio.start("Runner", "sync", {}, p["revision"])
        with pytest.raises(webui.EditorError, match="先停止"):
            studio.save("Runner", p["files"], p["revision"])
    finally:
        del studio.jobs["busy"]


def test_arco_assets_are_embedded_and_served_with_security_headers():
    import gzip

    handler = object.__new__(webui.Handler)
    handler.server = SimpleNamespace(
        studio=SimpleNamespace(token="test-token"), server_address=("127.0.0.1", 8765)
    )
    statuses, headers = [], {}
    handler.send_response = statuses.append
    handler.send_header = headers.__setitem__
    handler.end_headers = lambda: None
    handler.headers = {"Host": "127.0.0.1:8765"}
    for path, (mime, compressed) in webui.ASSETS.items():
        handler.wfile = io.BytesIO()
        handler.path = path
        handler.do_GET()
        assert statuses[-1] == 200
        assert headers["Content-Type"] == mime
        assert headers["Content-Encoding"] == "gzip"
        assert int(headers["Content-Length"]) == len(compressed)
        source = gzip.decompress(handler.wfile.getvalue()).decode()
        assert "arco-" in source
        assert path in webui.HTML
        assert "style-src 'self'" in headers["Content-Security-Policy"]
    assert set(webui.ASSETS) == {"/assets/studio.js", "/assets/studio.css"}
    assert 'meta name="studio-token"' in webui.HTML
    handler.path = "/assets/../webui.py"
    handler.wfile = io.BytesIO()
    handler.do_GET()
    assert statuses[-1] == 404
    handler.path = "/assets/studio.js"
    handler.headers["Host"] = "attacker.example:8765"
    handler.do_GET()
    assert statuses[-1] == 403


def test_open_existing_project_outside_workspace(studio, tmp_path):
    project = tmp_path / "已有项目"
    project.mkdir()
    (project / "site_config.py").write_text("raise RuntimeError('must not execute')\n")
    (project / "app" / "models").mkdir(parents=True)
    (project / "app" / "models" / "product.py").write_text("value = 1\n")
    opened = studio.open_path(str(project))
    assert opened["path"] == str(project.resolve())
    assert opened["files"]["app/models/product.py"] == "value = 1\n"
    assert studio.read(opened["name"]) == opened
    assert {"name": opened["name"], "path": opened["path"]} in studio.listing()
    files = dict(opened["files"], **{"app/models/product.py": "value = 2\n"})
    studio.save(opened["name"], files, opened["revision"])
    assert (project / "app" / "models" / "product.py").read_text() == "value = 2\n"
    assert not (studio.root / project.name).exists()
    assert studio.open_path(str(project))["name"] == opened["name"]
    assert len(studio.listing()) == 1


def test_open_project_validates_path_and_distinguishes_names(studio, tmp_path):
    for value in ("", None, str(tmp_path / "missing"), str(tmp_path)):
        with pytest.raises(webui.EditorError):
            studio.open_path(value)
    names = []
    for parent in (studio.root, tmp_path / "external"):
        project = parent / "Demo"
        project.mkdir(parents=True)
        (project / "site_config.json").write_text("{}")
        names.append(studio.open_path(str(project))["name"])
    assert names[0] == "Demo"
    assert names[0] != names[1]
    assert studio.open_path("Demo")["name"] == "Demo"
    with pytest.raises(webui.EditorError):
        studio.open_path(str(studio.root / "Demo" / "site_config.json"))
    with pytest.raises(webui.EditorError):
        studio.read(str(tmp_path / "unregistered"))


def test_browse_directories(studio, tmp_path):
    project = studio.root / "中文项目"
    project.mkdir()
    (project / "site_config.py").write_text("raise RuntimeError('not executed')")
    (studio.root / "notes.txt").write_text("not a directory")
    listing = studio.browse_directories()
    assert listing["path"] == str(studio.root)
    assert listing["parent"] == str(studio.root.parent)
    assert not listing["is_project"]
    assert listing["directories"] == [{"name": project.name, "path": str(project)}]
    selected = studio.browse_directories(str(project))
    assert selected["is_project"]
    assert selected["directories"] == []
    assert studio.open_path(selected["path"])["path"] == str(project)
    assert studio.browse_directories(studio.root.anchor)["parent"] is None
    for value in (42, "", str(tmp_path / "missing"), str(studio.root / "notes.txt")):
        with pytest.raises(webui.EditorError):
            studio.browse_directories(value)


def test_browse_permission_error(studio, monkeypatch):
    def denied(_):
        raise PermissionError("denied")
    monkeypatch.setattr(Path, "iterdir", denied)
    with pytest.raises(webui.EditorError, match="没有权限") as error:
        studio.browse_directories()
    assert error.value.status == 403


def test_native_directory_picker_selection_cancel_and_failure(studio, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    calls = []
    def selected(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="/tmp/项目 folder/\n")
    monkeypatch.setattr(webui.subprocess, "run", selected)
    assert studio.select_directory() == {"path": "/tmp/项目 folder/"}
    assert calls[0][0] == "/usr/bin/osascript"
    assert calls[0][-1] == str(studio.root)
    monkeypatch.setattr(webui.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="\n"))
    assert studio.select_directory() == {"path": None}
    monkeypatch.setattr(webui.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout=""))
    with pytest.raises(webui.EditorError, match="无法打开"):
        studio.select_directory()
    assert not studio.picker_lock.locked()
    studio.picker_lock.acquire()
    try:
        with pytest.raises(webui.EditorError, match="已打开"):
            studio.select_directory()
    finally:
        studio.picker_lock.release()


def test_open_or_create_cli_project(studio, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    created = studio.open_or_create("NewApp")
    assert created["path"] == str(tmp_path / "NewApp")
    assert "site_config.py" in created["files"]
    assert not (studio.root / "NewApp").exists()
    monkeypatch.setattr(studio, "_create_target", lambda *_: pytest.fail("existing project must not be recreated"))
    assert studio.open_or_create("NewApp") == created
    monkeypatch.chdir(tmp_path / "NewApp")
    assert studio.open_or_create(".") == created
    with pytest.raises(webui.EditorError, match="不是 OneSite 项目"):
        studio.open_or_create(tmp_path)


def test_main_selects_requested_project_at_bootstrap(tmp_path, monkeypatch):
    project = tmp_path / "Existing"
    project.mkdir()
    (project / "site_config.json").write_text("{}")
    captured = {}
    class Server:
        server_address = ("127.0.0.1", 8765)
        def __init__(self, *args):
            pass
        def serve_forever(self, **kwargs):
            handler = object.__new__(webui.Handler)
            handler.server = self
            captured.update(handler.dispatch("/api/bootstrap", {}))
            raise KeyboardInterrupt
        def server_close(self):
            pass
    monkeypatch.setattr(webui, "ThreadingHTTPServer", Server)
    monkeypatch.setattr(webui.signal, "signal", lambda *args: None)
    monkeypatch.setattr(sys, "argv", ["webui.py", str(project), "--projects-dir", str(tmp_path / "workspace"), "--no-browser"])
    webui.main()
    assert captured["initial_project"] == str(project)
    assert {"name": str(project), "path": str(project)} in captured["projects"]
