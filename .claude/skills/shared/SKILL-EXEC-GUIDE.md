# skill-exec 永久解决方案

## 问题背景

**原问题**：每个 `Bash` 工具调用都是独立的 shell 会话，`source` 加载的函数无法跨会话使用。

**错误示例**：
```bash
# ❌ 第一个 bash：加载函数
bash: source .claude/skills/shared/skill-session-lib.sh
bash: skill_session_init meta-ops test-conn "测试"

# ❌ 第二个 bash：函数不存在
bash: LOG_FILE=$(skill_session_log_path test.log)
# Error: command not found: skill_session_log_path
```

## 解决方案

使用统一的执行入口脚本 `skill-exec`，自动处理会话管理。

### 方案特点

✅ **自动加载函数库**：无需手动 source
✅ **统一会话管理**：自动创建会话目录
✅ **跨会话工作**：每次调用都是完整的执行环境
✅ **简化使用**：一行命令完成所有操作

## 使用方法

### 基本语法

```bash
.claude/skills/shared/bin/skill-exec \
  <skill-name> \
  <action-type> \
  "<description>" \
  -- <command>
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `skill-name` | 技能名称 | meta-ops, data-quality |
| `action-type` | 操作类型 | test-conn, discovery-full |
| `description` | 操作描述 | "测试数据库连接" |
| `--` | 分隔符 | 必须添加 |
| `command` | 执行的命令 | 任意 shell 命令 |

### 命令中可用的环境变量

命令执行时，以下环境变量自动设置：

- `$SESSION_ID` - 会话 ID
- `$SESSION_DIR` - 会话目录
- `$LOG_FILE` - 日志文件路径
- `$REPORT_FILE` - 报告文件路径
- `$SKILL_NAME` - 技能名称
- `$ACTION_TYPE` - 操作类型

## 使用示例

### 示例 1：测试数据库连接

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

**输出**：
```
初始化会话...
✓ 会话已创建
  技能: meta-ops
  操作: test-conn
  描述: 测试 PostgreSQL 连接
  会话: test-conn_20260113_155242
  目录: tmp/meta-ops/test-conn_20260113_155242

执行命令：
java -jar .claude/skills/meta-ops/assets/meta-discovery.jar ...

数据库连接测试成功

✓ 命令执行成功
```

### 示例 2：完整探查数据库

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

**说明**：
- 使用 `$REPORT_FILE` 环境变量，自动映射到会话的 `reports/result.md`
- 输出文件自动保存到 `tmp/meta-ops/discovery-full_YYYYMMDD_HHMMSS/reports/`

### 示例 3：列出所有表

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops list-tables "列出所有表" -- \
  java -jar .claude/skills/meta-ops/assets/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o tables \
    --output "$REPORT_FILE"
```

### 示例 4：执行多个命令

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops multi-step "多步骤操作" -- \
  bash -c '
    echo "步骤1: 测试连接" &&
    java -jar .claude/skills/meta-ops/assets/meta-discovery.jar -o test &&
    echo "步骤2: 列出表" &&
    java -jar .claude/skills/meta-ops/assets/meta-discovery.jar -o tables
  '
```

## 会话管理

### 会话目录结构

```
tmp/meta-ops/
└── test-conn_20260113_155242/
    ├── reports/
    │   └── result.md          # 输出报告
    ├── logs/
    │   └── execution.log      # 执行日志
    └── README.md              # 会话说明
```

### 会话保留策略

执行完成后会询问：
```
是否保留此会话？[Y/n]:
```

- **默认保留（Y）**：会话目录保留，用于后续查看
- **删除（n）**：立即删除会话目录

### 自动保留

设置环境变量跳过询问：

```bash
# 自动保留
export PRESERVE_SESSION=true
.claude/skills/shared/bin/skill-exec meta-ops test-conn "测试" -- <command>

# 自动清理
export AUTO_CLEANUP=true
.claude/skills/shared/bin/skill-exec meta-ops test-conn "测试" -- <command>
```

## 技能文档更新

在技能的 `SKILL.md` 中，将原来的命令示例替换为 `skill-exec`：

### ❌ 旧版本（不推荐）

```markdown
## 使用示例

```bash
source .claude/skills/shared/skill-session-lib.sh
skill_session_init meta-ops test-conn "测试"
LOG_FILE=$(skill_session_log_path test.log)
REPORT_FILE=$(skill_session_report_path result.md)

java -jar tool.jar --output "$REPORT_FILE" 2>&1 | tee "$LOG_FILE"
skill_session_finish "完成"
```
```

### ✅ 新版本（推荐）

```markdown
## 使用示例

### 测试数据库连接

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

### 完整探查数据库

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops discovery-full "完整探查" -- \
  java -jar .claude/skills/meta-ops/assets/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o full --format json \
    --output "$REPORT_FILE"
```

## 高级用法

### 创建快捷命令

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
# skill-exec 快捷方式
alias skill-exec='$PROJECT_ROOT/.claude/skills/shared/bin/skill-exec'
```

使用：

```bash
skill-exec meta-ops test-conn "测试" -- <command>
```

### 包装常用操作

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

## 故障排查

### 问题 1：命令找不到

```bash
Error: command not found: skill-exec
```

**解决**：使用完整路径
```bash
.claude/skills/shared/bin/skill-exec ...
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

### 问题 3：权限错误

```bash
Permission denied: .claude/skills/shared/bin/skill-exec
```

**解决**：
```bash
chmod +x .claude/skills/shared/bin/skill-exec
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