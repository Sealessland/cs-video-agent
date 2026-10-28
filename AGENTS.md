# AGENTS.md — 在本工作区工作的 Agent 请先读这里

Agent 驱动的 CS 科普视频生产线（Manim CE 0.22 + FFmpeg，Scene-IR 架构）。
Phase 0 已打通全链路，参考成品：`projects/epoll_explained/`。

## 铁律

1. **永远不要手改 `projects/*/gen/` 下的生成文件**。改 `storyboard.json`，然后重编译。
2. **新增/修改动作**时三处同步：`engine/actions_*.py`（实现 + `_DESC` + SPECS）、
   `engine/replay.py`（语义映射，若影响状态）、`tests/`；然后 `make docs` 重新生成参考文档。
3. **渲染失败先看证据**：`output/render_report.json` 的 `error_tail` 与 `logs/*.log`，
   修完后用 `tools/render_scene.py --scene <id>` 定向重渲，不要全量重跑。
4. **调用 Python 一律走 `./scripts/csva`**（自动用 .venv 并屏蔽 PYTHONHOME/PYTHONPATH 泄漏）。
   直接跑 `.venv/bin/python` 在被污染的环境里会解析到错误的解释器。
5. 技术事实以 `lesson.json` 的 `facts` 为准，画面/解说不得与之矛盾；
   语义正确性由 `engine/replay.py` 的不变量回放把关，不许为了画面绕过它。

## 常用命令

```bash
make check                 # 环境体检
make test                  # 单元测试（改了模型/编译器/回放必跑）
make validate              # 全部项目验证+编译（改了 storyboard 必跑）
./scripts/csva tools/make.py projects/<name> --quality preview   # 单项目预览
./scripts/csva tools/make.py projects/<name> --scene scene_2     # 单幕重渲
make preview               # 批量预览（所有 projects/*）
make final                 # 批量终版 1080p30
make new PROJECT=<topic>   # 新项目脚手架
```

## 新视频的标准流程

1. `make new PROJECT=<topic>`，然后编辑 `lesson.json`（教学三要素：
   misconception / visual_experiment / takeaway）与 `storyboard.json`
   （对象/节拍/动作词汇见 `docs/ACTIONS.md`）。
2. `make validate` → 不过就修 storyboard（错误信息带 scene/beat 定位）。
3. 预览渲染 → `tools/extract_frames.py` 抽帧 → 多模态评审 →
   把结论写进 `critic/<scene>.review.json`（`engine/critic_io.write_review`）→
   定向修复 → 复验。字幕阅读窗口按 ≤4.5 字/秒检查。
4. `--quality final` 终渲合成，核对 `output/`（final.mp4 + final.srt + render_report.json）。

## 已知坑

- 沙箱环境可能注入 `PYTHONHOME`，症状是 `sys.executable` 指向宿主 AppImage、
  import 找不到包 → 一律用 `./scripts/csva`。
- `theme.FONT` 硬编码 `Noto Sans CJK SC`，换机器先 `make check` 确认字体。
- 每幕结尾由编译器自动追加 `fade_all`，storyboard 里不要手写。
- 挂载/文件监视冲突时可加 `--disable_caching`（renderops 默认已加）。
