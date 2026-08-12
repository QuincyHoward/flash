#!/bin/bash
# 标签发布脚本 - 在打标签前运行全局测试
# 用法: ./scripts/03_git_publish/tag-release.sh <version> (e.g., v0.2.0)

set -e  # 任何命令失败则退出
VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> (e.g., v0.2.0)"
    exit 1
fi

# 定位项目根目录（向上查找含 pyproject.toml 的目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
while [ ! -f "$PROJECT_ROOT/pyproject.toml" ] && [ "$PROJECT_ROOT" != "/" ]; do
    PROJECT_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"
done
cd "$PROJECT_ROOT"

echo "Starting release process for $VERSION (project: $PROJECT_ROOT)..."

# 1. 运行代码格式检查
echo "Running code format check..."
black --check . --line-length=120 || (echo "Black check failed! Run 'make format' to fix." && exit 1)

# 2. 运行 linting
echo "Running linting..."
ruff check . || (echo "Ruff check failed! Run 'ruff check --fix .' to fix." && exit 1)

# 3. 运行全局测试（主项目 + 所有子模块）
echo "Running GLOBAL tests..."
echo "  - Flash framework tests..."
pytest test -q || (echo "Flash framework tests failed!" && exit 1)

echo "  - Input generation tests..."
pytest flash/input_gen/test -q || (echo "Input generation tests failed!" && exit 1)

echo "  - Output processors tests..."
pytest flash/output_processors/test -q || (echo "Output processors tests failed!" && exit 1)

echo "All global tests passed!"

# 4. 构建检查
echo "Running build check..."
pip install build
python -m build --sdist --wheel || (echo "Build failed!" && exit 1)

# 5. 打标签
echo "Creating tag $VERSION..."
git tag -a "$VERSION" -m "Release $VERSION"

echo "Release $VERSION ready!"
echo "Next steps:"
echo "   1. Push tag: git push origin $VERSION"
echo "   2. (Optional) Publish to PyPI: twine upload dist/*"
