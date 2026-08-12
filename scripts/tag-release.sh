#!/bin/bash
# 标签发布脚本 - 在打标签前运行全局测试

set -e  # 任何命令失败则退出
VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> (e.g., v0.2.0)"
    exit 1
fi

echo "Starting release process for $VERSION..."

# 1. 运行代码格式检查
echo "Running code format check..."
black --check . --line-length=120 || (echo "Black check failed! Run 'make format' to fix." && exit 1)

# 2. 运行 linting
echo "Running linting..."
ruff check . || (echo "Ruff check failed! Run 'ruff check --fix .' to fix." && exit 1)

# 3. 运行全局测试（主项目 + 所有子模块）
echo "Running GLOBAL tests..."
echo "  - Flash framework tests..."
pytest test -v || (echo "Flash framework tests failed!" && exit 1)

echo "  - Input generation tests..."
pytest flash/input_gen/test -v || (echo "Input generation tests failed!" && exit 1)

echo "  - Output processors tests..."
pytest flash/output_processors/test -v || (echo "Output processors tests failed!" && exit 1)

echo "  - Output processors input files tests..."
pytest flash/output_processors/inputfiles/test -v || (echo "Output processors input files tests failed!" && exit 1)

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
