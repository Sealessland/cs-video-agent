"""事件流视图：内核面板（interest list）、工作进程（epoll_wait）、箭头与脉冲。

epoll 场景的核心隐喻：连接 -> 内核（注册一次），内核 -> 就绪队列（回调入队），
就绪队列 -> 应用（epoll_wait 返回）。数据流动用发光脉冲沿路径运动来表现。
"""

from manim import (
    AnimationGroup,
    Arrow,
    Circumscribe,
    Create,
    DOWN,
    Dot,
    FadeIn,
    FadeOut,
    FadeTransform,
    LaggedStart,
    Line,
    MoveAlongPath,
    RoundedRectangle,
    Text,
    VGroup,
    Write,
    linear,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models import ReadyList
from cs_video_agent.visualkit.views.util import fit_text, make_chip, resolve_color, vec


class KernelPanel:
    def __init__(self, obj_id: str, ctx, center: tuple = (-1.9, 0.8), width: float = 2.7,
                 height: float = 3.2, label: str = "内核 kernel",
                 sub: str = "interest list · 注册一次"):
        self.ctx = ctx
        self.obj_id = obj_id
        self.model: ReadyList = ctx.shared.setdefault("ready_list", ReadyList())
        self.box = RoundedRectangle(corner_radius=0.18, width=width, height=height,
                                    stroke_width=2.5, stroke_color=theme.KERNEL,
                                    fill_color=theme.KERNEL, fill_opacity=0.10)
        self.box.move_to(vec(*center))
        self.title = Text(label, font=theme.FONT, font_size=theme.LABEL_SIZE, color=theme.KERNEL)
        self.sub = fit_text(
            Text(sub, font=theme.FONT, font_size=theme.SMALL_SIZE, color=theme.TEXT_DIM), width - 0.4
        )
        self.title.move_to(self.box.get_top() + vec(0, -0.45))
        self.sub.next_to(self.title, DOWN, buff=0.18)
        self.chips: dict[str, object] = {}
        self.chip_group = None
        self.root = self.box

    def _next_chip_pos(self):
        k = len(self.chips)
        return self.box.get_center() + vec(0.0, 0.15 - 0.52 * k)

    def register_chip(self, scene, fd, from_point) -> float:
        self.model.register(str(fd))
        chip = make_chip(fd, theme.EVENT)
        chip.move_to(from_point).scale(0.55)
        scene.add(chip)
        scene.play(chip.animate.move_to(self._next_chip_pos()).scale(1 / 0.55), run_time=0.5)
        self.chips[str(fd)] = chip
        return 0.6

    def callback_flash(self, scene, fd) -> float:
        chip = self.chips.get(str(fd))
        if chip is None:
            return 0.1
        scene.play(Circumscribe(chip, color=theme.READY, buff=0.10, time_width=2.0),
                   run_time=0.6)
        return 0.6

    def entrance(self):
        return AnimationGroup(Create(self.box), Write(self.title),
                              FadeIn(self.sub))

    def anchor(self, name: str):
        return {
            "left": self.box.get_left(),
            "right": self.box.get_right(),
            "top": self.box.get_top(),
            "bottom": self.box.get_bottom(),
            "center": self.box.get_center(),
        }[name]


class WorkerBox:
    """通用框：label（角色名）+ sub（角色说明）+ items（职责条目）+
    mini（内部微缩示意：elf / va）+ status（状态行）。

    label/sub/status 随入场出现；items/mini 通过 box_reveal 按节拍揭示。
    """

    def __init__(self, obj_id: str, ctx, center=(2.6, -1.5), width=3.2,
                 height=1.1, label="应用", status=None, color=None, sub=None,
                 items=None, mini=None):
        self.ctx = ctx
        self.obj_id = obj_id
        stroke = resolve_color(color) if color else theme.TEXT_DIM
        self.box = RoundedRectangle(corner_radius=0.14, width=width, height=height,
                                    stroke_width=2.2, stroke_color=stroke,
                                    fill_color="#1a2130", fill_opacity=0.95)
        self.box.move_to(vec(*center))
        cx = center[0]
        top = self.box.get_top()[1]

        self.label = Text(label, font=theme.FONT, font_size=theme.LABEL_SIZE,
                          color=theme.TEXT_MAIN)
        self.label.move_to(vec(cx, top - 0.32))
        y = top - 0.64
        self.sub = None
        if sub:
            self.sub = fit_text(Text(sub, font=theme.FONT, font_size=17,
                                     color=stroke), width - 0.5)
            self.sub.move_to(vec(cx, y - self.sub.height / 2))
            y -= self.sub.height + 0.14
        self.item_mobs = []
        for it in items or []:
            t = fit_text(Text(f"· {it}", font=theme.FONT, font_size=17,
                              color=theme.TEXT_MAIN), width - 0.6)
            t.move_to(vec(cx, y - t.height / 2))
            y -= t.height + 0.12
            self.item_mobs.append(t)
        self.mini_mob = None
        if mini == "elf":
            self.mini_mob = self._mini_elf(vec(cx, y - 0.62))
        elif mini == "va":
            self.mini_mob = self._mini_va(vec(cx, y - 0.58))
        self.status = None
        if status is not None:
            self.status = fit_text(
                Text(status, font=theme.FONT, font_size=theme.SMALL_SIZE,
                     color=theme.TEXT_DIM), width - 0.5)
            self.status.move_to(self.box.get_bottom() + vec(0, 0.30))
        self.root = self.box

    def _mini_elf(self, center):
        hdr = RoundedRectangle(corner_radius=0.04, width=1.9, height=0.24,
                               stroke_width=1, stroke_color=theme.READY,
                               fill_color=theme.READY, fill_opacity=0.3)
        parts = [hdr]
        for name, color, h in ((".text", theme.KERNEL, 0.30),
                               (".rodata", theme.GOOD, 0.24),
                               (".data", theme.EVENT, 0.24)):
            b = RoundedRectangle(corner_radius=0.03, width=1.9, height=h,
                                 stroke_width=1, stroke_color=color,
                                 fill_color=color, fill_opacity=0.3)
            t = Text(name, font=theme.FONT, font_size=13, color=theme.TEXT_MAIN)
            t.move_to(b.get_center())
            parts.append(VGroup(b, t))
        group = VGroup(*parts).arrange(DOWN, buff=0.07)
        group.move_to(center)
        return group

    def _mini_va(self, center):
        group = VGroup()
        for name, color in (("栈 stack", theme.TEXT_DIM), ("堆 heap", theme.TEXT_DIM),
                            ("数据 .data", theme.EVENT), ("代码 .text", theme.KERNEL)):
            b = RoundedRectangle(corner_radius=0.03, width=1.9, height=0.22,
                                 stroke_width=1, stroke_color=color,
                                 fill_color=color, fill_opacity=0.3)
            t = Text(name, font=theme.FONT, font_size=13, color=theme.TEXT_MAIN)
            t.move_to(b.get_center())
            group.add(VGroup(b, t))
        group.arrange(DOWN, buff=0.06).move_to(center)
        return group

    def reveal(self, scene) -> float:
        anims = []
        if self.item_mobs:
            anims.append(LaggedStart(*[FadeIn(t) for t in self.item_mobs],
                                     lag_ratio=0.3))
        if self.mini_mob is not None:
            anims.append(FadeIn(self.mini_mob))
        if not anims:
            return 0.2
        scene.play(*anims, run_time=1.0)
        return 1.0

    def set_state(self, scene, text: str, color=None) -> float:
        new = fit_text(
            Text(text, font=theme.FONT, font_size=theme.SMALL_SIZE,
                 color=color or theme.GOOD),
            self.box.width - 0.5,
        )
        if self.status is None:
            self.status = new
            self.status.move_to(self.box.get_bottom() + vec(0, 0.30))
            scene.play(FadeIn(self.status), run_time=0.6)
            return 0.6
        new.move_to(self.status.get_center())
        scene.play(FadeTransform(self.status, new), run_time=0.7)
        self.status = new
        return 0.7

    def flash(self, scene, color=None) -> float:
        scene.play(Circumscribe(self.box, color=color or theme.GOOD, buff=0.12,
                                time_width=2.0), run_time=0.6)
        return 0.6

    def entrance(self):
        anims = [Create(self.box), Write(self.label)]
        if self.sub is not None:
            anims.append(FadeIn(self.sub))
        if self.status is not None:
            anims.append(FadeIn(self.status))
        return AnimationGroup(*anims)

    def anchor(self, name: str):
        return {
            "left": self.box.get_left(),
            "right": self.box.get_right(),
            "top": self.box.get_top(),
            "bottom": self.box.get_bottom(),
            "center": self.box.get_center(),
        }[name]


class EventFlowView:
    """箭头集合：params.arrows = [{id, from, to, color?, faint?, tip?}]，端点用 obj.anchor 引用。"""

    def __init__(self, obj_id: str, ctx, arrows=None):
        self.ctx = ctx
        self.obj_id = obj_id
        self.lines = {}
        self._orig = {}
        for spec in arrows or []:
            start = ctx.anchor(spec["from"])
            end = ctx.anchor(spec["to"])
            color = resolve_color(spec.get("color", "TEXT_DIM"))
            faint = spec.get("faint", False)
            if spec.get("tip", False):
                line = Arrow(start, end, buff=0.12, stroke_width=3.5, color=color)
            else:
                line = Line(start, end, stroke_width=2, color=color)
            if faint:
                line.set_stroke(opacity=0.30)
            self.lines[spec["id"]] = line
            self._orig[spec["id"]] = dict(color=color, width=line.stroke_width,
                                          opacity=0.30 if faint else 1.0)
        self.root = None  # lines 直接 add 到 scene

    def attach(self, scene):
        for line in self.lines.values():
            scene.add(line)

    def entrance(self):
        return LaggedStart(*[Create(l) for l in self.lines.values()], lag_ratio=0.25,
                           run_time=1.4)

    def pulse(self, scene, arrow_id: str, color=None, run_time: float = 0.8,
              label: str | None = None) -> float:
        line = self.lines[arrow_id]
        color = color or theme.EVENT
        orig = self._orig[arrow_id]
        scene.play(line.animate.set_stroke(color, width=4, opacity=1.0).build(),
                   run_time=0.3)
        if label:
            txt = fit_text(
                Text(str(label), font=theme.FONT, font_size=theme.SMALL_SIZE,
                     color="#0b0d10"), 2.5,
            )
            pad_x, pad_y = 0.14, 0.06
            tag = RoundedRectangle(
                corner_radius=0.08, width=txt.width + pad_x * 2,
                height=txt.height + pad_y * 2, stroke_width=0,
                fill_color=color, fill_opacity=0.92,
            )
            tag.move_to(txt.get_center())
            traveler = VGroup(tag, txt)
        else:
            traveler = Dot(line.get_start(), radius=0.09, color=color)
        traveler.move_to(line.get_start())
        scene.add(traveler)
        scene.play(MoveAlongPath(traveler, line), run_time=run_time, rate_func=linear)
        scene.play(FadeOut(traveler),
                   line.animate.set_stroke(orig["color"], width=orig["width"],
                                           opacity=orig["opacity"]).build(),
                   run_time=0.3)
        scene.remove(traveler)
        return 0.3 + run_time + 0.3

    def anchor(self, name: str):
        raise KeyError("event_flow exposes no anchors")
