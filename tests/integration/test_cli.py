"""Integration tests for CLI commands."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "onco-extract" in result.output.lower() or "oncology" in result.output.lower()


def test_init_project(tmp_path):
    result = runner.invoke(app, [
        "init-project", "test_study",
        "--cancer", "lung",
        "--projects-dir", str(tmp_path),
    ])
    assert result.exit_code == 0
    assert (tmp_path / "test_study" / "data").exists()
    assert (tmp_path / "test_study" / "output").exists()
    assert (tmp_path / "test_study" / "study_config.yaml").exists()
    config_text = (tmp_path / "test_study" / "study_config.yaml").read_text()
    assert "lung" in config_text


def test_ingest_stub():
    result = runner.invoke(app, ["ingest", "/tmp/fake", "--project", "x"])
    assert result.exit_code == 0
    assert "Not yet implemented" in result.output


def test_ocr_stub():
    result = runner.invoke(app, ["ocr", "--project", "x"])
    assert result.exit_code == 0
    assert "Not yet implemented" in result.output


def test_translate_stub():
    result = runner.invoke(app, ["translate", "--project", "x"])
    assert result.exit_code == 0
    assert "Not yet implemented" in result.output


def test_extract_stub():
    result = runner.invoke(app, ["extract", "--project", "x"])
    assert result.exit_code == 0
    assert "Not yet implemented" in result.output


def test_derive_endpoints_stub():
    result = runner.invoke(app, ["derive-endpoints", "--project", "x"])
    assert result.exit_code == 0
    assert "Not yet implemented" in result.output


def test_export_csv_stub():
    result = runner.invoke(app, ["export-csv", "--project", "x"])
    assert result.exit_code == 0
    assert "Not yet implemented" in result.output


def test_review_ui_stub():
    result = runner.invoke(app, ["review-ui", "--project", "x"])
    assert result.exit_code == 0
    assert "Not yet implemented" in result.output


def test_all_commands_have_help():
    """Verify all commands are registered and have --help."""
    for cmd in ["init-project", "ingest", "ocr", "translate", "extract",
                "derive-endpoints", "export-csv", "review-ui", "serve"]:
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0, f"--help failed for {cmd}: {result.output}"
