"""M0-T1: Smoke tests — monorepo structure and package importability."""

from pathlib import Path

BACKEND = Path(__file__).parent.parent
APP = BACKEND / "app"


def test_app_package_importable() -> None:
    """The app package must be importable."""
    import app  # noqa: F401


def test_core_ports_dir_exists() -> None:
    assert (APP / "core" / "ports").is_dir()


def test_core_domain_dir_exists() -> None:
    assert (APP / "core" / "domain").is_dir()


def test_core_pipeline_dir_exists() -> None:
    assert (APP / "core" / "pipeline").is_dir()


def test_adapters_audio_dir_exists() -> None:
    assert (APP / "adapters" / "audio").is_dir()


def test_adapters_stt_dir_exists() -> None:
    assert (APP / "adapters" / "stt").is_dir()


def test_adapters_analyzer_dir_exists() -> None:
    assert (APP / "adapters" / "analyzer").is_dir()


def test_adapters_crm_dir_exists() -> None:
    assert (APP / "adapters" / "crm").is_dir()


def test_config_dir_exists() -> None:
    assert (APP / "config").is_dir()


def test_ruff_config_exists() -> None:
    assert (BACKEND.parent / "pyproject.toml").exists()


def test_mypy_config_exists() -> None:
    pyproject = BACKEND.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "[tool.mypy]" in content


def test_ruff_tool_section_exists() -> None:
    pyproject = BACKEND.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "[tool.ruff]" in content
