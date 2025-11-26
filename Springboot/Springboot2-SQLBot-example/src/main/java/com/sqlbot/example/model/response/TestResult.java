package com.sqlbot.example.model.response;

import lombok.Data;

/**
 * 测试结果响应模型
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class TestResult<T> {
    private boolean success;
    private String message;
    private T data;
    private long timestamp;
    
    public TestResult() {
        this.timestamp = System.currentTimeMillis();
    }
    
    public static <T> TestResult<T> success(T data) {
        TestResult<T> result = new TestResult<>();
        result.setSuccess(true);
        result.setMessage("操作成功");
        result.setData(data);
        return result;
    }
    
    public static <T> TestResult<T> error(String message) {
        TestResult<T> result = new TestResult<>();
        result.setSuccess(false);
        result.setMessage(message);
        return result;
    }
}
