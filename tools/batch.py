#!/usr/bin/env python3
"""批量流水线：对 projects/ 下所有（或指定的）视频项目依次跑完整管线。

用法：
  ./scripts/csva tools/batch.py --quality preview          # 全部项目预览
  ./scripts/csva tools/batch.py --quality final            # 全部项目终版
  ./scripts/csva tools/batch.py --validate-only            # 只验证 + 编译
  ./scripts/csva tools/batch.py --projects 'epoll*'        # 按名称/通配符筛选
  ./scripts/csva tools/batch.py --scene scene_1            # 每个项目只渲该幕

单个项目失败默认记录后继续，--fail-fast 可改为立即中止。
汇总写入 workspace 根目录 batch_report.json。
"""

import argparse
import fnmatch
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.make import run_pipeline  # noqa: E402


def discover(projects_root: Path, patterns=None) -> list[Path]:
    dirs = sorted(
        p for p in projects_root.iterdir()
        if p.is_dir() and (p / "storyboard.json").exists()
    )
    if not patterns:
        return dirs
    selected = []
    names = [p.name for p in dirs]
    for pat in patterns:
        matched = fnmatch.filter(names, pat)
        if pat in names and pat not in matched:
            matched.append(pat)
        if not matched:
            print(f"!! pattern {pat!r} matched no project (known: {names})")
        selected.extend(m for m in matched if m not in selected)
    return [p for p in dirs if p.name in selected]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quality", default="preview", choices=["preview", "final"])
    ap.add_argument("--projects", action="append",
                    help="项目名或通配符（可多次；默认全部）")
    ap.add_argument("--scene", action="append", help="每个项目只处理该 scene_id")
    ap.add_argument("--validate-only", action="store_true",
                    help="只做语义验证 + 编译，不渲染不合成")
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--skip-assemble", action="store_true")
    ap.add_argument("--fail-fast", action="store_true")
    args = ap.parse_args()

    projects_root = ROOT / "projects"
    dirs = discover(projects_root, args.projects)
    if not dirs:
        print("no projects found under projects/")
        return 2

    t0 = time.time()
    results = []
    for p in dirs:
        t1 = time.time()
        res = run_pipeline(
            p, quality=args.quality, scene_ids=args.scene,
            compile_only=args.validate_only,
            skip_render=args.skip_render or args.validate_only,
            skip_assemble=args.skip_assemble or args.validate_only)
        res["wall_sec"] = round(time.time() - t1, 1)
        results.append(res)
        if args.fail_fast and res["status"].startswith("failed"):
            print(f"!! fail-fast: stop at {p.name}")
            break

    ok = [r for r in results if not r["status"].startswith("failed")]
    failed = [r for r in results if r["status"].startswith("failed")]
    total_dur = sum(
        (r["final"] or {}).get("duration_sec") or 0 for r in ok)

    print("\n== batch summary ==")
    for r in results:
        n_scenes = len(r["scenes"])
        dur = (r["final"] or {}).get("duration_sec")
        line = f"  [{r['status']:<16}] {r['project']}: {n_scenes} scenes" + (
            f", final {dur}s" if dur else "")
        if r["error"]:
            line += f"  ({r['error']})"
        print(line)
    print(f"  ok={len(ok)} failed={len(failed)} total_final={total_dur}s "
          f"wall={round(time.time() - t0, 1)}s")

    report = {
        "quality": args.quality,
        "projects": results,
        "summary": {
            "ok": len(ok), "failed": len(failed),
            "total_final_duration_sec": total_dur,
            "wall_sec": round(time.time() - t0, 1),
        },
    }
    (ROOT / "batch_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  report -> batch_report.json")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
