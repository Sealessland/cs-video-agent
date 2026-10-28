"""项目源（默认为模板，可替换为任意项目）的端到端静态检查：
schema、语义回放、编译、导入。项目专属的深度断言在各项目的测试文件里。"""

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
    assert lesson.segments, "lesson has no segments"
    for seg in lesson.segments:
        assert seg.misconception and seg.visual_experiment and seg.takeaway
    assert lesson.facts, "lesson has no facts"


def test_storyboard_shape(project_dir):
    _, sb = _load(project_dir)
    assert len(sb.scenes) >= 1
    assert sum(s.duration_hint for s in sb.scenes) > 0
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


def test_compile_real_storyboard_and_import(tmp_path, project_dir):
    _, sb = _load(project_dir)
    paths = compile_storyboard(sb, tmp_path)
    assert len(paths) == len(sb.scenes)
    for p in paths:
        spec = importlib.util.spec_from_file_location(p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "OBJECTS")
        assert hasattr(mod, f"Scene{getattr(mod, 'SCENE_INDEX'):02d}")
