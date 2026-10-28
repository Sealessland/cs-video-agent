# CS Video Agent 工作区常用命令。make help 查看全部。
PY := ./scripts/csva

help: ## 显示本清单
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

setup: ## 一键配环境（venv + 依赖 + 自检）
	bash scripts/bootstrap.sh

check: ## 环境体检（依赖/ffmpeg/字体/泄漏变量；check-smoke 含渲染冒烟）
	$(PY) scripts/check_env.py

check-smoke: ## 环境体检 + 渲染冒烟
	$(PY) scripts/check_env.py --smoke

test: ## 单元测试
	$(PY) -m pytest tests/ -q

validate: ## 全部项目：语义验证 + 编译（不渲染）
	$(PY) tools/batch.py --validate-only

preview: ## 全部项目：预览质量（480p15）渲染 + 合成
	$(PY) tools/batch.py --quality preview

final: ## 全部项目：终版（1080p30）渲染 + 合成
	$(PY) tools/batch.py --quality final

new: ## 新建视频项目：make new PROJECT=my_topic
	@test -n "$(PROJECT)" || (echo "用法: make new PROJECT=my_topic"; exit 2)
	$(PY) tools/new_project.py projects/$(PROJECT)

docs: ## 重新生成动作参考 docs/ACTIONS.md
	$(PY) tools/gen_actions_doc.py

.PHONY: help setup check check-smoke test validate preview final new docs
