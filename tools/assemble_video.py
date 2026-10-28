#!/usr/bin/env python3
"""合成最终视频：拼接 + 字幕烧制。

用法：python tools/assemble_video.py projects/epoll_explained --quality final
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cs_video_agent.engine import assemble as assemble_mod  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project")
    ap.add_argument("--quality", default="final", choices=["preview", "final"])
    args = ap.parse_args()
    proj = (ROOT / args.project).resolve()
    try:
        info = assemble_mod.assemble(proj, quality=args.quality)
    except RuntimeError as e:
        print(f"assemble failed: {e}")
        return 1
    print(f"final: {info['final_path']}")
    print(f"  duration={info['duration_sec']}s {info['width']}x{info['height']} "
          f"fps={info['fps']} codec={info['codec']}")
    print(f"srt:   {info['srt_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
