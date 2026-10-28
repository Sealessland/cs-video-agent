"""Socket 视图：大规模网格（scene 1/2 的 100 连接）与纵向堆栈（scene 3 的 fd 列表）。

视图上的每一次状态变化都先经过 SocketSet 模型，保证画面与语义一致。
"""

from manim import (
    AnimationGroup,
    Circle,
    Circumscribe,
    Create,
    FadeIn,
    FadeOut,
    LEFT,
    LaggedStart,
    Rectangle,
    Succession,
    Text,
    VGroup,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models import SocketSet, socket_grid_ids, socket_stack_ids
from cs_video_agent.visualkit.views.util import vec


class SocketGridView:
    def __init__(self, obj_id: str, ctx, rows: int = 10, cols: int = 10,
                 center: tuple = (0.0, -0.35), cell_radius: float = 0.13, buff: float = 0.30):
        self.ctx = ctx
        self.obj_id = obj_id
        self.rows, self.cols = rows, cols
        self.ids = socket_grid_ids(obj_id, rows, cols)
        self.model = SocketSet(self.ids)
        cells = [
            Circle(
                radius=cell_radius,
                color=theme.IDLE,
                stroke_width=1,
                fill_color=theme.IDLE,
                fill_opacity=0.25,
            )
            for _ in self.ids
        ]
        self.grid = VGroup(*cells).arrange_in_grid(rows=rows, cols=cols, buff=buff)
        self.grid.move_to(vec(*center))
        self.root = self.grid

    # -- 动画入口（返回 Animation，由 action 层 play） --
    def entrance(self):
        return Create(self.grid, run_time=1.4)

    def _cell_anim_ready(self, i: int, subtle: bool):
        cell = self.grid[i]
        opacity = 0.28 if subtle else 1.0
        return cell.animate.set_fill(theme.READY, opacity=opacity).set_stroke(
            theme.READY_STROKE, width=1.5 if subtle else 2.5
        ).build()

    def mark_ready(self, index: int, subtle: bool = False):
        self.model.mark_ready(self.ids[index])
        return [self._cell_anim_ready(index, subtle)]

    def pulse(self, index: int, color=None):
        return Circumscribe(self.grid[index], color=color or theme.READY, buff=0.09, time_width=2.0)

    def dim_except(self, keep):
        anims = []
        for i, cell in enumerate(self.grid):
            if i not in keep:
                anims.append(cell.animate.set_opacity(0.15).build())
        return anims

    # -- 扫描：多段编排，直接驱动 scene --
    def scan(self, scene, run_time: float = 4.0):
        ticks = []
        for i, cell in enumerate(self.grid):
            hit = self.model.check(self.ids[i])
            if hit:
                ticks.append(self._cell_anim_ready(i, subtle=False))
            else:
                up = cell.animate.set_stroke(theme.SCAN_TICK, width=2).set_fill(
                    theme.SCAN_TICK, opacity=0.5
                ).build()
                down = cell.animate.set_stroke(theme.IDLE, width=1).set_fill(
                    theme.IDLE, opacity=0.25
                ).build()
                ticks.append(Succession(up, down))
        beam = Rectangle(
            width=self.grid.width + 0.5,
            height=0.62,
            fill_color=theme.SCAN_TICK,
            fill_opacity=0.12,
            stroke_width=0,
        )
        cx = self.grid.get_center()[0]
        row_ys = [self.grid[r * self.cols].get_center()[1] for r in range(self.rows)]
        moves = Succession(*[beam.animate.move_to(vec(cx, y)).build() for y in row_ys])
        scene.add(beam)
        scene.play(LaggedStart(*ticks, lag_ratio=0.96), moves, run_time=run_time)
        scene.play(FadeOut(beam), run_time=0.25)
        scene.remove(beam)

    def anchor(self, name: str):
        return self.grid.get_center()


class SocketStackView:
    def __init__(self, obj_id: str, ctx, fds=("3", "4", "5", "6", "7"),
                 x: float = -5.4, y_top: float = 2.3, spacing: float = 0.8, radius: float = 0.30):
        self.ctx = ctx
        self.obj_id = obj_id
        self.fds = [str(f) for f in fds]
        self.ids = socket_stack_ids(self.fds)
        self.model = SocketSet(self.ids)
        circles, labels = [], []
        for k, fd in enumerate(self.fds):
            c = Circle(radius=radius, color=theme.IDLE, stroke_width=2,
                       fill_color=theme.IDLE, fill_opacity=0.3)
            c.move_to(vec(x, y_top - k * spacing))
            label = Text(f"fd {fd}", font=theme.FONT, font_size=theme.SMALL_SIZE,
                         color=theme.TEXT_DIM)
            label.next_to(c, LEFT, buff=0.25)
            circles.append(c)
            labels.append(label)
        self.circles = VGroup(*circles)
        self.labels = VGroup(*labels)
        self.root = VGroup(self.circles, self.labels)

    def entrance(self):
        return AnimationGroup(Create(self.circles), LaggedStart(
            *[FadeIn(l) for l in self.labels], lag_ratio=0.3), run_time=1.4)

    def _fd_index(self, fd) -> int:
        return self.ids.index(str(fd))

    def mark_ready(self, fd, subtle: bool = False):
        self.model.mark_ready(str(fd))
        c = self.circles[self._fd_index(fd)]
        opacity = 0.4 if subtle else 1.0
        return [c.animate.set_fill(theme.READY, opacity=opacity).set_stroke(
            theme.READY_STROKE, width=2.5).build()]

    def pulse(self, fd, color=None):
        return Circumscribe(self.circles[self._fd_index(fd)], color=color or theme.READY,
                            buff=0.10, time_width=2.0)

    def anchor(self, name: str):
        if name == "center":
            return self.circles.get_center()
        return self.circles[self._fd_index(name)].get_center()
