"""语义回放：不渲染任何画面，把 Scene IR 的动作序列重放到纯 Model 上，
验证状态转移与场景声明的 invariants。

这是「先验证计算机原理，再生成动画代码」的确定性关卡。
"""

from cs_video_agent.schemas.scene_ir import SceneIR
from cs_video_agent.visualkit.models import (
    SUPPORTED_INVARIANTS,
    ReadyList,
    SocketSet,
    socket_grid_ids,
    socket_stack_ids,
)
from cs_video_agent.visualkit.models_os import (
    AddrSpaceModel,
    ElfFileModel,
    FdTableModel,
)
from cs_video_agent.visualkit.models_pay import (
    SUPPORTED_PAY_INVARIANTS,
    Ledger,
    StateMachine,
)

_KNOWN_INVARIANTS = SUPPORTED_INVARIANTS | SUPPORTED_PAY_INVARIANTS | {
    "exec_view_groups_sections_into_segments",
    "va_layout_code_low_stack_high",
    "lazy_alloc_on_first_touch",
    "segv_only_outside_vma",
    "dup_shares_offset",
    "open_creates_independent_instance",
    "fork_shares_file_instances",
}


def _socket_models(scene: SceneIR) -> dict[str, SocketSet]:
    models: dict[str, SocketSet] = {}
    for obj in scene.objects:
        if obj.type == "socket_grid":
            rows = obj.params.get("rows", 10)
            cols = obj.params.get("cols", 10)
            models[obj.id] = SocketSet(socket_grid_ids(obj.id, rows, cols))
        elif obj.type == "socket_stack":
            models[obj.id] = SocketSet(socket_stack_ids(obj.params.get(
                "fds", ["3", "4", "5", "6", "7"])))
    return models


def _grid_ids_of(scene: SceneIR, grid_id: str) -> list[str]:
    for obj in scene.objects:
        if obj.id == grid_id:
            if obj.type == "socket_grid":
                return socket_grid_ids(grid_id, obj.params.get("rows", 10),
                                       obj.params.get("cols", 10))
            if obj.type == "socket_stack":
                return socket_stack_ids(obj.params.get("fds", ["3", "4", "5", "6", "7"]))
    raise KeyError(f"no socket object {grid_id!r} in scene {scene.id}")


