"""fd 表视图：进程 fd 索引列 -> 内核对象实例（struct file，含 f_pos）。

语义（与 FdTableModel 严格同步）：
- open  -> 新实例（独立 f_pos）
- dup   -> 两个 fd 指向同一实例（共享 f_pos）
- fork  -> 子进程 fd 表副本，实例共享
"""

from manim import (
    AnimationGroup,
    Circumscribe,
    Create,
    Dot,
    DOWN,
    FadeIn,
    FadeTransform,
    Line,
    MoveAlongPath,
    RoundedRectangle,
    Text,
    UP,
    VGroup,
    linear,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models_os import FdTableModel
from cs_video_agent.visualkit.views.util import fit_text, make_chip, vec

_INSTANCE_SLOTS = [(0.55, 1.30), (0.55, 0.05), (0.55, -1.20)]  # 相对 obj_center


class FdTableView:
    def __init__(self, obj_id: str, ctx, center=(-3.0, 0.0), obj_center=(2.8, 0.0),
                 rows=("0", "1", "2", "3", "4", "5")):
        self.ctx = ctx
        self.obj_id = obj_id
        self.model = FdTableModel()
        cx, cy = center
        self.c = vec(cx, cy)
        self.rows = [str(r) for r in rows]

        self.table_box = RoundedRectangle(corner_radius=0.14, width=2.7, height=5.0,
                                          stroke_width=2, stroke_color=theme.TEXT_DIM,
                                          fill_color="#11151d", fill_opacity=0.75)
        self.table_box.move_to(self.c)
        self.table_label = Text("进程 fd 表", font=theme.FONT,
                                font_size=theme.SMALL_SIZE, color=theme.TEXT_DIM)
        self.table_label.next_to(self.table_box, UP, buff=0.2)

        std = {"0": "stdin", "1": "stdout", "2": "stderr"}
        self.chips: dict[str, object] = {}
        y_top = self.c[1] + 2.5 - 0.42
        for i, fd in enumerate(self.rows):
            if fd in std:
                chip = make_chip(f"fd {fd} · {std[fd]}", theme.IDLE, width=2.3,
                                 height=0.44)
                chip.set_opacity(0.55)
            else:
                chip = make_chip(f"fd {fd}", theme.TEXT_DIM, width=1.7, height=0.44)
                chip.set_opacity(0.75)
            chip.move_to(vec(self.c[0], y_top - i * 0.78))
            self.chips[fd] = chip

        ox, oy = obj_center
        self.obj_label = Text("内核对象实例（struct file）", font=theme.FONT,
                              font_size=theme.SMALL_SIZE, color=theme.TEXT_DIM)
        self.obj_label.move_to(vec(ox, oy + 2.72))
        self.obj_panel = RoundedRectangle(corner_radius=0.14, width=3.3, height=3.9,
                                          stroke_width=2, stroke_color=theme.TEXT_DIM,
                                          fill_color="#11151d", fill_opacity=0.75)
        self.obj_panel.move_to(vec(ox, oy))
        self.instances: dict[int, VGroup] = {}
        self.offset_texts: dict[int, Text] = {}
        self.lines: list[Line] = []
        self._child_chips: dict[str, object] = {}
        self._child_lines: list[Line] = []

    def entrance(self):
        return AnimationGroup(
            Create(self.table_box), FadeIn(self.table_label),
            Create(self.obj_panel), FadeIn(self.obj_label),
            *[FadeIn(c) for c in self.chips.values()])

    def anchor(self, name: str):
        if name == "center":
            return self.c
        if name.startswith("fd"):
            return self.chips[name[2:]].get_center()
        if name.startswith("inst"):
            return self.instances[int(name[4:])].get_center()
        return self.c

    # -- 实例 --
    def _slot_center(self, slot_idx: int):
        idx = min(slot_idx, len(_INSTANCE_SLOTS) - 1)
        dx, dy = _INSTANCE_SLOTS[idx]
        ox = self.obj_panel.get_center()[0]
        oy = self.obj_panel.get_center()[1]
        return vec(ox + dx - 0.35, oy + dy)

    def _make_instance(self, iid: int, label: str, slot_idx: int):
        box = RoundedRectangle(corner_radius=0.08, width=2.6, height=0.92,
                               stroke_width=1.8, stroke_color=theme.KERNEL,
                               fill_color=theme.KERNEL, fill_opacity=0.16)
        box.move_to(self._slot_center(slot_idx))
        name = Text(label, font=theme.FONT, font_size=17, color=theme.TEXT_MAIN)
        fit_text(name, 2.2)
        name.move_to(box.get_center() + vec(0, 0.17))
        pos = Text("f_pos: 0", font=theme.FONT, font_size=15, color=theme.TEXT_DIM)
        pos.move_to(box.get_center() + vec(0, -0.20))
        return VGroup(box, name, pos)

    def open(self, scene, fd: str, label: str) -> float:
        iid = self.model.open(int(fd), label)
        slot = len([i for i in self.instances])  # 顺序占用槽位
        inst = self._make_instance(iid, label, slot)
        self.instances[iid] = inst
        self.offset_texts[iid] = inst[2]
        scene.play(FadeIn(inst, scale=0.75), run_time=0.8)
        line = Line(self.chips[str(fd)].get_center(), inst.get_center(),
                    stroke_width=2, color=theme.KERNEL)
        self.lines.append(line)
        scene.play(Create(line), run_time=0.6)
        return 1.4

    def dup(self, scene, src: str, dst: str) -> float:
        ok = self.model.dup(int(src), int(dst))
        if not ok:
            return 0.2
        iid = self.model.table[int(dst)]
        inst = self.instances[iid]
        line = Line(self.chips[str(dst)].get_center(), inst.get_center(),
                    stroke_width=2.5, color=theme.EVENT)
        self.lines.append(line)
        scene.play(Create(line), run_time=0.6)
        badge = Text("dup：同一实例 · 共享 f_pos", font=theme.FONT,
                     font_size=15, color=theme.EVENT)
        badge.next_to(inst, DOWN, buff=0.12)
        scene.play(FadeIn(badge), run_time=0.5)
        return 1.1

    def read(self, scene, fd: str, n: int = 128, who: str = "parent") -> float:
        offset = self.model.read(int(fd), n, who)
        if offset is None:
            return 0.2
        if who == "child" and str(fd) in self._child_chips:
            start = self._child_chips[str(fd)].get_center()
            table = self.model.child_table
        else:
            start = self.chips[str(fd)].get_center()
            table = self.model.table
        iid = table[int(fd)]
        inst = self.instances[iid]
        line = Line(start, inst.get_center())
        dot = Dot(start, radius=0.08, color=theme.GOOD)
        scene.add(dot)
        scene.play(MoveAlongPath(dot, line), run_time=0.6, rate_func=linear)
        scene.remove(dot)
        new = Text(f"f_pos: {offset}", font=theme.FONT, font_size=15,
                   color=theme.GOOD)
        new.move_to(self.offset_texts[iid].get_center())
        scene.play(FadeTransform(self.offset_texts[iid], new), run_time=0.5)
        self.offset_texts[iid] = new
        return 1.1

    def fork(self, scene) -> float:
        if not self.model.fork():
            return 0.2
        base_x = self.c[0] + 3.05
        base_y = self.c[1] - 1.9
        label = Text("子进程 fd 表（fork 副本）", font=theme.FONT, font_size=16,
                     color=theme.GOOD)
        label.move_to(vec(base_x + 0.3, base_y + 1.05))
        scene.play(FadeIn(label), run_time=0.5)
        y = base_y + 0.55
        for fd in sorted(self.model.table):
            chip = make_chip(f"fd {fd}", theme.GOOD, width=1.3, height=0.4)
            chip.move_to(vec(base_x, y))
            self._child_chips[str(fd)] = chip
            iid = self.model.table[int(fd)]
            line = Line(chip.get_center(), self.instances[iid].get_center(),
                        stroke_width=1.5, color=theme.GOOD).set_stroke(opacity=0.65)
            self._child_lines.append(line)
            y -= 0.55
        scene.play(*[FadeIn(c) for c in self._child_chips.values()], run_time=0.6)
        scene.play(*[Create(l) for l in self._child_lines], run_time=0.8)
        scene.play(Circumscribe(self.obj_panel, color=theme.GOOD, buff=0.1,
                                time_width=2.0), run_time=0.6)
        return 2.5
