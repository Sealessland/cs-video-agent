"""编译器测试：IR -> 生成的 Manim 场景代码。"""

import py_compile

from cs_video_agent.engine.compiler import (
    CompileError,
    class_name,
    compile_scene,
    compile_storyboard,
    validate_actions,
)
from cs_video_agent.schemas.scene_ir import (
    ActionStep,
    Beat,
    SceneIR,
    SceneObject,
    Storyboard,
)


def _mini_storyboard() -> Storyboard:
    return Storyboard(lesson_ref="lesson.json", scenes=[
        SceneIR(
            id="s1", index=1, title="mini", duration_hint=5,
            objects=[SceneObject(id="g", type="socket_grid",
                                 params={"rows": 2, "cols": 2})],
            beats=[
                Beat(id="b1", narration="开场", dwell=0.5),
                Beat(id="b2", dwell=0.4, actions=[
                    ActionStep(action="grid_mark_ready",
                               params={"grid": "g", "index": 3}),
                ]),
            ],
        )
    ])


def test_validate_actions_ok():
    assert validate_actions(_mini_storyboard()) == []


def test_validate_actions_catches_unknown():
    sb = _mini_storyboard()
    sb.scenes[0].beats[1].actions[0].action = "no_such_action"
    errs = validate_actions(sb)
    assert errs and "no_such_action" in errs[0]


def test_validate_actions_catches_missing_param():
    sb = _mini_storyboard()
    sb.scenes[0].beats[1].actions[0].params = {"grid": "g"}  # 缺 index
    errs = validate_actions(sb)
    assert any("missing" in e for e in errs)


def test_compile_scene_generates_readable_code():
    sb = _mini_storyboard()
    code = compile_scene(sb.scenes[0])
    assert "class Scene01(BaseIRScene):" in code
    assert "self.stage(OBJECTS)" in code
    assert "self.beat('b1', '开场')" in code
    assert "self.act('grid_mark_ready', **{'grid': 'g', 'index': 3})" in code
    assert "self.close_scene()" in code


def test_compile_storyboard_writes_files(tmp_path):
    sb = _mini_storyboard()
    paths = compile_storyboard(sb, tmp_path / "gen")
    assert (tmp_path / "gen" / "scene_01.py").exists()
    py_compile.compile(str(paths[0]), doraise=True)


def test_compile_storyboard_raises_on_invalid(tmp_path):
    sb = _mini_storyboard()
    sb.scenes[0].beats[1].actions[0].action = "bogus"
    try:
        compile_storyboard(sb, tmp_path)
        assert False, "should raise"
    except CompileError as e:
        assert "bogus" in str(e)


def test_class_name():
    assert class_name(_mini_storyboard().scenes[0]) == "Scene01"
