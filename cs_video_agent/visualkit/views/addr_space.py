"""虚拟地址空间视图：左侧 VA 条（code/data/heap/mmap/stack），右侧物理内存格。

核心隐喻：mmap 只是记账（VMA 出现），物理页在第一次缺页时才点亮（惰性分配）。
访问未登记区域 -> SIGSEGV 红叉。状态转移全部先落在 AddrSpaceModel 上。
"""

from manim import (
    AnimationGroup,
    Circumscribe,
    Create,
    FadeIn,
    Line,
    RIGHT,
    RoundedRectangle,
    Text,
    UP,
    VGroup,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models_os import AddrSpaceModel
from cs_video_agent.visualkit.views.util import fit_text, vec

_REGION_SPEC = {
    # name: (height, 颜色, 标签)
    "code":  (0.65, theme.KERNEL, ".text 代码 (R+E)"),
    "data":  (0.50, theme.EVENT, ".data 数据 (RW)"),
    "heap":  (0.50, theme.TEXT_DIM, "heap 堆 ↑"),
    "libc":  (0.60, "#9bb8d3", "libc.so (mmap)"),
    "stack": (0.80, theme.TEXT_DIM, "stack 栈 ↓"),
}


class AddrSpaceView:
    def __init__(self, obj_id: str, ctx, center=(-3.4, 0.0), width=3.0,
                 height=5.0, phy_center=(3.4, 0.0)):
        self.ctx = ctx
        self.obj_id = obj_id
        self.model = AddrSpaceModel()
        cx, cy = center
        self.c = vec(cx, cy)
        self.width, self.height = width, height

        self.frame = RoundedRectangle(corner_radius=0.14, width=width, height=height,
                                      stroke_width=2, stroke_color=theme.TEXT_DIM,
                                      fill_color="#11151d", fill_opacity=0.75)
        self.frame.move_to(self.c)
        self.va_label = Text("虚拟地址空间", font=theme.FONT,
                             font_size=theme.SMALL_SIZE, color=theme.TEXT_DIM)
        self.va_label.next_to(self.frame, UP, buff=0.2)

        # 底部向上排布：code, data, heap, [gap], [libc 槽位], [gap], stack
        bottom = self.c[1] - height / 2 + 0.25
        self.regions: dict[str, VGroup] = {}
        self._region_bottom: dict[str, float] = {}
        y = bottom
        for name in ("code", "data", "heap"):
            self._place_region(name, y)
            y += _REGION_SPEC[name][0] + 0.15
        self._gap_mid = y + 0.35          # libc 槽位中心
        y += 0.7
        self._segv_point = vec(self.c[0], y + 0.25)
        y += 0.5
        self._place_region("stack", y)

        # 物理内存面板
        px, py = phy_center
        self.pa_label = Text("物理内存 PA", font=theme.FONT,
                             font_size=theme.SMALL_SIZE, color=theme.TEXT_DIM)
        self.pa_frame = RoundedRectangle(corner_radius=0.12, width=2.0, height=3.4,
                                         stroke_width=2, stroke_color=theme.TEXT_DIM,
                                         fill_color="#11151d", fill_opacity=0.75)
        self.pa_frame.move_to(vec(px, py))
        self.pa_label.next_to(self.pa_frame, UP, buff=0.2)
        self.pa_cells = VGroup()
        for r in range(6):
            for c in range(4):
                cell = RoundedRectangle(corner_radius=0.04, width=0.30, height=0.30,
                                        stroke_width=1, stroke_color=theme.IDLE,
                                        fill_color=theme.IDLE, fill_opacity=0.18)
                self.pa_cells.add(cell)
        self.pa_cells.arrange_in_grid(rows=6, cols=4, buff=0.14)
        self.pa_cells.move_to(vec(px, py))
        self._next_cell = 0
        self._links: list[Line] = []

    def _place_region(self, name: str, bottom_y: float):
        h, color, label = _REGION_SPEC[name]
        box = RoundedRectangle(corner_radius=0.07, width=self.width - 0.44, height=h,
                               stroke_width=1.5, stroke_color=color,
                               fill_color=color, fill_opacity=0.22)
        box.move_to(vec(self.c[0], bottom_y + h / 2))
        txt = Text(label, font=theme.FONT, font_size=16, color=theme.TEXT_MAIN)
        fit_text(txt, self.width - 0.6)
        txt.move_to(box.get_center())
        self.regions[name] = VGroup(box, txt)
        self._region_bottom[name] = bottom_y

    def entrance(self):
        blocks = [self.regions[n] for n in ("code", "data", "heap", "stack")]
        return AnimationGroup(
            Create(self.frame), FadeIn(self.va_label),
            Create(self.pa_frame), FadeIn(self.pa_label), FadeIn(self.pa_cells),
            *[FadeIn(b) for b in blocks])

    def anchor(self, name: str):
        if name == "gap":
            return self._segv_point
        if name == "mmap_slot":
            return vec(self.c[0], self._gap_mid)
        if name == "center":
            return self.c
        return self.regions[name].get_center()

    def map_region(self, scene, region: str) -> float:
        if not self.model.map_region(region):
            return 0.2
        h, color, label = _REGION_SPEC[region]
        box = RoundedRectangle(corner_radius=0.07, width=self.width - 0.44, height=h,
                               stroke_width=2, stroke_color=color,
                               fill_color=color, fill_opacity=0.15)
        box.move_to(self.anchor("mmap_slot"))
        txt = Text(label, font=theme.FONT, font_size=16, color=theme.TEXT_MAIN)
        fit_text(txt, self.width - 0.6)
        txt.move_to(box.get_center())
        blk = VGroup(box, txt)
        self.regions[region] = blk
        self._region_bottom[region] = self.anchor("mmap_slot")[1] - h / 2
        scene.play(FadeIn(blk, scale=0.7), run_time=0.8)
        scene.play(Circumscribe(box, color=color, buff=0.06, time_width=2.0),
                   run_time=0.6)
        return 1.4

    def grow(self, scene, region: str, factor: float = 1.45) -> float:
        box = self.regions[region][0]
        h = _REGION_SPEC[region][0]
        new_h = h * factor
        bottom = self._region_bottom[region]
        if region == "stack":  # 栈向下长：顶边固定
            top = bottom + h
            new_c = vec(self.c[0], top - new_h / 2)
            self._region_bottom[region] = top - new_h
        else:                 # 堆向上长：底边固定
            new_c = vec(self.c[0], bottom + new_h / 2)
        scene.play(box.animate.stretch_to_fit_height(new_h).move_to(new_c),
                   run_time=0.8)
        self.regions[region][1].move_to(new_c)
        return 0.8

    def touch(self, scene, region: str) -> float:
        result = self.model.touch(region)
        if result == "segv":
            p = self.anchor("gap")
            cross = VGroup(
                Line(p + vec(-0.22, 0.22), p + vec(0.22, -0.22)),
                Line(p + vec(-0.22, -0.22), p + vec(0.22, 0.22)),
            ).set_stroke(theme.COST, width=5)
            tag = Text("SIGSEGV", font=theme.FONT, font_size=theme.SMALL_SIZE,
                       color=theme.COST)
            tag.next_to(cross, RIGHT, buff=0.25)
            scene.play(FadeIn(cross), FadeIn(tag), run_time=0.6)
            return 0.6
        if result == "alloc":
            cell = self.pa_cells[self._next_cell]
            self._next_cell += 1
            line = Line(self.anchor(region), cell.get_center(),
                        stroke_width=2, color=theme.GOOD)
            self._links.append(line)
            scene.play(Circumscribe(self.regions[region], color=theme.GOOD,
                                    buff=0.06, time_width=2.0), run_time=0.5)
            scene.play(Create(line), cell.animate.set_fill(theme.GOOD, opacity=0.85)
                       .set_stroke(theme.GOOD, width=1.5), run_time=0.9)
            return 1.4
        scene.play(Circumscribe(self.regions[region], color=theme.READY,
                                buff=0.06, time_width=2.0), run_time=0.5)
        return 0.5
