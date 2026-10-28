"""Scene Compiler：Storyboard(IR) -> 可读的 Manim 场景代码（gen/scene_NN.py）。

生成物是普通 Python 文件：可读、可单独渲染、可 diff。
修改 storyboard 后重新编译即可，不手改生成文件。
"""

import pprint
from pathlib import Path

from cs_video_agent.engine.actions import ACTION_SPECS
from cs_video_agent.schemas.scene_ir import SceneIR, Storyboard


class CompileError(Exception):
    pass


def class_name(scene: SceneIR) -> str:
    return f"Scene{scene.index:02d}"


def gen_filename(scene: SceneIR) -> str:
    return f"scene_{scene.index:02d}.py"


def validate_actions(storyboard: Storyboard) -> list[str]:
    """检查每个动作的名字 / 必选参数 / 未知参数。"""
    errors = []
    for sc in storyboard.scenes:
        for b in sc.beats:
            for a in b.actions:
                spec = ACTION_SPECS.get(a.action)
                if spec is None:
                    errors.append(f"{sc.id}/{b.id}: unknown action {a.action!r}")
                    continue
                missing = [k for k in spec["required"] if k not in a.params]
                if missing:
                    errors.append(
                        f"{sc.id}/{b.id}/{a.action}: missing params {missing}")
                unknown = [
                    k for k in a.params
                    if k not in spec["required"] + spec["optional"]
                ]
                if unknown:
                    errors.append(
                        f"{sc.id}/{b.id}/{a.action}: unknown params {unknown}")
    return errors


_TEMPLATE = '''"""Auto-generated Manim scene — 请勿手改。
scene_id: {sid}    index: {idx}    title: {title}
由 cs_video_agent.engine.compiler 从 storyboard.json 生成；
要修改内容请编辑 storyboard.json 后重新编译（tools/make.py）。
"""
from cs_video_agent.engine.runtime import BaseIRScene

SCENE_ID = {sid!r}
SCENE_INDEX = {idx}
SCENE_TITLE = {title!r}
OBJECTS = {objects}


class {cls}(BaseIRScene):
    scene_id = {sid!r}

    def construct(self):
{body}
'''


def compile_scene(scene: SceneIR) -> str:
    body = []
    first = True
    for b in scene.beats:
        narr = f", {b.narration!r}" if b.narration else ""
        body.append(f"        self.beat({b.id!r}{narr})")
        if first:
            body.append("        self.stage(OBJECTS)")
            first = False
        for a in b.actions:
            body.append(f"        self.act({a.action!r}, **{a.params!r})")
        body.append(f"        self.dwell({round(b.dwell, 2)})")
    if first:  # 没有任何 beat
        body.append("        self.stage(OBJECTS)")
    body.append("        self.act('fade_all')")
    body.append("        self.dwell(0.1)")
    body.append("        self.close_scene()")
    return _TEMPLATE.format(
        sid=scene.id,
        idx=scene.index,
        title=scene.title,
        objects=pprint.pformat([o.model_dump() for o in scene.objects], width=96),
        cls=class_name(scene),
        body="\n".join(body),
    )


def compile_storyboard(storyboard: Storyboard, out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    errors = validate_actions(storyboard)
    if errors:
        raise CompileError("storyboard validation failed:\n  " + "\n  ".join(errors))
    paths = []
    for scene in storyboard.scenes:
        path = out_dir / gen_filename(scene)
        path.write_text(compile_scene(scene), encoding="utf-8")
        paths.append(path)
    return paths
