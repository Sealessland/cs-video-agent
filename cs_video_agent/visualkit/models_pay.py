"""支付业务纯状态模型：订单状态机 + 对账台账。

对应 payment_incident 的技术事实，全部不依赖 Manim，可独立回放验证：
- 订单状态只能沿声明的边推进；终态吸收一切后续推进；
  「被拒绝的非法转移」必须用 attempt 表达（attempt 永不改状态）
- 对账修复只允许发生在「渠道与本地不一致」的行上，
  且修复目标状态必须与渠道侧一致——渠道是权威，本地愿望不是
"""

from cs_video_agent.visualkit.models import LogEntry

SUPPORTED_PAY_INVARIANTS = {
    "state_moves_follow_declared_edges",
    "terminal_state_is_absorbing",
    "attempts_are_always_rejected",
    "ledger_fix_only_mismatched",
    "ledger_fix_matches_channel",
}


class StateMachine:
    """订单/支付状态机。

    - advance 沿声明边推进；标记在 requires_confirm 里的边还必须携带
      via="confirmed"（渠道确认）才被接受——超时本身不是确认。
    - attempt 演示注定被拒绝的推进（缺确认的需确认边，或无边），绝不改状态；
      落在普通合法边上的 attempt 属于误用，会被 check_attempts 抓住。
    """

    def __init__(self, states, transitions, initial, terminal=None,
                 requires_confirm=None):
        self.states = [str(s) for s in states]
        self.edges = {(str(a), str(b)) for a, b in (transitions or [])}
        self.confirm_edges = {(str(a), str(b)) for a, b in (requires_confirm or [])}
        unknown_c = self.confirm_edges - self.edges
        if unknown_c:
            raise ValueError(f"requires_confirm edges {sorted(unknown_c)} not declared")
        self.initial = str(initial)
        self.terminal = {str(s) for s in (terminal or [])}
        if self.initial not in self.states:
            raise ValueError(f"initial {self.initial!r} not in states {self.states}")
        unknown_t = self.terminal - set(self.states)
        if unknown_t:
            raise ValueError(f"terminal {sorted(unknown_t)} not in states")
        self.current = self.initial
        self.log: list[LogEntry] = []
        self._step = 0

    def _rec(self, op, ok, **detail) -> None:
        self.log.append(LogEntry(self._step, op, ok, detail))
        self._step += 1

    def advance(self, to, via=None) -> bool:
        """沿声明边推进；需确认的边必须 via="confirmed"。非法移动不动状态。"""
        frm = self.current
        to = str(to)
        ok = (frm, to) in self.edges and (
            (frm, to) not in self.confirm_edges or via == "confirmed"
        )
        if ok:
            self.current = to
        self._rec("advance", ok, frm=frm, to=to, via=via)
        return ok

    def attempt(self, to) -> bool:
        """演示一次注定被拒绝的推进：绝不改状态。

        被拒的合法演示 = 缺确认的需确认边，或根本无边；
        普通合法边上的 attempt 是误用（应该直接 advance）。
        """
        frm = self.current
        to = str(to)
        edge = (frm, to) in self.edges
        misuse = edge and (frm, to) not in self.confirm_edges
        self._rec("attempt", not misuse, frm=frm, to=to)
        return not misuse

    def check_edges(self) -> list[str]:
        return [
            f"illegal advance {e.detail['frm']}->{e.detail['to']}"
            + (f" (via={e.detail['via']!r})" if e.detail.get("via") else "")
            for e in self.log if e.op == "advance" and not e.ok
        ]

    def check_terminal(self) -> list[str]:
        return [
            f"move out of terminal state {e.detail['frm']} (to {e.detail['to']})"
            for e in self.log
            if e.op == "advance" and e.ok and e.detail["frm"] in self.terminal
        ]

    def check_attempts(self) -> list[str]:
        return [
            f"attempt on plain edge {e.detail['frm']}->{e.detail['to']}; use advance"
            for e in self.log if e.op == "attempt" and not e.ok
        ]


class Ledger:
    """T+1 对账台账：每行有 channel（渠道账单，权威）与 local（本地流水）两个状态。"""

    def __init__(self, rows):
        self.rows: dict[str, dict] = {}
        for r in rows or []:
            rid = str(r["id"])
            self.rows[rid] = {
                "label": str(r.get("label", rid)),
                "channel": str(r["channel"]),
                "local": str(r["local"]),
            }
        self.log: list[LogEntry] = []
        self._step = 0

    def _rec(self, op, ok, **detail) -> None:
        self.log.append(LogEntry(self._step, op, ok, detail))
        self._step += 1

    def mismatched(self) -> list[str]:
        return [rid for rid, r in self.rows.items() if r["channel"] != r["local"]]

    def scan(self) -> list[dict]:
        out = []
        for rid, r in self.rows.items():
            entry = {"row": rid, "matched": r["channel"] == r["local"]}
            out.append(entry)
            self._rec("scan", True, row=rid, matched=entry["matched"])
        return out

    def fix(self, rid, to) -> bool:
        """把本地状态补成 to：仅当行确实不一致，且 to 与渠道一致（渠道确认）。"""
        rid = str(rid)
        r = self.rows[rid]
        to = str(to)
        mismatched = r["channel"] != r["local"]
        confirmed = to == r["channel"]
        ok = mismatched and confirmed
        before = r["local"]
        if ok:
            r["local"] = to
        self._rec("fix", ok, row=rid, claimed=to, channel=r["channel"],
                  local_before=before, local_after=r["local"])
        return ok

    def check_fix_only_mismatched(self) -> list[str]:
        return [
            f"fix on matched row {e.detail['row']} (local already {e.detail['local_after']!r})"
            for e in self.log
            if e.op == "fix" and e.detail["local_before"] == e.detail["channel"]
        ]

    def check_fix_matches_channel(self) -> list[str]:
        return [
            f"fix row {e.detail['row']} claimed {e.detail['claimed']!r} "
            f"but channel says {e.detail['channel']!r}"
            for e in self.log if e.op == "fix" and e.detail["claimed"] != e.detail["channel"]
        ]
