"""纯 Python 状态模型（不依赖 Manim）。

Model 层保存真实状态与状态转移，并记录完整事件日志；
View/动画层只是这些状态变化的可视化解释。
语义回放（engine/replay.py）与单元测试直接跑这一层。

socket id 的构造规则也集中在这里，保证视图与回放使用同一套 id。
"""

from dataclasses import dataclass, field

SUPPORTED_INVARIANTS = {
    "only_ready_sockets_are_returned",
    "unregistered_sockets_never_enqueued",
    "ready_list_no_duplicates",
    "scan_checks_every_socket",
}


def socket_grid_ids(obj_id: str, rows: int, cols: int) -> list[str]:
    return [f"{obj_id}#{i}" for i in range(rows * cols)]


def socket_stack_ids(fds: list[str]) -> list[str]:
    return [str(fd) for fd in fds]


@dataclass
class LogEntry:
    step: int
    op: str
    ok: bool
    detail: dict = field(default_factory=dict)


class SocketSet:
    """一组 socket 连接的就绪状态机：idle -> readable。

    check() 模拟 select/poll 的逐个询问，返回该连接是否就绪并累计检查次数。
    """

    def __init__(self, ids: list[str]):
        self.ids: list[str] = list(ids)
        self._ready: set[str] = set()
        self.log: list[LogEntry] = []
        self._step = 0
        self.checks_count = 0

    def _rec(self, op: str, ok: bool, **detail) -> None:
        self.log.append(LogEntry(self._step, op, ok, detail))
        self._step += 1

    def mark_ready(self, sid: str) -> bool:
        ok = sid in self.ids
        if ok:
            self._ready.add(sid)
        self._rec("mark_ready", ok, sid=sid)
        return ok

    def is_ready(self, sid: str) -> bool:
        return sid in self._ready

    @property
    def ready_ids(self) -> set[str]:
        return set(self._ready)

    def check(self, sid: str) -> bool:
        """select/poll 的一次询问：无论结果如何都记一次检查。"""
        valid = sid in self.ids
        self.checks_count += 1
        self._rec("check", valid, sid=sid, ready=(sid in self._ready) if valid else None)
        return (sid in self._ready) if valid else False


class ReadyList:
    """epoll 的 interest list + ready list 模型。

    - register(fd)          对应 epoll_ctl(EPOLL_CTL_ADD)，重复注册幂等
    - on_readable(fd, ...)  内核回调：数据到达时把 fd 放入 ready list
                            （未注册的 fd 不入队；ready list 内不去重）
    - wait()                对应 epoll_wait：返回当前就绪列表并清空
    """

    def __init__(self) -> None:
        self.interest: set[str] = set()
        self._pending: list[str] = []
        self.returned: list[str] = []
        self.log: list[LogEntry] = []
        self._step = 0
        self.enqueue_log: list[dict] = []

    def _rec(self, op: str, ok: bool, **detail) -> None:
        self.log.append(LogEntry(self._step, op, ok, detail))
        self._step += 1

    def register(self, fd: str) -> bool:
        dup = fd in self.interest
        if not dup:
            self.interest.add(fd)
        self._rec("register", not dup, fd=fd, duplicate=dup)
        return not dup

    @property
    def pending(self) -> list[str]:
        return list(self._pending)

    @property
    def ever_enqueued(self) -> list[str]:
        return [e["fd"] for e in self.enqueue_log if e["accepted"]]

    def on_readable(self, fd: str, is_ready: bool | None = None) -> bool:
        """内核回调入队。is_ready 由调用方提供 socket 真实就绪态（若已知）。"""
        registered = fd in self.interest
        ready = (is_ready is not False)
        accepted = registered and ready and fd not in self._pending
        if accepted:
            self._pending.append(fd)
        entry = {
            "fd": fd,
            "registered": registered,
            "ready": ready,
            "accepted": accepted,
            "duplicate": registered and ready and fd in self._pending,
        }
        self.enqueue_log.append(entry)
        self._rec("enqueue", accepted, **entry)
        return accepted

    def wait(self) -> list[str]:
        out = list(self._pending)
        self._pending.clear()
        self.returned.extend(out)
        self._rec("wait", True, returned=out)
        return out
