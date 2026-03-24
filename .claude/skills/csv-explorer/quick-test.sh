#!/bin/bash
# CSV Fetch 技能快速测试脚本
# 用于验证技能是否正确配置并正常工作

set -e

# 加载配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/xan-config.sh" ]; then
    source "$SCRIPT_DIR/xan-config.sh"
else
    echo "❌ 找不到配置文件: xan-config.sh"
    echo "   请先运行: ./auto-setup.sh"
    exit 1
fi

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== CSV Fetch 技能快速测试 ===${NC}\n"

# 创建临时测试数据
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"

echo "📝 创建测试数据..."
cat > test_data.csv << EOF
id,name,age,city,salary
1,Alice,28,Beijing,12000
2,Bob,32,Shanghai,15000
3,Charlie,25,Beijing,8000
4,David,35,Shenzhen,18000
EOF

echo -e "\n${GREEN}✓ 测试数据创建成功${NC}"

# 测试 1: count
echo -e "\n${BLUE}测试 1: count（统计行数）${NC}"
if $XAN_PATH count test_data.csv | grep -q "4"; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 失败${NC}"
    exit 1
fi

# 测试 2: headers
echo -e "\n${BLUE}测试 2: headers（显示列名）${NC}"
if $XAN_PATH headers test_data.csv | grep -q "name"; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 失败${NC}"
    exit 1
fi

# 测试 3: view
echo -e "\n${BLUE}测试 3: view（预览数据）${NC}"
if $XAN_PATH view -l 2 test_data.csv > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 失败${NC}"
    exit 1
fi

# 测试 4: filter
echo -e "\n${BLUE}测试 4: filter（数值筛选）${NC}"
if $XAN_PATH filter 'age > 30' test_data.csv | grep -q "Bob"; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 失败${NC}"
    exit 1
fi

# 测试 5: search
echo -e "\n${BLUE}测试 5: search（字符串搜索）${NC}"
if $XAN_PATH search -s city 'Beijing' test_data.csv | grep -q "Alice"; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 失败${NC}"
    exit 1
fi

# 测试 6: sort
echo -e "\n${BLUE}测试 6: sort（排序）${NC}"
if $XAN_PATH sort -s age -N test_data.csv | tail -1 | grep -q "35"; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 失败${NC}"
    exit 1
fi

# 测试 7: stats
echo -e "\n${BLUE}测试 7: stats（统计信息）${NC}"
if $XAN_PATH stats -s salary test_data.csv | grep -q "mean"; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 失败${NC}"
    exit 1
fi

# 清理
cd - > /dev/null
rm -rf "$TEST_DIR"

echo -e "\n${GREEN}=== ✓ 所有测试通过 ===${NC}"
echo -e "${BLUE}技能已正确配置并可以正常使用！${NC}\n"
