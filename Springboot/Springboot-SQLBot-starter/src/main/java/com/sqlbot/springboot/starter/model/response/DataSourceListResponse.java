package com.sqlbot.springboot.starter.model.response;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 数据源列表响应模型
 * 对应API返回的完整响应结构
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
public class DataSourceListResponse {
    
    /**
     * 响应状态码，0表示成功
     */
    private Integer code;
    
    /**
     * 响应数据
     */
    private List<DataSourceResponse> data;
    
    /**
     * 响应消息
     */
    private String msg;
    
    /**
     * 检查响应是否成功
     *
     * @return 是否成功
     */
    @JsonIgnore
    public boolean isSuccess() {
        return code != null && code == 0;
    }
    
    /**
     * 获取数据源列表（便捷方法）
     *
     * @return 数据源列表
     */
    @JsonIgnore
    public List<DataSourceResponse> getDataSources() {
        return data;
    }
}
