.PHONY: test test-all lint format check build clean

# Flash 框架测试（主项目测试，快速）
test:
	pytest test -v

# 全局测试（主项目 + 所有子模块，慢速）
test-all:
	pytest test -v
	pytest input_gen/test -v
	pytest output_processors/test -v
	pytest output_processors/inputfiles/test -v

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
