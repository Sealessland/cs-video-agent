#!/usr/bin/env bash
# 一键配环境：Python 3.13 venv + 锁定依赖（editable 安装）+ 自检。
# 幂等：重复运行安全。
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== [1/3] 创建虚拟环境（Python 3.13）"
if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.13 .venv
  else
    echo "未找到 uv，回退 python3 -m venv（需要 Python >= 3.12）"
    python3 -m venv .venv
  fi
else
  echo "  .venv 已存在，跳过"
fi

echo "== [2/3] 安装依赖（pyproject + requirements.txt 锁定）"
if command -v uv >/dev/null 2>&1; then
  uv pip install --python .venv/bin/python -e ".[dev]"
else
  .venv/bin/pip install -U pip
  .venv/bin/pip install -e ".[dev]"
  .venv/bin/pip install -r requirements.txt
fi

echo "== [3/3] 环境自检"
env -u PYTHONHOME -u PYTHONPATH .venv/bin/python scripts/check_env.py

cat <<'TIP'

环境就绪。日常命令（推荐用统一入口 ./scripts/csva，或 make help）：
  make preview            # 全部项目 预览渲染+合成
  make final              # 全部项目 1080p 终版
  make new PROJECT=xxx    # 新建视频项目脚手架
  make check              # 环境体检
TIP
