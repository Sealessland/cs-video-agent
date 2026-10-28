"""OS 组件模型单元测试：ELF 双视图、地址空间惰性分配、fd 表语义。"""

from cs_video_agent.visualkit.models_os import (
    AddrSpaceModel,
    ElfFileModel,
    FdTableModel,
)


class TestElfFileModel:
    def test_default_grouping_valid(self):
        m = ElfFileModel()
        assert m.check_grouping() == []

    def test_switch_view(self):
        m = ElfFileModel()
        assert m.switch_view("exec") is True
        assert m.view == "exec"
        assert m.switch_view("bogus") is False

    def test_segment_of(self):
        m = ElfFileModel()
        assert m.segment_of(".text") == "R+E"
        assert m.segment_of(".rodata") == "R"
        assert m.segment_of(".data") == "RW"
        assert m.segment_of(".symtab") is None

    def test_broken_grouping_detected(self):
        m = ElfFileModel()
        m.segments = [{"perm": "R", "sections": [".text", ".data"]}]
        assert m.check_grouping() != []


class TestAddrSpaceModel:
    def test_lazy_allocation(self):
        m = AddrSpaceModel()
        assert m.touch("code") == "alloc"      # 第一次访存才分配
        assert m.touch("code") == "hit"
        assert "code" not in [e["region"] for e in m.fault_log
                              if e["op"] == "map"]

    def test_map_then_touch(self):
        m = AddrSpaceModel()
        assert m.map_region("libc") is True
        assert m.touch("libc") == "alloc"
        assert m.check_lazy() == []

    def test_segv_outside_vma(self):
        m = AddrSpaceModel()
        assert m.touch("gap") == "segv"
        assert m.check_segv() == []

    def test_layout_order(self):
        m = AddrSpaceModel()
        m.map_region("libc")
        assert m.check_layout() == []

    def test_duplicate_map_rejected(self):
        m = AddrSpaceModel()
        assert m.map_region("libc") is True
        assert m.map_region("libc") is False


class TestFdTableModel:
    def test_open_dup_read_sharing(self):
        t = FdTableModel()
        t.open(3, "a.txt")
        assert t.dup(3, 4) is True
        assert t.read(3, 100) == 100
        assert t.read(4, 50) == 150          # 同一实例，offset 累加
        assert t.table[3] == t.table[4]
        assert t.check_dup_shares() == []

    def test_open_creates_independent_instances(self):
        t = FdTableModel()
        t.open(3, "a.txt")
        t.open(5, "a.txt")
        assert t.table[3] != t.table[5]
        t.read(3, 100)
        assert t.offset(5) == 0
        assert t.check_open_independent() == []

    def test_fork_copies_table_shares_instances(self):
        t = FdTableModel()
        t.open(3, "a.txt")
        t.dup(3, 4)
        assert t.fork() is True
        assert t.read(3, 64, who="child") == 64
        assert t.offset(3, who="parent") == 64   # 父进程看到子进程的推进
        assert t.check_fork_shares() == []

    def test_read_unknown_fd_fails(self):
        t = FdTableModel()
        assert t.read(9, 10) is None
