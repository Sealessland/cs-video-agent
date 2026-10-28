#!/usr/bin/env python3
"""单项目全流程管线：验证 -> 编译 -> 渲染 -> 合成。

用法：
  ./scripts/csva tools/make.py projects/epoll_explained            # 预览质量全流程
  ./scripts/csva tools/make.py projects/epoll_explained --quality final
  ./scripts/csva tools/make.py projects/epoll_explained --scene scene_2
  ./scripts/csva tools/make.py projects/epoll_explained --compile-only

run_pipeline() 是可导入的函数，供 tools/batch.py 批量调用。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cs_video_agent.engine import assemble as assemble_mod  # noqa: E402
from cs_video_agent.engine import compiler, replay, renderops  # noqa: E402
from cs_video_agent.engine.validate_slots import validate_slots  # noqa: E402
from cs_video_agent.schemas.scene_ir import Storyboard  # noqa: E402


def load_storyboard(project_dir: Path) -> Storyboard:
    return Storyboard.model_validate(
        json.loads((project_dir / "storyboard.json").read_text(encoding="utf-8")))


def validate_step(sb: Storyboard, project_dir: Path) -> bool:
    errors = compiler.validate_actions(sb) + validate_slots(sb)
    results = [replay.replay_scene(sc) for sc in sb.scenes]
    log = {"action_errors": errors, "scenes": results}
    (project_dir / "logs").mkdir(parents=True, exist_ok=True)
    (project_dir / "logs" / "validate.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    for e in errors:
        print(f"  [action-error] {e}")
    for r in results:
        mark = "ok " if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['scene_id']}: {r['summary']}")
        for v in r["violations"]:
            print(f"         violation: {v}")
    return not errors and all(r["ok"] for r in results)


def run_pipeline(project_dir: Path, quality: str = "preview", scene_ids=None,
                 compile_only: bool = False, skip_render: bool = False,
                 skip_assemble: bool = False) -> dict:
    """跑完一个项目的完整管线，返回结构化结果（batch.py 的聚合单元）。"""
    project_dir = Path(project_dir)
    result = {"project": project_dir.name, "status": "failed", "code": 0,
              "scenes": [], "final": None, "error": None}
    sb = load_storyboard(project_dir)
    targets = sb.scenes
    if scene_ids:
        known = {s.id for s in sb.scenes}
        unknown = [s for s in scene_ids if s not in known]
        if unknown:
            result["error"] = f"unknown scene ids {unknown}; known: {sorted(known)}"
            result["code"] = 2
            print(f"!! {result['error']}")
            return result
        targets = [s for s in sb.scenes if s.id in set(scene_ids)]

    print(f"== project: {project_dir.name} | quality: {quality} "
          f"| scenes: {[s.id for s in targets]}")

    print("== [1/4] 语义验证（schema + 动作 + 模型回放不变量）")
    if not validate_step(sb, project_dir):
        result["error"] = "validation failed (see logs/validate.json)"
        result["code"] = 3
        return result

    print("== [2/4] 编译 Scene IR -> Manim 代码")
    try:
        paths = compiler.compile_storyboard(sb, project_dir / "gen")
    except compiler.CompileError as e:
        result["error"] = f"compile failed: {e}"
        result["code"] = 3
        print(f"!! {result['error']}")
        return result
    for p in paths:
        print(f"  generated {p.relative_to(project_dir)}")
    if compile_only:
        result.update(status="ok-compile-only", code=0)
        return result

    if not skip_render:
        print(f"== [3/4] 渲染（{quality}）")
        for sc in targets:
            meta = {
                "scene_id": sc.id,
                "index": sc.index,
                "class_name": compiler.class_name(sc),
                "gen_file": project_dir / "gen" / compiler.gen_filename(sc),
            }
            att = renderops.render_scene(project_dir, meta, quality=quality)
            mark = "ok " if att["status"] == "ok" else "FAIL"
            print(f"  [{mark}] {sc.id}: {att['duration_sec']}s "
                  f"wall={att['wall_sec']}s -> {att['video_path']}")
            result["scenes"].append({
                "scene_id": sc.id, "status": att["status"],
                "duration_sec": att["duration_sec"],
                "video_path": att["video_path"]})
            if att["error_tail"]:
                print("         " + att["error_tail"][-600:])
                result["error"] = f"render failed: {sc.id}"
                result["code"] = 4
                return result
    else:
        print("== [3/4] 跳过渲染")

    if not skip_assemble:
        print("== [4/4] 合成（concat + 字幕烧制）")
        try:
            info = assemble_mod.assemble(project_dir, quality=quality)
            result["final"] = info
            print(f"  final: {info['final_path']}  {info['duration_sec']}s "
                  f"{info['width']}x{info['height']}")
        except RuntimeError as e:
            result["error"] = f"assemble failed: {e}"
            result["code"] = 5
            print(f"  !! {result['error']}")
            return result
    result["status"] = "ok"
    print("== done.")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", nargs="?", default="projects/epoll_explained")
    ap.add_argument("--quality", default="preview", choices=["preview", "final"])
    ap.add_argument("--scene", action="append",
                    help="只处理指定 scene_id（可多次给出）")
    ap.add_argument("--compile-only", action="store_true")
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--skip-assemble", action="store_true")
    args = ap.parse_args()
    res = run_pipeline((ROOT / args.project).resolve(), quality=args.quality,
                       scene_ids=args.scene, compile_only=args.compile_only,
                       skip_render=args.skip_render, skip_assemble=args.skip_assemble)
    return res["code"]


if __name__ == "__main__":
    raise SystemExit(main())
