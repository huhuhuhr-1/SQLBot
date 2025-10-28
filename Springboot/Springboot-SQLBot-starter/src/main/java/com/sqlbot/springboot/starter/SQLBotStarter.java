package com.sqlbot.springboot.starter;

import com.sqlbot.springboot.starter.api.auth.AuthService;
import com.sqlbot.springboot.starter.api.user.UserService;
import com.sqlbot.springboot.starter.api.datasource.DataSourceService;
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
    
    // 未来可添加其他模块服务
    // @Getter
    // private final ChatService chatService;
    // @Getter
    // private final AssistantService assistantService;
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
}