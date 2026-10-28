import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

TEMPLATE = ROOT / "templates" / "project"


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """从仓库自带模板实例化一个项目目录（不依赖本地生成的项目内容）。"""
    assert (TEMPLATE / "storyboard.json").exists(), "scaffold template missing"
    for name in ("lesson.json", "storyboard.json"):
        (tmp_path / name).write_text(
            (TEMPLATE / name).read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path
