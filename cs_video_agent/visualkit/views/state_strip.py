"""订单/支付状态机视图：一排状态徽章 + 相邻箭头。

advance 的状态转移先落在 StateMachine 模型上，再解释为动画；
attempt 演示注定被拒绝的非法转移（红色闪烁 + ✗ 标记，状态不变）。
"""

from manim import (
    AnimationGroup,
    Arrow,
    Circumscribe,
    Create,
    Dot,
    FadeIn,
    FadeOut,
    Line,
    MoveAlongPath,
    RIGHT,
    RoundedRectangle,
    Text,
    UP,
    VGroup,
    Write,
    linear,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models_pay import StateMachine
from cs_video_agent.visualkit.views.util import fit_text, vec

_CUR_FILL = "#3d3320"


class StateStripView:
    def __init__(self, obj_id: str, ctx, states, transitions, initial,
                 terminal=None, requires_confirm=None, center=(0.0, 1.9),
                 chip_w=1.72, chip_h=0.66, buff=0.52):
        self.ctx = ctx
        self.obj_id = obj_id
        self.model = StateMachine(states, transitions, initial, terminal,
                                  requires_confirm)
        self.chip_mobs: dict[str, VGroup] = {}
        chips = []
        for st in self.model.states:
            current = st == self.model.initial
            box = RoundedRectangle(
                corner_radius=0.12, width=chip_w, height=chip_h,
                stroke_width=2.6 if current else 1.4,
                stroke_color=theme.READY if current else theme.IDLE,
                fill_color=_CUR_FILL if current else "#141a24",
                fill_opacity=0.95,
            )
            txt = Text(st, font=theme.FONT, font_size=theme.SMALL_SIZE,
                       color=theme.TEXT_MAIN if current else theme.TEXT_DIM)
            txt.move_to(box.get_center())
            mob = VGroup(box, txt)
            self.chip_mobs[st] = mob
            chips.append(mob)
        row = VGroup(*chips).arrange(RIGHT, buff=buff)
        self.arrows: list[Arrow] = []
        for a, b in zip(chips, chips[1:]):
            arr = Arrow(a.get_right(), b.get_left(), buff=0.06,
                        stroke_width=2.4, color=theme.IDLE)
            self.arrows.append(arr)
        row.move_to(vec(*center))
        self.root = VGroup(row, *self.arrows)

    def entrance(self):
        return AnimationGroup(
            Create(VGroup(*[m[0] for m in self.chip_mobs.values()])),
            Write(VGroup(*[m[1] for m in self.chip_mobs.values()])),
            FadeIn(VGroup(*self.arrows)),
        )

    def _style_current(self, st: str):
        box, txt = self.chip_mobs[st]
        return [
            box.animate.set_stroke(theme.READY, width=2.6).set_fill(_CUR_FILL, 0.95),
            txt.animate.set_color(theme.TEXT_MAIN),
        ]

    def _style_visited(self, st: str):
        box, txt = self.chip_mobs[st]
        return [
            box.animate.set_stroke(theme.GOOD, width=1.4).set_fill("#141a24", 0.95),
            txt.animate.set_color(theme.TEXT_DIM),
        ]

    def advance(self, scene, to: str, via: str | None = None,
                run_time: float = 1.3):
        frm = self.model.current
        self.model.advance(to, via=via)
        src = self.chip_mobs[frm][0].get_center()
        dst = self.chip_mobs[to][0].get_center()
        path = Line(src, dst)
        dot = Dot(radius=0.09, color=theme.EVENT)
        dot.move_to(src)
        scene.add(dot)
        scene.play(MoveAlongPath(dot, path), run_time=run_time * 0.55,
                   rate_func=linear)
        anims = self._style_current(to) + self._style_visited(frm)
        anims.append(FadeOut(dot))
        scene.play(*anims, run_time=run_time * 0.45)
        scene.remove(dot)

    def attempt(self, scene, to: str, run_time: float = 1.2):
        self.model.attempt(to)  # 记录被拒尝试；状态不变
        src = self.chip_mobs[self.model.current][0].get_center()
        dst = self.chip_mobs[to][0].get_center()
        path = Line(src, dst)
        dot = Dot(radius=0.09, color=theme.COST)
        dot.move_to(src)
        scene.add(dot)
        scene.play(MoveAlongPath(dot, path), run_time=run_time * 0.5,
                   rate_func=linear)
        cross = Text("超时不是确认，被拒绝", font=theme.FONT,
                     font_size=theme.SMALL_SIZE, color=theme.COST)
        cross.next_to(self.chip_mobs[to], UP, buff=0.16)
        scene.play(FadeIn(cross),
                   Circumscribe(self.chip_mobs[to], color=theme.COST,
                                buff=0.10, time_width=1.6),
                   FadeOut(dot), run_time=run_time * 0.3)
        scene.play(FadeOut(cross), run_time=run_time * 0.2)
        scene.remove(dot)

    def anchor(self, name: str):
        if name in self.chip_mobs:
            return self.chip_mobs[name][0].get_center()
        return {
            "left": self.root.get_left(),
            "right": self.root.get_right(),
            "top": self.root.get_top(),
            "bottom": self.root.get_bottom(),
            "center": self.root.get_center(),
        }[name]
