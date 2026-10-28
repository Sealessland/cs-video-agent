"""os_program_life（博客 OS 三篇合成的长视频）静态检查。"""

import importlib.util
import json

from cs_video_agent.engine.compiler import compile_storyboard, validate_actions
from cs_video_agent.engine.replay import replay_scene
from cs_video_agent.schemas.lesson import Lesson
from cs_video_agent.schemas.scene_ir import Storyboard

from tests.conftest import ROOT


def _load():
    d = ROOT / "projects" / "os_program_life"
    lesson = Lesson.model_validate(
        json.loads((d / "lesson.json").read_text(encoding="utf-8")))
    sb = Storyboard.model_validate(
        json.loads((d / "storyboard.json").read_text(encoding="utf-8")))
    return d, lesson, sb


def test_lesson_facts_and_segments():
    _, lesson, _ = _load()
    assert len(lesson.facts) >= 6
    for seg in lesson.segments:
        assert seg.misconception and seg.visual_experiment and seg.takeaway


def test_storyboard_shape():
    _, _, sb = _load()
    assert len(sb.scenes) == 6
    lo, hi = 170, 250
    total = sum(s.duration_hint for s in sb.scenes)
    assert lo <= total <= hi, f"durations {total} outside [{lo},{hi}]"
    assert validate_actions(sb) == []


def test_semantic_replay():
    _, _, sb = _load()
    for sc in sb.scenes:
        r = replay_scene(sc)
        assert r["ok"], f"{sc.id}: {r['violations']}"
    # scene_2 结束时应处于执行视图
    r2 = replay_scene(sb.scenes[1])
    assert r2["summary"]["elf_view"]["elf"] == "exec"
    # scene_4：libc 与 heap 各分配了物理页，gap 触发 segv
    r4 = replay_scene(sb.scenes[3])
    assert sorted(r4["summary"]["physical"]["space"]) == ["heap", "libc"]
    # scene_5：open 建了 2 个实例（fd3/4 共享 + fd5）
    r5 = replay_scene(sb.scenes[4])
    assert r5["summary"]["fd_instances"]["table"] == 2


def test_compile_and_import(tmp_path):
    d, _, sb = _load()
    paths = compile_storyboard(sb, tmp_path)
    assert len(paths) == 6
    for p in paths:
        spec = importlib.util.spec_from_file_location(p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
