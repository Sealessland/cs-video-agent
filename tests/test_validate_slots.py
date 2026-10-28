"""槽位重叠静态检测的单元测试：用真实踩过的布局坑做用例。"""

from cs_video_agent.engine.validate_slots import validate_slots
from cs_video_agent.schemas.scene_ir import SceneIR, Beat, ActionStep, Storyboard


def _scene(beats, invariants=None):
    return SceneIR(id="s", index=1, title="t", duration_hint=10,
                   objects=[], beats=beats,
                   invariants=invariants or [])


def _beat(bid, *actions, dwell=0.5, narration=None):
    steps = []
    for entry in actions:
        act = entry[0]
        params = entry[1] if len(entry) > 1 else {}
        steps.append(ActionStep(action=act, params=params))
    return Beat(id=bid, narration=narration, dwell=dwell, actions=steps)


def _sb(scene):
    return Storyboard(lesson_ref="lesson.json", scenes=[scene])


def test_leftover_card_under_question_is_flagged():
    scene = _scene([
        _beat("b1", ("show_card", {"id": "c1", "text": "左卡", "at": "left"})),
        _beat("b2", ("show_question", {"text": "这笔支付成功了吗？"})),
    ])
    errors = validate_slots(_sb(scene))
    assert any("c1" in e and "question" in e for e in errors), errors


def test_metric_over_title_is_flagged():
    scene = _scene([
        _beat("b1", ("show_title", {"text": "Go 服务内部",
                                    "sub": "路由 → Handler → goroutine"})),
        _beat("b2", ("show_metric", {"id": "g", "text": "后台 goroutine：512,038",
                                     "width": 5.6})),
    ])
    errors = validate_slots(_sb(scene))
    assert any("g" in e and "title" in e for e in errors), errors


def test_short_ascii_title_with_default_metric_is_clean():
    # epoll 老场景形态：ASCII 标题 + 短 metric（默认宽度）不应误报
    scene = _scene([
        _beat("b1", ("show_title", {"text": "select / poll",
                                    "sub": "每次调用，检查所有连接"})),
        _beat("b2", ("show_metric", {"id": "checks", "text": "检查：0 个"})),
    ])
    assert validate_slots(_sb(scene)) == []


def test_takeaway_over_leftover_card_is_flagged():
    scene = _scene([
        _beat("b1", ("show_card", {"id": "why", "text": " why", "at": "left"})),
        _beat("b2", ("show_card", {"id": "cb", "text": "cb", "at": "center"})),
        _beat("b3", ("show_takeaway", {"text": "结论"})),
    ])
    errors = validate_slots(_sb(scene))
    assert errors, "takeaway 压住残留卡必须报错"


def test_fade_then_show_is_clean():
    scene = _scene([
        _beat("b1", ("show_card", {"id": "c1", "text": "x", "at": "left"})),
        _beat("b2", ("fade_slot", {"id": "c1"}),
              ("show_question", {"text": "问题"})),
        _beat("b3", ("fade_question",), ("show_takeaway", {"text": "结论"})),
    ])
    assert validate_slots(_sb(scene)) == []


def test_three_side_by_side_cards_fit():
    scene = _scene([
        _beat("b1",
              ("show_card", {"id": "a", "text": "左", "at": "left", "width": 3.9}),
              ("show_card", {"id": "b", "text": "中", "at": "center", "width": 4.0}),
              ("show_card", {"id": "c", "text": "右", "at": "right", "width": 4.6})),
    ])
    assert validate_slots(_sb(scene)) == []
