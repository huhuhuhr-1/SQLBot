package com.sqlbot.springboot.starter.exception;

/**
 * SQLBot客户端异常类
 * 用于表示客户端请求相关的异常情况
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
public class SQLBotClientException extends SQLBotException {
    
    /**
     * 构造客户端异常
     *
     * @param message 异常消息
     */
    public SQLBotClientException(String message) {
        super(message, "CLIENT_ERROR", 400);
    }
    
    /**
     * 构造客户端异常
     *
     * @param message 异常消息
     * @param cause 异常原因
     */
    public SQLBotClientException(String message, Throwable cause) {
        super(message, "CLIENT_ERROR", 400, cause);
    }
    
    /**
     * 构造客户端异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     */
    public SQLBotClientException(String message, String errorCode) {
        super(message, errorCode, 400);
    }
    
    /**
     * 构造客户端异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param cause 异常原因
     */
    public SQLBotClientException(String message, String errorCode, Throwable cause) {
        super(message, errorCode, 400, cause);
    }
}
