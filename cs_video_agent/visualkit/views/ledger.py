"""对账台账视图：渠道账单 vs 本地流水的两列对照表。

scan/fix 的状态转移先落在 Ledger 模型上，再解释为动画；
scan 给每行打「一致 / 差异」标记，fix 只在模型接受时改写本地状态。
"""

from manim import (
    AnimationGroup,
    Circumscribe,
    Create,
    FadeIn,
    FadeOut,
    LaggedStart,
    Line,
    RIGHT,
    Rectangle,
    Text,
    VGroup,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.models_pay import Ledger
from cs_video_agent.visualkit.views.util import fit_text, vec

_ROW_BG = "#141a24"
_ROW_BG_BAD = "#2a1620"
_MARK_GOOD = "#59c96a"
_MARK_BAD = "#e05555"


class LedgerView:
    def __init__(self, obj_id: str, ctx, rows, center=(0.0, 0.3), width=9.2,
                 row_h=0.6, left_title="渠道账单", right_title="本地流水"):
        self.ctx = ctx
        self.obj_id = obj_id
        self.model = Ledger(rows)
        self.width = width
        self.row_h = row_h
        label_w = width * 0.34
        col_w = (width - label_w) / 2
        self._label_w = label_w
        self._col_w = col_w

        x0 = center[0] - width / 2
        top = center[1] + (len(self.model.rows) + 1) * row_h / 2

        header = VGroup()
        t0 = fit_text(Text("订单", font=theme.FONT, font_size=theme.SMALL_SIZE,
                           color=theme.TEXT_DIM), label_w - 0.3)
        t0.move_to(vec(x0 + label_w / 2, top - row_h / 2))
        t1 = fit_text(Text(left_title, font=theme.FONT, font_size=theme.SMALL_SIZE,
                           color=theme.KERNEL), col_w - 0.3)
        t1.move_to(vec(x0 + label_w + col_w / 2, top - row_h / 2))
        t2 = fit_text(Text(right_title, font=theme.FONT, font_size=theme.SMALL_SIZE,
                           color=theme.EVENT), col_w - 0.3)
        t2.move_to(vec(x0 + label_w + col_w * 1.5, top - row_h / 2))
        header.add(t0, t1, t2)
        self.header_line = Line([x0, top - row_h + 0.04, 0],
                                [x0 + width, top - row_h + 0.04, 0],
                                stroke_width=1.5, color=theme.TEXT_DIM)

        self.row_mobs: dict[str, dict] = {}
        body = VGroup()
        for i, (rid, r) in enumerate(self.model.rows.items()):
            y = top - row_h * (1.5 + i)
            self.row_mobs[rid] = self._build_row(rid, r, x0, y, label_w, col_w)
            body.add(self.row_mobs[rid]["group"])

        self.root = VGroup(header, self.header_line, body)

    def _build_row(self, rid, r, x0, y, label_w, col_w):
        bg = Rectangle(width=self.width, height=self.row_h - 0.06,
                       stroke_width=0, fill_color=_ROW_BG, fill_opacity=0.9)
        bg.move_to(vec(x0 + self.width / 2, y))
        label = fit_text(Text(r["label"], font=theme.FONT, font_size=theme.SMALL_SIZE,
                              color=theme.TEXT_MAIN), label_w - 0.35)
        label.move_to(vec(x0 + label_w / 2, y))
        matched = r["channel"] == r["local"]
        ch_color = theme.TEXT_MAIN if matched else theme.KERNEL
        lc_color = theme.TEXT_MAIN if matched else theme.COST
        ch = fit_text(Text(r["channel"], font=theme.FONT,
                           font_size=theme.SMALL_SIZE, color=ch_color), col_w - 0.3)
        ch.move_to(vec(x0 + label_w + col_w / 2, y))
        lc = fit_text(Text(r["local"], font=theme.FONT,
                           font_size=theme.SMALL_SIZE, color=lc_color), col_w - 0.3)
        lc.move_to(vec(x0 + label_w + col_w * 1.5, y))
        return {"group": VGroup(bg, label, ch, lc), "bg": bg, "ch": ch, "lc": lc,
                "mark": None}

    def entrance(self):
        row_groups = [self.row_mobs[r]["group"] for r in self.model.rows]
        return AnimationGroup(
            Create(self.header_line),
            FadeIn(VGroup(*[m for m in self.root[0]])),
            LaggedStart(*[FadeIn(g) for g in row_groups], lag_ratio=0.25),
        )

    def _bring_row_front(self, scene, rid):
        """bg 被 .animate 重排到顶层后会盖住行内文字，动画后把整行抬回。"""
        mob = self.row_mobs[rid]
        scene.remove(mob["bg"])
        scene.remove(mob["group"])
        scene.add(mob["group"])

    def _raise_on_top(self, scene, m):
        scene.remove(m)
        scene.add(m)

    def scan(self, scene, run_time: float = 1.8):
        results = self.model.scan()
        anims = []
        tinted = []
        for rid, res in zip(self.model.rows, results):
            mob = self.row_mobs[rid]
            if mob["mark"] is not None:
                continue
            if res["matched"]:
                mark = fit_text(Text("一致", font=theme.FONT, font_size=16,
                                     color=_MARK_GOOD), 1.1)
            else:
                mark = fit_text(Text("差异", font=theme.FONT, font_size=16,
                                     color=_MARK_BAD), 1.1)
                anims.append(mob["bg"].animate.set_fill(_ROW_BG_BAD, 0.95))
                tinted.append(rid)
            mark.next_to(mob["lc"], RIGHT, buff=0.25)
            mob["mark"] = mark
            anims.append(FadeIn(mark))
        if anims:
            scene.play(LaggedStart(*anims, lag_ratio=0.25), run_time=run_time)
            for rid in tinted:
                self._bring_row_front(scene, rid)
                self._raise_on_top(scene, self.row_mobs[rid]["mark"])

    def fix(self, scene, row: str, to: str, run_time: float = 1.4):
        rid = str(row)
        mob = self.row_mobs[rid]
        ok = self.model.fix(rid, to)
        if ok:
            new_lc = fit_text(Text(to, font=theme.FONT, font_size=theme.SMALL_SIZE,
                                   color=theme.GOOD), self._col_w - 0.3)
            new_lc.move_to(mob["lc"].get_center())
            new_mark = fit_text(Text("已补齐", font=theme.FONT, font_size=16,
                                     color=_MARK_GOOD), 1.2)
            new_mark.move_to(mob["mark"].get_center())
            old_lc, old_mark = mob["lc"], mob["mark"]
            anims = [
                mob["bg"].animate.set_fill(_ROW_BG, 0.9),
                FadeOut(old_lc), FadeIn(new_lc),
                FadeOut(old_mark), FadeIn(new_mark),
                Circumscribe(mob["group"], color=theme.GOOD, buff=0.08,
                             time_width=1.5),
            ]
            scene.play(*anims, run_time=run_time)
            # 用组内替换而非顶层叠加：新字归属行组，z 序天然正确
            group = mob["group"]
            group.remove(old_lc)
            group.add(new_lc)
            mob["lc"], mob["mark"] = new_lc, new_mark
            self._bring_row_front(scene, rid)
            self._raise_on_top(scene, new_mark)
        else:
            scene.play(Circumscribe(mob["group"], color=theme.COST, buff=0.08,
                                    time_width=1.5), run_time=run_time * 0.6)

    def anchor(self, name: str):
        if name.startswith("row_"):
            return self.row_mobs[name[4:]]["group"].get_right()
        return {
            "left": self.root.get_left(),
            "right": self.root.get_right(),
            "top": self.root.get_top(),
            "bottom": self.root.get_bottom(),
            "center": self.root.get_center(),
        }[name]
