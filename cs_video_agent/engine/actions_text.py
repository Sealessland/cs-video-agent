"""文本类动作：标题、提问、计数卡、结论卡、对比条、通用淡出。

这些动作管理 ctx.slots 中的『槽位』mobject，便于替换与定向清除。
"""

from manim import (
    BOLD,
    Create,
    DOWN,
    FadeIn,
    FadeOut,
    FadeTransform,
    GrowFromEdge,
    LEFT,
    LaggedStart,
    Rectangle,
    RIGHT,
    RoundedRectangle,
    Text,
    UP,
    VGroup,
)

from cs_video_agent import theme
from cs_video_agent.visualkit.views.util import fit_text, resolve_color

HANDLERS = {}
SPECS = {}


def _reg(name, required=(), optional=()):
    def deco(fn):
        HANDLERS[name] = fn
        SPECS[name] = {"required": list(required), "optional": list(optional)}
        return fn
    return deco


_DESC = {
    "show_title": "顶部标题卡（自动替换旧标题）",
    "show_question": "画面下方的问题句（黄色强调）",
    "fade_question": "淡出问题句",
    "show_metric": "右上角计数卡；同 id 再次调用 = 更新文本",
    "show_card": "下方信息卡：at=left/center/right 三列布局，同 id 替换",
    "show_takeaway": "底部结论横幅（每幕收尾用）",
    "show_bars": "水平对比条形图；items=[{label,value,color}]",
    "fade_slot": "淡出指定 id 的槽位（如 bars）",
    "fade_all": "淡出场上所有元素（编译器会在每幕结尾自动追加）",
}


def _slot_mobject(slot):
    return slot["group"] if isinstance(slot, dict) else slot


@_reg("show_title", required=["text"], optional=["sub"])
def show_title(scene, p):
    ctx = scene.ctx
    group = VGroup()
    t = fit_text(
        Text(p["text"], font=theme.FONT, font_size=theme.TITLE_SIZE,
             color=theme.TEXT_MAIN, weight=BOLD),
        9.8,
    )
    group.add(t)
    if p.get("sub"):
        s = fit_text(
            Text(p["sub"], font=theme.FONT, font_size=theme.SUB_SIZE,
                 color=theme.TEXT_DIM),
            10.5,
        )
        s.next_to(t, DOWN, buff=0.20)
        group.add(s)
    group.to_edge(UP, buff=0.42)
    old = ctx.slots.get("title")
    anims = [FadeIn(group)]
    if old is not None:
        anims.append(FadeOut(_slot_mobject(old)))
    scene.play(*anims, run_time=0.8)
    ctx.slots["title"] = group


@_reg("show_question", required=["text"])
def show_question(scene, p):
    q = fit_text(
        Text(p["text"], font=theme.FONT, font_size=34, color=theme.READY),
        10.0,
    )
    q.move_to([0.0, -3.32, 0.0])
    old = scene.ctx.slots.get("question")
    anims = [FadeIn(q)]
    if old is not None:
        anims.append(FadeOut(_slot_mobject(old)))
    scene.play(*anims, run_time=0.8)
    scene.ctx.slots["question"] = q


@_reg("fade_question")
def fade_question(scene, p):
    old = scene.ctx.slots.pop("question", None)
    if old is not None:
        scene.play(FadeOut(_slot_mobject(old)), run_time=0.5)


@_reg("show_metric", required=["id", "text"], optional=["width"])
def show_metric(scene, p):
    ctx = scene.ctx
    mid = p["id"]
    slot = ctx.slots.get(mid)
    if slot is None:
        w = float(p.get("width", 4.4))
        box = RoundedRectangle(corner_radius=0.12, width=w, height=0.78,
                               stroke_width=1.5, stroke_color=theme.TEXT_DIM,
                               fill_color="#161c26", fill_opacity=0.95)
        txt = fit_text(
            Text(p["text"], font=theme.FONT, font_size=theme.METRIC_SIZE,
                 color=theme.TEXT_MAIN),
            w - 0.5,
        )
        txt.move_to(box.get_center())
        group = VGroup(box, txt)
        group.to_edge(UP, buff=0.5).to_edge(RIGHT, buff=0.42)
        scene.play(FadeIn(group), run_time=0.7)
        ctx.slots[mid] = {"group": group, "text": txt}
    else:
        new = fit_text(
            Text(p["text"], font=theme.FONT, font_size=theme.METRIC_SIZE,
                 color=theme.TEXT_MAIN),
            slot["group"].width - 0.5,
        )
        new.move_to(slot["text"].get_center())
        scene.play(FadeTransform(slot["text"], new), run_time=0.7)
        slot["text"] = new


