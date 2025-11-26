# Springboot-SQLBot-starter 完善设计文档

## 1. 概述

本文档旨在设计和完善 Springboot-SQLBot-starter 项目，以全面覆盖 SQLBot backend 提供的所有接口。当前starter只覆盖了部分接口，需要添加对新接口（如plan接口）和其他缺失接口的支持。

## 2. 当前接口覆盖情况分析

### 2.1 已覆盖接口
- `/openapi/getToken` - 获取令牌接口
- `/openapi/getDataSourceList` - 获取数据源列表接口
- `/openapi/chat` - 聊天接口
- `/openapi/getData` - 获取数据接口
- `/openapi/getRecommend` - 获取推荐接口
- `/openapi/deleteChats` - 清理接口
- `/openapi/addPg` - 新增pg接口

### 2.2 未覆盖接口
- `/openapi/getDataSourceByIdOrName` - 根据ID或名称获取数据源
- `/openapi/getDataByDbIdAndSql` - 通过dbid和sql获取数据
- `/openapi/createRecordAndBindDb` - 创建记录并绑定数据源
- `/openapi/analysis` - 分析接口
- `/openapi/predict` - 预测接口
- `/openapi/uploadExcelAndCreateDatasource` - 上传Excel并创建数据源
- `/openapi/plan` - 智能规划执行接口（新建接口）
- `/openapi/deleteDatasource` - 删除数据源
- `/openapi/deleteExcels` - 清空excel

## 3. 设计目标

### 3.1 功能完整性
- 覆盖SQLBot backend的所有主要API接口
- 提供同步和异步调用方式
- 支持流式响应处理

### 3.2 易用性
- 提供简单直观的API调用方式
- 封装复杂的请求构建和响应解析逻辑
- 提供完整的错误处理和异常映射

### 3.3 扩展性
- 采用模块化设计，便于添加新接口
- 支持自定义配置和扩展
- 遵循Spring Boot自动配置最佳实践

## 4. 实现方案

### 4.1 更新SQLBotConstants.java
需要在API路径常量中添加新的接口路径：

```java
public static final String GET_DATASOURCE_BY_ID_OR_NAME = "/openapi/getDataSourceByIdOrName";
public static final String GET_DATA_BY_DB_ID_AND_SQL = "/openapi/getDataByDbIdAndSql";
public static final String CREATE_RECORD_AND_BIND_DB = "/openapi/createRecordAndBindDb";
public static final String ANALYSIS = "/openapi/analysis";
public static final String PREDICT = "/openapi/predict";
public static final String UPLOAD_EXCEL_AND_CREATE_DATASOURCE = "/openapi/uploadExcelAndCreateDatasource";
public static final String PLAN = "/openapi/plan";
public static final String DELETE_DATASOURCE = "/openapi/deleteDatasource";
public static final String DELETE_EXCELS = "/openapi/deleteExcels";
```

### 4.2 创建新的数据模型类
为新接口创建对应的请求/响应数据模型：

#### 4.2.1 DataSourceIdNameRequest.java
```java
public class DataSourceIdNameRequest {
    private String name;
    private Integer id;
    // getters and setters
}
```

#### 4.2.2 DataSourceRequestWithSql.java
```java
public class DataSourceRequestWithSql {
    private String dbId;
    private String sql;
    // getters and setters
}
```

#### 4.2.3 DbBindChat.java
```java
public class DbBindChat {
    private String title;
    private Integer dbId;
    private Integer origin;
    // getters and setters
}
```

#### 4.2.4 PlanRequest.java
```java
public class PlanRequest extends OpenChatQuestion {
    private Integer maxSteps;
    private Boolean enableRetry;
    private Integer maxRetries;
    private Map<String, Object> context;
    // getters and setters
}
```

### 4.3 扩展SQLBotService接口
创建新的方法来支持未覆盖的接口：

#### 4.3.1 同步方法
```java
// 根据ID或名称获取数据源
DataSourceResponse getDataSourceByIdOrName(String token, DataSourceIdNameRequest request);

// 通过dbid和sql获取数据
Object getDataByDbIdAndSql(String token, DataSourceRequestWithSql request);

// 创建记录并绑定数据源
Object createRecordAndBindDb(DbBindChat request);

// 分析接口
StreamingResponse analysis(String token, OpenChat request);

// 预测接口
StreamingResponse predict(String token, OpenChat request);

// 上传Excel并创建数据源
Object uploadExcelAndCreateDatasource(MultipartFile file, Map<String, Object> params);

// 智能规划执行接口
StreamingResponse plan(String token, PlanRequest request);

// 删除数据源
Object deleteDatasource(int id);

// 清空excel
Object deleteExcels(String token, CurrentUser user);
```

