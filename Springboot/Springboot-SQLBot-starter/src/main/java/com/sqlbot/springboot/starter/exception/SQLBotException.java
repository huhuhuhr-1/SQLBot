package com.sqlbot.springboot.starter.exception;

/**
 * SQLBot异常基类
 * 所有SQLBot相关异常的父类，提供统一的异常处理机制
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
public class SQLBotException extends RuntimeException {
    
    /**
     * 错误码
     */
    private final String errorCode;
    
    /**
     * HTTP状态码
     */
    private final int httpStatus;
    
    /**
     * 构造SQLBot异常
     *
     * @param message 异常消息
     */
    public SQLBotException(String message) {
        super(message);
        this.errorCode = "UNKNOWN_ERROR";
        this.httpStatus = 500;
    }
    
    /**
     * 构造SQLBot异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     */
    public SQLBotException(String message, String errorCode) {
        super(message);
        this.errorCode = errorCode;
        this.httpStatus = 500;
    }
    
    /**
     * 构造SQLBot异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param httpStatus HTTP状态码
     */
    public SQLBotException(String message, String errorCode, int httpStatus) {
        super(message);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
    }
    
    /**
     * 构造SQLBot异常
     *
     * @param message 异常消息
     * @param cause 异常原因
     */
    public SQLBotException(String message, Throwable cause) {
        super(message, cause);
        this.errorCode = "UNKNOWN_ERROR";
        this.httpStatus = 500;
    }
    
    /**
     * 构造SQLBot异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param cause 异常原因
     */
    public SQLBotException(String message, String errorCode, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.httpStatus = 500;
    }
    
    /**
     * 构造SQLBot异常
     *
     * @param message 异常消息
     * @param errorCode 错误代码
     * @param httpStatus HTTP状态码
     * @param cause 异常原因
     */
    public SQLBotException(String message, String errorCode, int httpStatus, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
    }
    
    /**
     * 获取错误代码
     *
     * @return 错误代码
     */
    public String getErrorCode() {
        return errorCode;
    }
    
    /**
     * 获取HTTP状态码
     *
     * @return HTTP状态码
     */
    public int getHttpStatus() {
        return httpStatus;
    }
}