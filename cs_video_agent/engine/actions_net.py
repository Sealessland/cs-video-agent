"""网格/连接/内核/队列/工作进程动作。

约定：动作先落在视图绑定的 Model 上（SocketSet / ReadyList），
再把状态变化解释为动画，画面永远不先于语义。
"""

from cs_video_agent.visualkit.views.util import resolve_color

HANDLERS = {}
SPECS = {}


def _reg(name, required=(), optional=()):
    def deco(fn):
        HANDLERS[name] = fn
        SPECS[name] = {"required": list(required), "optional": list(optional)}
        return fn
    return deco


_DESC = {
    "grid_mark_ready": "网格中第 index 个连接变就绪（subtle=true 低饱和提示）",
    "grid_pulse": "圈选强调网格中某个连接",
    "grid_dim_except": "除 keep 列表外全部压暗（聚焦）",
    "grid_scan": "扫描波逐个检查全部连接（select/poll 隐喻），就绪者保持高亮",
    "stack_mark_ready": "fd 堆栈中某连接变就绪",
    "flow_register": "把 fds 依次注册进内核 interest list（chip 飞入）",
    "flow_emit": "数据到达：socket 就绪 -> 沿箭头发光脉冲 -> 内核徽章闪烁",
    "queue_enqueue": "就绪事件入队（fd 徽章从 from 锚点飞入队列）",
    "queue_pop": "队头出队，飞向 to 锚点（epoll_wait 返回）",
    "worker_state": "更新应用框状态文字",
    "worker_receive": "应用框闪烁（收到就绪 fd）",
    "box_reveal": "逐条显示 worker 框的职责条目与微缩示意（items/mini）",
}


def _color(p):
    return resolve_color(p["color"]) if p.get("color") else None


@_reg("grid_mark_ready", required=["grid", "index"], optional=["subtle"])
def grid_mark_ready(scene, p):
    view = scene.ctx.objects[p["grid"]]
    scene.play(*view.mark_ready(int(p["index"]), bool(p.get("subtle", False))),
               run_time=0.8)


@_reg("grid_pulse", required=["grid", "index"], optional=["color"])
def grid_pulse(scene, p):
    view = scene.ctx.objects[p["grid"]]
    scene.play(view.pulse(int(p["index"]), _color(p)), run_time=0.9)


@_reg("grid_dim_except", required=["grid", "keep"])
def grid_dim_except(scene, p):
    view = scene.ctx.objects[p["grid"]]
    anims = view.dim_except([int(k) for k in p["keep"]])
    if anims:
        scene.play(*anims, run_time=0.8)


@_reg("grid_scan", required=["grid"], optional=["run_time"])
def grid_scan(scene, p):
    view = scene.ctx.objects[p["grid"]]
    view.scan(scene, float(p.get("run_time", 4.0)))


@_reg("stack_mark_ready", required=["stack", "fd"], optional=["subtle"])
def stack_mark_ready(scene, p):
    view = scene.ctx.objects[p["stack"]]
    scene.play(*view.mark_ready(str(p["fd"]), bool(p.get("subtle", False))),
               run_time=0.8)


@_reg("flow_register", required=["kernel", "stack", "fds"])
def flow_register(scene, p):
    kernel = scene.ctx.objects[p["kernel"]]
    stack = scene.ctx.objects[p["stack"]]
    for fd in p["fds"]:
        kernel.register_chip(scene, str(fd), stack.anchor(str(fd)))


@_reg("flow_emit", required=["flow", "arrow", "stack", "fd", "kernel"],
      optional=["pulse_run_time"])
def flow_emit(scene, p):
    stack = scene.ctx.objects[p["stack"]]
    scene.play(*stack.mark_ready(str(p["fd"])), run_time=0.5)
    scene.play(stack.pulse(str(p["fd"])), run_time=0.6)
    flow = scene.ctx.objects[p["flow"]]
    flow.pulse(scene, p["arrow"], run_time=float(p.get("pulse_run_time", 0.7)))
    kernel = scene.ctx.objects[p["kernel"]]
    kernel.callback_flash(scene, str(p["fd"]))


@_reg("queue_enqueue", required=["queue", "fd", "from"])
def queue_enqueue(scene, p):
    view = scene.ctx.objects[p["queue"]]
    view.enqueue(scene, str(p["fd"]), scene.ctx.anchor(p["from"]))


@_reg("queue_pop", required=["queue", "to"])
def queue_pop(scene, p):
    view = scene.ctx.objects[p["queue"]]
    view.pop(scene, scene.ctx.anchor(p["to"]))


@_reg("worker_state", required=["worker", "text"], optional=["color"])
def worker_state(scene, p):
    w = scene.ctx.objects[p["worker"]]
    w.set_state(scene, p["text"], _color(p))


@_reg("worker_receive", required=["worker"], optional=["color"])
def worker_receive(scene, p):
    w = scene.ctx.objects[p["worker"]]
    w.flash(scene, _color(p))


@_reg("box_reveal", required=["worker"])
def box_reveal(scene, p):
    w = scene.ctx.objects[p["worker"]]
    w.reveal(scene)
