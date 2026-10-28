"""渲染操作：以子进程方式调用 manim render，ffprobe 检测产物，维护 render_report.json。

每次渲染都是一次 attempt（成功/失败/超时），完整日志落在项目 logs/ 下，
供 Agent 定向修复后重试（验收指标：可自动修复的渲染失败、失败重试记录）。
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

QUALITY_FLAGS = {
    "preview": ["-ql"],
    "final": ["-r", "1920,1080", "--fps", "30"],
}


def clean_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH")}
    return env


def ffprobe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {out.stderr[-400:]}")
    data = json.loads(out.stdout)
    stream = next((s for s in data.get("streams", [])
                   if s.get("codec_type") == "video"), {})
    duration = data.get("format", {}).get("duration") or stream.get("duration") or 0
    return {
        "duration_sec": round(float(duration), 3),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": stream.get("avg_frame_rate"),
        "codec": stream.get("codec_name"),
        "path": str(path),
    }


def report_path(project_dir: Path) -> Path:
    return project_dir / "output" / "render_report.json"


def load_report(project_dir: Path) -> dict:
    p = report_path(project_dir)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"project": project_dir.name, "scenes": [], "assemble": None}


def save_report(project_dir: Path, report: dict) -> None:
    p = report_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _upsert_attempt(report: dict, meta: dict, attempt: dict) -> dict:
    rec = next((r for r in report["scenes"] if r["scene_id"] == meta["scene_id"]), None)
    if rec is None:
        rec = {
            "scene_id": meta["scene_id"],
            "index": meta["index"],
            "class_name": meta["class_name"],
            "gen_file": str(meta["gen_file"]),
            "attempts": [],
        }
        report["scenes"].append(rec)
        report["scenes"].sort(key=lambda r: r["index"])
    else:
        rec["class_name"] = meta["class_name"]
        rec["gen_file"] = str(meta["gen_file"])
    rec["attempts"].append(attempt)
    return report


def render_scene(project_dir: Path, meta: dict, quality: str = "preview",
                 timeout: int = 1800) -> dict:
    """meta: {scene_id, index, class_name, gen_file}。返回本次 attempt 记录。"""
    project_dir = Path(project_dir)
    (project_dir / "logs").mkdir(parents=True, exist_ok=True)
    (project_dir / "scenes").mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    log_path = project_dir / "logs" / f"{meta['scene_id']}.{quality}.{stamp}.log"
    cmd = [
        sys.executable, "-m", "manim", "render",
        "--disable_caching",
        "--media_dir", str(project_dir / "media"),
        "-o", meta["scene_id"],
        *QUALITY_FLAGS[quality],
        str(meta["gen_file"]),
        meta["class_name"],
    ]
    env = clean_env()
    env["CSVA_TIMINGS_DIR"] = str(project_dir / "scenes")
    t0 = time.time()
    status, tail = "ok", None
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              env=env, cwd=str(project_dir))
        wall = round(time.time() - t0, 1)
        log_path.write_text(
            "$ " + " ".join(cmd) + "\n\n" + proc.stdout
            + "\n--- stderr ---\n" + proc.stderr,
            encoding="utf-8",
        )
        if proc.returncode != 0:
            status = "error"
            tail = (proc.stdout[-800:] + "\n" + proc.stderr[-1200:]).strip()
    except subprocess.TimeoutExpired as e:
        wall = round(time.time() - t0, 1)
        status = "timeout"
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        log_path.write_text("$ " + " ".join(cmd) + "\n\nTIMEOUT\n" + out, encoding="utf-8")
        tail = "render timed out"

    attempt = {
        "quality": quality,
        "status": status,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "wall_sec": wall,
        "duration_sec": None,
        "video_path": None,
        "log_path": str(log_path),
        "error_tail": tail,
    }
    if status == "ok":
        stem = Path(meta["gen_file"]).stem
        vids = sorted(
            (project_dir / "media").glob(f"videos/{stem}/**/{meta['scene_id']}*.mp4"),
            key=lambda p: p.stat().st_mtime,
        )
        if not vids:
            vids = sorted(
                (project_dir / "media").glob(f"videos/**/{meta['scene_id']}*.mp4"),
                key=lambda p: p.stat().st_mtime,
            )
        if vids:
            probe = ffprobe(vids[-1])
            attempt["duration_sec"] = probe["duration_sec"]
            attempt["video_path"] = probe["path"]
        else:
            attempt["status"] = "error"
            attempt["error_tail"] = "manim exited 0 but no output video found"

    report = load_report(project_dir)
    _upsert_attempt(report, meta, attempt)
    save_report(project_dir, report)
    return attempt


def latest_ok_video(project_dir: Path, scene_id: str, quality: str) -> dict | None:
    report = load_report(project_dir)
    rec = next((r for r in report["scenes"] if r["scene_id"] == scene_id), None)
    if rec is None:
        return None
    for att in reversed(rec["attempts"]):
        if att["quality"] == quality and att["status"] == "ok":
            return att
    return None
