"""合成：拼接全部场景 -> 对齐字幕（SRT）-> 烧制输出 final.mp4。"""

import json
import subprocess
from pathlib import Path

from cs_video_agent.engine import subtitles
from cs_video_agent.engine.renderops import ffprobe, load_report, save_report

SUBTITLE_STYLE = (
    "FontName=Noto Sans CJK SC,FontSize=18,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H96000000,BorderStyle=1,Outline=1.2,Shadow=0,"
    "MarginV=32,Alignment=2"
)


def _scene_entries(project_dir: Path, records: list[dict], quality: str) -> tuple[list[str], list[dict]]:
    files, entries, missing = [], [], []
    for rec in sorted(records, key=lambda r: r["index"]):
        att = None
        for a in reversed(rec["attempts"]):
            if a["quality"] == quality and a["status"] == "ok":
                att = a
                break
        if att is None:
            missing.append(rec["scene_id"])
            continue
        files.append(att["video_path"])
        timings = json.loads(
            (project_dir / "scenes" / f"{rec['scene_id']}.timings.json").read_text(
                encoding="utf-8"))
        entries.append({
            "duration": att["duration_sec"] or timings["duration"],
            "beats": timings["beats"],
        })
    if missing:
        raise RuntimeError(
            f"scenes missing a successful {quality} render: {missing}")
    return files, entries


def assemble(project_dir: Path, quality: str = "final") -> dict:
    project_dir = Path(project_dir)
    report = load_report(project_dir)
    if not report["scenes"]:
        raise RuntimeError("render report has no scenes; render first")

    files, entries = _scene_entries(project_dir, report["scenes"], quality)
    out_dir = project_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    srt_text = subtitles.build_srt(entries)
    (out_dir / "final.srt").write_text(srt_text, encoding="utf-8")

    concat = out_dir / "concat.txt"
    concat.write_text(
        "".join(f"file '{Path(f).resolve()}'\n" for f in files), encoding="utf-8")

    vf = f"subtitles=final.srt:force_style='{SUBTITLE_STYLE}'"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", "concat.txt",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "final.mp4",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(out_dir))
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg assemble failed:\n" + proc.stderr[-2000:])

    probe = ffprobe(out_dir / "final.mp4")
    report["assemble"] = {
        "quality": quality,
        "final_path": str((out_dir / "final.mp4").resolve()),
        "srt_path": str((out_dir / "final.srt").resolve()),
        "scenes_concat": files,
        **probe,
    }
    save_report(project_dir, report)
    return report["assemble"]
