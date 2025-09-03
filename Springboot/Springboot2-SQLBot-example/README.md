# SQLBot SpringBoot 集成示例

这是一个展示如何将SQLBot集成到SpringBoot应用中的完整示例项目。

## 🚀 项目特性

- **完整的SQLBot集成**: 包含所有核心功能的示例代码
- **详细的日志记录**: 结构化日志，便于调试和监控
- **错误处理**: 完善的异常处理和错误信息
- **配置灵活**: 支持不同环境的配置
- **RESTful API**: 提供完整的测试接口

## 📋 项目结构

```
src/main/java/com/sqlbot/example/
├── controller/          # 控制器层
│   └── SQLBotTestController.java
├── service/            # 服务层
│   └── SQLBotTestService.java
├── model/              # 数据模型
│   ├── request/        # 请求模型
│   └── response/       # 响应模型
└── Application.java    # 主应用类

src/main/resources/
├── application.yml     # 应用配置
├── logback-spring.xml # 日志配置
└── templates/         # 前端模板
```

## ⚙️ 配置说明

### 1. SQLBot配置 (application.yml)

```yaml
sqlbot:
  url: http://10.20.14.100:8000          # SQLBot服务器地址
  connection-timeout: 10000               # 连接超时时间(ms)
  read-timeout: 30000                    # 读取超时时间(ms)
  timeout: 30000                         # 写入超时时间(ms)
  max-retries: 3                         # 最大重试次数
```

### 2. 日志配置

项目使用Logback作为日志框架，提供以下特性：

- **控制台输出**: 彩色日志，便于开发调试
- **文件输出**: 按日期和大小滚动
- **分类日志**: SQLBot相关日志单独存储
- **错误日志**: 错误日志单独收集

#### 日志文件结构

```
logs/
├── sqlbot-example.log          # 所有日志
├── sqlbot-example-error.log    # 错误日志
└── sqlbot-example-sqlbot.log   # SQLBot相关日志
```

#### 日志级别配置

```yaml
logging:
  level:
    com.sqlbot: DEBUG                    # SQLBot包日志级别
    com.sqlbot.example: DEBUG            # 示例应用日志级别
    com.sqlbot.springboot.starter: DEBUG # Starter包日志级别
    okhttp3: DEBUG                       # HTTP请求日志
    org.springframework.web: DEBUG       # Spring框架日志
```

## 🔧 使用方法

### 1. 启动应用

```bash
# 使用Maven
mvn spring-boot:run

# 或者打包后运行
mvn clean package
java -jar target/sqlbot-springboot-example-1.0.0.jar
```

### 2. 测试接口

#### 健康检查
```bash
curl http://localhost:8080/api/test/health
```

#### 获取令牌
```bash
curl -X POST "http://localhost:8080/api/test/token?username=admin&password=SQLBot@123456"
```

#### 获取数据源列表
```bash
curl http://localhost:8080/api/test/datasource
```

#### 测试聊天
```bash
curl -X POST http://localhost:8080/api/test/chat \
  -H "Content-Type: application/json" \
  -d '{
    "dbId": 1,
    "question": "查询用户表的数据",
    "chatId": "test_chat_123"
  }'
```

## 📊 日志示例

### 1. 请求日志

```
🚀 收到聊天测试请求 - 请求ID: 1756693000000
📋 聊天测试请求详情 - 数据源ID: 1, 问题: 查询用户表的数据, 聊天ID: test_chat_123
📤 转发请求到服务层
🧪 开始测试聊天功能 - 请求ID: 1756693000000
📋 聊天请求参数 - 数据源ID: 1, 问题: 查询用户表的数据, 聊天ID: test_chat_123
✅ chatId类型转换成功 - 字符串: 'test_chat_123' -> 整数: 123
📋 聊天请求参数验证通过 - 数据源ID: 1, 问题长度: 12, 聊天ID: 123
📤 调用SQLBot聊天接口 - 数据源ID: 1, 问题: 查询用户表的数据, 聊天ID: 123
```

### 2. HTTP请求日志

```
🚀 发起POST请求 - URL: http://10.20.14.100:8000/openapi/chat, 响应类型: ChatResponse
📤 请求体 - 类型: ChatRequest, 内容: {"dbId":1,"question":"查询用户表的数据","chatId":123}
🔑 已添加认证头 - Token: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
📥 收到POST响应 - URL: http://10.20.14.100:8000/openapi/chat, 状态码: 200, 响应大小: 256 bytes
🔍 处理响应 - 状态码: 200, 响应体长度: 256 字符
✅ 响应解析成功 - 类型: ChatResponse, 结果: ChatResponse@12345
✅ POST请求成功 - URL: http://10.20.14.100:8000/openapi/chat, 响应类型: ChatResponse, 结果: 非空
```

### 3. 成功响应日志

```
✅ 聊天测试成功 - 聊天记录ID: 456, 响应状态: SUCCESS, 答案长度: 128
📝 聊天答案内容: 根据您的查询，用户表中共有25条数据...
✅ 聊天测试成功完成 - 耗时: 1250ms, 聊天记录ID: 456
```

### 4. 错误日志

```
❌ 聊天测试失败 - 数据源ID: 1, 问题: 查询用户表的数据, 错误: HTTP 400 Bad Request
❌ 聊天测试失败 - 耗时: 1250ms, 错误: HTTP 400 Bad Request
```

## 🐛 故障排除

### 1. 常见问题

#### 连接超时
```
❌ 网络请求失败: connect timed out
```
**解决方案**: 检查SQLBot服务器地址和网络连接

#### 认证失败
```
❌ 认证失败: Invalid token
```
**解决方案**: 检查用户名密码，重新获取令牌

#### 参数错误
```
❌ 请求参数错误: dbId cannot be null
```
**解决方案**: 检查请求参数是否完整

### 2. 日志调试

启用详细日志：
```bash
# 设置系统属性
-Dsqlbot.debug=true

# 或在application.yml中设置
logging:
  level:
    com.sqlbot: DEBUG
    okhttp3: DEBUG
```

### 3. 性能监控

日志中包含性能指标：
- 请求耗时
- 响应大小
- 重试次数
- 错误统计

## 🔄 更新日志

### v1.0.0 (2025-01-01)
- 初始版本发布
- 完整的SQLBot集成
- 详细的日志记录
- 完善的错误处理

## 📝 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📞 支持

如有问题，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至: support@sqlbot.com
- 查看文档: https://docs.sqlbot.com
