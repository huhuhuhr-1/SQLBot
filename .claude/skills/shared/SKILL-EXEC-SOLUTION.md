# skill-exec 永久解决方案

## 问题总结

**原问题**：Claude Code 中每次 `Bash` 工具调用都是独立的 shell 会话，导致：

1. `source` 加载的函数无法跨会话使用
2. 需要手动管理会话目录和路径
3. 容易出现函数未定义错误
4. 命令冗长且容易出错

## 解决方案

创建了 **统一的执行入口脚本**：`.claude/skills/shared/bin/skill-exec`

### 核心特点

✅ **自动加载函数库**：无需手动 source
✅ **统一会话管理**：自动创建会话目录和文件
✅ **跨会话工作**：每次调用都是完整的执行环境
✅ **简化使用**：一行命令完成所有操作
✅ **错误处理**：自动捕获和显示错误
✅ **会话保留**：自动询问是否保留会话

## 使用方法

### 基本语法

```bash
.claude/skills/shared/bin/skill-exec \
  <skill-name> \
  <action-type> \
  "<description>" \
  -- <command>
```

### 示例

#### 1. 测试数据库连接

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops test-conn "测试 PostgreSQL 连接" -- \
  java -jar .claude/skills/meta-ops/assets/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o test
```

#### 2. 完整探查数据库

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops discovery-full "完整探查数据库" -- \
  java -jar .claude/skills/meta-ops/assets/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o full --format json \
    --output "$REPORT_FILE"
```

## 文件结构

```
.claude/skills/shared/
├── bin/
│   ├── skill-exec           # 主执行脚本
│   └── test-skill-exec      # 测试脚本
├── skill-session-lib.sh     # 会话管理函数库
├── SKILL-EXEC-GUIDE.md      # 详细使用指南
└── SKILL-EXEC-SOLUTION.md   # 本文档
```

## 会话目录结构

```
tmp/<skill-name>/
└── <action-type>_YYYYMMDD_HHMMSS/
    ├── reports/
    │   └── result.md          # 输出报告
    ├── logs/
    │   └── execution.log      # 执行日志
    └── README.md              # 会话说明
```

## 环境变量

使用 `skill-exec` 时，以下环境变量自动可用：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `$SESSION_ID` | 会话 ID | `test-conn_20260113_155242` |
| `$SESSION_DIR` | 会话目录 | `tmp/meta-ops/test-conn_20260113_155242` |
| `$LOG_FILE` | 日志文件路径 | `.../logs/execution.log` |
| `$REPORT_FILE` | 报告文件路径 | `.../reports/result.md` |
| `$SKILL_NAME` | 技能名称 | `meta-ops` |
| `$ACTION_TYPE` | 操作类型 | `test-conn` |

## 对比：旧方法 vs 新方法

### 旧方法（❌ 不推荐）

```bash
# 第一步：初始化会话
source .claude/skills/shared/skill-session-lib.sh
skill_session_init meta-ops test-conn "测试连接"

# 第二步：获取路径
LOG_FILE=$(skill_session_log_path test.log)
REPORT_FILE=$(skill_session_report_path result.md)

# 第三步：执行命令
java -jar .claude/skills/meta-ops/assets/meta-discovery.jar \
  -u sqlbot -p sqlbot -j jdbc:postgresql://localhost:8086/sqlbot \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o test --output "$REPORT_FILE" 2>&1 | tee "$LOG_FILE"

# 第四步：完成会话
skill_session_finish "测试完成"
```

**问题**：
- ❌ 跨 Bash 调用时函数丢失
- ❌ 命令冗长（4 步）
- ❌ 容易出错（忘记 source、路径错误）
- ❌ 不适合 Claude Code

### 新方法（✅ 推荐）

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops test-conn "测试连接" -- \
  java -jar .claude/skills/meta-ops/assets/meta-discovery.jar \
    -u sqlbot -p sqlbot -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o test
