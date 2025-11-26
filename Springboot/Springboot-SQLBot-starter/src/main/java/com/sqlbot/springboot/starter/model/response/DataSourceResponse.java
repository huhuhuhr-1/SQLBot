package com.sqlbot.springboot.starter.model.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 数据源响应模型
 * 对应API返回的数据源信息
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DataSourceResponse {
    /**
     * 数据源ID
     */
    private Integer id;
    
    /**
     * 数据源名称
     */
    private String name;
    
    /**
     * 数据源类型代码（如：pg, mysql等）
     */
    private String type;
    
    /**
     * 数据源类型名称（如：PostgreSQL, MySQL等）
     */
    @JsonProperty("type_name")
    private String typeName;
    
    /**
     * 数据源描述
     */
    private String description;
    
    /**
     * 数据源状态
     */
    private String status;
    
    /**
     * 创建时间
     */
    @JsonProperty("create_time")
    private String createTime;
    
    /**
     * 更新时间
     */
    @JsonProperty("update_time")
    private String updateTime;
    
    /**
     * 数据源编号（如：1/6）
     */
    private String num;
    
    /**
     * 组织ID
     */
    private Integer oid;
    
    /**
     * 配置信息（加密）
     */
    private String configuration;
    
    /**
     * 创建者ID
     */
    @JsonProperty("create_by")
    private Integer createBy;
}