#### 4.3.2 异步方法
```java
CompletableFuture<DataSourceResponse> getDataSourceByIdOrNameAsync(String token, DataSourceIdNameRequest request);
CompletableFuture<Object> getDataByDbIdAndSqlAsync(String token, DataSourceRequestWithSql request);
CompletableFuture<Object> planAsync(String token, PlanRequest request);
// ... 其他异步方法
```

### 4.4 实现SQLBotAutoConfiguration
确保新的API路径和默认值在自动配置中可用：

```java
@Configuration
@ConditionalOnProperty(prefix = SQLBotConstants.CONFIG_PREFIX, name = "enabled", 
                      havingValue = "true", matchIfMissing = true)
@EnableConfigurationProperties(SQLBotProperties.class)
public class SQLBotAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public SQLBotService sqlBotService(SQLBotProperties properties, 
                                       RestTemplate restTemplate,
                                       ObjectMapper objectMapper) {
        return new SQLBotServiceImpl(properties, restTemplate, objectMapper);
    }
}
```

### 4.5 创建通用响应处理机制
为流式响应（如chat、analysis、predict、plan）创建统一的处理器：

```java
public interface StreamingResponseHandler<T> {
    void onMessage(T message);
    void onError(Exception e);
    void onComplete();
}

public class StreamResponseCallback<T> implements StreamingResponseHandler<T> {
    // 实现流式响应处理逻辑
}
```

### 4.6 添加配置选项
在配置属性类中添加新接口的配置选项：

```java
@ConfigurationProperties(prefix = SQLBotConstants.CONFIG_PREFIX)
public class SQLBotProperties {
    // 现有配置...
    
    // 新增接口相关配置
    private PlanConfig plan = new PlanConfig();
    private AnalysisConfig analysis = new AnalysisConfig();
    private PredictConfig predict = new PredictConfig();
    
    // getters and setters
}

public class PlanConfig {
    private int maxSteps = 10;
    private boolean enableRetry = true;
    private int maxRetries = 3;
    // getters and setters
}
```

### 4.7 实现重试和错误处理机制
为新接口实现统一的重试和错误处理机制：

```java
public class RetryableSQLBotService extends SQLBotServiceImpl {
    // 实现重试逻辑
}
```

## 5. 测试计划

### 5.1 单元测试
为新添加的接口方法编写单元测试，验证请求构建和响应解析逻辑。

### 5.2 集成测试
编写集成测试，验证与SQLBot backend的实际交互。

### 5.3 异步调用测试
测试异步方法的正确性和性能表现。

### 5.4 流式响应测试
测试流式响应的处理，特别是chat、analysis、predict、plan等接口。

## 6. 向后兼容性

- 保留所有现有接口和方法
- 确保默认配置值与现有配置兼容
- 提供清晰的升级指南

## 7. 实施步骤

### 第一阶段：常量和模型
1. 更新 SQLBotConstants.java 添加新接口路径
2. 创建新的请求/响应数据模型类

### 第二阶段：服务接口和实现
3. 扩展 SQLBotService 接口
4. 实现新接口的方法

### 第三阶段：配置和自动配置
5. 更新配置属性类
6. 完善自动配置类

### 第四阶段：高级功能
7. 实现流式响应处理机制
8. 添加重试和错误处理

### 第五阶段：测试和文档
9. 编写测试用例
10. 更新使用文档

## 8. 预期成果

完成此完善工作后，Springboot-SQLBot-starter 将：

1. 完全覆盖 SQLBot backend 的所有主要接口
2. 提供一致的API调用体验
3. 支持同步和异步调用
4. 支持流式响应处理
5. 具备良好的扩展性
6. 遵循 Spring Boot 最佳实践
7. 提供全面的错误处理和重试机制

## 9. 质量保证

- 遵循 Java 编码规范
- 实现全面的异常处理
- 提供详尽的 JavaDoc 文档
- 实现单元测试覆盖率达到80%以上