@_reg("show_takeaway", required=["text"])
def show_takeaway(scene, p):
    card = RoundedRectangle(corner_radius=0.14, width=11.6, height=1.05,
                            stroke_width=2, stroke_color="#d98a6a",
                            fill_color="#141c2a", fill_opacity=0.96)
    txt = fit_text(
        Text(p["text"], font=theme.FONT, font_size=theme.TAKEAWAY_SIZE,
             color=theme.TEXT_MAIN),
        10.6,
    )
    txt.move_to(card.get_center())
    group = VGroup(card, txt)
    group.to_edge(DOWN, buff=0.32)
    old = scene.ctx.slots.pop("takeaway", None)
    anims = [Create(card), FadeIn(txt)]
    if old is not None:
        anims.append(FadeOut(_slot_mobject(old)))
    scene.play(*anims, run_time=1.2)
    scene.ctx.slots["takeaway"] = group


@_reg("show_bars", required=["id", "items"],
      optional=["max_value", "unit", "bar_max_len", "center"])
def show_bars(scene, p):
    items = p["items"]
    max_v = float(p.get("max_value") or max(it["value"] for it in items))
    unit = p.get("unit", "")
    bar_max = float(p.get("bar_max_len", 4.4))
    cx, cy = p.get("center", [-0.6, -3.05])
    x_left = cx - bar_max / 2
    v_gap = 0.92
    n = len(items)
    group = VGroup()
    bars = []
    for i, it in enumerate(items):
        y = cy + (n - 1) * v_gap / 2 - i * v_gap
        label = fit_text(
            Text(it["label"], font=theme.FONT, font_size=22,
                 color=theme.TEXT_MAIN),
            6.4,
        )
        label.move_to([x_left + label.width / 2, y + 0.33, 0.0])
        w = max(0.35, float(it["value"]) / max_v * bar_max)
        color = resolve_color(it.get("color", "GOOD"))
        bar = Rectangle(width=w, height=0.34, fill_color=color,
                        fill_opacity=0.9, stroke_width=0)
        bar.move_to([x_left + w / 2, y - 0.10, 0.0])
        val = Text(f"{it['value']}{unit}", font=theme.FONT, font_size=22,
                   color=theme.TEXT_DIM)
        val.next_to(bar, RIGHT, buff=0.18)
        group.add(VGroup(label, bar, val))
        bars.append(bar)
    labels_group = VGroup(*[sub[0] for sub in group])
    vals_group = VGroup(*[sub[2] for sub in group])
    scene.play(LaggedStart(*[GrowFromEdge(b, LEFT) for b in bars], lag_ratio=0.4),
               FadeIn(labels_group), FadeIn(vals_group), run_time=1.6)
    scene.ctx.slots[p["id"]] = group


_CARD_X = {"left": -4.6, "center": 0.0, "right": 4.6}


@_reg("show_card", required=["id", "text"], optional=["at", "width", "color"])
def show_card(scene, p):
    ctx = scene.ctx
    w = float(p.get("width", 4.5))
    color = resolve_color(p.get("color", "TEXT_DIM"))
    card = RoundedRectangle(corner_radius=0.12, width=w, height=0.78,
                            stroke_width=1.5, stroke_color=color,
                            fill_color="#161c26", fill_opacity=0.95)
    txt = fit_text(
        Text(p["text"], font=theme.FONT, font_size=22, color=theme.TEXT_MAIN),
        w - 0.4,
    )
    txt.move_to(card.get_center())
    group = VGroup(card, txt)
    group.move_to([_CARD_X[p.get("at", "center")], -3.32, 0.0])
    old = ctx.slots.pop(p["id"], None)
    anims = [FadeIn(group)]
    if old is not None:
        anims.append(FadeOut(_slot_mobject(old)))
    scene.play(*anims, run_time=0.6)
    ctx.slots[p["id"]] = group


@_reg("fade_slot", required=["id"])
def fade_slot(scene, p):
    slot = scene.ctx.slots.pop(p["id"], None)
    if slot is not None:
        scene.play(FadeOut(_slot_mobject(slot)), run_time=0.5)


@_reg("fade_all")
def fade_all(scene, p):
    mobs = list(scene.mobjects)
    if mobs:
        scene.play(*[FadeOut(m) for m in mobs], run_time=0.6)
        scene.remove(*mobs)
    scene.ctx.slots.clear()
