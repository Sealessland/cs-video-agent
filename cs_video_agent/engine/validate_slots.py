"""底部/顶部槽位静态重叠检测：在 validate 阶段拦住「卡片残留叠罗汉」「计数卡压标题」。

只看每拍动作序列结束后的可见槽位集合（transient 动画重叠不管），
槽位的几何模型与 actions_text 的实际布局保持一致（有意留保守余量）。
"""

from cs_video_agent.schemas.scene_ir import Storyboard

CARD_X = {"left": -4.6, "center": 0.0, "right": 4.6}


def _est_text_w(s: str) -> float:
    """按字符类别粗估文本宽度（CJK 类 0.30，ASCII 类 0.14，基准 +0.3）。"""
    w = 0.3
    for ch in str(s):
        w += 0.30 if ord(ch) > 0x2E80 else 0.14
    return w


def _slot_box(action: str, params: dict) -> tuple[str, float, float] | None:
    """返回 (band, x_left, x_right)；未知动作返回 None。"""
    if action == "show_card":
        w = float(params.get("width", 4.5))
        cx = CARD_X[params.get("at", "center")]
        return "bottom", cx - w / 2, cx + w / 2
    if action == "show_question":
        return "bottom", -5.0, 5.0
    if action == "show_takeaway":
        return "bottom", -5.8, 5.8
    if action == "show_bars":
        bar_max = float(params.get("bar_max_len", 4.4))
        cx = float(params.get("center", [-0.6, -3.05])[0])
        return "bottom", cx - bar_max / 2 - 3.3, cx + bar_max / 2 + 0.6
    if action == "show_metric":
        w = float(params.get("width", 4.4))
        right = 7.11 - 0.42
        return "top", right - w, right
    if action == "show_title":
        half = max(_est_text_w(params.get("text", "")),
                   _est_text_w(params.get("sub", ""))) / 2
        return "top", -half, half
    return None


def _apply(active: dict, action: str, params: dict) -> None:
    if action == "fade_all":
        active.clear()
        return
    if action == "fade_question":
        active.pop("question", None)
        return
    if action == "fade_slot":
        active.pop(str(params.get("id")), None)
        return
    slot = _slot_box(action, params)
    if slot is None:
        return
    band, xl, xr = slot
    if action == "show_title":
        active["title"] = ("top", xl, xr)
        return
    key = str(params["id"]) if action != "show_question" and action != "show_takeaway" \
        else action.removeprefix("show_")
    active[key] = (band, xl, xr)


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[1] < b[2] - 0.05 and b[1] < a[2] - 0.05


def validate_slots(storyboard: Storyboard) -> list[str]:
    errors: list[str] = []
    for sc in storyboard.scenes:
        active: dict[str, tuple[str, float, float]] = {}
        for beat in sc.beats:
            for a in beat.actions:
                _apply(active, a.action, a.params)
            slots = list(active.items())
            for i, (k1, s1) in enumerate(slots):
                for k2, s2 in slots[i + 1:]:
                    if s1[0] != s2[0] or not _overlaps(s1, s2):
                        continue
                    errors.append(
                        f"{sc.id}/{beat.id}: 可见槽位重叠 "
                        f"[{k1}] 与 [{k2}]（{s1[0]} 带）；"
                        f"先 fade_slot/换位，或收窄 width")
    return errors
