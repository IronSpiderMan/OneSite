"""Coverage for development and Nuitka production image builds."""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from typer.testing import CliRunner

from onesite.main import app


def _project(tmp_path: Path) -> Path:
    return _modern_project(tmp_path)


def _modern_project(tmp_path: Path) -> Path:
    generated = tmp_path / "generated"
    backend = generated / "backend"
    frontend = generated / "frontend"
    backend.mkdir(parents=True)
    frontend.mkdir()
    (tmp_path / "app").mkdir()
    (backend / "Dockerfile").write_text(
        "FROM python:3.10-slim AS development\n"
        "FROM python:3.10-slim AS production\n"
        "--include-package=passlib.handlers\n"
        "--include-package=bcrypt\n",
        encoding="utf-8",
    )
    (backend / "nuitka_entrypoint.py").write_text(
        "import uvicorn\n",
        encoding="utf-8",
    )
    (frontend / "Dockerfile").write_text("", encoding="utf-8")
    (frontend / ".dockerignore").write_text(
        "node_modules\ndist\n",
        encoding="utf-8",
    )
    return tmp_path


def test_production_build_targets_nuitka_backend_and_tags_both_images(
    tmp_path, monkeypatch
):
    project = _project(tmp_path)
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )
    monkeypatch.setattr("onesite.generator.generate_file", lambda *args, **kwargs: None)

    result = CliRunner().invoke(app, ["build", "--production", "--tag", "v2.4.0"])

    assert result.exit_code == 0, result.output
    build_commands = [command for command, _ in calls if command[1] == "build"]
    backend_command = build_commands[0]
    frontend_command = build_commands[1]
    assert backend_command == [
        "docker",
        "build",
        "-t",
        f"{project.name.lower()}-backend:v2.4.0",
        "--target",
        "production",
        ".",
    ]
    assert frontend_command == [
        "docker",
        "build",
        "-t",
        f"{project.name.lower()}-frontend:v2.4.0",
        ".",
    ]


def test_development_is_default_and_modes_are_mutually_exclusive(
    tmp_path, monkeypatch
):
    project = _project(tmp_path)
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append(command),
    )
    monkeypatch.setattr("onesite.generator.generate_file", lambda *args, **kwargs: None)

    runner = CliRunner()
    result = runner.invoke(app, ["build", "--component", "backend"])
    invalid = runner.invoke(app, ["build", "--production", "--development"])

    assert result.exit_code == 0, result.output
    build_commands = [command for command in calls if command[1] == "build"]
    assert build_commands[0][-3:] == ["--target", "development", "."]
    assert invalid.exit_code != 0


def test_build_uses_generated_contexts_for_modern_projects(tmp_path, monkeypatch):
    project = _modern_project(tmp_path)
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )
    monkeypatch.setattr("onesite.generator.generate_file", lambda *args, **kwargs: None)

    result = CliRunner().invoke(app, ["build"])

    assert result.exit_code == 0, result.output
    build_calls = [
        (command, kwargs)
        for command, kwargs in calls
        if len(command) > 1 and command[1] == "build"
    ]
    assert Path(build_calls[0][1]["cwd"]) == project / "generated" / "backend"
    assert Path(build_calls[1][1]["cwd"]) == project / "generated" / "frontend"


def test_build_writes_compose_into_deploy_directory(tmp_path, monkeypatch):
    project = _modern_project(tmp_path)
    (project / "site_config.json").write_text(
        json.dumps(
            {
                "allowed_origins": ["http://localhost:3000"],
                "database_url": "sqlite:///./app.db",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: None,
    )

    result = CliRunner().invoke(app, ["build"])

    assert result.exit_code == 0, result.output
    compose = project / "deploy" / "docker-compose.yml"
    assert compose.exists()
    assert "../uploads:/app/uploads" in compose.read_text(encoding="utf-8")
    assert not (project / "docker-compose.yml").exists()


def test_compose_uses_deploy_file_and_optional_env(tmp_path, monkeypatch):
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    compose = deploy / "docker-compose.yml"
    compose.write_text("services: {}\n", encoding="utf-8")
    env_file = deploy / ".env"
    env_file.write_text("PROJECT_NAME=test\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )

    result = CliRunner().invoke(app, ["compose", "up", "-d"])

    assert result.exit_code == 0, result.output
    assert calls[0][0] == [
        "docker-compose",
        "--env-file",
        str(env_file),
        "-f",
        str(compose),
        "up",
        "-d",
    ]


def test_compose_does_not_use_a_root_level_compose_file(tmp_path, monkeypatch):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services: {}\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append(command),
    )

    result = CliRunner().invoke(app, ["compose", "down"])

    assert result.exit_code == 1
    assert "Run 'site build' first" in result.output
    assert calls == []


def test_production_build_stops_before_engine_when_project_needs_sync(
    tmp_path, monkeypatch
):
    project = _project(tmp_path)
    (project / "generated" / "backend" / "Dockerfile").write_text(
        "FROM python:3.10-slim\n",
        encoding="utf-8",
    )
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append(command),
    )

    result = CliRunner().invoke(app, ["build", "--production"])

    assert result.exit_code == 1
    assert "site sync" in result.output
    assert calls == []


def test_production_dockerfile_uses_buildpack_builder():
    dockerfile = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "backend"
        / "Dockerfile"
    ).read_text(encoding="utf-8")

    assert "python:3.10-slim-bookworm AS base" in dockerfile
    assert "python:3.10-bookworm AS production-builder" in dockerfile
    assert "debian:bookworm-slim AS production" in dockerfile
    assert "python:3.10-slim-bookworm AS production" not in dockerfile
    assert (
        "python -m pip install --no-cache-dir --retries 20 "
        "nuitka ordered-set zstandard patchelf"
        in dockerfile
    )
    assert "--include-package=passlib.handlers" in dockerfile
    assert "--include-package=bcrypt" in dockerfile
    assert "RUN mkdir -p /app/data /app/uploads" in dockerfile
    assert (
        "COPY --from=production-builder /etc/ssl/certs/ca-certificates.crt "
        "/etc/ssl/certs/ca-certificates.crt"
        in dockerfile
    )
    assert (
        "PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
        in dockerfile
    )
    assert "--retries 20 -r requirements.txt" in dockerfile
    assert "{% if kafka %}" in dockerfile


