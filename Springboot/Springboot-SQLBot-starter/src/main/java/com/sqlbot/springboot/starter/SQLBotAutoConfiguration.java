package com.sqlbot.springboot.starter;

import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * SQLBot自动配置类
 * 提供SQLBot相关的Bean自动配置，包括SQLBotClient和SQLBotTemplate
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Configuration
@EnableConfigurationProperties(SQLBotProperties.class)
@ConditionalOnProperty(prefix = "sqlbot", name = "enabled", havingValue = "true", matchIfMissing = true)
@ConditionalOnClass(okhttp3.OkHttpClient.class)
public class SQLBotAutoConfiguration {

    /**
     * 创建SQLBot客户端Bean
     * 当容器中不存在SQLBotClient类型的Bean时自动创建
     *
     * @param properties SQLBot配置属性
     * @return SQLBot客户端实例
     */
    @Bean
    @ConditionalOnMissingBean
    public SQLBotClient sqlBotClient(SQLBotProperties properties) {
        return new SQLBotClient(properties);
    }

    /**
     * 创建SQLBot模板Bean
     * 当容器中不存在SQLBotTemplate类型的Bean时自动创建
     *
     * @param client SQLBot客户端实例
     * @return SQLBot模板实例
     */
    @Bean
    @ConditionalOnMissingBean
    public SQLBotTemplate sqlBotTemplate(SQLBotClient client) {
        return new SQLBotTemplate(client);
    }
}