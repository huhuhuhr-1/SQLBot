package com.sqlbot.springboot.starter;

import com.sqlbot.springboot.starter.constant.SQLBotConstants;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;

/**
 * SQLBot配置属性类
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@ConfigurationProperties(prefix = SQLBotConstants.CONFIG_PREFIX)
public class SQLBotProperties {
    
    /**
     * SQLBot服务器地址
     */
    @NotBlank(message = "SQLBot服务器地址不能为空")
    private String url = SQLBotConstants.DefaultValues.DEFAULT_URL;
    
    /**
     * 用户名（可选，也可在运行时通过API指定）
     */
    private String username;
    
    /**
     * 密码（可选，也可在运行时通过API指定）
     */
    private String password;
    
    /**
     * 请求超时时间（毫秒）
     */
    @Min(value = 1000, message = "请求超时时间不能小于1000毫秒")
    private int timeout = SQLBotConstants.DefaultValues.DEFAULT_TIMEOUT;
    
    /**
     * 最大重试次数
     */
    @Min(value = 0, message = "最大重试次数不能小于0")
    private int maxRetries = SQLBotConstants.DefaultValues.DEFAULT_MAX_RETRIES;
    
    /**
     * 连接超时时间（毫秒）
     */
    @Min(value = 1000, message = "连接超时时间不能小于1000毫秒")
    private int connectionTimeout = SQLBotConstants.DefaultValues.DEFAULT_CONNECTION_TIMEOUT;
    
    /**
     * 读取超时时间（毫秒）
     */
    @Min(value = 1000, message = "读取超时时间不能小于1000毫秒")
    private int readTimeout = SQLBotConstants.DefaultValues.DEFAULT_READ_TIMEOUT;
    
    /**
     * 是否启用SQLBot功能
     */
    private boolean enabled = SQLBotConstants.DefaultValues.DEFAULT_ENABLED;
    
    /**
     * OkHttp相关配置
     */
    private OkHttpConfig okhttp = new OkHttpConfig();
    
    /**
     * 调试模式
     */
    private boolean debug = false;
    
    /**
     * OkHttp配置类
     */
    @Data
    public static class OkHttpConfig {
        /**
         * 最大空闲连接数
         */
        @Min(value = 1, message = "最大空闲连接数不能小于1")
        private int maxIdleConnections = 5;
        
        /**
         * 连接保活时间（秒）
         */
        @Min(value = 30, message = "连接保活时间不能小于30秒")
        private long keepAliveDuration = 300;
        
        /**
         * 连接池大小
         */
        @Min(value = 1, message = "连接池大小不能小于1")
        private int connectionPoolSize = 10;
        
        /**
         * 是否启用HTTP日志
         */
        private boolean enableLogging = false;
        
        /**
         * HTTP日志级别（NONE, BASIC, HEADERS, BODY）
         */
        private String logLevel = "BASIC";
    }
    
    /**
     * 获取完整的认证信息
     * 
     * @return 是否配置了完整的认证信息
     */
    public boolean hasCompleteCredentials() {
        return username != null && !username.trim().isEmpty() 
            && password != null && !password.trim().isEmpty();
    }
    
    /**
     * 验证配置是否有效
     * 
     * @throws IllegalArgumentException 当配置无效时抛出异常
     */
    public void validate() {
        if (url == null || url.trim().isEmpty()) {
            throw new IllegalArgumentException("SQLBot服务器地址不能为空");
        }
        
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            throw new IllegalArgumentException("SQLBot服务器地址必须以http://或https://开头");
        }
        
        if (timeout <= 0) {
            throw new IllegalArgumentException("请求超时时间必须大于0");
        }
        
        if (connectionTimeout <= 0) {
            throw new IllegalArgumentException("连接超时时间必须大于0");
        }
        
        if (readTimeout <= 0) {
            throw new IllegalArgumentException("读取超时时间必须大于0");
        }
        
        if (maxRetries < 0) {
            throw new IllegalArgumentException("最大重试次数不能小于0");
        }
        
        // 验证OkHttp配置
        if (okhttp != null) {
            if (okhttp.getMaxIdleConnections() <= 0) {
                throw new IllegalArgumentException("最大空闲连接数必须大于0");
            }
            
            if (okhttp.getKeepAliveDuration() <= 0) {
                throw new IllegalArgumentException("连接保活时间必须大于0");
            }
            
            if (okhttp.getConnectionPoolSize() <= 0) {
                throw new IllegalArgumentException("连接池大小必须大于0");
            }
        }
    }
    
    /**
     * 获取格式化的配置信息
     * 
     * @return 配置信息字符串
     */
    public String getConfigSummary() {
        return String.format(
            "SQLBot配置摘要: url=%s, enabled=%s, timeout=%dms, connectionTimeout=%dms, " +
            "readTimeout=%dms, maxRetries=%d, hasCredentials=%s",
            url, enabled, timeout, connectionTimeout, readTimeout, maxRetries, hasCompleteCredentials()
        );
    }
}