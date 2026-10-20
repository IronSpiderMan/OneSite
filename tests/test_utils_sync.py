"""Developer utils package synchronization coverage."""

from onesite.codegen.assets import _sync_project_utils


def test_modern_utils_tree_is_mirrored_into_generated_backend(tmp_path):
    source = tmp_path / "app" / "utils"
    (source / "data").mkdir(parents=True)
    (source / "formatting.py").write_text(
        "def format_alarm(value):\n"
        "    return str(value)\n",
        encoding="utf-8",
    )
    (source / "data" / "defaults.json").write_text(
        '{"severity": "warning"}\n',
        encoding="utf-8",
    )
    backend = tmp_path / "generated" / "backend"

    _sync_project_utils(tmp_path, backend)

    destination = backend / "app" / "utils"
    assert (source / "__init__.py").exists()
    assert (destination / "__init__.py").exists()
    assert (destination / "formatting.py").read_text(encoding="utf-8") == (
        source / "formatting.py"
    ).read_text(encoding="utf-8")
    assert (destination / "data" / "defaults.json").exists()


def test_utils_source_overwrites_and_removes_stale_generated_files(tmp_path):
    source = tmp_path / "app" / "utils"
    source.mkdir(parents=True)
    source_file = source / "alarm.py"
    source_file.write_text("VALUE = 'source'\n", encoding="utf-8")
    backend = tmp_path / "generated" / "backend"
    destination = backend / "app" / "utils"
    destination.mkdir(parents=True)
    (destination / "alarm.py").write_text("VALUE = 'backend'\n", encoding="utf-8")
    (destination / "retired.py").write_text("OLD = True\n", encoding="utf-8")

    _sync_project_utils(tmp_path, backend)

    assert (destination / "alarm.py").read_text(encoding="utf-8") == (
        "VALUE = 'source'\n"
    )
    assert not (destination / "retired.py").exists()

    source_file.unlink()
    _sync_project_utils(tmp_path, backend)

    assert not (destination / "alarm.py").exists()
    assert (destination / "__init__.py").exists()


def test_top_level_utils_directory_is_not_used_as_project_source(tmp_path):
    source = tmp_path / "utils"
    source.mkdir()
    (source / "legacy.py").write_text("LEGACY = True\n", encoding="utf-8")
    backend = tmp_path / "generated" / "backend"

    _sync_project_utils(tmp_path, backend)

    assert not (backend / "app" / "utils" / "legacy.py").exists()
