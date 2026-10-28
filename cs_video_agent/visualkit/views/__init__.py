"""对象构建注册表：Scene IR 的 type -> View。

视图持有的模型（SocketSet / ReadyList）在构建时创建；
kernel 与 queue 共享同一个 ReadyList（同一个 epoll 域）。
"""

from cs_video_agent.visualkit.models import ReadyList
from cs_video_agent.visualkit.views.addr_space import AddrSpaceView
from cs_video_agent.visualkit.views.elf_file import ElfFileView
from cs_video_agent.visualkit.views.event_flow import EventFlowView, KernelPanel, WorkerBox
from cs_video_agent.visualkit.views.fd_table import FdTableView
from cs_video_agent.visualkit.views.ledger import LedgerView
from cs_video_agent.visualkit.views.ready_queue import ReadyQueueView
from cs_video_agent.visualkit.views.state_strip import StateStripView
from cs_video_agent.visualkit.views.socket_grid import SocketGridView, SocketStackView

_TYPES = {
    "socket_grid": SocketGridView,
    "socket_stack": SocketStackView,
    "ready_queue": ReadyQueueView,
    "kernel_panel": KernelPanel,
    "worker_box": WorkerBox,
    "event_flow": EventFlowView,
    "elf_file": ElfFileView,
    "addr_space": AddrSpaceView,
    "fd_table": FdTableView,
    "state_strip": StateStripView,
    "ledger": LedgerView,
}

# 每种类型允许的构造参数（多余的 key 会在构建时报错，捕获 storyboard 笔误）
_ALLOWED = {
    "socket_grid": {"rows", "cols", "center", "cell_radius", "buff"},
    "socket_stack": {"fds", "x", "y_top", "spacing", "radius"},
    "ready_queue": {"slots", "center", "slot_w", "slot_h", "buff", "label"},
    "kernel_panel": {"center", "width", "height", "label", "sub"},
    "worker_box": {"center", "width", "height", "label", "status", "color",
                   "sub", "items", "mini"},
    "event_flow": {"arrows"},
    "elf_file": {"center", "width", "height", "sections", "segments", "label"},
    "addr_space": {"center", "width", "height", "phy_center"},
    "fd_table": {"center", "obj_center", "rows"},
    "state_strip": {"states", "transitions", "initial", "terminal",
                    "requires_confirm", "center", "chip_w", "chip_h", "buff"},
    "ledger": {"rows", "center", "width", "row_h", "left_title", "right_title"},
}


def build_object(obj_type: str, params: dict, ctx, obj_id: str):
    if obj_type not in _TYPES:
        raise ValueError(f"unknown object type {obj_type!r}")
    unknown = set(params) - _ALLOWED[obj_type]
    if unknown:
        raise ValueError(f"object {obj_id!r} ({obj_type}): unknown params {sorted(unknown)}")
    view = _TYPES[obj_type](obj_id, ctx, **params)
    view.type = obj_type
    return view


def ensure_shared_ready_list(ctx) -> ReadyList:
    return ctx.shared.setdefault("ready_list", ReadyList())


__all__ = [
    "build_object",
    "ensure_shared_ready_list",
    "SocketGridView",
    "SocketStackView",
    "ReadyQueueView",
    "KernelPanel",
    "WorkerBox",
    "EventFlowView",
    "ElfFileView",
    "AddrSpaceView",
    "FdTableView",
    "StateStripView",
    "LedgerView",
]
