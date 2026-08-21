"""
Unit Tests for Internal Audit Console CLI
"""

from pathlib import Path
from src.cli import run_cli_audit


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
    assert "TechCrunch" in content or "techcrunch.com" in content
