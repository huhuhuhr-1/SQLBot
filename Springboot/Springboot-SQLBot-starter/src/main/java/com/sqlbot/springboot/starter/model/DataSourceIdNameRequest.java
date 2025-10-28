package com.sqlbot.springboot.starter.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

/**
 * 数据源ID或名称请求模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class DataSourceIdNameRequest {

    /**
     * 数据源名称
     */
    @JsonProperty("name")
    private String name;

    /**
     * 数据源ID
     */
    @JsonProperty("id")
    private Integer id;
}