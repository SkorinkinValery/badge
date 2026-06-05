"""M0-T2: Validate docker-compose.yml structure without starting containers."""

from pathlib import Path

import yaml

COMPOSE_FILE = Path(__file__).parent.parent.parent.parent / "infra" / "docker-compose.yml"


def _load_compose() -> dict:  # type: ignore[type-arg]
    assert COMPOSE_FILE.exists(), f"docker-compose.yml not found at {COMPOSE_FILE}"
    with open(COMPOSE_FILE) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def test_compose_file_exists() -> None:
    assert COMPOSE_FILE.exists()


def test_compose_has_postgres_service() -> None:
    cfg = _load_compose()
    assert "postgres" in cfg["services"]


def test_compose_has_minio_service() -> None:
    cfg = _load_compose()
    assert "minio" in cfg["services"]


def test_postgres_has_healthcheck() -> None:
    cfg = _load_compose()
    pg = cfg["services"]["postgres"]
    assert "healthcheck" in pg, "postgres must have healthcheck"
    hc = pg["healthcheck"]
    assert "test" in hc


def test_minio_has_healthcheck() -> None:
    cfg = _load_compose()
    minio = cfg["services"]["minio"]
    assert "healthcheck" in minio, "minio must have healthcheck"
    hc = minio["healthcheck"]
    assert "test" in hc


def test_postgres_has_port_mapping() -> None:
    cfg = _load_compose()
    pg = cfg["services"]["postgres"]
    assert "ports" in pg


def test_minio_has_port_mapping() -> None:
    cfg = _load_compose()
    minio = cfg["services"]["minio"]
    assert "ports" in minio


def test_postgres_has_volume() -> None:
    cfg = _load_compose()
    pg = cfg["services"]["postgres"]
    assert "volumes" in pg


def test_minio_has_volume() -> None:
    cfg = _load_compose()
    minio = cfg["services"]["minio"]
    assert "volumes" in minio


def test_named_volumes_defined() -> None:
    cfg = _load_compose()
    assert "volumes" in cfg
    volumes = cfg["volumes"]
    assert volumes is not None


def test_caddy_service_present() -> None:
    """Caddy is a TLS-proxy stub for MVP."""
    cfg = _load_compose()
    assert "caddy" in cfg["services"]
