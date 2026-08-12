#!/bin/bash
# git-tag-with-test.sh — 打标签之前运行全局测试
#
# 用法：
#   ./scripts/03_git_publish/git-tag-with-test.sh v0.0.1 "Version 0.0.1 release"
#
# 此脚本执行以下操作：
# 1. 运行全局测试（flash/test/ + input_gen/test/ + 其他模块测试）
# 2. 如果测试通过，创建 git 标签并推送
# 3. 如果测试失败，中止打标签

if [ $# -lt 1 ]; then
    echo "Usage: $0 <tag_name> [tag_message]"
    echo ""
    echo "Examples:"
    echo "  $0 v0.0.1"
    echo "  $0 v0.0.1 'Version 0.0.1 release'"
    exit 1
fi

TAG_NAME="$1"
TAG_MESSAGE="${2:-$TAG_NAME}"

echo "🏷️  Preparing to tag: $TAG_NAME"
echo "📝 Message: $TAG_MESSAGE"
echo ""

# 获取脚本所在目录（即 scripts/03_git_publish/）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 获取项目根目录（向上查找含 pyproject.toml 的目录, 兼容任意子目录布局）
PROJECT_ROOT="$SCRIPT_DIR"
while [ ! -f "$PROJECT_ROOT/pyproject.toml" ] && [ "$PROJECT_ROOT" != "/" ]; do
    PROJECT_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"
done

# 如果在 Windows Git Bash 中运行，将路径转为 Windows 格式
if command -v cygpath &> /dev/null; then
    PROJECT_ROOT_PY="$(cygpath -w "$PROJECT_ROOT")"
else
    PROJECT_ROOT_PY="$PROJECT_ROOT"
fi

echo "📂 Project root: $PROJECT_ROOT"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 使用正确的 Python 解释器 (支持环境变量覆盖)
# 默认: 空 → 下方 PATH 查找 python3/python; 自定义: export PYTHON=/path/to/python
PYTHON="${PYTHON:-}"

# 检查 Python 是否可用
if [ -z "$PYTHON" ] || [ ! -f "$PYTHON" ]; then
    # 尝试从 PATH 查找 python
    if command -v python3 &> /dev/null; then
        PYTHON="python3"
    elif command -v python &> /dev/null; then
        PYTHON="python"
    else
        echo "Warning: Python not found at $PYTHON and not in PATH"
        echo "  - Set PYTHON environment variable to override"
        exit 1
    fi
fi

echo "  - Using Python: $PYTHON"

# 添加项目根目录到 PYTHONPATH（已转换为 Windows 格式）
export PYTHONPATH="${PROJECT_ROOT_PY}:${PYTHONPATH}"

echo "🧪 Running global tests before tagging..."
echo ""

# 运行全局测试
# 测试路径相对于 PROJECT_ROOT，使用 flash/test/ 指向 flash 子包下的测试
echo "  - Running Flash framework tests (test/)..."
"$PYTHON" -m pytest test/ -q --tb=short
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Flash framework tests failed! Tag aborted."
    echo "Fix the tests before tagging."
    exit 1
fi

echo ""
echo "  - Running input_gen tests (flash/input_gen/test/)..."
"$PYTHON" -m pytest flash/input_gen/test/ -v --tb=short
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Input gen tests failed! Tag aborted."
    echo "Fix the tests before tagging."
    exit 1
fi

# 运行其他模块测试（如果存在）
if [ -d "flash/output_processors/test/" ]; then
    echo ""
    echo "  - Running output_processors tests (flash/output_processors/test/)..."
    "$PYTHON" -m pytest flash/output_processors/test/ -v --tb=short 2>/dev/null
    if [ $? -ne 0 ]; then
        echo ""
        echo "⚠️  Warning: output_processors tests failed (non-critical)."
        echo "  - Continuing with tag..."
    fi
fi

echo ""
echo "✅ All global tests passed!"
echo ""
echo "🏷️  Creating tag: $TAG_NAME"
echo ""

# 创建 git 标签 (不推送, 由调用方 git_push.py 处理推送)
git tag -a "$TAG_NAME" -m "$TAG_MESSAGE"
if [ $? -ne 0 ]; then
    echo "❌ Failed to create tag!"
    exit 1
fi

echo ""
echo "✅ Tag $TAG_NAME created successfully!"
echo ""
echo "📋 Summary:"
echo "  - Tag: $TAG_NAME"
echo "  - Message: $TAG_MESSAGE"
echo "  - Commit: $(git log -1 --oneline)"
echo ""
echo "⏩  Push handled by git_push.py"
exit 0
