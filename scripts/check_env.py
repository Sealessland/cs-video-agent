#!/usr/bin/env python3
"""环境体检：解释器 / 依赖 / ffmpeg / CJK 字体 / 环境变量泄漏。

退出码非 0 表示有阻断性问题。可选 --smoke 额外渲染 2 秒中文样片（最彻底的验证）。
"""

import os
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import version as pkg_version, PackageNotFoundError

CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "", fix: str = "") -> None:
    CHECKS.append({"name": name, "ok": ok, "detail": detail, "fix": fix})
    mark = "ok " if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f": {detail}" if detail else ""))
    if not ok and fix:
        print(f"         fix: {fix}")


def main() -> int:
    print("== cs-video-agent 环境体检")

    check("python>=3.12", sys.version_info >= (3, 12), sys.version.split()[0])

    for mod, dist, need in (("manim", "manim", "0.22"), ("pydantic", "pydantic", "2"),
                            ("srt", "srt", "3"), ("PIL", "pillow", None),
                            ("pydub", "pydub", None)):
        try:
            __import__(mod)
            try:
                ver = pkg_version(dist)
            except PackageNotFoundError:
                ver = "unknown"
            ok = ver.startswith(need) if need else True
            check(f"import {mod}", ok, ver)
        except Exception as e:  # noqa: BLE001
            check(f"import {mod}", False, str(e),
                  fix="重新运行 bash scripts/bootstrap.sh 安装依赖")

    for tool in ("ffmpeg", "ffprobe"):
        check(f"{tool} in PATH", shutil.which(tool) is not None,
              shutil.which(tool) or "not found",
              fix="安装 ffmpeg（Arch: pacman -S ffmpeg；Debian: apt install ffmpeg）")

    fc = shutil.which("fc-list")
    if fc:
        out = subprocess.run([fc, ":lang=zh", "family"], capture_output=True,
                             text=True).stdout
        has_noto_sc = "Noto Sans CJK SC" in out
        if has_noto_sc:
            check("CJK 字体（Noto Sans CJK SC）", True)
        else:
            check("CJK 字体（Noto Sans CJK SC）", False,
                  "未找到主题指定的 Noto Sans CJK SC",
                  fix="安装 noto-fonts-cjk（Arch）/ fonts-noto-cjk（Debian），"
                      "或改 cs_video_agent/theme.py 的 FONT")
    else:
        check("fc-list", False, "not found", fix="安装 fontconfig")

    leak = [k for k in ("PYTHONHOME", "PYTHONPATH") if os.environ.get(k)]
    if leak:
        print(f"  [warn] 检测到 {leak} 已设置 —— 请用 ./scripts/csva 调用，"
              f"它会自动屏蔽这些变量")
    else:
        print("  [ok ] 无 PYTHONHOME/PYTHONPATH 泄漏")

    if "--smoke" in sys.argv:
        with tempfile.TemporaryDirectory() as td:
            src = f"{td}/smoke.py"
            with open(src, "w", encoding="utf-8") as f:
                f.write(
                    "from manim import *\n"
                    "class Smoke(Scene):\n"
                    "    def construct(self):\n"
                    "        self.play(Write(Text('环境冒烟', "
                    "font='Noto Sans CJK SC')), run_time=1.5)\n"
                    "        self.wait(0.5)\n")
            r = subprocess.run(
                [sys.executable, "-m", "manim", "render", "-ql",
                 "--disable_caching", "--media_dir", f"{td}/media", src, "Smoke"],
                capture_output=True, text=True,
                env={k: v for k, v in os.environ.items()
                     if k not in ("PYTHONHOME", "PYTHONPATH")})
            ok = r.returncode == 0
            check("渲染冒烟（中文样片）", ok,
                  "" if ok else (r.stderr or r.stdout)[-400:],
                  fix="查看上方错误；常见为缺系统库（pango/cairo）或字体")

    failed = [c for c in CHECKS if not c["ok"]]
    print(f"\n== 体检结果: {len(CHECKS) - len(failed)}/{len(CHECKS)} 通过"
          + ("" if not failed else f"，失败项: {[c['name'] for c in failed]}"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
