"""真实 storyboard 的端到端静态检查：schema、语义回放、编译、导入。"""

import importlib.util
import json

from cs_video_agent.engine.compiler import compile_storyboard, validate_actions
from cs_video_agent.engine.replay import replay_scene
from cs_video_agent.schemas.lesson import Lesson
from cs_video_agent.schemas.scene_ir import Storyboard
from cs_video_agent.visualkit.models import SUPPORTED_INVARIANTS


def _load(project_dir):
    lesson = Lesson.model_validate(
        json.loads((project_dir / "lesson.json").read_text(encoding="utf-8")))
    sb = Storyboard.model_validate(
        json.loads((project_dir / "storyboard.json").read_text(encoding="utf-8")))
    return lesson, sb


def test_lesson_segments_have_pedagogy_fields(project_dir):
    lesson, _ = _load(project_dir)
    assert len(lesson.segments) >= 3
    for seg in lesson.segments:
        assert seg.misconception and seg.visual_experiment and seg.takeaway
    assert len(lesson.facts) >= 4


def test_storyboard_shape(project_dir):
    _, sb = _load(project_dir)
    assert len(sb.scenes) == 3
    total = sum(s.duration_hint for s in sb.scenes)
    lo, hi = 55, 95
    assert lo <= total <= hi, f"duration hints sum {total} outside [{lo},{hi}]"
    for sc in sb.scenes:
        assert sc.beats, f"{sc.id} has no beats"
        unknown = set(sc.invariants) - SUPPORTED_INVARIANTS
        assert not unknown, f"{sc.id} unknown invariants {unknown}"


def test_actions_all_valid(project_dir):
    _, sb = _load(project_dir)
    assert validate_actions(sb) == []


def test_semantic_replay_invariants(project_dir):
    _, sb = _load(project_dir)
    for sc in sb.scenes:
        r = replay_scene(sc)
        assert r["ok"], f"{sc.id}: {r['violations']}"
    # scene_2 必须真的扫了两遍全部 100 个连接
    r2 = replay_scene(sb.scenes[1])
    assert r2["summary"]["checks_total"] == 200
    # scene_3 必须只返回 fd 5
    r3 = replay_scene(sb.scenes[2])
    assert r3["summary"]["returned"] == ["5"]
    assert r3["summary"]["registered"] == ["3", "4", "5", "6", "7"]


def test_compile_real_storyboard_and_import(tmp_path, project_dir):
    _, sb = _load(project_dir)
    paths = compile_storyboard(sb, tmp_path)
    assert len(paths) == 3
    for p in paths:
        spec = importlib.util.spec_from_file_location(p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "OBJECTS")
        assert hasattr(mod, f"Scene{getattr(mod, 'SCENE_INDEX'):02d}")
