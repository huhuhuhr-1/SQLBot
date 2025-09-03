package com.sqlbot.springboot.starter.exception;

/**
 * SQLBot API异常类
 * 用于表示API调用过程中的各种异常情况
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
public class SQLBotApiException extends SQLBotException {
    
    /**
     * 构造API异常
     *
     * @param message 异常消息
     */
    public SQLBotApiException(String message) {
        super(message, "API_ERROR", 500);
    }
    
    /**
     * 构造API异常
     *
     * @param message 异常消息
     * @param cause 异常原因
     */
    public SQLBotApiException(String message, Throwable cause) {
        super(message, "API_ERROR", 500, cause);
    }
    
    /**
     * 构造API异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     */
    public SQLBotApiException(String message, String errorCode) {
        super(message, errorCode, 500);
    }
    
    /**
     * 构造API异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param cause 异常原因
     */
    public SQLBotApiException(String message, String errorCode, Throwable cause) {
        super(message, errorCode, 500, cause);
    }
    
    /**
     * 构造API异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param httpStatus HTTP状态码
     */
    public SQLBotApiException(String message, String errorCode, int httpStatus) {
        super(message, errorCode, httpStatus);
    }
    
    /**
     * 构造API异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param httpStatus HTTP状态码
     * @param cause 异常原因
     */
    public SQLBotApiException(String message, String errorCode, int httpStatus, Throwable cause) {
        super(message, errorCode, httpStatus, cause);
    }
}
