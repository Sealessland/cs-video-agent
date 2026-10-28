"""ELF 文件视图：一份文件、两种读法。

链接视图（Section 平铺，含调试节） <-> 执行视图（按 PT_LOAD 分组成 Segment，
调试节淡出 = strip 隐喻）。区块颜色 = 装载权限，与 addr_space 视图保持一致：
R+E=KERNEL(青) / R=GOOD(绿) / RW=EVENT(橙)。
"""

from manim import (
    AnimationGroup,
    Circumscribe,
    Create,
    FadeIn,
    FadeOut,
    LaggedStart,
    RIGHT,
    RoundedRectangle,
    Text,
    UP,
    VGroup,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models_os import (
    DEFAULT_SECTIONS,
    DEFAULT_SEGMENTS,
    ElfFileModel,
)
from cs_video_agent.visualkit.views.util import vec

_PERM_COLOR = {"R+E": theme.KERNEL, "R": theme.GOOD, "RW": theme.EVENT}
_HEIGHTS = {".text": 0.95, ".rodata": 0.55, ".data": 0.45, ".bss": 0.38,
            ".symtab": 0.40}


class ElfFileView:
    def __init__(self, obj_id: str, ctx, center=(-3.4, 0.0), width=2.3,
                 height=5.0, sections=None, segments=None, label="a.out"):
        self.ctx = ctx
        self.obj_id = obj_id
        self.model = ElfFileModel(
            sections or [dict(s) for s in DEFAULT_SECTIONS],
            segments or [dict(s) for s in DEFAULT_SEGMENTS])
        cx, cy = center
        self.c = vec(cx, cy)
        self.width, self.height = width, height

        self.frame = RoundedRectangle(corner_radius=0.14, width=width, height=height,
                                      stroke_width=2, stroke_color=theme.TEXT_DIM,
                                      fill_color="#11151d", fill_opacity=0.75)
        self.frame.move_to(self.c)
        self.file_label = Text(label, font=theme.FONT, font_size=theme.LABEL_SIZE,
                               color=theme.TEXT_DIM)
        self.file_label.next_to(self.frame, UP, buff=0.22)

        self.header = VGroup(
            RoundedRectangle(corner_radius=0.08, width=width - 0.32, height=1.0,
                             stroke_width=1.5, stroke_color=theme.READY,
                             fill_color=theme.READY, fill_opacity=0.12),
        )
        h1 = Text("ELF Header", font=theme.FONT, font_size=theme.SMALL_SIZE,
                  color=theme.READY)
        h2 = Text("magic 7f 45 4c 46 · entry _start", font=theme.FONT,
                  font_size=15, color=theme.TEXT_DIM)
        h1.move_to(self.header[0].get_center() + vec(0, 0.18))
        h2.move_to(self.header[0].get_center() + vec(0, -0.22))
        self.header.add(h1, h2)
        self.header.move_to(self.c + vec(0, height / 2 - 0.62))

        self.blocks: dict[str, VGroup] = {}
        for spec in self.model.sections:
            name = spec["name"]
            h = _HEIGHTS.get(name, 0.5)
            color = (self.model.segment_of(name) and
                     _PERM_COLOR[self.model.segment_of(name)]) or theme.TEXT_DIM
            box = RoundedRectangle(corner_radius=0.06, width=width - 0.36, height=h,
                                   stroke_width=1.5, stroke_color=color,
                                   fill_color=color,
                                   fill_opacity=0.28 if not spec["debug"] else 0.10)
            if spec["debug"]:
                box.set_stroke(opacity=0.55)
            txt = Text(name, font=theme.FONT, font_size=17, color=theme.TEXT_MAIN)
            txt.move_to(box.get_center())
            self.blocks[name] = VGroup(box, txt)
        for pos, blk in zip(self._link_positions(), self.model.sections):
            self.blocks[blk["name"]].move_to(pos)
        self._extras: list = []

    # -- 布局计算 --
    def _body_top(self):
        return self.c[1] + self.height / 2 - 1.20

    def _link_positions(self):
        y = self._body_top()
        out = []
        for spec in self.model.sections:
            h = _HEIGHTS.get(spec["name"], 0.5)
            out.append(vec(self.c[0], y - h / 2))
            y -= h + 0.10
        return out

    def _exec_positions(self):
        """非调试节按 segment 分组重排，组间留空隙。"""
        y = self._body_top()
        out = {}
        for seg in self.model.segments:
            for name in seg["sections"]:
                h = _HEIGHTS.get(name, 0.5)
                out[name] = vec(self.c[0], y - h / 2)
                y -= h + 0.08
            y -= 0.28  # segment 间隙
        return out

    def entrance(self):
        blocks = [self.blocks[s["name"]] for s in self.model.sections]
        return AnimationGroup(
            Create(self.frame), FadeIn(self.file_label), FadeIn(self.header),
            LaggedStart(*[FadeIn(b) for b in blocks], lag_ratio=0.25))

    def highlight(self, key: str):
        target = self.header if key == "header" else self.blocks[key]
        return Circumscribe(target, color=theme.READY, buff=0.08, time_width=2.0)

    def switch_view(self, scene, view: str) -> float:
        if self.model.view == view:
            return 0.2
        self.model.switch_view(view)
        if view == "exec":
            targets = self._exec_positions()
            anims = []
            for seg in self.model.segments:
                for name in seg["sections"]:
                    anims.append(self.blocks[name].animate.move_to(targets[name]).build())
            debug = [self.blocks[s["name"]] for s in self.model.sections if s["debug"]]
            scene.play(*anims, *[FadeOut(d) for d in debug], run_time=1.6)
            self._extras = []
            for seg in self.model.segments:
                names = seg["sections"]
                color = _PERM_COLOR[seg["perm"]]
                top = targets[names[0]][1] + _HEIGHTS.get(names[0], 0.5) / 2 + 0.10
                bot = targets[names[-1]][1] - _HEIGHTS.get(names[-1], 0.5) / 2 - 0.10
                bracket = RoundedRectangle(
                    corner_radius=0.1, width=self.width + 0.26, height=top - bot,
                    stroke_color=color, stroke_width=2.5, fill_opacity=0)
                bracket.move_to(vec(self.c[0], (top + bot) / 2))
                badge = Text(f"PT_LOAD {seg['perm']}", font=theme.FONT,
                             font_size=16, color=color)
                badge.next_to(bracket, RIGHT, buff=0.18)
                scene.play(Create(bracket), FadeIn(badge), run_time=0.7)
                self._extras += [bracket, badge]
            return 1.6 + 0.7 * len(self.model.segments)
        # 回到链接视图
        anims = []
        for pos, spec in zip(self._link_positions(), self.model.sections):
            if spec["debug"]:
                anims.append(FadeIn(self.blocks[spec["name"]]))
        pos_map = dict(zip([s["name"] for s in self.model.sections],
                           self._link_positions()))
        for name, blk in self.blocks.items():
            anims.append(blk.animate.move_to(pos_map[name]).build())
        ex = self._extras
        scene.play(*anims, *[FadeOut(e) for e in ex], run_time=1.4)
        scene.remove(*ex)
        self._extras = []
        return 1.4

    def anchor(self, name: str):
        if name == "header":
            return self.header.get_center()
        return self.c
