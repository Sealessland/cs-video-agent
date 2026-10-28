"""质检与渲染报告 Schema。

- CriticInput: 交给多模态视觉评审的输入（关键帧 + 节拍上下文 + 检查问题）
- ReviewReport: 视觉评审结论（finding 列表，供定向修复）
- RenderReport: 渲染流水线账本（每个场景的每次尝试 / ffprobe / 合成结果）
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warn", "error"]


class ReviewFinding(BaseModel):
    scene_id: str
    beat_id: str | None = None
    frame: str | None = None
    kind: Literal["deterministic", "semantic", "perceptual", "geometry"] = "perceptual"
    severity: Severity = "warn"
    message: str
    suggestion: str | None = None


class ReviewReport(BaseModel):
    scene_id: str
    verdict: Literal["pass", "fix_required"]
    findings: list[ReviewFinding] = Field(default_factory=list)
    reviewed_by: str = "multimodal-critic"
    created_at: str = ""


class CriticFrame(BaseModel):
    path: str
    t_sec: float
    beat_id: str | None = None
    narration: str | None = None


class CriticInput(BaseModel):
    scene_id: str
    topic: str
    title: str
    invariants: list[str] = Field(default_factory=list)
    frames: list[CriticFrame] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class RenderAttempt(BaseModel):
    quality: str
    status: Literal["ok", "error", "timeout"]
    ts: str = ""
    wall_sec: float = 0.0
    duration_sec: float | None = None
    video_path: str | None = None
    log_path: str | None = None
    error_tail: str | None = None


class SceneRenderRecord(BaseModel):
    scene_id: str
    index: int
    class_name: str
    gen_file: str
    attempts: list[RenderAttempt] = Field(default_factory=list)

    @property
    def latest_ok(self) -> RenderAttempt | None:
        for a in reversed(self.attempts):
            if a.status == "ok":
                return a
        return None


class RenderReport(BaseModel):
    project: str
    scenes: list[SceneRenderRecord] = Field(default_factory=list)
    assemble: dict[str, Any] | None = None

    def record(self, scene_id: str) -> SceneRenderRecord | None:
        for r in self.scenes:
            if r.scene_id == scene_id:
                return r
        return None
