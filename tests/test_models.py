"""事件状态转移单元测试（验收项 10）。"""

from cs_video_agent.visualkit.models import ReadyList, SocketSet


class TestSocketSet:
    def test_mark_ready_and_query(self):
        s = SocketSet(["a", "b", "c"])
        assert not s.is_ready("b")
        assert s.mark_ready("b") is True
        assert s.is_ready("b")
        assert s.ready_ids == {"b"}

    def test_mark_ready_unknown_rejected(self):
        s = SocketSet(["a"])
        assert s.mark_ready("zzz") is False
        assert s.ready_ids == set()

    def test_check_counts_every_call(self):
        s = SocketSet(["a", "b"])
        s.mark_ready("a")
        assert s.check("a") is True
        assert s.check("b") is False
        assert s.check("b") is False
        assert s.checks_count == 3

    def test_check_unknown_is_false_but_counted(self):
        s = SocketSet(["a"])
        assert s.check("nope") is False
        assert s.checks_count == 1


class TestReadyList:
    def test_register_enqueue_wait_roundtrip(self):
        r = ReadyList()
        assert r.register("3") is True
        assert r.on_readable("3", is_ready=True) is True
        assert r.pending == ["3"]
        assert r.wait() == ["3"]
        assert r.pending == []
        assert r.returned == ["3"]

    def test_unregistered_never_enqueued(self):
        r = ReadyList()
        assert r.on_readable("9", is_ready=True) is False
        assert r.pending == []
        assert r.wait() == []
        assert any(not e["registered"] for e in r.enqueue_log)

    def test_not_ready_socket_never_enqueued(self):
        r = ReadyList()
        r.register("3")
        assert r.on_readable("3", is_ready=False) is False
        assert r.pending == []

    def test_no_duplicate_pending(self):
        r = ReadyList()
        r.register("3")
        assert r.on_readable("3", is_ready=True) is True
        assert r.on_readable("3", is_ready=True) is False  # 已在队列中，不重复
        assert r.pending == ["3"]

    def test_duplicate_register_is_idempotent(self):
        r = ReadyList()
        assert r.register("3") is True
        assert r.register("3") is False  # 幂等：不算新注册
        assert r.interest == {"3"}

    def test_wait_returns_all_pending_once(self):
        r = ReadyList()
        for fd in ("3", "4"):
            r.register(fd)
            r.on_readable(fd, is_ready=True)
        assert r.wait() == ["3", "4"]
        assert r.wait() == []  # 清空后不再返回
