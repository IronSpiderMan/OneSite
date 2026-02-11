import typer
import shutil
import os
import sys
from typing import Optional
from pathlib import Path
from rich.console import Console
from jinja2 import Environment, FileSystemLoader

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

def get_cwd_safely() -> Path:
    try:
        return Path(os.getcwd())
    except FileNotFoundError:
        console.print("[bold red]Error: The current working directory no longer exists![/bold red]")
        console.print("[yellow]This often happens if you deleted the directory you are currently in.[/yellow]")
        console.print("[green]Please run 'cd ..' or switch to a valid directory.[/green]")
        raise typer.Exit(code=1)

TEMPLATE_DIR = Path(__file__).parent / "templates"

def render_template(template_path: Path, context: dict, output_path: Path):
    env = Environment(loader=FileSystemLoader(str(template_path.parent)))
    template = env.get_template(template_path.name)
    content = template.render(context)
    output_path.write_text(content)

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
    
    # Copy templates
    shutil.copytree(TEMPLATE_DIR, target_dir)
    
    # Render templates (e.g. .env, config.py)
    # Walk through the directory and render files ending with .py or .env or others if needed
    # For now, we just copied, let's assume simple copy is fine for most, 
    # but we might want to replace {{ project_name }} in config.py
    
    config_file = target_dir / "backend/app/core/config.py"
    if config_file.exists():
        content = config_file.read_text()
        content = content.replace("{{ project_name }}", project_name)
        config_file.write_text(content)

    console.print(f"[bold green]Project {project_name} created successfully![/bold green]")
    console.print(f"cd {project_name} && site sync")

@app.command()
def sync(
    install: bool = typer.Option(False, "--install", "-i", help="Install dependencies for backend and frontend")
):
    """
    Sync models to generate APIs, Schemas, CRUDs, and Frontend code.
    Optionally install dependencies with --install.
    """
    # Ensure we are in a valid directory
    get_cwd_safely()
    
    console.print("[green]Syncing models...[/green]")
    from onesite.generator import generate_code
    generate_code()
    
    if install:
        console.print("[green]Installing dependencies...[/green]")
        import subprocess
        base_dir = get_cwd_safely()
        backend_dir = base_dir / "backend"
        frontend_dir = base_dir / "frontend"
        
        # Install Backend Dependencies
        if (backend_dir / "requirements.txt").exists():
            console.print("[blue]Installing backend dependencies...[/blue]")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=str(backend_dir))
        
        # Install Frontend Dependencies
        if (frontend_dir / "package.json").exists():
             console.print("[blue]Installing frontend dependencies...[/blue]")
             subprocess.run(["npm", "install"], cwd=str(frontend_dir))

@app.command()
def run(
    project_path: Path = typer.Argument(Path("."), help="Path to the project directory"),
    component: str = typer.Option("all", help="Component to run: backend, frontend, or all")
):
    """
    Run the project (Backend and Frontend).
    """
    console.print(f"[green]Running {component}...[/green]")
    
    import subprocess
    import concurrent.futures

    base_dir = project_path.resolve()
    backend_dir = base_dir / "backend"
    frontend_dir = base_dir / "frontend"

    def run_backend():
        if not backend_dir.exists():
             console.print(f"[red]Backend directory not found at {backend_dir}![/red]")
             console.print("[yellow]Tip: Make sure you are in the project directory or specify the project path.[/yellow]")
             return
        console.print("[blue]Starting Backend...[/blue]")
        subprocess.run(["uvicorn", "app.main:app", "--reload"], cwd=str(backend_dir))

    def run_frontend():
        if not frontend_dir.exists():
             console.print(f"[red]Frontend directory not found at {frontend_dir}![/red]")
             return
        
        package_json = frontend_dir / "package.json"
        if package_json.exists():
            console.print("[blue]Starting Frontend (npm run dev)...[/blue]")
            # Check if node_modules exists, if not maybe suggest install?
            if not (frontend_dir / "node_modules").exists():
                console.print("[yellow]node_modules not found. Installing dependencies...[/yellow]")
                subprocess.run(["npm", "install"], cwd=str(frontend_dir))
            
            subprocess.run(["npm", "run", "dev"], cwd=str(frontend_dir))
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
    component: str = typer.Option("all", "--component", "-c", help="Component to build: backend, frontend, or all"),
    engine: str = typer.Option("docker", "--engine", "-e", help="Container engine: docker or podman"),
    tag: str = typer.Option("latest", "--tag", "-t", help="Image tag"),
    frontend_port: int = typer.Option(3000, "--port", "-p", help="Frontend exposed port")
):
    """
    Build container images for the project and generate docker-compose.yml.
    """
    import subprocess
    from onesite.generator import generate_file
    
    base_dir = get_cwd_safely()
    project_name = base_dir.name.lower()
    
    backend_image = f"{project_name}-backend:{tag}"
    frontend_image = f"{project_name}-frontend:{tag}"
    
    def run_build(context_dir, image_name):
        console.print(f"[blue]Building {image_name} with {engine}...[/blue]")
        try:
            subprocess.run(
                [engine, "build", "-t", image_name, "."], 
                cwd=str(context_dir),
                check=True
            )
            console.print(f"[green]Successfully built {image_name}[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to build {image_name}: {e}[/red]")
        except FileNotFoundError:
            console.print(f"[red]Engine '{engine}' not found. Please install it or check your path.[/red]")

    if component in ["backend", "all"]:
        backend_dir = base_dir / "backend"
        if (backend_dir / "Dockerfile").exists():
            run_build(backend_dir, backend_image)
        else:
            console.print(f"[yellow]Backend Dockerfile not found in {backend_dir}. Run 'site sync' first.[/yellow]")

    if component in ["frontend", "all"]:
        frontend_dir = base_dir / "frontend"
        if (frontend_dir / "Dockerfile").exists():
            run_build(frontend_dir, frontend_image)
        else:
            console.print(f"[yellow]Frontend Dockerfile not found in {frontend_dir}. Run 'site sync' first.[/yellow]")
            
    # Generate docker-compose.yml with correct images and ports
    console.print(f"[blue]Generating docker-compose.yml...[/blue]")
    context = {
        "project_name": project_name,
        "backend_image": backend_image,
        "frontend_image": frontend_image,
        "frontend_port": frontend_port
    }
    generate_file("docker-compose.yml.j2", context, base_dir / "docker-compose.yml")
    console.print(f"[green]Generated docker-compose.yml with images: {backend_image}, {frontend_image} and port {frontend_port}[/green]")

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
    compose_file = base_dir / "docker-compose.yml"
    
    if not compose_file.exists():
        console.print(f"[red]docker-compose.yml not found in {base_dir}. Run 'site sync' first.[/red]")
        raise typer.Exit(code=1)

    # Use context args for the command
    compose_args = ctx.args
    
    compose_cmd = "docker-compose"
    if engine == "podman":
        compose_cmd = "podman-compose"
    
    if not compose_args:
        # If no args provided, show help for the compose tool
        compose_args = ["--help"]
        
    full_cmd = [compose_cmd] + compose_args
    
    console.print(f"[blue]Running: {' '.join(full_cmd)}[/blue]")
    
    try:
        subprocess.run(full_cmd, cwd=str(base_dir), check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed: {e}[/red]")
    except FileNotFoundError:
        console.print(f"[red]Command '{compose_cmd}' not found. Please install it.[/red]")

if __name__ == "__main__":
    app()
