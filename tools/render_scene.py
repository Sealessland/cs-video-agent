#!/usr/bin/env python3
"""单独渲染/重渲指定场景。

用法：python tools/render_scene.py projects/epoll_explained --scene scene_2 --quality preview
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cs_video_agent.engine import compiler, renderops  # noqa: E402
from tools.make import load_storyboard  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--quality", default="preview", choices=["preview", "final"])
    args = ap.parse_args()

    proj = (ROOT / args.project).resolve()
    sb = load_storyboard(proj)
    sc = next((s for s in sb.scenes if s.id == args.scene), None)
    if sc is None:
        print(f"unknown scene {args.scene!r}; known: {[s.id for s in sb.scenes]}")
        return 2
    meta = {
        "scene_id": sc.id,
        "index": sc.index,
        "class_name": compiler.class_name(sc),
        "gen_file": proj / "gen" / compiler.gen_filename(sc),
    }
    att = renderops.render_scene(proj, meta, quality=args.quality)
    print(f"{att['status']}: {att['duration_sec']}s wall={att['wall_sec']}s")
    print(f"video: {att['video_path']}")
    print(f"log:   {att['log_path']}")
    if att["error_tail"]:
        print(att["error_tail"][-2000:])
    return 0 if att["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
