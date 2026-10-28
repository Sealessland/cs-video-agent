"""OS 组件纯状态模型：ELF 双视图、虚拟地址空间（VMA/缺页）、fd 表。

对应三篇博客文章的技术事实，全部不依赖 Manim，可独立回放验证：
- execute.md  : 内核按 Segment 装载，Section 是链接/调试视图
- process.md  : mmap 只注册 VMA，物理页在第一次缺页时才分配；越界访存 SIGSEGV
- object.md   : fd 是索引；dup 共享实例（共享 f_pos），open 新建实例；fork 复制 fd 表
"""

SUPPORTED_OS_INVARIANTS = {
    "exec_view_groups_sections_into_segments",
    "va_layout_code_low_stack_high",
    "lazy_alloc_on_first_touch",
    "segv_only_outside_vma",
    "dup_shares_offset",
    "open_creates_independent_instance",
    "fork_shares_file_instances",
}

DEFAULT_SECTIONS = [
    {"name": ".text", "debug": False},
    {"name": ".rodata", "debug": False},
    {"name": ".data", "debug": False},
    {"name": ".bss", "debug": False},
    {"name": ".symtab", "debug": True},
]

DEFAULT_SEGMENTS = [
    {"perm": "R+E", "sections": [".text"]},
    {"perm": "R", "sections": [".rodata"]},
    {"perm": "RW", "sections": [".data", ".bss"]},
]


class ElfFileModel:
    """ELF 双视图状态：link（Section 视图）/ exec（Segment 视图）。"""

    def __init__(self, sections=None, segments=None):
        self.sections = sections or [dict(s) for s in DEFAULT_SECTIONS]
        self.segments = segments or [dict(s) for s in DEFAULT_SEGMENTS]
        self.view = "link"
        self.log: list[tuple] = []

    def switch_view(self, view: str) -> bool:
        ok = view in ("link", "exec")
        if ok:
            self.view = view
        self.log.append(("switch_view", view, ok))
        return ok

    def segment_of(self, section: str) -> str | None:
        for seg in self.segments:
            if section in seg["sections"]:
                return seg["perm"]
        return None

    def check_grouping(self) -> list[str]:
        """非调试 section 必须恰好属于一个 segment；调试 section 不参与装载。"""
        problems = []
        for s in self.sections:
            n = sum(1 for seg in self.segments if s["name"] in seg["sections"])
            if not s["debug"] and n != 1:
                problems.append(f"{s['name']} belongs to {n} segments (expect 1)")
            if s["debug"] and n != 0:
                problems.append(f"debug section {s['name']} must not be loaded")
        return problems


class AddrSpaceModel:
    """虚拟地址空间：低地址 code/data，heap 向上，mmap 区，stack 在高地址向下。

    vma = 已登记的区间；physical = 已交付物理页的区间。
    touch() 是唯一能把区间从「记账」变成「有物理页」的操作（惰性分配）。
    """

    ORDER = ["code", "data", "heap", "libc", "stack"]  # 低 -> 高

    def __init__(self):
        self.vmas: list[str] = ["code", "data", "heap", "stack"]
        self.physical: set[str] = set()
        self.fault_log: list[dict] = []

    def map_region(self, region: str) -> bool:
        ok = region in self.ORDER and region not in self.vmas
        if ok:
            self.vmas.append(region)
            self.vmas.sort(key=self.ORDER.index)
        self.fault_log.append({"op": "map", "region": region, "ok": ok,
                               "physical_after": region in self.physical})
        return ok

    def touch(self, region: str) -> str:
        """返回 'hit'（已有物理页）/ 'alloc'（缺页后分配）/ 'segv'（无 VMA）。"""
        if region not in self.vmas:
            result = "segv"
        elif region in self.physical:
            result = "hit"
        else:
            self.physical.add(region)
            result = "alloc"
        self.fault_log.append({"op": "touch", "region": region, "result": result})
        return result

    def check_layout(self) -> list[str]:
        idx = [self.ORDER.index(r) for r in self.vmas]
        if idx != sorted(idx):
            return ["vma order violates code<data<heap<libc<stack"]
        return []

    def check_lazy(self) -> list[str]:
        """任何 alloc 必须来自 touch，且 map 时不得直接交付物理页。"""
        bad = [e for e in self.fault_log if e["op"] == "map" and e["physical_after"]]
        return [f"map delivered physical pages directly: {e}" for e in bad]

    def check_segv(self) -> list[str]:
        bad = [e for e in self.fault_log
               if e["op"] == "touch" and e["result"] == "segv"
               and e["region"] in self.vmas]
        return [f"segv inside a valid vma: {e}" for e in bad]


