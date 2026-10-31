.PHONY: test test-all lint format check build clean plasmapy-install plasmapy-test plasmapy-check

# Flash 框架测试（主项目测试，快速）
test:
	pytest test -v

# 全局测试（主项目 + 所有子模块，慢速）
test-all:
	pytest test -v
	pytest flash/input_gen/test -v
	pytest flash/output_pro/test -v

# 代码格式检查
lint:
	black --check . --line-length=120
	ruff check .

# 自动格式化代码
format:
	black . --line-length=120
	ruff check --fix .

# 运行所有检查（提交前运行）
check: lint test

# 构建分发包
build:
	pip install build
	python -m build

# 清理构建文件
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

# ─────────────────────────────────────────────────────────────────────
# PlasmaPy 开发要求（2026-10-30, vendor 快照合规）
#   详见 docs/PLASMAPY_DEVELOPMENT.md 与 NOTICE（BSD-3 边界声明）
# ─────────────────────────────────────────────────────────────────────

# PlasmaPy editable 安装进当前环境 (source of truth = vendor 目录)
plasmapy-install:
	python flash/output_pro/PlasmaPy/install_editable.py

# 桥接层物理交叉验证 (12 项) + PlasmaPy 冒烟
plasmapy-test:
	pytest flash/output_pro/test/test_plasmapy_bridge.py -v
	python flash/output_pro/PlasmaPy/install_editable.py --check

# 开发工具链对齐检查 (依赖 extra: pip install -e ".[plasmapy-dev]")
#   codespell 只扫 PlasmaPy 相关文件 (全仓为软工具, 存量拼写债见 PLASMAPY_DEVELOPMENT.md §2)
plasmapy-check:
	codespell flash/output_pro/plasmapy_bridge.py docs/PLASMAPY_DEVELOPMENT.md NOTICE README.md DEPENDENCIES.md
	black --check flash/output_pro/plasmapy_bridge.py --line-length=120
	ruff check flash/output_pro/plasmapy_bridge.py
	python -m pytest flash/output_pro/test/test_plasmapy_bridge.py -q
