"""Tests validating deployment artifacts are syntactically/structurally sound."""

from pathlib import Path

import yaml

DEPLOYMENT_ROOT = Path(__file__).resolve().parent.parent / "deployment"


def test_dev_compose_file_is_valid_yaml() -> None:
    """docker-compose.yml should parse as valid YAML with expected services."""
    path = DEPLOYMENT_ROOT / "compose" / "docker-compose.yml"
    data = yaml.safe_load(path.read_text())

    for service in ("postgres", "redis", "backend", "worker", "beat"):
        assert service in data["services"]


def test_prod_compose_file_is_valid_yaml() -> None:
    """docker-compose.prod.yml should parse as valid YAML with nginx included."""
    path = DEPLOYMENT_ROOT / "compose" / "docker-compose.prod.yml"
    data = yaml.safe_load(path.read_text())

    for service in ("postgres", "redis", "backend", "worker", "beat", "nginx"):
        assert service in data["services"]


def test_all_dockerfiles_exist() -> None:
    """Every referenced Dockerfile should exist on disk."""
    expected = [
        DEPLOYMENT_ROOT / "docker" / "backend.Dockerfile",
        DEPLOYMENT_ROOT / "docker" / "frontend.Dockerfile",
        DEPLOYMENT_ROOT / "docker" / "worker.Dockerfile",
        DEPLOYMENT_ROOT / "docker" / "beat.Dockerfile",
        DEPLOYMENT_ROOT / "nginx" / "Dockerfile",
    ]

    for path in expected:
        assert path.exists(), f"Missing: {path}"


def test_dockerfiles_run_as_non_root() -> None:
    """Every Dockerfile should switch to a non-root user before CMD."""
    dockerfiles = list((DEPLOYMENT_ROOT / "docker").glob("*.Dockerfile"))
    dockerfiles.append(DEPLOYMENT_ROOT / "nginx" / "Dockerfile")

    for path in dockerfiles:
        content = path.read_text()
        assert "USER appuser" in content, f"{path} does not drop to non-root."


def test_deployment_scripts_are_executable_shell() -> None:
    """Every deployment script should start with a bash shebang."""
    scripts_dir = DEPLOYMENT_ROOT / "scripts"
    for script in scripts_dir.glob("*.sh"):
        first_line = script.read_text().splitlines()[0]
        assert first_line.startswith("#!"), f"{script} missing shebang."
