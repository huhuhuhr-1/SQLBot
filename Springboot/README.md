# 🚀 SQLBot Spring Boot 项目使用指南

## 📁 项目结构

```
Springboot/
├── Springboot-SQLBot-starter/          # 核心启动器
├── Springboot2-SQLBot-example/         # Spring Boot 2.x 示例
└── Springboot3-SQLBot-example/         # Spring Boot 3.x 示例
```

## 🔧 1. Springboot-SQLBot-starter (核心启动器)

### 安装到本地Maven仓库

```bash
cd Springboot/Springboot-SQLBot-starter
mvn clean install
```

### 在其他项目中使用

```xml
<dependency>
    <groupId>com.sqlbot</groupId>
    <artifactId>springboot-sqlbot-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

### 配置示例

```yaml
sqlbot:
  base-url: http://localhost:8080
  username: admin
  password: admin123
  timeout: 30000
  debug: true
```

### 代码使用示例

```java
@Autowired
private SQLBotClient sqlBotClient;

// 获取Token
GetTokenResponse token = sqlBotClient.getToken("username", "password", true);

// 聊天
ChatResponse chat = sqlBotClient.chat(dbId, "你的问题", chatId);

// 获取数据
GetDataResponse data = sqlBotClient.getData(chatRecordId);

// 获取推荐
GetRecommendResponse recommend = sqlBotClient.getRecommend(chatRecordId);

// 清理聊天记录
CleanResponse clean = sqlBotClient.clean(chatIds);
```

## 🎯 2. Springboot2-SQLBot-example (Spring Boot 2.x 示例)

### 启动方式

```bash
cd Springboot/Springboot2-SQLBot-example
mvn spring-boot:run
```

### 访问地址

- **主页**: `http://localhost:8080/`
- **聊天测试**: `http://localhost:8080/chat-test`
- **API文档**: `http://localhost:8080/swagger-ui.html`

### 测试账号

- **用户名**: `test`
- **密码**: `test123`

## 🎯 3. Springboot3-SQLBot-example (Spring Boot 3.x 示例)

### 启动方式

```bash
cd Springboot/Springboot3-SQLBot-example
mvn spring-boot:run
```

### 访问地址

- **主页**: `http://localhost:8080/`
- **聊天测试**: `http://localhost:8081/chat-test`
- **API文档**: `http://localhost:8081/swagger-ui.html`

### 测试账号

- **用户名**: `test`
- **密码**: `test123`

## 🧪 快速测试流程

### 1. 启动项目

```bash
# 终端1：启动Spring Boot 2.x示例
cd Springboot/Springboot2-SQLBot-example
mvn spring-boot:run

# 终端2：启动Spring Boot 3.x示例
cd Springboot/Springboot3-SQLBot-example
mvn spring-boot:run
```

### 2. 访问测试页面

- Spring Boot 2.x: `http://localhost:8080/chat-test`
- Spring Boot 3.x: `http://localhost:8081/chat-test`

### 3. 测试步骤

1. **登录**: 使用 `test/test123` 账号登录
2. **选择数据源**: 从下拉列表选择数据源
3. **开始聊天**: 在输入框中输入问题
4. **观察SSE响应**: 实时查看流式聊天过程
5. **查看结果**: 聊天完成后显示数据和推荐问题

## 🔌 API接口说明

### 认证接口

```http
POST /api/test/login
Content-Type: application/json

{
  "username": "test",
  "password": "test123",
  "createChat": true
}
```

### 数据源接口

```http
GET /api/test/datasources
```

### 聊天接口 (SSE流式)

```http
POST /api/test/chat
Content-Type: application/json

{
  "dbId": 1,
  "question": "查询用户数据",
  "chatId": "chat_123"
}
```

### 获取数据接口

```http
POST /api/test/getData
Content-Type: application/json

{
  "chatRecordId": 123
}
```

### 推荐接口 (SSE流式)

```http
POST /api/test/recommend
Content-Type: application/json

{
  "chatRecordId": 123
}
```

### 清理接口

```http
POST /api/test/clean
Content-Type: application/json

{
  "chatIds": [1, 2, 3]
}
```

## 📊 SSE消息格式

### 消息类型

- `id`: 返回聊天记录ID
- `start`: 开始处理消息
- `sql-result`: SQL生成过程
- `sql`: 最终SQL语句
- `chart-result`: 图表配置生成过程
- `chart`: 最终图表配置
- `finish`: 结束信号
- `error`: 错误信息

### 示例消息

```json
data: {"type": "id", "id": 123}

data: {"type": "start", "message": "开始处理您的问题..."}

data: {"type": "sql", "content": "SELECT * FROM users"}

data: {"type": "finish"}
```

## 🛠️ 开发集成

### 添加依赖

```xml
<dependency>
    <groupId>com.sqlbot</groupId>
    <artifactId>springboot-sqlbot-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

### 启用自动配置

```java
@SpringBootApplication
@EnableAsync  // 启用异步支持
public class YourApplication {
    public static void main(String[] args) {
        SpringApplication.run(YourApplication.class, args);
    }
}
```

### 注入客户端

```java
@Service
public class YourService {
    
    @Autowired
    private SQLBotClient sqlBotClient;
    
    @Autowired
    private SQLBotTemplate sqlBotTemplate;
    
    public void chatExample() {
        // 使用客户端
        ChatResponse response = sqlBotClient.chat(1L, "查询数据", "chat_123");
        
        // 使用模板（链式调用）
        sqlBotTemplate
            .withDataSource(1L)
            .chat("查询数据")
            .getData()
            .getRecommend();
    }
}
```

## ⚠️ 注意事项

1. **端口配置**: 确保两个示例项目使用不同端口
2. **异步支持**: 已启用`@EnableAsync`注解
3. **SSE连接**: 服务端自动管理连接生命周期
4. **超时设置**: SSE连接30秒超时
5. **错误处理**: 完善的异常处理和资源清理

## 🎯 总结

三个Spring Boot项目完全就绪，支持：

- ✅ 完整的SQLBot API集成
- ✅ SSE流式聊天和推荐
- ✅ 现代化的Web测试界面
- ✅ Spring Boot 2.x和3.x兼容性
- ✅ 完善的错误处理和资源管理

**现在可以开始测试了！** 🚀

---

## 📝 更新日志

- **v1.0.0** - 初始版本，支持Spring Boot 2.x和3.x
- 完整的SSE流式聊天功能
- 现代化的Web测试界面
- 完善的错误处理和资源管理
