"""支付业务模型单元测试：状态机边界 + 对账修复约束。"""

import pytest

from cs_video_agent.visualkit.models_pay import Ledger, StateMachine


def _sm():
    return StateMachine(
        ["CREATED", "PAYING", "UNKNOWN", "PAID"],
        [["CREATED", "PAYING"], ["PAYING", "UNKNOWN"], ["PAYING", "PAID"],
         ["UNKNOWN", "PAID"]],
        "CREATED",
        terminal=["PAID"],
        requires_confirm=[["PAYING", "PAID"], ["UNKNOWN", "PAID"]],
    )


def test_advance_only_along_declared_edges():
    sm = _sm()
    sm.advance("PAYING")
    sm.advance("UNKNOWN")
    sm.advance("PAID", via="confirmed")
    assert sm.check_edges() == []


def test_illegal_advances_are_reported():
    sm = _sm()
    assert sm.advance("PAID") is False  # CREATED -> PAID 无边
    assert sm.current == "CREATED"
    sm.advance("PAYING")
    sm.advance("UNKNOWN")
    assert sm.advance("PAID") is False  # 缺渠道确认
    problems = sm.check_edges()
    assert len(problems) == 2
    assert "CREATED->PAID" in problems[0]
    assert "UNKNOWN->PAID" in problems[1]


def test_confirm_edges_require_channel_confirmation():
    sm = _sm()
    sm.advance("PAYING")
    assert sm.advance("PAID") is False  # 缺渠道确认：超时不等于成功
    assert sm.current == "PAYING"
    assert sm.advance("PAID", via="guess") is False
    assert sm.current == "PAYING"
    fresh = _sm()
    fresh.advance("PAYING")
    assert fresh.advance("PAID", via="confirmed") is True
    assert fresh.check_edges() == []


def test_attempt_never_changes_state():
    sm = _sm()
    sm.advance("PAYING")
    # 需确认边缺渠道确认：合法的被拒演示（返回 True = 演示成立）
    assert sm.attempt("PAID") is True
    assert sm.current == "PAYING"
    assert sm.check_attempts() == []
    sm.advance("UNKNOWN")
    assert sm.attempt("PAYING") is True  # 无边：同样是被拒演示
    assert sm.current == "UNKNOWN"
    assert sm.check_attempts() == []
    plain = StateMachine(["A", "B"], [["A", "B"]], "A")
    assert plain.attempt("B") is False  # 普通边应直接 advance，attempt 属误用
    assert len(plain.check_attempts()) == 1


def test_terminal_state_absorbs():
    sm = _sm()
    for step in (("PAYING",), ("UNKNOWN",), ("PAID", "confirmed")):
        assert sm.advance(*step) is True
    assert sm.check_terminal() == []
    # 若声明了终态出边，推进能成功但不变量必须抓住
    bad = StateMachine(["A", "B"], [["A", "B"], ["B", "A"]], "A", terminal=["B"])
    bad.advance("B")
    bad.advance("A")
    assert bad.check_terminal() != []


def test_invalid_machine_definition():
    with pytest.raises(ValueError):
        StateMachine(["A"], [["A", "A"]], "X")
    with pytest.raises(ValueError):
        StateMachine(["A"], [["A", "A"]], "A", terminal=["Z"])
    with pytest.raises(ValueError):
        StateMachine(["A", "B"], [["A", "B"]], "A", requires_confirm=[["B", "A"]])


def test_ledger_scan_classifies_rows():
    lg = Ledger([
        {"id": "1", "label": "o1", "channel": "成功", "local": "成功"},
        {"id": "2", "label": "o2", "channel": "成功", "local": "待支付"},
    ])
    res = lg.scan()
    assert [r["matched"] for r in res] == [True, False]
    assert lg.mismatched() == ["2"]


def test_ledger_fix_requires_channel_confirmation():
    lg = Ledger([
        {"id": "x", "label": "o", "channel": "无记录", "local": "待支付"},
    ])
    assert lg.fix("x", "成功") is False  # 渠道没有记录，本地不许自行标成功
    assert lg.rows["x"]["local"] == "待支付"
    assert lg.check_fix_matches_channel() != []


def test_ledger_fix_only_mismatched_and_idempotent():
    lg = Ledger([
        {"id": "1", "label": "o", "channel": "成功", "local": "待支付"},
    ])
    assert lg.fix("1", "成功") is True
    assert lg.fix("1", "成功") is False  # 已一致，再次修复应被拒绝
    assert lg.check_fix_only_mismatched() != []
    assert lg.check_fix_matches_channel() == []
