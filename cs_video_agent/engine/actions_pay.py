"""支付业务动作：状态机推进 / 被拒尝试演示 / 对账扫描与修复。

约定与 actions_net 相同：动作先落在视图绑定的 Model 上
（StateMachine / Ledger），再把状态变化解释为动画。
"""

HANDLERS = {}
SPECS = {}


def _reg(name, required=(), optional=()):
    def deco(fn):
        HANDLERS[name] = fn
        SPECS[name] = {"required": list(required), "optional": list(optional)}
        return fn
    return deco


_DESC = {
    "state_advance": "订单状态沿声明边推进（需确认边须带 via=confirmed，脉冲点亮目标徽章）",
    "state_attempt": "演示一次注定被拒绝的推进（缺渠道确认/无边：红色提示，状态不变）",
    "ledger_scan": "对账扫描：逐行标记 一致/差异",
    "ledger_fix": "对账修复：以渠道为准补齐本地状态（row/to）",
}


@_reg("state_advance", required=["strip", "to"], optional=["run_time", "via"])
def state_advance(scene, p):
    view = scene.ctx.objects[p["strip"]]
    view.advance(scene, str(p["to"]), via=p.get("via"),
                 run_time=float(p.get("run_time", 1.3)))


@_reg("state_attempt", required=["strip", "to"], optional=["run_time"])
def state_attempt(scene, p):
    view = scene.ctx.objects[p["strip"]]
    view.attempt(scene, str(p["to"]),
                 run_time=float(p.get("run_time", 1.2)))


@_reg("ledger_scan", required=["ledger"], optional=["run_time"])
def ledger_scan(scene, p):
    view = scene.ctx.objects[p["ledger"]]
    view.scan(scene, run_time=float(p.get("run_time", 1.8)))


@_reg("ledger_fix", required=["ledger", "row", "to"], optional=["run_time"])
def ledger_fix(scene, p):
    view = scene.ctx.objects[p["ledger"]]
    view.fix(scene, str(p["row"]), str(p["to"]),
             run_time=float(p.get("run_time", 1.4)))
