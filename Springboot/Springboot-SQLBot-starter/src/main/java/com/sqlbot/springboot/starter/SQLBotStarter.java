package com.sqlbot.springboot.starter;

import com.sqlbot.springboot.starter.api.auth.AuthService;
import com.sqlbot.springboot.starter.api.user.UserService;
import com.sqlbot.springboot.starter.api.datasource.DataSourceService;
import com.sqlbot.springboot.starter.api.assistant.AssistantService;
import com.sqlbot.springboot.starter.api.aimodel.AiModelService;
import com.sqlbot.springboot.starter.api.terminology.TerminologyService;
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
    
    // 未来可添加其他模块服务
    // @Getter
    // private final ChatService chatService;
    // 等等...

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
}