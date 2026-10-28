"""全局视觉主题：3b1b 风格的深色画布 + 固定色板与字体。

颜色语义约定（教学一致性）：
- IDLE  空闲连接（灰）
- READY 就绪连接/就绪高亮（黄）
- EVENT 内核事件/回调（橙）
- KERNEL 内核（青）
- GOOD  epoll 收益侧（绿）
- COST  select/poll 成本侧（红）
"""

from manim import (
    BLUE_E,
    GREY_B,
    GREY_D,
    GREEN,
    ORANGE,
    RED,
    TEAL,
    WHITE,
    YELLOW,
    YELLOW_E,
)

BG_COLOR = "#0e1116"
FONT = "Noto Sans CJK SC"

IDLE = GREY_D
READY = YELLOW
READY_STROKE = YELLOW_E
SCAN_TICK = BLUE_E
EVENT = ORANGE
KERNEL = TEAL
GOOD = GREEN
COST = RED
TEXT_DIM = GREY_B
TEXT_MAIN = WHITE

# 字号（Manim font_size，1080p 基准）
TITLE_SIZE = 38
SUB_SIZE = 24
LABEL_SIZE = 24
SMALL_SIZE = 20
METRIC_SIZE = 24
TAKEAWAY_SIZE = 24
