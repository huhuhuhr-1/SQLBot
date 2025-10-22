package com.sqlbot.springboot.starter.model.response;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 获取数据响应模型（包装结构）
 * 兼容后端新增字段并保持向后兼容
 */
@Data
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true) // 忽略外层未知字段，增强兼容性
public class CommonDataResponse {
    /**
     * 响应状态码，0表示成功
     */
    private Integer code;

    /**
     * 实际数据载荷
     */
    private Map<String, Object> data;

    /**
     * 响应消息
     */
    private String msg;
}
