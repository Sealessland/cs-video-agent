"""OS 组件动作：ELF 双视图、地址空间（map/touch/grow）、fd 表（open/dup/read/fork）。

约定不变：动作先落到视图绑定的 Model 上，再把状态变化解释为动画。
"""

from cs_video_agent.visualkit.views.util import resolve_color

HANDLERS = {}
SPECS = {}

_DESC = {
    "elf_layout": "ELF 文件在链接视图(Section)/执行视图(Segment)间切换（morph）",
    "elf_highlight": "圈选强调 ELF 头或某个 section",
    "mem_map": "mmap：在 VA 上登记一个新 VMA（如 libc），不交付物理页",
    "mem_touch": "访存：缺页则点亮一个物理页；无 VMA 则 SIGSEGV",
    "mem_grow": "堆/栈生长（brk/栈扩展）",
    "fd_open": "open：新建内核对象实例并连线 fd",
    "fd_dup": "dup：新 fd 连向同一实例（共享 f_pos）",
    "fd_read": "read：脉冲沿连线推进实例的 f_pos（who=child 演示 fork 共享）",
    "fd_fork": "fork：生成子进程 fd 表副本，连线到同一组实例",
    "flow_pulse": "沿指定箭头发光脉冲（通用数据流强调）；label=随行的文字标签（如 查询/回调/重复投递）",
}


def _reg(name, required=(), optional=()):
    def deco(fn):
        HANDLERS[name] = fn
        SPECS[name] = {"required": list(required), "optional": list(optional)}
        return fn
    return deco


@_reg("flow_pulse", required=["flow", "arrow"],
      optional=["color", "run_time", "label"])
def flow_pulse(scene, p):
    flow = scene.ctx.objects[p["flow"]]
    flow.pulse(scene, p["arrow"],
               color=resolve_color(p["color"]) if p.get("color") else None,
               run_time=float(p.get("run_time", 0.7)),
               label=p.get("label"))


@_reg("elf_layout", required=["file", "view"])
def elf_layout(scene, p):
    view = scene.ctx.objects[p["file"]]
    view.switch_view(scene, p["view"])


@_reg("elf_highlight", required=["file", "key"])
def elf_highlight(scene, p):
    view = scene.ctx.objects[p["file"]]
    scene.play(view.highlight(p["key"]), run_time=0.9)


@_reg("mem_map", required=["space", "region"])
def mem_map(scene, p):
    view = scene.ctx.objects[p["space"]]
    view.map_region(scene, p["region"])


@_reg("mem_touch", required=["space", "region"])
def mem_touch(scene, p):
    view = scene.ctx.objects[p["space"]]
    view.touch(scene, p["region"])


@_reg("mem_grow", required=["space", "region"], optional=["factor"])
def mem_grow(scene, p):
    view = scene.ctx.objects[p["space"]]
    view.grow(scene, p["region"], float(p.get("factor", 1.45)))


@_reg("fd_open", required=["table", "fd", "label"])
def fd_open(scene, p):
    view = scene.ctx.objects[p["table"]]
    view.open(scene, str(p["fd"]), p["label"])


@_reg("fd_dup", required=["table", "src", "dst"])
def fd_dup(scene, p):
    view = scene.ctx.objects[p["table"]]
    view.dup(scene, str(p["src"]), str(p["dst"]))


@_reg("fd_read", required=["table", "fd"], optional=["bytes", "who"])
def fd_read(scene, p):
    view = scene.ctx.objects[p["table"]]
    view.read(scene, str(p["fd"]), int(p.get("bytes", 128)), p.get("who", "parent"))


@_reg("fd_fork", required=["table"])
def fd_fork(scene, p):
    view = scene.ctx.objects[p["table"]]
    view.fork(scene)
