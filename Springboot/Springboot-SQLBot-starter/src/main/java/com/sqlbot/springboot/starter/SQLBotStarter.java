package com.sqlbot.springboot.starter;

import com.sqlbot.springboot.starter.api.auth.AuthService;
import com.sqlbot.springboot.starter.api.user.UserService;
import com.sqlbot.springboot.starter.api.datasource.DataSourceService;
import com.sqlbot.springboot.starter.api.assistant.AssistantService;
import com.sqlbot.springboot.starter.api.aimodel.AiModelService;
import com.sqlbot.springboot.starter.api.terminology.TerminologyService;
import com.sqlbot.springboot.starter.api.data_training.DataTrainingService;
import com.sqlbot.springboot.starter.api.chat.ChatService;
import com.sqlbot.springboot.starter.api.dashboard.DashboardService;
import com.sqlbot.springboot.starter.api.mcp.McpService;
import com.sqlbot.springboot.starter.api.table_relation.TableRelationService;
import com.sqlbot.springboot.starter.api.demo.DemoService;
import com.sqlbot.springboot.starter.api.settings.SettingsService;
import com.sqlbot.springboot.starter.api.workspace.WorkspaceService;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

/**
 * SQLBot主服务类
 * 聚合所有API模块的服务类，提供统一的访问入口
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class SQLBotStarter {

    @Getter
    private final AuthService authService;
    
    @Getter
    private final UserService userService;
    
    @Getter
    private final DataSourceService dataSourceService;
    
    @Getter
    private final AssistantService assistantService;
    
    @Getter
    private final AiModelService aiModelService;
    
    @Getter
    private final TerminologyService terminologyService;
    
    @Getter
    private final DataTrainingService dataTrainingService;
    
    @Getter
    private final ChatService chatService;
    
    @Getter
    private final DashboardService dashboardService;
    
    @Getter
    private final McpService mcpService;
    
    @Getter
    private final TableRelationService tableRelationService;
    
    @Getter
    private final DemoService demoService;

    @Getter
    private final SettingsService settingsService;
    
    @Getter
    private final WorkspaceService workspaceService;

    /**
     * 构造SQLBot主服务
     *
     * @param properties SQLBot配置属性
     */
    public SQLBotStarter(SQLBotProperties properties) {
        log.info("正在初始化SQLBot主服务");
        
        this.authService = new AuthService(properties);
        this.userService = new UserService(properties);
        this.dataSourceService = new DataSourceService(properties);
        this.assistantService = new AssistantService(properties);
        this.aiModelService = new AiModelService(properties);
        this.terminologyService = new TerminologyService(properties);
        this.dataTrainingService = new DataTrainingService(properties);
        this.chatService = new ChatService(properties);
        this.dashboardService = new DashboardService(properties);
        this.mcpService = new McpService(properties);
        this.tableRelationService = new TableRelationService(properties);
        this.demoService = new DemoService(properties);
        this.settingsService = new SettingsService(properties);
        this.workspaceService = new WorkspaceService(properties);
        
        log.info("SQLBot主服务初始化完成");
    }
    
    /**
     * 获取认证服务
     *
     * @return 认证服务实例
     */
    public AuthService getAuth() {
        return authService;
    }
    
    /**
     * 获取用户服务
     *
     * @return 用户服务实例
     */
    public UserService getUser() {
        return userService;
    }
    
    /**
     * 获取数据源服务
     *
     * @return 数据源服务实例
     */
    public DataSourceService getDataSource() {
        return dataSourceService;
    }
    
    /**
     * 获取助手服务
     *
     * @return 助手服务实例
     */
    public AssistantService getAssistant() {
        return assistantService;
    }
    
    /**
     * 获取AI模型服务
     *
     * @return AI模型服务实例
     */
    public AiModelService getAiModel() {
        return aiModelService;
    }
    
    /**
     * 获取术语服务
     *
     * @return 术语服务实例
     */
    public TerminologyService getTerminology() {
        return terminologyService;
    }
    
    /**
     * 获取数据训练服务
     *
     * @return 数据训练服务实例
     */
    public DataTrainingService getDataTraining() {
        return dataTrainingService;
    }
    
    /**
     * 获取聊天服务
     *
     * @return 聊天服务实例
     */
    public ChatService getChat() {
        return chatService;
    }
    
    /**
     * 获取仪表板服务
     *
     * @return 仪表板服务实例
     */
    public DashboardService getDashboard() {
        return dashboardService;
    }
    
    /**
     * 获取MCP服务
     *
     * @return MCP服务实例
     */
    public McpService getMcp() {
        return mcpService;
    }
    
    /**
     * 获取表关系服务
     *
     * @return 表关系服务实例
     */
    public TableRelationService getTableRelation() {
        return tableRelationService;
    }
    
    /**
     * 获取Demo服务
     *
     * @return Demo服务实例
     */
    public DemoService getDemo() {
        return demoService;
    }
    
    /**
     * 获取设置服务
     *
     * @return 设置服务实例
     */
    public SettingsService getSettings() {
        return settingsService;
    }
    
    /**
     * 获取工作空间服务
     *
     * @return 工作空间服务实例
     */
    public WorkspaceService getWorkspace() {
        return workspaceService;
    }
}