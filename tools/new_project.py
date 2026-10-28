#!/usr/bin/env python3
"""新建视频项目脚手架：从 templates/ 复制 lesson + storyboard 模板。

用法：
  ./scripts/csva tools/new_project.py projects/my_topic
  ./scripts/csva tools/new_project.py projects/my_topic --topic "..." --title "..."
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMPLATE_DIR = ROOT / "templates" / "project"
SUBDIRS = ["gen", "scenes", "frames", "critic", "logs", "output"]


def slug_ok(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9_\-]*", name))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", help="项目目录，通常放 projects/<name> 下")
    ap.add_argument("--topic", help="lesson.topic（默认取目录名）")
    ap.add_argument("--title", help="lesson.title（默认取目录名）")
    ap.add_argument("--force", action="store_true", help="覆盖已有文件")
    args = ap.parse_args()

    target = (ROOT / args.path).resolve()
    if "projects" not in target.parts:
        print("提示：建议放在 projects/ 目录下，batch.py 只扫描 projects/*")
    name = target.name
    if not slug_ok(name):
        print(f"项目名 {name!r} 需匹配 [a-z0-9][a-z0-9_-]*")
        return 2
    if (target / "storyboard.json").exists() and not args.force:
        print(f"{target} 已存在，用 --force 覆盖")
        return 2

    target.mkdir(parents=True, exist_ok=True)
    for d in SUBDIRS:
        (target / d).mkdir(exist_ok=True)

    topic, title = args.topic or name, args.title or name
    for fname in ("lesson.json", "storyboard.json"):
        text = (TEMPLATE_DIR / fname).read_text(encoding="utf-8")
        text = text.replace("{{TOPIC}}", topic).replace("{{TITLE}}", title)
        (target / fname).write_text(text, encoding="utf-8")
        print(f"  wrote {target / fname}")
    print(f"项目 {name} 就绪。下一步：")
    print(f"  1. 编辑 {target / 'lesson.json'}   （教学设计：misconception/visual_experiment/takeaway）")
    print(f"  2. 编辑 {target / 'storyboard.json'}（分镜：objects/beats/actions，参考 docs/ACTIONS.md）")
    print(f"  3. ./scripts/csva tools/make.py {Path(args.path)} --quality preview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
