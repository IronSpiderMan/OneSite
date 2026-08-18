import typer
import shutil
import os
import re
import sys
import importlib.util
import subprocess
from pathlib import Path
from rich.console import Console

from .project_paths import get_project_paths

# Add current path to sys.path so we can import modules from the generated project
try:
    sys.path.append(os.getcwd())
except FileNotFoundError:
    # Handle the case where the current working directory has been deleted
    # We can't print to console easily here as it might not be init, but we can safely ignore
    # The command execution will likely fail later with a better error or we can check in commands
    pass

app = typer.Typer(
    help="OneSiteTool - Generate Web Projects from SQLModel",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
console = Console()


def _npm_executable() -> str | None:
    """Return the npm executable, accounting for npm.cmd on Windows."""
    return shutil.which("npm.cmd") if os.name == "nt" else shutil.which("npm")


def _backend_install_command() -> list[str] | None:
    """Return an installer command that works for the active environment.

    ``uv venv`` environments are not guaranteed to contain pip, so prefer uv
    when it is available. Fall back to ``python -m pip`` for regular virtual
    environments.
    """
    uv = shutil.which("uv")
    if uv:
        return [uv, "pip", "install", "--python", sys.executable, "-r", "requirements.txt"]
    if importlib.util.find_spec("pip") is not None:
        return [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    return None


def _install_project_dependencies(backend_dir: Path, frontend_dir: Path) -> None:
    """Install generated backend and frontend dependencies with clear errors."""
    failures: list[str] = []

    if (backend_dir / "requirements.txt").exists():
        console.print("[blue]Installing backend dependencies...[/blue]")
        command = _backend_install_command()
        if command is None:
            failures.append(
                "Backend dependencies were not installed because neither uv nor pip is available. "
                "Install uv, or recreate the virtual environment with pip enabled."
            )
        else:
            try:
                subprocess.run(command, cwd=str(backend_dir), check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                failures.append(f"Backend dependency installation failed: {exc}")

    if (frontend_dir / "package.json").exists():
        console.print("[blue]Installing frontend dependencies...[/blue]")
        npm = _npm_executable()
        if npm is None:
            failures.append(
                "Frontend dependencies were not installed because npm was not found. "
                "Install Node.js and ensure npm is available on PATH."
            )
        else:
            try:
                subprocess.run([npm, "install"], cwd=str(frontend_dir), check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                failures.append(f"Frontend dependency installation failed: {exc}")

    if failures:
        for failure in failures:
            console.print(f"[bold red]Error:[/bold red] {failure}")
        raise typer.Exit(code=1)

def get_cwd_safely() -> Path:
    try:
        return Path(os.getcwd())
    except FileNotFoundError:
        console.print("[bold red]Error: The current working directory no longer exists![/bold red]")
        console.print("[yellow]This often happens if you deleted the directory you are currently in.[/yellow]")
        console.print("[green]Please run 'cd ..' or switch to a valid directory.[/green]")
        raise typer.Exit(code=1)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _ensure_resource_hooks(source_dir: Path) -> None:
    """Create the developer-owned resource lifecycle module when absent."""
    resource_file = source_dir / "resources.py"
    if resource_file.exists():
        return
    source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE_DIR / "backend" / "app" / "resources.py", resource_file)
    console.print(f"[green]Created {resource_file}[/green]")


def _desktop_config_defaults(project_name: str) -> dict[str, object]:
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", project_name).strip("-").lower() or "app"
    if slug[0].isdigit():
        slug = f"app-{slug}"
    return {
        "identifier": f"com.onesite.{slug}",
        "version": "0.1.0",
        "api_url": "http://127.0.0.1:8000/api/v1",
        "width": 1280,
        "height": 800,
    }


def _write_python_site_config(target: Path, project_name: str) -> None:
    """Write the typed project configuration template with project defaults."""
    desktop = _desktop_config_defaults(project_name)
    content = (TEMPLATE_DIR / "site_config.py").read_text(encoding="utf-8")
    content = content.replace("__PROJECT_NAME__", repr(project_name))
    content = content.replace("__DESKTOP_IDENTIFIER__", repr(desktop["identifier"]))
    target.write_text(content, encoding="utf-8")


def _ensure_deploy_files(base_dir: Path) -> Path:
    """Create the deployment directory without overwriting user environment files."""
    deploy_dir = get_project_paths(base_dir).deploy
    deploy_dir.mkdir(parents=True, exist_ok=True)
    env_example_source = TEMPLATE_DIR / "deploy" / ".env.example"
    env_example_target = deploy_dir / ".env.example"
    if env_example_source.exists() and not env_example_target.exists():
        shutil.copy2(env_example_source, env_example_target)
        console.print(f"[green]Created {env_example_target}[/green]")
    return deploy_dir


@app.command()
def init():
    """
    Initialize site_config.py and base models in an existing project.
    Ensures necessary models (User, SystemConfig, CustomConfig) exist.
    """
    base_dir = get_cwd_safely()
    has_modern_layout = (base_dir / "app").exists() or (base_dir / "generated").exists()
    has_legacy_layout = any(
        (base_dir / name).exists() for name in ("models", "backend", "frontend")
    )
    paths = get_project_paths(
        base_dir,
        modern=has_modern_layout or not has_legacy_layout,
    )

    # Check current state
    has_models = paths.models.exists()
    has_site_config = any(
        (base_dir / name).exists() for name in ("site_config.py", "site_config.json")
    )
    has_backend = paths.backend.exists()
    has_frontend = paths.frontend.exists()

    # If any project files exist, treat as existing project
    if has_models or has_site_config or has_backend or has_frontend:
        console.print("[blue]Existing project detected[/blue]")
    else:
        console.print("[yellow]No existing project files found, will initialize from scratch[/yellow]")

    template_models_dir = Path(__file__).parent / "templates" / "models"
    models_dir = paths.models
    site_config_file = base_dir / "site_config.py"

    # Create the typed Python configuration if no supported configuration exists.
    if not has_site_config:
        project_name = base_dir.name.lower().replace("-", "_")
        _write_python_site_config(site_config_file, project_name)
        console.print(f"[green]Created site_config.py[/green]")
    else:
        console.print("[blue]Project configuration already exists[/blue]")

    # Create models directory if not exists
    if not has_models:
        models_dir.mkdir(parents=True, exist_ok=True)

        # Ensure necessary models exist
        necessary_models = [
            "user.py",
            "system_config.py",
            "custom_config.py",
            "location.py",
        ]
        for model_file in necessary_models:
            src = template_models_dir / model_file
            dst = models_dir / model_file
            if src.exists():
                shutil.copy2(src, dst)
                console.print(f"[green]Created {model_file} from template[/green]")
            else:
                console.print(f"[yellow]Template {model_file} not found[/yellow]")
    else:
        console.print(f"[blue]models directory already exists[/blue]")

    utils_dir = paths.source / "utils"
    utils_dir.mkdir(parents=True, exist_ok=True)
    utils_init = utils_dir / "__init__.py"
    if not utils_init.exists():
        utils_init.write_text("", encoding="utf-8")
        console.print("[green]Created utils/__init__.py[/green]")
    _ensure_resource_hooks(paths.source)

    visualization_file = base_dir / "visualizations.py"
    if not visualization_file.exists():
        shutil.copy2(Path(__file__).parent / "templates" / "visualizations.py", visualization_file)
        console.print("[green]Created visualizations.py from template[/green]")

    _ensure_deploy_files(base_dir)

    for filename in (".gitignore", "icon-reference.html"):
        source = TEMPLATE_DIR / filename
        destination = base_dir / filename
        if source.exists() and not destination.exists():
            shutil.copy2(source, destination)
            console.print(f"[green]Created {filename}[/green]")

    console.print("[bold green]Initialization complete![/bold green]")
    console.print("[green]Run 'site sync' to generate API code.[/green]")


@app.command()
def create(
    project_name: str = typer.Argument(..., help="The name of the project to create"),
):
    """
    Create a new full-stack project with backend and frontend.
    """
    console.print(f"[green]Creating project: {project_name}[/green]")

    target_dir = get_cwd_safely() / project_name
    if target_dir.exists():
        console.print(f"[red]Directory {project_name} already exists![/red]")
        raise typer.Exit(code=1)

    target_dir.mkdir(parents=True)
    paths = get_project_paths(target_dir, modern=True)
    copy_ignore = shutil.ignore_patterns("__pycache__", "*.pyc")

    shutil.copytree(
        TEMPLATE_DIR / "models",
        paths.models,
        ignore=copy_ignore,
    )
    shutil.copytree(
        TEMPLATE_DIR / "backend",
        paths.backend,
        ignore=copy_ignore,
    )
    shutil.copytree(
        TEMPLATE_DIR / "frontend",
        paths.frontend,
        ignore=copy_ignore,
    )
    utils_dir = paths.source / "utils"
    utils_dir.mkdir(parents=True)
    (utils_dir / "__init__.py").write_text("", encoding="utf-8")
    _ensure_resource_hooks(paths.source)
    _ensure_deploy_files(target_dir)

    for filename in (".gitignore", "icon-reference.html"):
        source = TEMPLATE_DIR / filename
        if source.exists():
            shutil.copy2(source, target_dir / filename)
    shutil.copy2(TEMPLATE_DIR / "visualizations.py", target_dir / "visualizations.py")

    # Render templates (e.g. .env, config.py)
    # Walk through the directory and render files ending with .py or .env or others if needed
    # For now, we just copied, let's assume simple copy is fine for most,
    # but we might want to replace {{ project_name }} in config.py

    config_file = paths.backend / "app" / "core" / "config.py"
    if config_file.exists():
        content = config_file.read_text(encoding="utf-8")
        content = content.replace("{{ project_name }}", project_name)
        content = content.replace("{{ access_token_expire_minutes }}", "11520")
        config_file.write_text(content, encoding="utf-8")

    index_html = paths.frontend / "index.html"
    if index_html.exists():
        content = index_html.read_text(encoding="utf-8")
        content = content.replace("{{ project_name }}", project_name)
        index_html.write_text(content, encoding="utf-8")

    _write_python_site_config(target_dir / "site_config.py", project_name)

    console.print(f"[bold green]Project {project_name} created successfully![/bold green]")
    console.print(f"cd {project_name} && site sync")

@app.command()
def sync(
    install: bool = typer.Option(False, "--install", "-i", help="Install dependencies for backend and frontend"),
    build_cmd: bool = typer.Option(
        False,
        "--build-cmd",
        help="Build app/cmd projects and copy executables to the generated backend",
    ),
):
    """
    Sync models to generate APIs, Schemas, CRUDs, and Frontend code.
    Optionally build command projects with --build-cmd and install dependencies
    with --install.
    """
    # Ensure we are in a valid directory
    base_dir = get_cwd_safely()
    _ensure_deploy_files(base_dir)

    console.print("[green]Syncing models...[/green]")
    from onesite.generator import generate_code
    generate_code()

    if build_cmd:
        from onesite.cmd_build import CommandBuildError, build_command_projects

        try:
            build_command_projects(base_dir)
        except CommandBuildError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    if install:
        console.print("[green]Installing dependencies...[/green]")
        base_dir = get_cwd_safely()
        paths = get_project_paths(base_dir)
        _install_project_dependencies(paths.backend, paths.frontend)

@app.command()
def run(
    project_path: Path = typer.Argument(Path("."), help="Path to the project directory"),
    component: str = typer.Option("all", help="Component to run: backend, frontend, or all"),
    host: str | None = typer.Option(
        None,
        "--host",
        help="Host address to bind the backend and frontend development servers",
    ),
):
    """
    Run the project (Backend and Frontend).
    """
    console.print(f"[green]Running {component}...[/green]")

    import concurrent.futures

    base_dir = project_path.resolve()
    paths = get_project_paths(base_dir)
    backend_dir = paths.backend
    frontend_dir = paths.frontend

    if component not in {"backend", "frontend", "all"}:
        raise typer.BadParameter("--component must be backend, frontend, or all")

    if component in {"backend", "all"}:
        from onesite.codegen.config import (
            SiteConfigError,
            load_site_config,
            validate_video_stream_config,
        )

        try:
            site_config = load_site_config(base_dir)
            validate_video_stream_config(site_config)
        except SiteConfigError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc
    def run_backend():
        if not backend_dir.exists():
             console.print(f"[red]Backend directory not found at {backend_dir}![/red]")
             console.print("[yellow]Tip: Make sure you are in the project directory or specify the project path.[/yellow]")
             return
        console.print("[blue]Starting Backend...[/blue]")
        command = ["uvicorn", "app.main:app", "--reload"]
        if host:
            command.extend(["--host", host])
        subprocess.run(command, cwd=str(backend_dir))

    def run_frontend():
        if not frontend_dir.exists():
             console.print(f"[red]Frontend directory not found at {frontend_dir}![/red]")
             return

        package_json = frontend_dir / "package.json"
        if package_json.exists():
            console.print("[blue]Starting Frontend (npm run dev)...[/blue]")
            npm = _npm_executable()
            if npm is None:
                console.print(
                    "[bold red]Error:[/bold red] npm was not found. "
                    "Install Node.js and ensure npm is available on PATH."
                )
                return

            # Check if node_modules exists, if not maybe suggest install?
            if not (frontend_dir / "node_modules").exists():
                console.print("[yellow]node_modules not found. Installing dependencies...[/yellow]")
                try:
                    subprocess.run([npm, "install"], cwd=str(frontend_dir), check=True)
                except (OSError, subprocess.CalledProcessError) as exc:
                    console.print(f"[bold red]Error:[/bold red] npm install failed: {exc}")
                    return

            try:
                command = [npm, "run", "dev"]
                if host:
                    command.extend(["--", "--host", host])
                subprocess.run(command, cwd=str(frontend_dir), check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                console.print(f"[bold red]Error:[/bold red] Frontend failed to start: {exc}")
        else:
            console.print("[blue]Starting Frontend...[/blue]")
            console.print("[yellow]Frontend runner not fully implemented without package.json, skipping...[/yellow]")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        if component in ["backend", "all"]:
            futures.append(executor.submit(run_backend))
        if component in ["frontend", "all"]:
            futures.append(executor.submit(run_frontend))

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


@app.command()
def build(
    component: str = typer.Option("all", "--component", "-c", help="Component to build: backend, frontend, desktop, or all"),
    engine: str = typer.Option("docker", "--engine", "-e", help="Container engine: docker or podman"),
    tag: str = typer.Option("latest", "--tag", "-t", help="Tag applied to both backend and frontend images"),
    frontend_port: int = typer.Option(3000, "--port", "-p", help="Frontend exposed port"),
    production: bool = typer.Option(False, "--production", help="Compile the Python backend with Nuitka"),
    development: bool = typer.Option(False, "--development", help="Use the regular Python backend image (default)"),
):
    """
    Build container images, or a native desktop client for the current platform.

    Note: Frontend API URL can be configured at runtime via docker-compose environment variables:
    - API_URL: Backend API URL (default: http://backend:80)
    - WS_URL: WebSocket URL (default: ws://backend:80)
    """
    import subprocess
    from onesite.generator import generate_file

    base_dir = get_cwd_safely()
    paths = get_project_paths(base_dir)

    if production and development:
        raise typer.BadParameter("--production and --development cannot be used together")
    if component not in {"backend", "frontend", "desktop", "all"}:
        raise typer.BadParameter(
            "--component must be backend, frontend, desktop, or all"
        )

    if component == "desktop":
        if production or development:
            raise typer.BadParameter(
                "--production/--development apply to backend container builds only"
            )
        if sys.platform not in {"darwin", "win32"}:
            console.print(
                "[bold red]Desktop builds currently support macOS and Windows hosts only.[/bold red]"
            )
            raise typer.Exit(code=1)

        frontend_dir = paths.frontend
        tauri_config = frontend_dir / "src-tauri" / "tauri.conf.json"
        desktop_env = frontend_dir / ".env.desktop"
        package_json = frontend_dir / "package.json"
        if not all(path.exists() for path in (tauri_config, desktop_env, package_json)):
            console.print("[bold red]Desktop build files are missing or out of date.[/bold red]")
            console.print(
                "Run [bold]site sync --install[/bold], then retry "
                "[bold]site build --component desktop[/bold]."
            )
            raise typer.Exit(code=1)

        npm = _npm_executable()
        if npm is None:
            console.print(
                "[bold red]npm was not found.[/bold red] Install Node.js and ensure npm is on PATH."
            )
            raise typer.Exit(code=1)
        if shutil.which("cargo") is None:
            console.print(
                "[bold red]Rust/Cargo was not found.[/bold red] Install the Rust toolchain required by Tauri."
            )
            raise typer.Exit(code=1)
        tauri_cli = frontend_dir / "node_modules" / ".bin" / (
            "tauri.cmd" if sys.platform == "win32" else "tauri"
        )
        if not tauri_cli.exists():
            console.print("[bold red]The Tauri CLI dependency is not installed.[/bold red]")
            console.print(
                "Run [bold]site sync --install[/bold], then retry the desktop build."
            )
            raise typer.Exit(code=1)

        platform_name = "macOS" if sys.platform == "darwin" else "Windows"
        console.print(f"[blue]Building native {platform_name} desktop client...[/blue]")
        try:
            subprocess.run(
                [npm, "run", "tauri", "--", "build"],
                cwd=str(frontend_dir),
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            console.print(f"[bold red]Desktop build failed:[/bold red] {exc}")
            raise typer.Exit(code=1)

        bundle_kind = "macos and dmg" if sys.platform == "darwin" else "nsis"
        bundle_dir = frontend_dir / "src-tauri" / "target" / "release" / "bundle"
        console.print(
            f"[bold green]Desktop build complete.[/bold green] "
            f"Bundles ({bundle_kind}) are under {bundle_dir}."
        )
        return

    _ensure_deploy_files(base_dir)
    project_name = base_dir.name.lower()

    if engine not in {"docker", "podman"}:
        raise typer.BadParameter("--engine must be docker or podman")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        raise typer.BadParameter(
            "--tag must be a valid container tag using letters, digits, '.', '_' or '-'"
        )

    build_mode = "production" if production else "development"
    backend_image = f"{project_name}-backend:{tag}"
    frontend_image = f"{project_name}-frontend:{tag}"

    def run_build(context_dir, image_name, *, target=None) -> bool:
        mode_suffix = f" ({target})" if target else ""
        console.print(f"[blue]Building {image_name} with {engine}{mode_suffix}...[/blue]")
        command = [engine, "build", "-t", image_name]
        if target:
            command.extend(["--target", target])
        command.append(".")
        try:
            subprocess.run(
                command,
                cwd=str(context_dir),
                check=True
            )
            console.print(f"[green]Successfully built {image_name}[/green]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to build {image_name}: {e}[/red]")
            return False
        except FileNotFoundError:
            console.print(f"[red]Engine '{engine}' not found. Please install it or check your path.[/red]")
            return False

    if component in ["backend", "all"]:
        backend_dir = paths.backend
        backend_dockerfile = backend_dir / "Dockerfile"
        if backend_dockerfile.exists():
            if production:
                dockerfile_content = backend_dockerfile.read_text(
                    encoding="utf-8", errors="replace"
                )
                has_production_target = re.search(
                    r"(?im)^\s*FROM\s+\S+(?:\s+AS\s+production)\s*$",
                    dockerfile_content,
                )
                has_required_dynamic_packages = all(
                    option in dockerfile_content
                    for option in (
                        "--include-package=passlib.handlers",
                        "--include-package=bcrypt",
                    )
                )
                nuitka_entrypoint = backend_dir / "nuitka_entrypoint.py"
                if (
                    not has_production_target
                    or not has_required_dynamic_packages
                    or not nuitka_entrypoint.exists()
                ):
                    console.print(
                        "[bold red]Backend production build files are out of date.[/bold red]"
                    )
                    console.print(
                        "Run [bold]site sync[/bold] in this project, then retry "
                        "[bold]site build --production[/bold]."
                    )
                    raise typer.Exit(code=1)

            # Prompt for deleting existing images
            should_build = True
            try:
                image_query = subprocess.run(
                    [engine, "images", "-q", backend_image],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                existing_images = image_query.stdout.strip()
                if existing_images and "command not found" not in existing_images:
                    if typer.confirm(f"Image {backend_image} already exists. Delete it?", default=True):
                        console.print(f"[blue]Deleting {backend_image}...[/blue]")
                        subprocess.run([engine, "rmi", "-f", backend_image], check=False)
                    else:
                        console.print(f"[yellow]Skipping build for {backend_image} as per user request.[/yellow]")
                        should_build = False
            except Exception as e:
                # Ignore errors here (e.g. docker not installed), run_build will handle/report it
                pass

            if should_build:
                if not run_build(backend_dir, backend_image, target=build_mode):
                    raise typer.Exit(code=1)
        else:
            console.print(f"[yellow]Backend Dockerfile not found in {backend_dir}. Run 'site sync' first.[/yellow]")
            raise typer.Exit(code=1)

    if component in ["frontend", "all"]:
        frontend_dir = paths.frontend
        if (frontend_dir / "Dockerfile").exists():
            dockerignore = frontend_dir / ".dockerignore"
            ignored_entries = set()
            if dockerignore.exists():
                ignored_entries = {
                    line.strip().rstrip("/")
                    for line in dockerignore.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                }
            if "node_modules" not in ignored_entries:
                console.print(
                    "[bold red]Frontend Docker build files are out of date.[/bold red]"
                )
                console.print(
                    f"The Docker context must exclude {frontend_dir}/node_modules. "
                    "Run [bold]site sync[/bold], then retry the build."
                )
                raise typer.Exit(code=1)

            # Prompt for deleting existing images
            should_build = True
            try:
                image_query = subprocess.run(
                    [engine, "images", "-q", frontend_image],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                existing_images = image_query.stdout.strip()
                if existing_images and "command not found" not in existing_images:
                    if typer.confirm(f"Image {frontend_image} already exists. Delete it?", default=True):
                        console.print(f"[blue]Deleting {frontend_image}...[/blue]")
                        subprocess.run([engine, "rmi", "-f", frontend_image], check=False)
                    else:
                        console.print(f"[yellow]Skipping build for {frontend_image} as per user request.[/yellow]")
                        should_build = False
            except Exception as e:
                pass

            if should_build:
                if not run_build(frontend_dir, frontend_image):
                    raise typer.Exit(code=1)
        else:
            console.print(f"[yellow]Frontend Dockerfile not found in {frontend_dir}. Run 'site sync' first.[/yellow]")
            raise typer.Exit(code=1)

    # Generate deploy/docker-compose.yml with correct images and ports
    console.print("[blue]Generating deploy/docker-compose.yml...[/blue]")

    # Load through the common boundary so Python and legacy JSON projects
    # produce the same deployment artifacts.
    from onesite.codegen.config import SiteConfigError, load_site_config

    try:
        site_config = load_site_config(base_dir)
    except SiteConfigError as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    db_url = site_config.get("database_url", "")
    use_pg = isinstance(db_url, str) and db_url.startswith("postgresql")

    context = {
        "project_name": project_name,
        "backend_image": backend_image,
        "frontend_image": frontend_image,
        "frontend_port": frontend_port,
        "use_pg": use_pg,
        "config": site_config,
        "version": tag,
        "project_root_prefix": "..",
    }
    compose_file = paths.deploy / "docker-compose.yml"
    generate_file("docker-compose.yml.j2", context, compose_file)

    console.print(
        f"[green]Generated {compose_file} with images: {backend_image}, "
        f"{frontend_image}, backend mode: {build_mode}, and port {frontend_port}[/green]"
    )
    if use_pg:
        console.print("[green]PostgreSQL service added to deploy/docker-compose.yml[/green]")

@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def compose(
    ctx: typer.Context,
    engine: str = typer.Option("docker", "--engine", "-e", help="Container engine: docker or podman"),
):
    """
    Run docker-compose commands.
    Examples:
        site compose up -d
        site compose down
        site compose logs -f
    """
    import subprocess

    base_dir = get_cwd_safely()
    deploy_compose = get_project_paths(base_dir).deploy / "docker-compose.yml"
    legacy_compose = base_dir / "docker-compose.yml"
    compose_file = deploy_compose if deploy_compose.exists() else legacy_compose

    if not compose_file.exists():
        console.print(
            f"[red]docker-compose.yml not found in {deploy_compose.parent}. "
            "Run 'site build' first.[/red]"
        )
        raise typer.Exit(code=1)

    # Use context args for the command
    compose_args = ctx.args

    compose_cmd = "docker-compose"
    if engine == "podman":
        compose_cmd = "podman-compose"

    if not compose_args:
        # If no args provided, show help for the compose tool
        compose_args = ["--help"]

    full_cmd = [compose_cmd]
    deploy_env = compose_file.parent / ".env"
    if deploy_env.exists():
        full_cmd.extend(["--env-file", str(deploy_env)])
    full_cmd.extend(["-f", str(compose_file)])
    full_cmd.extend(compose_args)

    console.print(f"[blue]Running: {' '.join(full_cmd)}[/blue]")

    try:
        subprocess.run(full_cmd, cwd=str(base_dir), check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed: {e}[/red]")
    except FileNotFoundError:
        console.print(f"[red]Command '{compose_cmd}' not found. Please install it.[/red]")

if __name__ == "__main__":
    app()
