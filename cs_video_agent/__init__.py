"""cs_video_agent: Agent 驱动的计算机科学科普视频生产线（Phase 0）.

分层：
- schemas/     结构化契约（Lesson / Scene IR / Review / RenderReport）
- visualkit/   可复用组件：Model（纯状态） + View（Manim 视图）
- engine/      Scene Compiler、动作运行时、语义回放、渲染与合成
- tools/       CLI 工具（make / render_scene / validate / extract_frames / assemble）
"""

__version__ = "0.1.0"
