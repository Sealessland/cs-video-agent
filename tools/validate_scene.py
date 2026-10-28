#!/usr/bin/env python3
"""确定性验证：schema 校验 + 动作合法性 + 模型回放不变量。

用法：python tools/validate_scene.py projects/epoll_explained
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.make import load_storyboard, validate_step  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project")
    args = ap.parse_args()
    proj = (ROOT / args.project).resolve()
    sb = load_storyboard(proj)  # pydantic 解析失败会直接抛出
    ok = validate_step(sb, proj)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
