"""
Unit Tests for Internal Audit Console CLI
"""

from pathlib import Path
from src.cli import run_cli_audit, run_cli_query_map, run_cli_verify_source


def test_cli_audit_with_valid_fixture(tmp_path: Path):
    """Test executing CLI audit against a valid fixture JSON file."""
    fixture_file = Path("data/fixtures/sample_audit.json")
    output_file = tmp_path / "test_report.md"

    exit_code = run_cli_audit(fixture_path=fixture_file, output_path=output_file)
    assert exit_code == 0
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    assert "# 📊 GEO/AEO Evidence-Governed Audit Report" in content
    assert "searchbloom.com" in content
    assert "synthetic-search.example.com" in content
    assert "SYNTHETIC FIXTURE DATA" in content


def test_cli_query_map_successful_export(tmp_path: Path):
    """Test executing CLI query-map command against valid fixtures."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")
    output_file = tmp_path / "source_ledger.md"

    exit_code = run_cli_query_map(
        query_map_path=qm_file, manifest_path=man_file, output_path=output_file
    )
    assert exit_code == 0
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    assert "Controlled Source Ledger" in content
    assert "Python Software Foundation" in content
    assert "Verified Public Sources" in content


def test_cli_query_map_file_not_found(tmp_path: Path):
    """Test CLI query-map with non-existent file returns exit code 1."""
    qm_file = Path("nonexistent_qm.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")

    exit_code = run_cli_query_map(
        query_map_path=qm_file, manifest_path=man_file, output_path=None
    )
    assert exit_code == 1


def test_cli_verify_source_invalid_source_type():
    """Test CLI verify-source with invalid source type returns exit code 1."""
    exit_code = run_cli_verify_source(
        url="https://example.com",
        excerpt="Some excerpt",
        source_type_str="invalid_type_name",
    )
    assert exit_code == 1
