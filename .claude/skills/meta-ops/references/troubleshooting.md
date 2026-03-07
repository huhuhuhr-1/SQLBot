# 故障排查和最佳实践

## 故障排查

### 连接失败

**症状**：无法连接到数据库

**排查步骤**：

1. 检查 JDBC URL 格式
2. 验证用户名和密码
3. 确认数据库服务运行
4. 检查防火墙和网络连接

**示例**：

```bash
# 测试网络连通性
ping localhost
telnet localhost 17082

# 验证数据库服务
ps aux | grep postgres
```

### 驱动错误

**症状**：ClassNotFoundException 或找不到驱动

**排查步骤**：

1. 确认驱动 JAR 路径正确：`.claude/skills/database-drivers/drivers/`
2. 验证驱动类名
3. 检查 JAR 文件完整性

**示例**：

```bash
# 检查驱动文件
ls -lh .claude/skills/database-drivers/drivers/

# 验证驱动类名
unzip -p postgresql-42.3.8.jar META-INF/services/java.sql.Driver
```

### 权限错误

**症状**：permission denied 或 insufficient privileges

**排查步骤**：

1. 确认用户有足够的权限（SELECT、CREATE 等）
2. 检查 schema 访问权限
3. 验证表空间权限

**示例**：

```bash
# 检查用户权限
psql -U sqlbot -d metadata_db -c "\du"

# 授予权限（PostgreSQL）
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sqlbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sqlbot;
```

## 最佳实践

### 1. 使用会话模式

所有操作都应使用 `skill-session-lib.sh` 创建会话目录：

```bash
source .claude/skills/shared/skill-session-lib.sh
skill_session_init meta-ops <action-type> "<description>"
# ... 执行操作 ...
skill_session_finish "操作完成"
```

### 2. 使用 skill-exec 统一入口

推荐使用 `skill-exec` 避免跨 shell 会话函数丢失问题：

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops <action-type> "<description>" -- \
  <command>
```

### 3. 记录日志

使用 `tee` 命令同时输出到文件和终端：

```bash
java -jar tool.jar [options] 2>&1 | tee "$(skill_session_log_path operation.log)"
```

### 4. 验证结果

执行关键操作后验证结果：

```bash
# 导入后查询数据源
java -jar meta-cli.jar datasource list

# 创建表后查看结构
java -jar meta-discovery.jar -o describe --schema public --table users
```

### 5. 使用 JSON 格式

对于需要脚本处理的结果，使用 `--format json`：

```bash
java -jar meta-discovery.jar -o full --format json --output metadata.json
```

### 6. 敏感信息保护

避免在日志中记录密码：

```bash
# ❌ 错误：密码会出现在日志中
echo "Connecting with password: $PASSWORD"

# ✅ 正确：使用配置文件或环境变量
java -jar tool.jar -u user -p "$PASSWORD" ...
```

## 协作技能

- **database-drivers**：统一管理数据库驱动 JAR 文件
- **data-integration**：执行数据同步（DataX）
- **data-quality**：数据质量检查
- **data-security**：敏感数据扫描和脱敏

## 调试技巧

### 启用详细输出

```bash
# Java 启用详细日志
java -verbose:class -jar tool.jar [options]

# Bash 脚本调试
bash -x script.sh
```

### 检查环境变量

```bash
# 查看所有环境变量
env | grep -i meta

# 检查 Java 版本
java -version
```

### 验证文件完整性

```bash
# 检查 JAR 文件
jar tf tool.jar | head -20

# 检查文件权限
ls -lh .claude/skills/meta-ops/scripts/
```