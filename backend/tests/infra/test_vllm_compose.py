"""M9-T1: vLLM service in compose config + self-host profile in providers.yaml."""

from pathlib import Path

import yaml

COMPOSE_FILE = Path(__file__).parent.parent.parent.parent / "infra" / "docker-compose.yml"
PROVIDERS_FILE = Path(__file__).parent.parent.parent.parent / "infra" / "config" / "providers.yaml"


def _load_compose() -> dict:  # type: ignore[type-arg]
    with open(COMPOSE_FILE) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def _load_providers() -> dict:  # type: ignore[type-arg]
    with open(PROVIDERS_FILE) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


# --- compose tests ---


def test_vllm_service_present() -> None:
    cfg = _load_compose()
    assert "vllm" in cfg["services"], "vllm service must be defined in docker-compose.yml"


def test_vllm_has_self_host_profile() -> None:
    cfg = _load_compose()
    vllm = cfg["services"]["vllm"]
    profiles = vllm.get("profiles", [])
    assert "self-host" in profiles, "vllm service must be in 'self-host' profile"


def test_vllm_exposes_openai_compatible_port() -> None:
    cfg = _load_compose()
    vllm = cfg["services"]["vllm"]
    ports = vllm.get("ports", [])
    port_strings = [str(p) for p in ports]
    assert any("8000" in p for p in port_strings), "vllm must expose port 8000 (OpenAI-compatible)"


def test_vllm_has_model_volume() -> None:
    cfg = _load_compose()
    vllm = cfg["services"]["vllm"]
    assert "volumes" in vllm, "vllm must mount a model directory volume"


def test_vllm_has_gpu_reservation() -> None:
    cfg = _load_compose()
    vllm = cfg["services"]["vllm"]
    deploy = vllm.get("deploy", {})
    resources = deploy.get("resources", {})
    reservations = resources.get("reservations", {})
    devices = reservations.get("devices", [])
    assert any(d.get("capabilities") == ["gpu"] for d in devices), (
        "vllm must have GPU reservation in deploy.resources.reservations.devices"
    )


def test_vllm_model_configurable_via_env() -> None:
    cfg = _load_compose()
    vllm = cfg["services"]["vllm"]
    command = vllm.get("command", "") or ""
    if isinstance(command, list):
        command = " ".join(command)
    assert "VLLM_MODEL" in command or "${VLLM_MODEL" in command, (
        "vllm model must be configurable via VLLM_MODEL env var"
    )


# --- providers.yaml tests ---


def test_providers_has_self_host_llm_profile() -> None:
    cfg = _load_providers()
    llm_profiles = cfg.get("llm_profiles", {})
    assert "self_host" in llm_profiles, "providers.yaml must have llm_profiles.self_host section"


def test_self_host_profile_has_vllm_base_url() -> None:
    cfg = _load_providers()
    profile = cfg["llm_profiles"]["self_host"]
    base_url = profile.get("base_url", "")
    assert "8000" in base_url or "vllm" in base_url, (
        "self_host profile must point base_url at vllm service (port 8000)"
    )


def test_self_host_profile_has_qwen_model() -> None:
    cfg = _load_providers()
    profile = cfg["llm_profiles"]["self_host"]
    model = profile.get("model", "")
    assert "Qwen" in model or "qwen" in model, (
        "self_host profile must specify a Qwen2.5 model"
    )


def test_self_host_profile_vram_documented() -> None:
    cfg = _load_providers()
    profile = cfg["llm_profiles"]["self_host"]
    assert "vram_gb" in profile or "gpu_memory_utilization" in profile, (
        "self_host profile must document VRAM/gpu_memory_utilization for model selection"
    )