def replay_scene(scene: SceneIR) -> dict:
    sockets = _socket_models(scene)
    ready = ReadyList()
    elf_files = {o.id: ElfFileModel(o.params.get("sections"), o.params.get("segments"))
                 for o in scene.objects if o.type == "elf_file"}
    spaces = {o.id: AddrSpaceModel() for o in scene.objects if o.type == "addr_space"}
    tables = {o.id: FdTableModel() for o in scene.objects if o.type == "fd_table"}
    strips = {
        o.id: StateMachine(o.params.get("states"), o.params.get("transitions"),
                           o.params.get("initial"), o.params.get("terminal"),
                           o.params.get("requires_confirm"))
        for o in scene.objects if o.type == "state_strip"
    }
    ledgers = {o.id: Ledger(o.params.get("rows"))
               for o in scene.objects if o.type == "ledger"}
    runtime_errors: list[str] = []
    scan_counts: dict[str, int] = {k: 0 for k in sockets}
    checks_at_scan_start: dict[str, int] = {k: 0 for k in sockets}

    def is_ready_any(fd: str) -> bool | None:
        for m in sockets.values():
            if fd in m.ids:
                return m.is_ready(fd)
        return None

    for beat in scene.beats:
        for a in beat.actions:
            n, p = a.action, a.params
            if n == "grid_mark_ready":
                sid = _grid_ids_of(scene, p["grid"])[int(p["index"])]
                sockets[p["grid"]].mark_ready(sid)
            elif n == "stack_mark_ready":
                sockets[p["stack"]].mark_ready(str(p["fd"]))
            elif n == "grid_scan":
                gid = p["grid"]
                checks_at_scan_start[gid] = sockets[gid].checks_count
                for sid in _grid_ids_of(scene, gid):
                    sockets[gid].check(sid)
                scan_counts[gid] += 1
            elif n == "flow_register":
                for fd in p["fds"]:
                    ready.register(str(fd))
            elif n == "flow_emit":
                fd = str(p["fd"])
                for m in sockets.values():
                    if fd in m.ids:
                        m.mark_ready(fd)
            elif n == "queue_enqueue":
                fd = str(p["fd"])
                ready.on_readable(fd, is_ready=is_ready_any(fd))
            elif n == "queue_pop":
                ready.wait()
            elif n == "elf_layout":
                if not elf_files[p["file"]].switch_view(p["view"]):
                    runtime_errors.append(f"elf_layout bad view {p['view']!r}")
            elif n == "elf_highlight" or n == "mem_grow":
                pass  # 纯视觉强调
            elif n == "mem_map":
                if not spaces[p["space"]].map_region(p["region"]):
                    runtime_errors.append(f"mem_map invalid region {p['region']!r}")
            elif n == "mem_touch":
                spaces[p["space"]].touch(p["region"])
            elif n == "fd_open":
                tables[p["table"]].open(int(p["fd"]), p["label"])
            elif n == "fd_dup":
                if not tables[p["table"]].dup(int(p["src"]), int(p["dst"])):
                    runtime_errors.append(f"fd_dup src {p['src']} 未打开")
            elif n == "fd_read":
                off = tables[p["table"]].read(int(p["fd"]),
                                              int(p.get("bytes", 128)),
                                              p.get("who", "parent"))
                if off is None:
                    runtime_errors.append(f"fd_read {p['fd']} ({p.get('who')}) 未打开")
            elif n == "fd_fork":
                if not tables[p["table"]].fork():
                    runtime_errors.append("fd_fork 重复 fork")
            elif n == "state_advance":
                m = strips[p["strip"]]
                if not m.advance(str(p["to"]), via=p.get("via")):
                    runtime_errors.append(
                        f"state_advance {p['to']!r} 不可达（当前 {m.current!r}）")
            elif n == "state_attempt":
                strips[p["strip"]].attempt(str(p["to"]))
            elif n == "ledger_scan":
                ledgers[p["ledger"]].scan()
            elif n == "ledger_fix":
                m = ledgers[p["ledger"]]
                if not m.fix(str(p["row"]), str(p["to"])):
                    runtime_errors.append(
                        f"ledger_fix row={p['row']!r} to={p['to']!r} 被拒绝"
                        f"（渠道值 {m.rows[str(p['row'])]['channel']!r}）")
            # 文本/worker 动作不影响语义状态

    violations: list[str] = list(runtime_errors)
    for inv in scene.invariants:
        if inv not in _KNOWN_INVARIANTS:
            violations.append(f"unsupported invariant {inv!r}")

    if "only_ready_sockets_are_returned" in scene.invariants:
        accepted_ready = {e["fd"] for e in ready.enqueue_log
                          if e["accepted"] and e["ready"]}
        bad = [fd for fd in ready.returned if fd not in accepted_ready]
        if bad:
            violations.append(f"returned fds never enqueued-as-ready: {bad}")
        not_ready = [e["fd"] for e in ready.enqueue_log if e["accepted"] and not e["ready"]]
        if not_ready:
            violations.append(f"enqueued while socket not ready: {not_ready}")

    if "unregistered_sockets_never_enqueued" in scene.invariants:
        attempted = [e["fd"] for e in ready.enqueue_log if not e["registered"]]
        if attempted:
            violations.append(f"enqueue attempted for unregistered fds: {attempted}")

    if "ready_list_no_duplicates" in scene.invariants:
        for entry in ready.log:
            if entry.op == "wait" and len(set(entry.detail.get("returned", []))) != len(
                    entry.detail.get("returned", [])):
                violations.append(f"duplicate fds in one wait(): {entry.detail}")

    if "scan_checks_every_socket" in scene.invariants:
        for gid, m in sockets.items():
            if scan_counts[gid]:
                expected = len(m.ids) * scan_counts[gid]
                if m.checks_count != expected:
                    violations.append(
                        f"{gid}: checks {m.checks_count} != {expected} "
                        f"(sockets x scans)")

    if "exec_view_groups_sections_into_segments" in scene.invariants:
        for oid, m in elf_files.items():
            for prob in m.check_grouping():
                violations.append(f"{oid}: {prob}")
    if "va_layout_code_low_stack_high" in scene.invariants:
        for oid, m in spaces.items():
            violations += [f"{oid}: {p}" for p in m.check_layout()]
    if "lazy_alloc_on_first_touch" in scene.invariants:
        for oid, m in spaces.items():
            violations += [f"{oid}: {p}" for p in m.check_lazy()]
    if "segv_only_outside_vma" in scene.invariants:
        for oid, m in spaces.items():
            violations += [f"{oid}: {p}" for p in m.check_segv()]
    if "dup_shares_offset" in scene.invariants:
        for oid, m in tables.items():
            violations += [f"{oid}: {p}" for p in m.check_dup_shares()]
    if "open_creates_independent_instance" in scene.invariants:
        for oid, m in tables.items():
            violations += [f"{oid}: {p}" for p in m.check_open_independent()]
    if "fork_shares_file_instances" in scene.invariants:
        for oid, m in tables.items():
            violations += [f"{oid}: {p}" for p in m.check_fork_shares()]

    if "state_moves_follow_declared_edges" in scene.invariants:
        for oid, m in strips.items():
            violations += [f"{oid}: {v}" for v in m.check_edges()]
    if "terminal_state_is_absorbing" in scene.invariants:
        for oid, m in strips.items():
            violations += [f"{oid}: {v}" for v in m.check_terminal()]
    if "attempts_are_always_rejected" in scene.invariants:
        for oid, m in strips.items():
            violations += [f"{oid}: {v}" for v in m.check_attempts()]
    if "ledger_fix_only_mismatched" in scene.invariants:
        for oid, m in ledgers.items():
            violations += [f"{oid}: {v}" for v in m.check_fix_only_mismatched()]
    if "ledger_fix_matches_channel" in scene.invariants:
        for oid, m in ledgers.items():
            violations += [f"{oid}: {v}" for v in m.check_fix_matches_channel()]

    return {
        "scene_id": scene.id,
        "ok": not violations,
        "violations": violations,
        "summary": {
            "checks_total": sum(m.checks_count for m in sockets.values()),
            "registered": sorted(ready.interest),
            "returned": list(ready.returned),
            "pending": list(ready.pending),
            "elf_view": {k: v.view for k, v in elf_files.items()},
            "vmas": {k: v.vmas for k, v in spaces.items()},
            "physical": {k: sorted(v.physical) for k, v in spaces.items()},
            "fd_instances": {k: len(v.instances) for k, v in tables.items()},
            "states": {k: v.current for k, v in strips.items()},
            "ledger_mismatch": {k: v.mismatched() for k, v in ledgers.items()},
        },
    }
