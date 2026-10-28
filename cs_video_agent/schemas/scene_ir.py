"""Scene IR：结构化场景描述（对象、节拍、动作）。

这是「教学设计 -> Manim 代码」的中间表示：
- objects: 场景中的语义对象（socket_grid / ready_queue / ...）
- beats:   教学节拍，每个节拍带一句解说（= 字幕）+ 若干动作
- invariants: 该场景承诺保持的语义不变量（由纯 Python 模型回放验证）

动作本身是薄分发层（engine/actions），真正语义在 visualkit 的 Model/View 中，
保证「先验证计算机原理，再生成动画代码」。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ObjectTypes = Literal[
    "socket_grid",
    "socket_stack",
    "ready_queue",
    "kernel_panel",
    "worker_box",
    "event_flow",
    "elf_file",
    "addr_space",
    "fd_table",
    "state_strip",
    "ledger",
]


class SceneObject(BaseModel):
    id: str
    type: ObjectTypes
    params: dict[str, Any] = Field(default_factory=dict)


class ActionStep(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class Beat(BaseModel):
    id: str
    narration: str | None = None
    dwell: float = Field(default=0.6, ge=0.0, description="动作之后留给观众阅读的停顿（秒）")
    actions: list[ActionStep] = Field(default_factory=list)


class SceneIR(BaseModel):
    id: str
    index: int
    title: str
    duration_hint: float
    objects: list[SceneObject]
    beats: list[Beat]
    invariants: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> "SceneIR":
        obj_ids = [o.id for o in self.objects]
        if len(obj_ids) != len(set(obj_ids)):
            raise ValueError(f"scene {self.id}: duplicate object ids")
        beat_ids = [b.id for b in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError(f"scene {self.id}: duplicate beat ids")
        return self


class Storyboard(BaseModel):
    lesson_ref: str
    scenes: list[SceneIR]

    @model_validator(mode="after")
    def _ordered_unique(self) -> "Storyboard":
        idx = [s.index for s in self.scenes]
        if idx != sorted(idx):
            raise ValueError("scenes must be ordered by index")
        if len(idx) != len(set(idx)):
            raise ValueError("duplicate scene index")
        return self
