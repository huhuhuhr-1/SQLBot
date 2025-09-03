# SQLBot Spring Boot Starter

## 🚀 快速开始

### 1. 添加依赖

```xml
<dependency>
    <groupId>com.sqlbot</groupId>
    <artifactId>springboot-sqlbot-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

### 2. 配置属性

```yaml
sqlbot:
  enabled: true
  url: http://10.20.14.100:8000
  connection-timeout: 10000
  read-timeout: 30000
  timeout: 30000
  max-retries: 3
```

### 3. 使用示例

```java
@Autowired
private SQLBotTemplate sqlBotTemplate;

// 链式调用
sqlBotTemplate
    .login("admin", "SQLBot@123456")
    .selectDataSource(1)
    .ask("查询用户表数据");
```

## 🔧 最近修复

### JSON反序列化问题修复

**问题描述**：
API返回的JSON结构与响应模型类不匹配，导致反序列化失败。

**错误信息**：
```
Unrecognized field "code" (class com.sqlbot.springboot.starter.model.response.GetTokenResponse), 
not marked as ignorable (4 known properties: "token_type", "chat_id", "access_token", "expire"])
```

**修复内容**：

1. **创建通用API响应包装类** `ApiResponse<T>`
   - 处理API的统一响应格式：`{code, data, msg}`
   - 提供成功状态检查和数据提取方法

2. **修复GetTokenResponse类**
   - 继承自`ApiResponse<TokenData>`
   - 保持向后兼容的便捷方法
   - 正确处理嵌套的令牌数据结构

3. **修复数据源列表获取**
   - 使用`ApiResponse<List<DataSourceResponse>>`包装
   - 正确处理API响应状态码

**API响应结构**：
```json
{
  "code": 0,
  "data": {
    "access_token": "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expire": "2025-09-09 06:12:58",
    "chat_id": null
  },
  "msg": null
}
```

## 📋 功能特性

- ✅ HTTP客户端封装（基于OkHttp）
- ✅ 自动重试机制
- ✅ 完整的异常处理
- ✅ 链式调用模板
- ✅ 自动配置支持
- ✅ 完整的JavaDoc文档

## 🐛 问题排查

如果遇到问题，请检查：

1. **网络连接**：确保能访问SQLBot服务器
2. **配置正确性**：检查URL、用户名、密码等配置
3. **API版本**：确认API路径是否正确
4. **日志输出**：查看详细的错误日志

## 📞 技术支持

如有问题，请联系SQLBot团队。