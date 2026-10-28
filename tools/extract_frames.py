#!/usr/bin/env python3
"""关键帧采样 + 生成多模态视觉评审输入（critic_input.json）。

采样规则：取带解说的 beat 起点后 0.45s（画面已落定的阅读时刻）+ 结尾帧，
生成 PNG 与拼图 contact sheet，并按 Review Schema 写出评审输入。

用法：python tools/extract_frames.py projects/epoll_explained --quality preview
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cs_video_agent.engine.renderops import latest_ok_video  # noqa: E402
from cs_video_agent.schemas.review import CriticFrame, CriticInput  # noqa: E402

QUESTIONS = [
    "画面元素是否越界、被裁切或互相遮挡？",
    "所有文字是否清晰可读（字号/对比度/无重叠）？",
    "当前画面与解说词、教学意图是否一致？",
    "信息密度是否过高或过低？动画状态是否正确？",
]


def extract(project: Path, scene_id: str, quality: str, n: int = 6) -> Path | None:
    att = latest_ok_video(project, scene_id, quality)
    if att is None:
        print(f"  skip {scene_id}: no ok render at {quality}")
        return None
    video = Path(att["video_path"])
    dur = float(att["duration_sec"])
    timings = json.loads(
        (project / "scenes" / f"{scene_id}.timings.json").read_text(encoding="utf-8"))

    cands = []
    for b in timings["beats"]:
        if not (b.get("narration") or "").strip():
            continue
        # 采样点取本拍动作序列完成之后、dwell 阅读窗口的中段：
        # end = 下一拍 start（动作+dwell 全部播完），回退到窗口 45% 处，
        # 避免「多动作节拍在 start+0.45s 时画面还没落定」的假阳性。
        end = float(b.get("end") or (float(b["start"]) + 0.45))
        t = min(max(end - 0.45 * (end - float(b["start"])), 0.0),
                max(dur - 0.15, 0.0))
        cands.append((b["id"], t, b["narration"]))
    cands.append(("end", max(dur - 0.4, 0.0), None))
    if len(cands) > n:
        step = len(cands) / n
        cands = [cands[min(int(i * step), len(cands) - 1)] for i in range(n)]

    out_dir = project / "frames" / scene_id
    if out_dir.exists():
        # 重跑前清空：上一轮的 PNG 混进拼图会让评审看到不存在的画面
        for old in out_dir.glob("*.png"):
            old.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for bid, t, narr in cands:
        out = out_dir / f"{bid}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video),
             "-frames:v", "1", "-q:v", "2", str(out)],
            check=True,
        )
        frames.append(CriticFrame(path=str(out), t_sec=round(t, 2),
                                  beat_id=bid, narration=narr))
    _contact_sheet(out_dir)

    lesson = json.loads((project / "lesson.json").read_text(encoding="utf-8"))
    sb = json.loads((project / "storyboard.json").read_text(encoding="utf-8"))
    sc = next(s for s in sb["scenes"] if s["id"] == scene_id)
    critic = CriticInput(
        scene_id=scene_id, topic=lesson["topic"], title=sc["title"],
        invariants=sc.get("invariants", []), frames=frames, questions=QUESTIONS)
    (project / "critic").mkdir(parents=True, exist_ok=True)
    out_json = project / "critic" / f"{scene_id}.critic_input.json"
    out_json.write_text(critic.model_dump_json(indent=2), encoding="utf-8")
    print(f"  {scene_id}: {len(frames)} frames -> {out_dir} | critic: {out_json.name}")
    return out_dir


def _contact_sheet(frame_dir: Path) -> None:
    pngs = sorted(frame_dir.glob("*.png"))
    if not pngs:
        return
    from PIL import Image
    imgs = [Image.open(p) for p in pngs]
    w, h = imgs[0].size
    cols = 2
    rows = math.ceil(len(imgs) / cols)
    sheet = Image.new("RGB", (cols * w, rows * h), (16, 18, 24))
    for i, im in enumerate(imgs):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(frame_dir / "contact.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project")
    ap.add_argument("--quality", default="preview")
    ap.add_argument("--scene", action="append")
    ap.add_argument("--n", type=int, default=6)
    args = ap.parse_args()
    proj = (ROOT / args.project).resolve()
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
    ids = args.scene or [s["id"] for s in sb["scenes"]]
    for sid in ids:
        extract(proj, sid, args.quality, args.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
