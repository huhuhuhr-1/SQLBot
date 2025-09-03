package com.sqlbot.springboot.starter.model.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 通用API响应包装类
 * 用于包装所有API的响应数据
 *
 * @param <T> 响应数据类型
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {
    /**
     * 响应状态码，0表示成功
     */
    private Integer code;
    
    /**
     * 响应数据
     */
    private T data;
    
    /**
     * 响应消息
     */
    private String msg;
    
    /**
     * 检查响应是否成功
     *
     * @return 是否成功
     */
    public boolean isSuccess() {
        return code != null && code == 0;
    }
    
    /**
     * 获取响应数据，如果失败则抛出异常
     *
     * @return 响应数据
     * @throws RuntimeException 当响应失败时抛出异常
     */
    public T getDataOrThrow() {
        if (!isSuccess()) {
            throw new RuntimeException("API调用失败: " + msg + " (code: " + code + ")");
        }
        return data;
    }
}
