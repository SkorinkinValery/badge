"""M0-T6: Tests for Alembic baseline setup."""

from pathlib import Path

BACKEND = Path(__file__).parent.parent.parent
ALEMBIC_INI = BACKEND / "alembic.ini"
MIGRATIONS_DIR = BACKEND / "app" / "db" / "migrations"
CI_WORKFLOW = Path(__file__).parent.parent.parent.parent / ".github" / "workflows" / "ci.yml"


def test_alembic_ini_exists() -> None:
    assert ALEMBIC_INI.exists(), f"alembic.ini not found at {ALEMBIC_INI}"


def test_alembic_env_py_exists() -> None:
    env_py = MIGRATIONS_DIR / "env.py"
    assert env_py.exists(), f"alembic env.py not found at {env_py}"


def test_alembic_versions_dir_exists() -> None:
    versions = MIGRATIONS_DIR / "versions"
    assert versions.is_dir(), f"alembic versions dir not found at {versions}"


def test_alembic_baseline_revision_exists() -> None:
    versions = MIGRATIONS_DIR / "versions"
    revisions = list(versions.glob("*.py"))
    assert len(revisions) >= 1, "At least one Alembic revision must exist (baseline)"


def test_alembic_single_head() -> None:
    """There must be exactly one Alembic head (no branching)."""
    import subprocess

    result = subprocess.run(
        [".venv/bin/alembic", "-c", "backend/alembic.ini", "heads"],
        capture_output=True,
        text=True,
        cwd=str(BACKEND.parent),
    )
    assert result.returncode == 0, f"alembic heads failed: {result.stderr}"
    heads = [line for line in result.stdout.splitlines() if line.strip() and "(head)" in line]
    assert len(heads) == 1, f"Expected 1 Alembic head, got {len(heads)}: {result.stdout}"


def test_ci_workflow_exists() -> None:
    assert CI_WORKFLOW.exists(), f"CI workflow not found at {CI_WORKFLOW}"


def test_ci_workflow_has_ruff_step() -> None:
    content = CI_WORKFLOW.read_text()
    assert "ruff" in content.lower()


def test_ci_workflow_has_mypy_step() -> None:
    content = CI_WORKFLOW.read_text()
    assert "mypy" in content.lower()


def test_ci_workflow_has_pytest_step() -> None:
    content = CI_WORKFLOW.read_text()
    assert "pytest" in content.lower()


def test_ci_workflow_has_eval_job_as_non_critical() -> None:
    """Eval job must be non-critical (continue-on-error)."""
    content = CI_WORKFLOW.read_text()
    assert "continue-on-error" in content
