#!/bin/bash
# install-git-hooks.sh — 安装 Git 钩子
#
# 用法：
#   ./scripts/install-git-hooks.sh
#
# 此脚本会：
# 1. 创建符号链接从 .git/hooks/ 到 scripts/git-hooks/
# 2. 设置执行权限
# 3. 验证安装是否成功

echo "📦 Installing Git hooks..."

# 获取脚本所在目录（即 scripts/）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 获取项目根目录（scripts/ 的父目录）
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 检查是否在 Git 仓库中
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "❌ Error: Not in a Git repository!"
    echo "  - Expected .git directory at: $PROJECT_ROOT/.git"
    exit 1
fi

echo "  - Project root: $PROJECT_ROOT"
echo "  - Git hooks dir: $PROJECT_ROOT/.git/hooks"
echo "  - Source hooks dir: $SCRIPT_DIR/git-hooks"
echo ""

# 创建符号链接
echo "🔗 Creating symbolic links..."

# Pre-commit hook
if [ -e "$PROJECT_ROOT/.git/hooks/pre-commit" ]; then
    echo "  - Backing up existing pre-commit hook..."
    mv "$PROJECT_ROOT/.git/hooks/pre-commit" "$PROJECT_ROOT/.git/hooks/pre-commit.backup"
fi

ln -s "../../scripts/git-hooks/pre-commit" "$PROJECT_ROOT/.git/hooks/pre-commit"
if [ $? -eq 0 ]; then
    echo "  ✅ pre-commit hook installed"
else
    echo "  ❌ Failed to install pre-commit hook"
    exit 1
fi

# Pre-push hook
if [ -e "$PROJECT_ROOT/.git/hooks/pre-push" ]; then
    echo "  - Backing up existing pre-push hook..."
    mv "$PROJECT_ROOT/.git/hooks/pre-push" "$PROJECT_ROOT/.git/hooks/pre-push.backup"
fi

ln -s "../../scripts/git-hooks/pre-push" "$PROJECT_ROOT/.git/hooks/pre-push"
if [ $? -eq 0 ]; then
    echo "  ✅ pre-push hook installed"
else
    echo "  ❌ Failed to install pre-push hook"
    exit 1
fi

echo ""

# 设置执行权限
echo "🔑 Setting execute permissions..."
chmod +x "$SCRIPT_DIR/git-hooks/pre-commit"
chmod +x "$SCRIPT_DIR/git-hooks/pre-push"
chmod +x "$SCRIPT_DIR/git-tag-with-test.sh"
echo "  ✅ Permissions set"
echo ""

# 验证安装
echo "🔍 Verifying installation..."
echo ""

# 检查符号链接
if [ -L "$PROJECT_ROOT/.git/hooks/pre-commit" ]; then
    echo "  ✅ pre-commit hook: symbolic link created"
else
    echo "  ❌ pre-commit hook: not a symbolic link"
fi

if [ -L "$PROJECT_ROOT/.git/hooks/pre-push" ]; then
    echo "  ✅ pre-push hook: symbolic link created"
else
    echo "  ❌ pre-push hook: not a symbolic link"
fi

# 检查执行权限
if [ -x "$SCRIPT_DIR/git-hooks/pre-commit" ]; then
    echo "  ✅ pre-commit hook: execute permission set"
else
    echo "  ❌ pre-commit hook: missing execute permission"
fi

if [ -x "$SCRIPT_DIR/git-hooks/pre-push" ]; then
    echo "  ✅ pre-push hook: execute permission set"
else
    echo "  ❌ pre-push hook: missing execute permission"
fi

echo ""

# 测试钩子
echo "🧪 Testing hooks..."
echo ""

# 测试 pre-commit hook
echo "  - Testing pre-commit hook..."
"$SCRIPT_DIR/git-hooks/pre-commit" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "    ✅ pre-commit hook: test passed"
else
    echo "    ⚠️  pre-commit hook: test failed (but hook is installed)"
fi

echo ""

# 总结
echo "✅ Git hooks installed successfully!"
echo ""
echo "📋 Summary:"
echo "  - pre-commit: $PROJECT_ROOT/.git/hooks/pre-commit"
echo "  - pre-push: $PROJECT_ROOT/.git/hooks/pre-push"
echo "  - Custom tag script: $SCRIPT_DIR/git-tag-with-test.sh"
echo ""
echo "📖 Usage:"
echo "  1. git commit (triggers pre-commit hook)"
echo "  2. git push (triggers pre-push hook)"
echo "  3. ./scripts/git-tag-with-test.sh <tag_name> (custom tag script)"
echo ""
echo "📝 Note:"
echo "  - To skip hooks, use 'git commit --no-verify' or 'git push --no-verify'"
echo "  - To uninstall hooks, run: ./scripts/uninstall-git-hooks.sh"
echo ""
exit 0
