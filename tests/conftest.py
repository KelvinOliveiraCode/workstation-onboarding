"""Fixtures compartilhadas dos testes.
Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def raiz() -> Path:
    """Raiz do repositorio.
    Repository root."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def config_dir(raiz: Path) -> Path:
    """Pasta de configuracao do projeto.
    Project config directory."""
    return raiz / "config"


@pytest.fixture()
def scripts_dir(raiz: Path) -> Path:
    """Pasta de scripts PowerShell do projeto.
    Project PowerShell scripts directory."""
    return raiz / "scripts"
