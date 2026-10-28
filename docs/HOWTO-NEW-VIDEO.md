# 创作手册：从选题到成片

面向「人 + Agent 协作」的视频创作流程。读完这一篇就能独立产出一期。

## 0. 心法

好视频的顺序是：**事实 → 认知设计 → 分镜（IR）→ 动画 → 质检**。
任何一步出了问题，回到上一步修，不要在生成代码上打补丁。

## 1. 选题与研究（lesson.json : facts）

- 选题要能回答「观众的反直觉在哪里」。epoll 期的答案是：
  「为什么扫全部连接是慢的，而 epoll 不用扫」。
- 把确认过的事实逐条写进 `facts`（可溯源：官方文档 / 源码 / 实验）。
  这些事实同时是 Agent 的护栏：画面与解说不得与之矛盾。
- 诚实边界先想清楚：这期**不**讲什么（epoll 期没展开 LT/ET 细节，就在 facts 里声明）。

## 2. 教学设计（lesson.json : segments）

每个教学片段必须写满三要素，这是分镜的验收标准：

| 字段 | 问自己 |
|---|---|
| `misconception` | 观众现在脑子里那个错误（或缺失）的模型是什么？ |
| `visual_experiment` | 动画让观察者**亲眼看到**什么，从而推翻/建立模型？ |
| `takeaway` | 这幕结束时，观众能用一句话说出什么？ |

叙事骨架（3b1b 式）：反直觉问题 → 建立直觉 → 暴露旧方法的局限 →
机制可视化 → 抽象收束 + 纠偏。

## 3. 写分镜（storyboard.json）

结构：`scenes[] -> objects[]（画面里的语义对象）+ beats[]（节拍）`。
每个 beat = 一句解说（= 一条字幕）+ 顺序动作 + dwell 停顿。

- 对象/动作/锚点/不变量的完整词汇表见 **[ACTIONS.md](ACTIONS.md)**（由代码生成，始终最新）。
- 参考实现：`projects/epoll_explained/storyboard.json`（三幕、三种构图）。
- 时长预算：每幕 20–40s，全片 60–90s；`dwell` 保证解说阅读窗口
  **≤ 4.5 字/秒**（字数 ÷ (动作时长+dwell)）。
- 语义承诺：给场景声明 `invariants`（如 `only_ready_sockets_are_returned`），
  渲染前的回放校验会真的去验证它。

## 4. 验证与预览

```bash
./scripts/csva tools/make.py projects/<name> --quality preview
```

一条命令完成：语义验证（schema/动作/回放）→ 编译生成 Manim 代码 →
480p15 渲染 → 合成 + 烧字幕。验证失败的定位信息形如
`scene_3/b4/queue_enqueue: missing params ['fd']`。

## 5. 视觉质检与修复循环

```bash
./scripts/csva tools/extract_frames.py projects/<name> --quality preview
```

- 产出：`frames/<scene>/*.png`（带解说的关键帧）+ `contact.png` 拼图 +
  `critic/<scene>.critic_input.json`（评审输入：帧 + 节拍上下文 + 检查问题）。
- 用多模态模型（或人眼）逐帧检查：越界/遮挡、文字清晰度、画面与解说一致性、信息密度。
- 结论写进 `critic/<scene>.review.json`（`engine.critic_io.write_review`），
  `severity=error` 的问题必须修复。
- 修复后**只重渲出问题的幕**：

```bash
./scripts/csva tools/render_scene.py projects/<name> --scene scene_2 --quality preview
```

常见问题速查：

| 症状 | 修法 |
|---|---|
| 渲染报 NameError/ImportError | 看 render_report 的 error_tail；`pyflakes` 全扫；修视图代码后定向重渲 |
| 动作参数写错 | 编译期就会报 unknown/missing params，改 storyboard |
| 文字溢出/重叠 | 缩短文案或让文本走 `fit_text` 上限；布局参数在视图构造 params 里 |
| 总长超 90s | 压 dwell（保住 4.5 字/秒下限）；压缩重复动作 run_time |
| 字幕与画面错位 | 正常不会——timings.json 用真实渲染时钟；若改了动画，必须重渲该幕再合成 |

## 6. 终版与发布

```bash
./scripts/csva tools/make.py projects/<name> --quality final
```

发布前核对 `output/`：

- [ ] `final.mp4`：1920×1080、h264、时长 60–90s（`ffprobe` 复核）
- [ ] `final.srt`：条目数 = 带解说的 beat 数，中文无乱码
- [ ] `render_report.json`：全部场景 final 质量 attempt=ok
- [ ] `critic/*.review.json`：无 severity=error 的未处理项
- [ ] 源码归档：storyboard/lesson/gen/logs 均在项目目录内（可复现）

## 7. 批量产出

```bash
make preview    # 或 make final：projects/ 下所有项目依次跑全流程
```

- 汇总报告：`batch_report.json`（每项目状态/时长/失败原因）。
- 筛选：`tools/batch.py --projects 'redis_*' --quality final`。
- 新项目一律从 `make new PROJECT=<topic>` 开始（模板自带可渲染的示例幕，
  创建完立刻就能 `make preview` 跑通管线，再往里替换内容）。
