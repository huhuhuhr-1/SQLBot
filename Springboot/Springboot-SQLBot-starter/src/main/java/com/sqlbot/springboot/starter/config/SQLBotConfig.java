package com.sqlbot.springboot.starter.config;

import com.sqlbot.springboot.starter.SQLBotProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import javax.annotation.PostConstruct;

/**
 * SQLBot配置类
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
@Configuration
@EnableConfigurationProperties(SQLBotProperties.class)
public class SQLBotConfig {
    
    private final SQLBotProperties properties;
    
    /**
     * 构造SQLBot配置
     *
     * @param properties SQLBot配置属性
     */
    public SQLBotConfig(SQLBotProperties properties) {
        this.properties = properties;
    }
    
    /**
     * 初始化配置
     */
    @PostConstruct
    public void init() {
        log.info("SQLBot Starter 配置初始化完成");
        log.info("服务器地址: {}", properties.getUrl());
        log.info("启用状态: {}", properties.isEnabled());
        log.info("连接超时: {}ms", properties.getConnectionTimeout());
        log.info("读取超时: {}ms", properties.getReadTimeout());
        log.info("请求超时: {}ms", properties.getTimeout());
        log.info("最大重试次数: {}", properties.getMaxRetries());
        
        // 验证配置
        validateConfiguration();
    }
    
    /**
     * 验证配置参数
     */
    private void validateConfiguration() {
        if (properties.getUrl() == null || properties.getUrl().trim().isEmpty()) {
            throw new IllegalArgumentException("SQLBot服务器地址不能为空");
        }
        
        if (properties.getTimeout() <= 0) {
            throw new IllegalArgumentException("超时时间必须大于0");
        }
        
        if (properties.getConnectionTimeout() <= 0) {
            throw new IllegalArgumentException("连接超时时间必须大于0");
        }
        
        if (properties.getReadTimeout() <= 0) {
            throw new IllegalArgumentException("读取超时时间必须大于0");
        }
        
        if (properties.getMaxRetries() < 0) {
            throw new IllegalArgumentException("最大重试次数不能小于0");
        }
        
        log.debug("SQLBot配置验证通过");
    }
}

