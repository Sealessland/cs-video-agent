# CS Video Agent

Agent 驱动的计算机科学科普视频生产线（Manim CE 0.22 + FFmpeg，Scene-IR 架构）。
输入一份教学计划和一个分镜 JSON，产出一部带中文解说字幕的 1080p 程序化动画视频。

核心思路不是「LLM 直接生成一坨 Manim 代码」，而是让每个环节都落在**可检测、可修复、可复用**的中间产物上：

```
教学计划(Lesson) → Scene IR(JSON) → 语义回放验证 → 编译为 Manim 场景代码
                        ↓                        ↓
                  纯 Python 状态模型      渲染 → 关键帧质检 → 定向修复 → 合成
```

## 成品示例

仓库内的 `projects/` 只保留源文件（`lesson.json` + `storyboard.json`），
渲染产物不进版本库，克隆后跑 `make preview` 即可本地复现：

| 项目 | 时长 | 规模 | 覆盖主题 |
|---|---|---|---|
| `epoll_explained` | 88s | 3 幕 | select/poll 的 O(n) 扫描 vs epoll 事件回调 |
| `os_program_life` | ~3.6min | 5 幕 | 进程生命周期：fork/exec/调度/等待/退出 |
| `payment_incident` | 10.3min | 17 幕 | 一次支付请求引发的线上事故：TCP/TLS、HTTP/2、GMP 泄漏、三色标记 GC、Redis 结构、Cache-Aside 竞态、B+ 树、MVCC 死锁、Kafka ISR、Outbox、状态机、Snowflake、限流熔断、对账 |

## 快速开始

```bash
bash scripts/bootstrap.sh     # venv + 锁定依赖 + 环境自检
make check                    # 环境体检（check-smoke 含渲染冒烟）
make validate                 # 全部项目：语义验证 + 编译（不渲染）
make preview                  # 全部项目：预览(480p15)渲染 + 合成
make final                    # 全部项目：终版(1080p30)渲染 + 合成
make new PROJECT=my_topic     # 新建视频项目脚手架
make test                     # 单元测试
```

之后所有 Python 调用统一走 `./scripts/csva`（自动用 .venv，并屏蔽宿主注入的
`PYTHONHOME/PYTHONPATH`——某些沙箱会破坏 venv 解析）。

单项目 / 单幕操作：

```bash
./scripts/csva tools/make.py projects/epoll_explained --quality preview   # 单项目全流程
./scripts/csva tools/make.py projects/epoll_explained --scene scene_2     # 只重渲一幕
./scripts/csva tools/batch.py --projects 'epoll*' --quality final         # 批量筛选
./scripts/csva tools/extract_frames.py projects/epoll_explained           # 关键帧+评审输入
```

产物：每个项目 `projects/<name>/output/` 下 `final.mp4` + `final.srt` + `render_report.json`。

## 目录结构

```
├── AGENTS.md / Makefile / README.md / LICENSE
├── scripts/          bootstrap.sh（配环境）/ csva（统一入口）/ check_env.py（体检）
├── templates/        新项目脚手架模板（lesson + storyboard）
├── docs/             HOWTO-NEW-VIDEO.md（创作手册）/ ACTIONS.md（自动生成的动作参考）
├── cs_video_agent/
│   ├── schemas/        Pydantic 契约：Lesson（教学计划）/ Scene IR（分镜）/ Review（质检与渲染报告）
│   ├── visualkit/
│   │   ├── models*.py  纯 Python 状态模型（不依赖 Manim）：SocketSet、GMP、GC、状态机、对账账本…
│   │   └── views/      视图：SocketGrid、EventFlow、StateStripView、LedgerView、KVStoreView…
│   └── engine/
│       ├── runtime.py  BaseIRScene：stage / beat 计时 / act 分发 / timings.json 落盘
│       ├── actions*.py 动作注册表（文本类 + OS/网络类 + 支付域），带参数规格供编译期检查
│       ├── compiler.py Scene IR -> 可读的 Manim 场景代码（gen/scene_NN.py）
│       ├── replay.py   语义回放：动作序列重放到纯模型，验证场景声明的 invariants
│       ├── validate_slots.py  槽位重叠静态检测：编译前拦截卡片残留/标题遮挡
│       ├── renderops.py manim 子进程渲染 + ffprobe + render_report 账本
│       ├── assemble.py concat + SRT 字幕烧制（libass）
│       └── subtitles.py / critic_io.py
├── tools/            CLI：make / batch / new_project / render_scene / validate_scene / extract_frames / assemble_video / gen_actions_doc
└── projects/         每期视频一个目录（见上表；仓库只含 lesson.json + storyboard.json）
```

