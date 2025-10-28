# Springboot-SQLBot-starter 完善设计文档 - 第二阶段

## 1. 概述

在第一阶段完成基础API覆盖后，本阶段将扩展Springboot-SQLBot-starter以覆盖APIRouter中定义的所有接口，并按照不同的业务领域组织代码结构。

## 2. 需要覆盖的API模块

根据提供的APIRouter配置，需要覆盖的模块包括：
- openapi - 已部分覆盖
- demo - 已部分覆盖
- login - 认证相关接口
- user - 用户管理接口
- workspace - 工作空间接口
- assistant - 助手相关接口
- aimodel - AI模型接口
- terminology - 术语管理接口
- data_training - 数据训练接口
- datasource - 数据源管理接口
- chat - 聊天相关接口
- dashboard_api - 仪表板接口
- mcp - MCP相关接口
- table_relation - 表关系接口

## 3. 目录结构设计

为了更好地组织代码，重新设计目录结构：

```
src/main/java/com/sqlbot/springboot/starter/
├── api/
│   ├── openapi/
│   │   ├── OpenApiService.java
│   │   ├── OpenApiTemplate.java
│   │   └── model/
│   │       ├── request/
│   │       └── response/
│   ├── auth/
│   │   ├── AuthService.java
│   │   ├── AuthTemplate.java
│   │   └── model/
│   │       ├── request/
│   │       └── response/
│   ├── user/
│   │   ├── UserService.java
│   │   ├── UserTemplate.java
│   │   └── model/
│   │       ├── request/
│   │       └── response/
│   ├── datasource/
│   │   ├── DataSourceService.java
│   │   ├── DataSourceTemplate.java
│   │   └── model/
│   │       ├── request/
│   │       └── response/
│   ├── chat/
│   │   ├── ChatService.java
│   │   ├── ChatTemplate.java
│   │   └── model/
│   │       ├── request/
│   │       └── response/
│   └── ... 其他模块
├── config/
├── constant/
├── exception/
├── util/
└── SQLBotStarter.java (主入口)
```

## 4. 实现方案

### 4.1 创建模块化服务类

为每个API模块创建专门的服务类：
- OpenApiService - 覆盖openapi模块接口
- AuthService - 覆盖login模块接口
- UserService - 覆盖user模块接口
- WorkspaceService - 覆盖workspace模块接口
- AssistantService - 覆盖assistant模块接口
- AiModelService - 覆盖aimodel模块接口
- TerminologyService - 覆盖terminology模块接口
- DataTrainingService - 覆盖data_training模块接口
- DataSourceService - 覆盖datasource模块接口
- ChatService - 覆盖chat模块接口
- DashboardService - 覆盖dashboard_api模块接口
- McpService - 覆盖mcp模块接口
- TableRelationService - 覆盖table_relation模块接口
- DemoService - 覆盖demo模块接口

### 4.2 创建统一的主服务类

创建一个主服务类，聚合所有模块服务，提供统一的API入口。

### 4.3 更新SQLBotTemplate

扩展SQLBotTemplate，使其能够访问所有模块的服务。

## 5. 实施步骤

### 第一步：创建目录结构和基础模块
1. 创建新的目录结构
2. 为每个模块创建基础服务类

### 第二步：实现具体接口
3. 为每个模块实现具体的接口方法

### 第三步：创建主入口服务
4. 创建聚合所有模块的主服务类

### 第四步：测试和验证
5. 测试所有新实现的接口

## 6. 向后兼容性

- 保持现有的OpenApiService和相关接口不变
- 新的模块服务以可选方式集成
- 确保现有功能不受影响

## 7. 预期成果

完成此阶段后，Springboot-SQLBot-starter将：
1. 覆盖所有APIRouter中定义的接口
2. 采用清晰的模块化目录结构
3. 支持所有业务领域的功能
4. 保持良好的可维护性和扩展性