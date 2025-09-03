package com.sqlbot.springboot.starter.exception;

/**
 * SQLBot认证异常类
 * 用于表示认证和授权相关的异常情况
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
public class SQLBotAuthenticationException extends SQLBotException {
    
    /**
     * 构造认证异常
     *
     * @param message 异常消息
     */
    public SQLBotAuthenticationException(String message) {
        super(message, "AUTHENTICATION_ERROR", 401);
    }
    
    /**
     * 构造认证异常
     *
     * @param message 异常消息
     * @param cause 异常原因
     */
    public SQLBotAuthenticationException(String message, Throwable cause) {
        super(message, "AUTHENTICATION_ERROR", 401, cause);
    }
    
    /**
     * 构造认证异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     */
    public SQLBotAuthenticationException(String message, String errorCode) {
        super(message, errorCode, 401);
    }
    
    /**
     * 构造认证异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param cause 异常原因
     */
    public SQLBotAuthenticationException(String message, String errorCode, Throwable cause) {
        super(message, errorCode, 401, cause);
    }
}
