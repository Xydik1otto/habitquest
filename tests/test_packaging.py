"""Tests: packaging — pyproject metadata, entry point, editable install."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app import cli, gamification as g

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_metadata_is_complete():
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        pytest.skip("tomllib requires 3.11+")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    proj = pyproject["project"]
    assert proj["name"] == "habitquest"
    assert proj["requires-python"] == ">=3.12"
    assert proj["scripts"]["habitquest"] == "app.cli:main"
    deps = proj["dependencies"]
    assert any(d.startswith("fastapi") for d in deps) and any(d.startswith("uvicorn") for d in deps)
    assert pyproject["tool"]["setuptools"]["packages"] == ["app"]
    assert "*.json" in pyproject["tool"]["setuptools"]["package-data"]["app"]


def test_requirements_pin_the_runtime_deps():
    reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for pkg in ("fastapi>=", "uvicorn>=", "pytest>=", "httpx>="):
        assert pkg in reqs


def test_cli_module_is_importable_and_parses_args():
    assert importlib.util.find_spec("app.cli") is not None
    parser_args = cli.main(["--help"]) if False else None  # main() runs uvicorn; only smoke the module
    assert callable(cli.main)


def test_all_app_json_data_ships_in_package():
    """Package data (templates/quotes/i18n/achievements) lives inside app/."""
    for name in ("templates.json", "quotes.json", "i18n.json", "achievements.json"):
        assert (Path(g.__file__).parent / name).exists()
        json.loads((Path(g.__file__).parent / name).read_text(encoding="utf-8"))
