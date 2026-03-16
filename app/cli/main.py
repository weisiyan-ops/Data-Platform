"""CLI entry point using Typer."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint

app = typer.Typer(
    name="onco-extract",
    help="Oncology data extraction platform — research use only.",
)


@app.command()
def init_project(
    name: str = typer.Argument(..., help="Project name"),
    cancer: str = typer.Option("lung", help="Cancer type (lung, breast, etc.)"),
    projects_dir: str = typer.Option("projects", help="Base directory for projects"),
) -> None:
    """Initialize a new research project with config and directory structure."""
    project_path = Path(projects_dir) / name
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "data").mkdir(exist_ok=True)
    (project_path / "output").mkdir(exist_ok=True)

    config_content = f"study_name: {name}\ncancer_type: {cancer}\n"
    config_file = project_path / "study_config.yaml"
    config_file.write_text(config_content)

    rprint(f"[green]Project '{name}' initialized at {project_path}[/green]")
    rprint(f"  Cancer type: {cancer}")
    rprint(f"  Config: {config_file}")


@app.command()
def ingest(
    path: str = typer.Argument(..., help="Path to files to ingest"),
    project: str = typer.Option(..., help="Project name"),
) -> None:
    """Ingest source files into a project."""
    rprint("[yellow]Not yet implemented — see Phase 3[/yellow]")


@app.command()
def ocr(
    project: str = typer.Option(..., help="Project name"),
) -> None:
    """Run OCR on ingested images."""
    rprint("[yellow]Not yet implemented — see Phase 7[/yellow]")


@app.command()
def translate(
    project: str = typer.Option(..., help="Project name"),
) -> None:
    """Translate Chinese documents to English."""
    rprint("[yellow]Not yet implemented — see Phase 7[/yellow]")


@app.command()
def extract(
    project: str = typer.Option(..., help="Project name"),
    cancer: str = typer.Option("lung", help="Cancer type"),
) -> None:
    """Run extraction pipeline on project documents."""
    rprint("[yellow]Not yet implemented — see Phase 4[/yellow]")


@app.command()
def derive_endpoints(
    project: str = typer.Option(..., help="Project name"),
) -> None:
    """Compute PFS, OS, and local control endpoints."""
    rprint("[yellow]Not yet implemented — see Phase 6[/yellow]")


@app.command()
def export_csv(
    project: str = typer.Option(..., help="Project name"),
) -> None:
    """Export analysis-ready CSV."""
    rprint("[yellow]Not yet implemented — see Phase 8[/yellow]")


@app.command()
def review_ui(
    project: str = typer.Option(..., help="Project name"),
) -> None:
    """Launch Streamlit review UI."""
    rprint("[yellow]Not yet implemented — see Phase 8[/yellow]")


@app.command()
def serve(
    port: int = typer.Option(8000, help="Port to listen on"),
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
) -> None:
    """Start the FastAPI server."""
    import uvicorn

    from app.api.app import create_app

    api = create_app()
    uvicorn.run(api, host=host, port=port)


if __name__ == "__main__":
    app()
