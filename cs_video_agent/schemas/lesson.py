"""教学计划（Lesson）Schema。

教学设计三要素（每个教学片段必须显式给出）：
- misconception     观众容易产生的错误直觉
- visual_experiment 动画如何让观众亲眼观察到问题
- takeaway          这段结束后观众必须理解什么
"""

from pydantic import BaseModel, Field


class TeachingSegment(BaseModel):
    id: str
    title: str
    misconception: str = Field(description="观众容易产生的错误直觉")
    visual_experiment: str = Field(description="如何用动画让观众观察到问题")
    takeaway: str
    narration_outline: list[str] = []


class Lesson(BaseModel):
    topic: str
    title: str
    audience: str = "对计算机系统感兴趣的初学者"
    duration_target_sec: list[int] = [60, 90]
    facts: list[str] = Field(
        default_factory=list,
        description="经过研究确认的技术事实，视频内容不得与其矛盾",
    )
    segments: list[TeachingSegment]
