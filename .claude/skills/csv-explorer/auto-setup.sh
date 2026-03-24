#!/bin/bash
# CSV Explorer 技能自动配置脚本
# 自动检测平台并配置环境变量

echo "🔍 正在检测平台..."

ARCH=$(uname -m)
OS=$(uname -s)

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XAN_DIR="$SCRIPT_DIR"

# 检测操作系统和CPU架构
if [ "$OS" = "Linux" ]; then
    if [ "$ARCH" = "x86_64" ]; then
        XAN_PATH="$XAN_DIR/x86_64-linux-gnu/xan"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        XAN_PATH="$XAN_DIR/aarch64-linux-gnu/xan"
    else
        echo "❌ 不支持的CPU架构: $ARCH"
        exit 1
    fi
elif [ "$OS" = "Darwin" ]; then
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        XAN_PATH="$XAN_DIR/aarch64-apple-darwin/xan"
    else
        XAN_PATH="$XAN_DIR/x86_64-apple-darwin/xan"
    fi
else
    echo "❌ 不支持的操作系统: $OS"
    exit 1
fi

# 验证文件是否存在
if [ ! -f "$XAN_PATH" ]; then
    echo "❌ 找不到 xan 可执行文件: $XAN_PATH"
    exit 1
fi

# 添加执行权限
chmod +x "$XAN_PATH" 2>/dev/null

# 生成环境变量配置
CONFIG_FILE="$SCRIPT_DIR/xan-config.sh"
cat > "$CONFIG_FILE" << EOFCONFIG
# CSV Explorer 技能环境变量配置
# 生成时间: $(date)
# 平台: $OS $ARCH

export XAN_PATH="$XAN_PATH"

# 可选：添加别名（取消注释以启用）
# alias xan='\$XAN_PATH'
EOFCONFIG

echo "✅ 平台检测完成"
echo "   操作系统: $OS"
echo "   CPU架构: $ARCH"
echo ""
echo "📝 配置文件已生成: $CONFIG_FILE"
echo ""
echo "📖 使用方法:"
echo ""
echo "   临时配置（当前会话）:"
echo "   source $CONFIG_FILE"
echo ""
echo "   永久配置（添加到 ~/.bashrc）:"
echo "   echo 'source $CONFIG_FILE' >> ~/.bashrc"
echo "   source ~/.bashrc"
echo ""
echo "   快速测试:"
echo "   \$XAN_PATH --version"
