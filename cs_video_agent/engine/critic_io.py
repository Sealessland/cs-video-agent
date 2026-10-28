"""评审报告读写辅助：把 findings 落成 ReviewReport JSON（供修复循环与人工审片）。"""

from datetime import datetime
from pathlib import Path

from cs_video_agent.schemas.review import ReviewFinding, ReviewReport


def write_review(project_dir: Path, scene_id: str, findings: list[dict],
                 reviewed_by: str = "multimodal-critic") -> ReviewReport:
    verdict = "fix_required" if any(
        f.get("severity") == "error" for f in findings) else "pass"
    report = ReviewReport(
        scene_id=scene_id,
        verdict=verdict,
        findings=[ReviewFinding(scene_id=scene_id, **f) for f in findings],
        reviewed_by=reviewed_by,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    out = project_dir / "critic" / f"{scene_id}.review.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