def test_frontend_docker_build_does_not_copy_host_node_modules():
    template_dir = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
    )
    dockerfile = (template_dir / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (template_dir / ".dockerignore").read_text(encoding="utf-8")

    assert "FROM node:18-alpine AS build" in dockerfile
    assert "npm ci" in dockerfile
    assert "node_modules" in dockerignore.splitlines()
    assert "dist" in dockerignore.splitlines()


def test_frontend_build_stops_when_dockerignore_can_copy_node_modules(
    tmp_path, monkeypatch
):
    project = _project(tmp_path)
    (project / "generated" / "frontend" / ".dockerignore").unlink()
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append(command),
    )

    result = CliRunner().invoke(app, ["build", "--component", "frontend"])

    assert result.exit_code == 1
    assert "Run site" in result.output
    assert "sync, then retry" in result.output
    assert "node_modules" in result.output
    assert calls == []


def test_sqlite_compose_uses_a_directory_volume():
    template_dir = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    compose = environment.get_template("docker-compose.yml.j2").render(
        backend_image="example-backend:v1",
        frontend_image="example-frontend:v1",
        project_name="example",
        frontend_port=3000,
        use_pg=False,
        config={"allowed_origins": []},
    )
    db_template = (template_dir / "db.py.j2").read_text(encoding="utf-8")

    assert "sqlite+aiosqlite:////app/data/app.db" in compose
    assert "sqlite_data:/app/data" in compose
    assert "./app.db:/app/app.db" not in compose
    assert "sqlite_path.parent.mkdir(parents=True, exist_ok=True)" in db_template
    assert "SQLite database path points to a directory" in db_template


def test_compose_exposes_kafka_runtime_overrides():
    template_dir = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    compose = environment.get_template("docker-compose.yml.j2").render(
        backend_image="example-backend:v1",
        frontend_image="example-frontend:v1",
        project_name="example",
        frontend_port=3000,
        use_pg=False,
        config={
            "allowed_origins": [],
            "kafka": {
                "brokers": ["kafka:9092"],
                "callbacks": [
                    {
                        "topic": "devices.telemetry",
                        "handler": "on_telemetry",
                        "group_id": "onesite_backend",
                    }
                ],
            },
        },
    )

    assert 'KAFKA_BROKERS=${KAFKA_BROKERS:-["kafka:9092"]}' in compose
    assert (
        "KAFKA_CALLBACK_0_TOPIC=${KAFKA_CALLBACK_0_TOPIC:-devices.telemetry}"
        in compose
    )
    assert (
        "KAFKA_CALLBACK_0_GROUP_ID=${KAFKA_CALLBACK_0_GROUP_ID:-onesite_backend}"
        in compose
    )


def test_compose_exposes_agent_runtime_overrides():
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))
    compose = environment.get_template("docker-compose.yml.j2").render(
        backend_image="example-backend:v1",
        frontend_image="example-frontend:v1",
        project_name="example",
        frontend_port=3000,
        use_pg=False,
        config={
            "allowed_origins": [],
            "agents": {
                "assistant": {
                    "base_url": "https://gateway.example/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "model": "gpt-4.1-mini",
                }
            },
        },
    )

    assert "AGENT_BASE_URL=${AGENT_BASE_URL:-https://gateway.example/v1}" in compose
    assert "AGENT_MODEL=${AGENT_MODEL:-gpt-4.1-mini}" in compose
    assert "OPENAI_API_KEY=${OPENAI_API_KEY:-}" in compose