一个项目目录在完整跑过管线后是这样（生成部分已 gitignore）：

```
projects/<name>/
├── lesson.json         教学计划：每段含 misconception / visual_experiment / takeaway
├── storyboard.json     Scene IR：objects / beats（解说+动作+dwell）/ invariants
├── gen/                编译生成的 Manim 场景代码（勿手改；改 storyboard 后重编译）
├── scenes/             每幕 timings.json（真实渲染时钟，字幕对齐用）
├── frames/ critic/     关键帧、拼图、评审输入与结论
├── logs/               渲染日志、validate.json
└── output/             final.mp4 / final.srt / render_report.json
```

## 质量闭环（Agent 的修复循环）

1. **确定性检查**：pydantic schema、动作名/参数规格、槽位重叠静态检测（`validate_slots`）、pyflakes、pytest。
2. **语义检查**：`engine/replay.py` 把 beats 重放到纯 Python 状态模型上，断言场景声明的 invariants。
   例如支付域：状态机「直接标 PAID」只能以 attempt 演示且必然被拒（超时≠确认）；
   对账修复只允许改不一致行，且金额必须与渠道一致——画面设计不许绕过语义。
3. **渲染账本**：每次渲染是一条 attempt（ok/error/timeout），日志在 `logs/`，
   `render_report.json` 记录 ffprobe 结果；失败后修 storyboard/视图，用
   `tools/render_scene.py --scene X` 定向重渲，不全量重跑。
4. **视觉质检**：`extract_frames.py` 按「本拍阅读窗口」采样关键帧 + 拼图，输出 `critic_input.json`，
   多模态评审结论写入 `critic/*.review.json`，按 finding 定向修复后复验。
5. **字幕节奏**：按 ≤4.5 字/秒检查每拍解说阅读窗口。

## 教学三要素

每个视频段落（segment）必须回答三件事，写进 `lesson.json`：

- **misconception** —— 观众的反直觉锚点（如「epoll = 魔法 O(1)」）
- **visual_experiment** —— 用什么画面实验戳破它（注册一次→回调脉冲→只返回就绪者）
- **takeaway** —— 一句话带走（省掉的是重复扫描，不是一切成本）

## 扩展新领域

新增一领域（如 Raft、TCP 拥塞控制）按三处同步：

1. `visualkit/models_<domain>.py`：纯 Python 状态模型 + 该领域 invariants；
2. `visualkit/views/`：对应的 Manim 视图；
3. `engine/actions_<domain>.py`：动作实现 + `_DESC` + 参数规格，`engine/replay.py` 补语义映射，
   `tests/` 补用例，然后 `make docs` 重新生成 `docs/ACTIONS.md`。

## 诚实的边界

- 配音/TTS 未接入（字幕方案交付：`final.srt` + 烧制进成片）。
- 「视觉评审」由多模态模型逐帧审看（人工可复看 `critic/*.review.json`），尚未全自动闭环打分。
- 语义回放覆盖已实现的动作词汇；新增动作需同步 `engine/replay.py` 的映射。

## 文档

- **[docs/HOWTO-NEW-VIDEO.md](docs/HOWTO-NEW-VIDEO.md)** —— 创作手册：选题→教学设计→分镜→质检→发布
- **[docs/ACTIONS.md](docs/ACTIONS.md)** —— Scene IR 词汇表（对象/动作/锚点/不变量），由代码自动生成
- **[AGENTS.md](AGENTS.md)** —— 在本工作区工作的 Agent 规则（改哪里、怎么验、已知坑）

## License

[MIT](LICENSE)