class FdTableModel:
    """fd 表：fd -> 实例(iid)；实例持有 offset。open 新建实例，dup 复用实例，fork 复制表。"""

    def __init__(self):
        self.instances: dict[int, dict] = {}
        self.table: dict[int, int] = {}
        self.child_table: dict[int, int] | None = None
        self._next_iid = 1
        self.log: list[dict] = []

    def open(self, fd: int, label: str) -> int:
        iid = self._next_iid
        self._next_iid += 1
        self.instances[iid] = {"label": label, "offset": 0}
        self.table[fd] = iid
        self.log.append({"op": "open", "fd": fd, "iid": iid, "new_instance": True})
        return iid

    def dup(self, src: int, dst: int) -> bool:
        ok = src in self.table
        if ok:
            self.table[dst] = self.table[src]
        self.log.append({"op": "dup", "src": src, "dst": dst, "ok": ok,
                         "new_instance": False})
        return ok

    def read(self, fd: int, n: int, who: str = "parent") -> int | None:
        table = self.table if who == "parent" else self.child_table
        if table is None or fd not in table:
            self.log.append({"op": "read", "fd": fd, "who": who, "ok": False})
            return None
        iid = table[fd]
        self.instances[iid]["offset"] += n
        self.log.append({"op": "read", "fd": fd, "who": who, "iid": iid, "n": n,
                         "ok": True})
        return self.instances[iid]["offset"]

    def offset(self, fd: int, who: str = "parent") -> int | None:
        table = self.table if who == "parent" else self.child_table
        if table is None or fd not in table:
            return None
        return self.instances[table[fd]]["offset"]

    def fork(self) -> bool:
        ok = self.child_table is None
        if ok:
            self.child_table = dict(self.table)
        self.log.append({"op": "fork", "ok": ok})
        return ok

    def check_dup_shares(self) -> list[str]:
        """dup 的语义承诺：两个 fd 路由到同一个实例（f_pos 天然共享）。"""
        problems = []
        for d in [e for e in self.log if e["op"] == "dup" and e["ok"]]:
            if self.table.get(d["src"]) != self.table.get(d["dst"]):
                problems.append(f"dup({d['src']},{d['dst']}) 分裂了实例")
        return problems

    def check_open_independent(self) -> list[str]:
        """open 永远新建实例；每个实例的 offset 恰等于经它的读入总量
        （读操作不会串到其他实例）。"""
        problems = []
        iids = [e["iid"] for e in self.log if e["op"] == "open"]
        if len(iids) != len(set(iids)):
            problems.append("open reused an existing instance")
        reads: dict[int, int] = {}
        for e in self.log:
            if e["op"] == "read" and e.get("ok"):
                reads[e["iid"]] = reads.get(e["iid"], 0) + e["n"]
        for iid, total in reads.items():
            if self.instances[iid]["offset"] != total:
                problems.append(f"实例 {iid} offset 与经它的读入不符")
        return problems

    def check_fork_shares(self) -> list[str]:
        if self.child_table is None:
            return []
        problems = []
        for fd, iid in self.table.items():
            if self.child_table.get(fd) != iid:
                problems.append(f"fork 后 fd{fd} 不再指向同一实例")
        return problems
