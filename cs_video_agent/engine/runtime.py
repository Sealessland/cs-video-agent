"""Manim 场景运行时：IR 场景基类。

职责：
- stage: 按 IR objects 构建视图并播放入场动画
- beat:  记录节拍时间戳（与解说一一对应，用于字幕对齐）
- act:   动作分发（engine/actions 注册表）
- close_scene: 落盘 timings.json（真实渲染时钟，非估算）
"""

import json
import os

from manim import LaggedStart, Scene

from cs_video_agent import theme
from cs_video_agent.visualkit import build_object
from cs_video_agent.visualkit.models import SocketSet


class SceneContext:
    """场景级对象注册表 + 锚点解析 + 跨视图共享模型（ReadyList 域）。"""

    def __init__(self, scene):
        self.scene = scene
        self.objects: dict = {}
        self.slots: dict = {}
        self.shared: dict = {}

    def anchor(self, ref: str):
        """'obj.anchor_name' -> 该视图锚点；'obj' -> 视图中心。"""
        if "." in ref:
            obj_id, name = ref.split(".", 1)
            if obj_id not in self.objects:
                raise KeyError(f"anchor {ref!r}: unknown object {obj_id!r}")
            return self.objects[obj_id].anchor(name)
        return self.objects[ref].anchor("center")

    def is_socket_ready(self, fd) -> bool | None:
        fd = str(fd)
        for view in self.objects.values():
            model = getattr(view, "model", None)
            if isinstance(model, SocketSet) and fd in model.ids:
                return model.is_ready(fd)
        return None


class BaseIRScene(Scene):
    scene_id = "scene"

    def setup(self):
        self.camera.background_color = theme.BG_COLOR
        self.ctx = SceneContext(self)
        self._beats: list[dict] = []

    def stage(self, objects: list[dict]):
        for spec in objects:
            view = build_object(spec["type"], spec.get("params", {}), self.ctx, spec["id"])
            self.ctx.objects[spec["id"]] = view
        anims = [v.entrance() for v in self.ctx.objects.values()]
        anims = [a for a in anims if a is not None]
        if anims:
            self.play(LaggedStart(*anims, lag_ratio=0.35), run_time=1.8)

    def beat(self, bid: str, narration: str | None = None):
        self._beats.append({"id": bid, "narration": narration, "start": self._now()})

    def act(self, name: str, **params):
        from cs_video_agent.engine.actions import get_handler

        get_handler(name)(self, params)

    def dwell(self, t: float):
        if t > 0:
            self.wait(t)

    def _now(self) -> float:
        try:
            return float(self.renderer.time)
        except Exception:
            return 0.0

    def close_scene(self):
        end = self._now()
        beats = []
        for i, b in enumerate(self._beats):
            b2 = dict(b)
            b2["end"] = self._beats[i + 1]["start"] if i + 1 < len(self._beats) else end
            beats.append(b2)
        out_dir = os.environ.get("CSVA_TIMINGS_DIR") or "."
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{self.scene_id}.timings.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"scene_id": self.scene_id, "duration": end, "beats": beats},
                f, ensure_ascii=False, indent=2,
            )