```

**优势**：
- ✅ 自动加载函数库
- ✅ 一行命令完成
- ✅ 自动管理会话
- ✅ 完美适配 Claude Code

## 验证安装

运行测试脚本验证 `skill-exec` 是否正常工作：

```bash
bash .claude/skills/shared/bin/test-skill-exec
```

预期输出：
```
测试 skill-exec 脚本...

测试 1：执行简单命令
初始化会话...
✓ 会话已创建
  技能: test
  操作: echo-output
  会话: echo-output_20260113_XXXXXX

执行命令：...
Hello from skill-exec!
✓ 命令执行成功

✓ 测试完成

检查会话目录：
tmp/test/echo-output_20260113_XXXXXX/
```

## 更新技能文档

### 推荐的技能 SKILL.md 结构

```markdown
## 执行规范（重要）

### ⚠️ 使用 skill-exec 统一入口

**所有操作必须通过 `skill-exec` 执行**，确保会话管理和路径正确。

```bash
.claude/skills/shared/bin/skill-exec \
  <skill-name> <action-type> "<description>" -- \
  <command>
```

**关键优势**：
- ✅ 自动管理会话目录和文件
- ✅ 统一的日志和报告路径
- ✅ 避免跨 shell 会话函数丢失问题
- ✅ 支持 Claude Code 的 Bash 工具调用

## 使用示例

### 示例 1：测试连接

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops test-conn "测试连接" -- \
  java -jar .claude/skills/meta-ops/assets/tool.jar ...
```

### 示例 2：执行探查

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops discovery-full "完整探查" -- \
  java -jar .claude/skills/meta-ops/assets/tool.jar ... \
    --output "$REPORT_FILE"
```
```

## 故障排查

### 问题 1：权限错误

```bash
Permission denied: .claude/skills/shared/bin/skill-exec
```

**解决**：
```bash
chmod +x .claude/skills/shared/bin/skill-exec
```

### 问题 2：不在项目根目录

```bash
错误：不在项目根目录（找不到 .claude/skills）
```

**解决**：
```bash
cd /path/to/project
pwd  # 确认在项目根目录
```

### 问题 3：换行符问题

```bash
$'\r': 未找到命令
```

**解决**：
```bash
sed -i 's/\r$//' .claude/skills/shared/bin/skill-exec
chmod +x .claude/skills/shared/bin/skill-exec
```

## 自动化建议

### 创建快捷命令

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
# skill-exec 快捷方式
alias skill-exec='$PROJECT_ROOT/.claude/skills/shared/bin/skill-exec'
```

### 创建包装脚本

为常用操作创建包装脚本：

```bash
# .claude/skills/meta-ops/scripts/test-connection.sh
#!/bin/bash
.claude/skills/shared/bin/skill-exec \
  meta-ops test-conn "测试数据库连接" -- \
  java -jar .claude/skills/meta-ops/assets/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o test
```

使用：
```bash
bash .claude/skills/meta-ops/scripts/test-connection.sh
```

## 总结

| 方面 | 旧方法 | 新方法（skill-exec） |
|------|--------|---------------------|
| **会话管理** | 手动 source 和调用 | 自动管理 |
| **跨会话** | ❌ 不支持 | ✅ 支持 |
| **使用复杂度** | 高（多行命令） | 低（一行命令） |
| **可维护性** | 低（容易出错） | 高（统一入口） |
| **适合场景** | 交互式 shell | Claude Code / 脚本 |

**推荐**：所有 Claude Code 中的技能操作都使用 `skill-exec` 执行。

## 相关文档

- **详细指南**：`.claude/skills/shared/SKILL-EXEC-GUIDE.md`
- **函数库**：`.claude/skills/shared/skill-session-lib.sh`
- **技能示例**：`.claude/skills/meta-ops/SKILL.md`

## 版本历史

- **v1.0.0** (2026-01-13)：初始版本
  - 创建统一的执行入口脚本
  - 自动会话管理
  - 环境变量支持
  - 错误处理和日志记录