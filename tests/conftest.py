import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest


@pytest.fixture()
def project_dir() -> Path:
    d = ROOT / "projects" / "epoll_explained"
    assert (d / "storyboard.json").exists(), "fixture project missing"
    return d
