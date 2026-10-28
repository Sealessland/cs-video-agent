"""payment_incident（支付超时事故全链路）静态检查。"""

import importlib.util
import json

from cs_video_agent.engine.compiler import compile_storyboard, validate_actions
from cs_video_agent.engine.replay import replay_scene, _KNOWN_INVARIANTS
from cs_video_agent.schemas.lesson import Lesson
from cs_video_agent.schemas.scene_ir import Storyboard

from tests.conftest import ROOT


def _load():
    d = ROOT / "projects" / "payment_incident"
    lesson = Lesson.model_validate(
        json.loads((d / "lesson.json").read_text(encoding="utf-8")))
    sb = Storyboard.model_validate(
        json.loads((d / "storyboard.json").read_text(encoding="utf-8")))
    return d, lesson, sb


def test_lesson_facts_and_segments():
    _, lesson, _ = _load()
    assert len(lesson.facts) >= 8
    for seg in lesson.segments:
        assert seg.misconception and seg.visual_experiment and seg.takeaway


def test_storyboard_shape():
    _, _, sb = _load()
    assert len(sb.scenes) == 17
    total = sum(s.duration_hint for s in sb.scenes)
    assert 580 <= total <= 860, f"durations {total} outside [580,860]"
    for sc in sb.scenes:
        assert sc.beats, f"{sc.id} has no beats"
        unknown = set(sc.invariants) - _KNOWN_INVARIANTS
        assert not unknown, f"{sc.id} unknown invariants {unknown}"


def test_actions_all_valid():
    _, _, sb = _load()
    assert validate_actions(sb) == []


def test_semantic_replay():
    _, _, sb = _load()
    for sc in sb.scenes:
        r = replay_scene(sc)
        assert r["ok"], f"{sc.id}: {r['violations']}"
    # scene_13：直接把 PAYING 标 PAID 的 attempt 被拒后，经渠道确认推进到 PAID
    r13 = replay_scene(sb.scenes[12])
    assert r13["summary"]["states"] == {"strip": "PAID"}
    # scene_6：三色标记 白→灰→黑 顺序推进
    r6 = replay_scene(sb.scenes[5])
    assert r6["summary"]["states"] == {"colors": "黑"}
    # scene_16：对账修复后差异清零，订单从 UNKNOWN 推进到 PAID
    r16 = replay_scene(sb.scenes[15])
    assert r16["summary"]["states"] == {"strip": "PAID"}
    assert r16["summary"]["ledger_mismatch"] == {"ledger": []}


def test_compile_and_import(tmp_path):
    _, _, sb = _load()
    paths = compile_storyboard(sb, tmp_path)
    assert len(paths) == 17
    for p in paths:
        spec = importlib.util.spec_from_file_location(p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "OBJECTS")
        assert hasattr(mod, f"Scene{getattr(mod, 'SCENE_INDEX'):02d}")
