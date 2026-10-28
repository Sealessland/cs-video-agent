"""就绪队列（ready list）视图。

enqueue/pop 的状态转移先落在 ReadyList 模型上，再解释为动画；
is_ready 由场景上下文从 SocketSet 模型取真实就绪态。
"""

from manim import (
    AnimationGroup,
    Create,
    FadeIn,
    FadeOut,
    RIGHT,
    RoundedRectangle,
    Text,
    UP,
    VGroup,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models import ReadyList
from cs_video_agent.visualkit.views.util import fit_text, make_chip, vec


class ReadyQueueView:
    def __init__(self, obj_id: str, ctx, slots: int = 4, center: tuple = (2.6, 0.9),
                 slot_w: float = 1.0, slot_h: float = 0.5, buff: float = 0.18,
                 label: str = "就绪队列 ready list"):
        self.ctx = ctx
        self.obj_id = obj_id
        self.model: ReadyList = ctx.shared.setdefault("ready_list", ReadyList())
        boxes = [
            RoundedRectangle(corner_radius=0.08, width=slot_w, height=slot_h,
                             stroke_width=1.5, stroke_color=theme.IDLE,
                             fill_color="#141a24", fill_opacity=0.95)
            for _ in range(slots)
        ]
        self.slots = VGroup(*boxes).arrange(RIGHT, buff=buff)
        self.slots.move_to(vec(*center))
        self.label = fit_text(
            Text(label, font=theme.FONT, font_size=theme.LABEL_SIZE, color=theme.TEXT_DIM),
            4.2,
        )
        self.label.next_to(self.slots, UP, buff=0.18)
        self.chips: dict[int, VGroup] = {}
        self.root = VGroup(self.slots, self.label)

    def entrance(self):
        return AnimationGroup(Create(self.slots), FadeIn(self.label))

    def enqueue(self, scene, fd, from_point) -> float:
        ready_flag = self.ctx.is_socket_ready(str(fd))
        ok = self.model.on_readable(str(fd), is_ready=ready_flag)
        if not ok:
            return 0.2
        idx = len(self.chips)
        chip = make_chip(fd, theme.EVENT)
        chip.move_to(from_point).scale(0.55)
        scene.add(chip)
        scene.play(chip.animate.move_to(self.slots[idx].get_center()).scale(1 / 0.55),
                   run_time=0.8)
        self.chips[idx] = chip
        return 0.8

    def pop(self, scene, to_point):
        returned = self.model.wait()
        if not self.chips:
            return ",".join(returned)
        idx = min(self.chips)
        chip = self.chips.pop(idx)
        scene.play(chip.animate.move_to(to_point).scale(0.75), run_time=0.7)
        scene.play(FadeOut(chip), run_time=0.3)
        scene.remove(chip)
        return ",".join(returned)

    def anchor(self, name: str):
        if name == "in":
            return self.slots[0].get_left() + vec(-0.35, 0)
        if name == "bottom":
            return self.slots.get_bottom() + vec(0, -0.1)
        if name == "center":
            return self.slots.get_center()
        raise KeyError(f"ready_queue: unknown anchor {name}")
