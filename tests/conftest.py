"""Shared pytest fixtures."""
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Fresh temp dir representing a LaTeX project root."""
    return tmp_path


def _has(binary: str) -> bool:
    return shutil.which(binary) is not None


@pytest.fixture(scope="session")
def has_latexindent() -> bool:
    return _has("latexindent")


@pytest.fixture(scope="session")
def has_chktex() -> bool:
    return _has("chktex")


@pytest.fixture(scope="session")
def has_latexmk() -> bool:
    return _has("latexmk")
