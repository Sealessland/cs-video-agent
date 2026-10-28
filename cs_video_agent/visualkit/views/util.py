"""视图层小工具：筹码（fd 徽章）、文字防溢出、调色板解析。"""

import numpy as np
from manim import RoundedRectangle, Text, VGroup

from cs_video_agent import theme

_PALETTE = {
    "IDLE": theme.IDLE,
    "READY": theme.READY,
    "EVENT": theme.EVENT,
    "KERNEL": theme.KERNEL,
    "GOOD": theme.GOOD,
    "COST": theme.COST,
    "SCAN_TICK": theme.SCAN_TICK,
    "TEXT_DIM": theme.TEXT_DIM,
}


def resolve_color(name_or_color):
    return _PALETTE.get(name_or_color, name_or_color)


def make_chip(label: str, color, width: float = 0.92, height: float = 0.44) -> VGroup:
    """fd 徽章：内核 interest list 与就绪队列共用的最小视觉单元。"""
    box = RoundedRectangle(
        corner_radius=0.10,
        width=width,
        height=height,
        stroke_width=1.5,
        stroke_color=color,
        fill_color=color,
        fill_opacity=0.85,
    )
    txt = Text(str(label), font=theme.FONT, font_size=theme.SMALL_SIZE, color="#0b0d10")
    txt.move_to(box.get_center())
    return VGroup(box, txt)


def fit_text(text: Text, max_width: float) -> Text:
    if text.width > max_width:
        text.scale_to_fit_width(max_width)
    return text


def vec(x: float, y: float) -> np.ndarray:
    return np.array([x, y, 0.0])
